import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
import calendar

st.set_page_config(page_title="Sistema de Custo de Entrega", layout="wide")

if st.sidebar.button("Voltar"):
        st.switch_page("app.py")

# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página

# Configuração
pd.set_option('future.no_silent_downcasting', True)

def obter_lojas_disponiveis(engine):
    """Obtém todas as lojas disponíveis com custos de FROTA"""
    from sqlalchemy import text
    query = "SELECT DISTINCT COMP_LOJA FROM comp_rate_ativ WHERE DSCR LIKE :frota_pattern ORDER BY COMP_LOJA"
    result = pd.read_sql_query(text(query), engine, params={'frota_pattern': '%FROTA%'})
    return result['COMP_LOJA'].tolist()

def obter_loja_dict(engine):
    """Cria dicionário de lojas dinamicamente"""
    lojas = obter_lojas_disponiveis(engine)
    return {loja: f'LOJA_{loja}' for loja in lojas}

# -----------------------
# Conexão e Dados
# -----------------------
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

def obter_entregas(engine, inicio_str, fim_str, tipo_entrega="TODAS", loja_dict=None):
    """Obtém dados de entregas baseado no tipo selecionado."""
    
    if tipo_entrega == "ENTREGA PARA CLIENTES":
        query = f"""
        SELECT E.CADASTRO, E.LOJA, SUM(EI.ITEM) AS TOTAL_ENTREGAS
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}' AND C.NOME NOT LIKE '%%AUTO GERAL AUTO%%'
        GROUP BY E.CADASTRO, E.LOJA
        """
    elif tipo_entrega == "ROTA":
        query_todas = f"""
        SELECT E.CADASTRO, E.LOJA, SUM(EI.ITEM) AS TOTAL_ENTREGAS
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}'
        GROUP BY E.CADASTRO, E.LOJA
        """
        
        query_clientes = f"""
        SELECT E.CADASTRO, E.LOJA, SUM(EI.ITEM) AS TOTAL_ENTREGAS
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}' AND C.NOME NOT LIKE '%%AUTO GERAL AUTO%%'
        GROUP BY E.CADASTRO, E.LOJA
        """
        
        try:
            df_todas = pd.read_sql(query_todas, engine)
            df_clientes = pd.read_sql(query_clientes, engine)
            
            if not df_todas.empty and not df_clientes.empty:
                df_merged = df_todas.merge(df_clientes, on=['CADASTRO', 'LOJA'], suffixes=('_todas', '_clientes'))
                df_merged['TOTAL_ENTREGAS'] = df_merged['TOTAL_ENTREGAS_todas'] - df_merged['TOTAL_ENTREGAS_clientes']
                df = df_merged[['CADASTRO', 'LOJA', 'TOTAL_ENTREGAS']].copy()
                df["DATA"] = pd.to_datetime(df["CADASTRO"]).dt.date
                if loja_dict:
                    df['LOJA_NOME'] = df['LOJA'].map(loja_dict)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Erro ao obter entregas ROTA: {e}")
            return pd.DataFrame()
    
    else:  # TODAS ENTREGAS
        query = f"""
        SELECT E.CADASTRO, E.LOJA, SUM(EI.ITEM) AS TOTAL_ENTREGAS
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}'
        GROUP BY E.CADASTRO, E.LOJA
        """
    
    try:
        df = pd.read_sql(query, engine)
        if not df.empty:
            df["DATA"] = pd.to_datetime(df["CADASTRO"]).dt.date
            if loja_dict:
                df['LOJA_NOME'] = df['LOJA'].map(loja_dict)
        return df
    except Exception as e:
        st.error(f"Erro ao obter entregas: {e}")
        return pd.DataFrame()

def consulta_custos_totais(data_inicio, data_fim, engine, lojas_selecionadas=None, descricoes_selecionadas=None):
    """Consulta custos totais entre datas com filtros - apenas custos de FROTA"""
    where_conditions = [
        f"a.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'"
    ]
    
    # Adicionar filtro FROTA usando text() para escape adequado
    from sqlalchemy import text
    
    if lojas_selecionadas:
        lojas_str = ','.join(map(str, lojas_selecionadas))
        where_conditions.append(f"c.COMP_LOJA IN ({lojas_str})")
    
    if descricoes_selecionadas:
        descricoes_str = "','".join(descricoes_selecionadas)
        where_conditions.append(f"c.DSCR IN ('{descricoes_str}')")
    
    query = f"""
    SELECT
        c.COMP_LOJA AS LOJA,
        c.COMP_CODI AS COMPRA,
        c.CADA_ATIV_ID AS CADASTRO_VEICULO,
        c.VALR_RATE AS VALOR_UNITARIO_CUSTO,
        (c.VALR_RATE / a.VALOR_TOTAL_NOTA) AS PERC,
        c.DSCR AS DESCRICAO,
        a.CADASTRO,
        a.VALOR_TOTAL_NOTA
    FROM comp_rate_ativ c
    LEFT JOIN compras_dbf a ON c.COMP_CODI = a.COMPRA
    AND c.COMP_LOJA = a.LOJA
    WHERE {' AND '.join(where_conditions)} AND c.DSCR LIKE :frota_pattern
    ORDER BY a.CADASTRO, c.COMP_LOJA
    """
    
    return pd.read_sql_query(text(query), engine, params={'frota_pattern': '%FROTA%'})

def obter_custos_por_tipo(engine, inicio_str, fim_str, tipo_entrega, loja_dict=None):
    """Obtém custos baseado no tipo de entrega"""
    try:
        df_custos = consulta_custos_totais(inicio_str, fim_str, engine)
        if df_custos.empty:
            return pd.DataFrame()
        
        # Processar dados
        df_custos['CADASTRO'] = pd.to_datetime(df_custos['CADASTRO'])
        df_custos['DATA'] = df_custos['CADASTRO'].dt.date
        if loja_dict:
            df_custos['LOJA_NOME'] = df_custos['LOJA'].map(loja_dict)
        
        # Agrupar por loja
        resumo_custos = df_custos.groupby(['LOJA', 'LOJA_NOME'])['VALOR_UNITARIO_CUSTO'].sum().reset_index()
        resumo_custos['TIPO_ENTREGA'] = tipo_entrega
        
        return resumo_custos
    except Exception as e:
        st.error(f"Erro ao obter custos {tipo_entrega}: {e}")
        return pd.DataFrame()

# -----------------------
# Visualização
# -----------------------
def criar_grafico_otimizado(dados, titulo, y_label):
    """Cria gráfico de barras otimizado"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    if not dados.empty:
        # Filtrar valores > 0
        dados_filtrados = dados[dados > 0]
        
        if not dados_filtrados.empty:
            # Cores baseadas nos valores
            cores = ['green' if x == dados_filtrados.min() else 'red' if x == dados_filtrados.max() else 'lightblue' 
                    for x in dados_filtrados.values]
            
            bars = ax.bar(dados_filtrados.index, dados_filtrados.values, color=cores)
            
            # Adicionar valores nas barras
            for bar in bars:
                altura = bar.get_height()
                if altura > 0:
                    texto = f'R$ {altura:,.0f}' if 'R$' in y_label else f'{altura:,.0f}'
                    ax.text(bar.get_x() + bar.get_width()/2, altura + altura*0.01,
                           texto, ha='center', va='bottom', fontsize=9)
    
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_xlabel("Lojas")
    ax.set_ylabel(y_label)
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    return fig

def calcular_custo_por_entrega(df_custos, df_entregas):
    """Calcula custo por entrega"""
    if df_custos.empty or df_entregas.empty:
        return pd.DataFrame()
    
    # Preparar dados
    custos_agrupados = df_custos.groupby('LOJA_NOME')['VALOR_UNITARIO_CUSTO'].sum()
    entregas_agrupadas = df_entregas.groupby('LOJA_NOME')['TOTAL_ENTREGAS'].sum()
    
    # Combinar dados
    df_resultado = pd.DataFrame({
        'CUSTOS': custos_agrupados,
        'ENTREGAS': entregas_agrupadas
    }).fillna(0)
    
    # Calcular custo por entrega
    df_resultado['CUSTO_POR_ENTREGA'] = np.where(
        df_resultado['ENTREGAS'] > 0,
        df_resultado['CUSTOS'] / df_resultado['ENTREGAS'],
        0
    )
    
    return df_resultado

def configurar_periodo():
    """Configura período via sidebar"""
    st.sidebar.subheader("📅 Período")
    tipo_periodo = st.sidebar.radio("Tipo:", ["Mês Atual", "Meses", "Personalizado"])
    
    if tipo_periodo == "Mês Atual":
        hoje = datetime.now()
        return f"{hoje.year}-{hoje.month:02d}-01 00:00:00", f"{hoje.year}-{hoje.month:02d}-{calendar.monthrange(hoje.year, hoje.month)[1]} 23:59:59"
    elif tipo_periodo == "Meses":
        ano = st.sidebar.selectbox("Ano:", range(datetime.now().year, datetime.now().year - 3, -1))
        meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        meses = st.sidebar.multiselect("Meses:", meses_nomes, default=[meses_nomes[datetime.now().month-1]])
        
        if not meses:
            st.warning("Selecione pelo menos um mês")
            st.stop()
        
        nums_meses = [meses_nomes.index(m) + 1 for m in meses]
        mes_min, mes_max = min(nums_meses), max(nums_meses)
        ultimo_dia = calendar.monthrange(ano, mes_max)[1]
        return f"{ano}-{mes_min:02d}-01 00:00:00", f"{ano}-{mes_max:02d}-{ultimo_dia} 23:59:59"
    else:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            inicio = st.date_input("Início:", value=date.today() - timedelta(days=30))
        with col2:
            fim = st.date_input("Fim:", value=date.today())
        
        if inicio > fim:
            st.error("Data início deve ser anterior ao fim")
            st.stop()
        
        return inicio.strftime("%Y-%m-%d 00:00:00"), fim.strftime("%Y-%m-%d 23:59:59")

# -----------------------
# Interface Principal
# -----------------------
def main():
    """Função principal"""
    
    st.title("📊 Sistema de Custo de Entrega - Frota")
    
    # Sidebar
    st.sidebar.header("⚙️ Configurações")
    
    tipo_entrega = st.sidebar.selectbox(
        "Tipo de Entrega:",
        ["TODOS OS TIPOS", "TODAS ENTREGAS", "ENTREGA PARA CLIENTES", "ROTA"]
    )
    
    inicio_str, fim_str = configurar_periodo()
    
    if st.sidebar.button("🔄 Processar", type="primary"):
        st.info(f"📅 Período: {inicio_str.split()[0]} até {fim_str.split()[0]}")
        
        with st.spinner("Carregando dados..."):
            engine = criar_conexao()
            loja_dict = obter_loja_dict(engine)
            
            if tipo_entrega == "TODOS OS TIPOS":
                # Processar todos os tipos
                tipos = ["TODAS ENTREGAS", "ENTREGA PARA CLIENTES", "ROTA"]
                dados_todos = []
                
                for tipo in tipos:
                    df_custos = obter_custos_por_tipo(engine, inicio_str, fim_str, tipo, loja_dict)
                    df_entregas = obter_entregas(engine, inicio_str, fim_str, tipo, loja_dict)
                    
                    if not df_custos.empty and not df_entregas.empty:
                        df_resultado = calcular_custo_por_entrega(df_custos, df_entregas)
                        df_resultado['TIPO'] = tipo
                        dados_todos.append(df_resultado)
                
                if dados_todos:
                    # Exibir tabela comparativa
                    st.header("📊 Comparativo de Custo por Entrega - Todos os Tipos")
                    
                    # Métricas gerais
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_custos = sum([df['CUSTOS'].sum() for df in dados_todos])
                        st.metric("💰 Total Custos", f"R$ {total_custos:,.2f}")
                    with col2:
                        total_entregas = sum([df['ENTREGAS'].sum() for df in dados_todos])
                        st.metric("📦 Total Entregas", f"{total_entregas:,.0f}")
                    with col3:
                        custo_medio_geral = total_custos / total_entregas if total_entregas > 0 else 0
                        st.metric("🎯 Custo Médio Geral", f"R$ {custo_medio_geral:.2f}")
                    
                    # Tabela detalhada
                    for i, df in enumerate(dados_todos):
                        tipo_atual = tipos[i]
                        st.subheader(f"📋 {tipo_atual}")
                        
                        # Filtrar dados válidos
                        df_valido = df[df['CUSTO_POR_ENTREGA'] > 0]
                        
                        if not df_valido.empty:
                            st.dataframe(
                                df_valido.style.format({
                                    'CUSTOS': 'R$ {:.2f}',
                                    'ENTREGAS': '{:.0f}',
                                    'CUSTO_POR_ENTREGA': 'R$ {:.2f}'
                                }),
                                use_container_width=True
                            )
                            
                            # Gráfico para cada tipo
                            custo_por_entrega = df_valido['CUSTO_POR_ENTREGA'].sort_values()
                            fig = criar_grafico_otimizado(
                                custo_por_entrega,
                                f"Custo por Entrega - {tipo_atual}",
                                "Custo por Entrega (R$)"
                            )
                            st.pyplot(fig)
                        else:
                            st.warning(f"Sem dados válidos para {tipo_atual}")
                        
                        st.markdown("---")
                else:
                    st.error("❌ Nenhum dado encontrado para análise")
            
            else:
                # Processar tipo específico
                df_custos = obter_custos_por_tipo(engine, inicio_str, fim_str, tipo_entrega, loja_dict)
                df_entregas = obter_entregas(engine, inicio_str, fim_str, tipo_entrega, loja_dict)
                
                if df_custos.empty or df_entregas.empty:
                    st.error("❌ Nenhum dado encontrado")
                    return
                
                df_resultado = calcular_custo_por_entrega(df_custos, df_entregas)
                
                if df_resultado.empty:
                    st.error("❌ Não foi possível calcular custo por entrega")
                    return
                
                # Exibir análise específica
                st.header(f"📊 Análise de Custo - {tipo_entrega}")
                
                # Métricas
                df_valido = df_resultado[df_resultado['CUSTO_POR_ENTREGA'] > 0]
                
                if not df_valido.empty:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("💰 Total Custos", f"R$ {df_resultado['CUSTOS'].sum():,.2f}")
                    with col2:
                        st.metric("📦 Total Entregas", f"{df_resultado['ENTREGAS'].sum():,.0f}")
                    with col3:
                        custo_medio = df_resultado['CUSTOS'].sum() / df_resultado['ENTREGAS'].sum()
                        st.metric("🎯 Custo Médio", f"R$ {custo_medio:.2f}")
                    with col4:
                        melhor_loja = df_valido['CUSTO_POR_ENTREGA'].idxmin()
                        st.metric("⭐ Melhor Loja", melhor_loja, f"R$ {df_valido.loc[melhor_loja, 'CUSTO_POR_ENTREGA']:.2f}")
                    
                    # Tabela
                    st.subheader("📋 Detalhes por Loja")
                    st.dataframe(
                        df_valido.style.format({
                            'CUSTOS': 'R$ {:.2f}',
                            'ENTREGAS': '{:.0f}',
                            'CUSTO_POR_ENTREGA': 'R$ {:.2f}'
                        }),
                        use_container_width=True
                    )
                    
                    # Gráfico
                    st.subheader("📈 Ranking de Custo por Entrega")
                    custo_ordenado = df_valido['CUSTO_POR_ENTREGA'].sort_values()
                    fig = criar_grafico_otimizado(
                        custo_ordenado,
                        f"Custo por Entrega - {tipo_entrega}",
                        "Custo por Entrega (R$)"
                    )
                    st.pyplot(fig)
                else:
                    st.warning("⚠️ Sem dados válidos para análise")
    
    # Informações
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### ℹ️ Tipos de Entrega
    - **TODAS:** Todas as entregas registradas
    - **CLIENTES:** Entregas para clientes (sem AUTO GERAL AUTO)
    - **ROTA:** Diferença entre TODAS e CLIENTES
    - **TODOS OS TIPOS:** Comparativo entre os 3 tipos
    
    ### 🚛 Custos de Frota
    Análise focada apenas em custos com descrição contendo "FROTA"
    """)

if __name__ == "__main__":
    main()