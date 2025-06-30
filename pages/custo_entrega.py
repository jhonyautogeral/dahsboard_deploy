import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
import calendar

# Configuração
pd.set_option('future.no_silent_downcasting', True)

# Dicionário de Lojas
# Comentado CD pois é um out lier e atrapalha a visualização dos graficos

LOJA_DICT = { # 1: 'CD', 
    2: 'SALTO', 3: 'SOROCABA', 4: 'CAETANO', 5: 'INDAIATUBA',
    6: 'PORTO FELIZ', 7: 'ÉDEN', 8: 'JACARE', 9: 'TATUI', 10: 'BOITUVA',
    11: 'PIEDADE', 12: 'OTAVIANO', 13: 'CERQUILHO'
}

# -----------------------
# 1. Conexão e Dados
# -----------------------
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

def obter_entregas(engine, inicio_str, fim_str, tipo_entrega="TODAS"):
    """Obtém dados de entregas baseado no tipo selecionado."""
    
    if tipo_entrega == "ENTREGA PARA CLIENTES":
        query = f"""
        SELECT E.CADASTRO, E.LOJA, C.NOME AS CLIENTE, SUM(EI.ITEM) AS TOTAL_ENTREGAS
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN entregador N ON E.ENTREGADOR_CODIGO = N.CODIGO
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}' AND C.NOME NOT LIKE '%%AUTO GERAL AUTO%%'
        GROUP BY E.CADASTRO, E.LOJA
        """
    elif tipo_entrega == "ROTA":
        # Para ROTA, fazemos consulta especial com subtração
        query_todas = f"""
        SELECT E.CADASTRO, E.LOJA, 'TODAS' AS TIPO, SUM(EI.ITEM) AS TOTAL_ENTREGAS
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN entregador N ON E.ENTREGADOR_CODIGO = N.CODIGO
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}'
        GROUP BY E.CADASTRO, E.LOJA
        """
        
        query_clientes = f"""
        SELECT E.CADASTRO, E.LOJA, 'CLIENTES' AS TIPO, SUM(EI.ITEM) AS TOTAL_ENTREGAS
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN entregador N ON E.ENTREGADOR_CODIGO = N.CODIGO
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}' AND C.NOME NOT LIKE '%%AUTO GERAL AUTO%%'
        GROUP BY E.CADASTRO, E.LOJA
        """
        
        try:
            df_todas = pd.read_sql(query_todas, engine)
            df_clientes = pd.read_sql(query_clientes, engine)
            
            if not df_todas.empty and not df_clientes.empty:
                # Merge e subtração para calcular ROTA
                df_merged = df_todas.merge(df_clientes, on=['CADASTRO', 'LOJA'], suffixes=('_todas', '_clientes'))
                df_merged['TOTAL_ENTREGAS'] = df_merged['TOTAL_ENTREGAS_todas'] - df_merged['TOTAL_ENTREGAS_clientes']
                df = df_merged[['CADASTRO', 'LOJA', 'TOTAL_ENTREGAS']].copy()
                df["DATA"] = pd.to_datetime(df["CADASTRO"]).dt.date
                df['LOJA_NOME'] = df['LOJA'].map(LOJA_DICT)
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Erro ao obter entregas ROTA: {e}")
            return pd.DataFrame()
    
    else:  # TODAS ENTREGAS
        query = f"""
        SELECT E.CADASTRO, E.LOJA, C.NOME AS CLIENTE, SUM(EI.ITEM) AS TOTAL_ENTREGAS
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN entregador N ON E.ENTREGADOR_CODIGO = N.CODIGO
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}'
        GROUP BY E.CADASTRO, E.LOJA
        """
    
    try:
        df = pd.read_sql(query, engine)
        if not df.empty:
            df["DATA"] = pd.to_datetime(df["CADASTRO"]).dt.date
            df['LOJA_NOME'] = df['LOJA'].map(LOJA_DICT)
        return df
    except Exception as e:
        st.error(f"Erro ao obter entregas: {e}")
        return pd.DataFrame()

def obter_despesas(inicio_str, fim_str):
    """Obtém dados de todas as APIs de despesas."""
    apis_config = [
        ("api_custo_cobli", "cobli_api", "DATA_REFERENCIA", "VALOR_TOTAL"),
        ("api_custo_combustivel", "preparar_dados", "CADASTRO", "VALOR_TOTAL"),
        ("api_custo_motoboy_tercerizado", "calc_custo_motobiy_tercerizado", "EMISSAO", "VALOR_TOTAL"),
        ("api_custo_pedagio", "calcula_custo_pedagio", "DATA_UTILIZACAO", "CUSTO_TOTAL")
    ]
    
    manutencao_apis = [
        ("api_custo_manutencao_frota", "pecas_nfe", "EMISSAO", "VALOR_TOTAL"),
        ("api_custo_manutencao_frota", "pecas_pedidos", "EMISSAO", "VALOR_TOTAL"),
        ("api_custo_manutencao_frota", "mao_obra_NF", "EMISSAO", "VALOR_TOTAL"),
        ("api_custo_manutencao_frota", "mao_obra_despesas", "EMISSAO", "VALOR_TOTAL")
    ]
    
    valid_dfs = []
    
    # APIs principais
    for modulo, funcao, col_data, col_valor in apis_config:
        try:
            exec(f"from {modulo} import {funcao}")
            df = eval(f"{funcao}('{inicio_str}', '{fim_str}')")
            if df is not None and not df.empty:
                df = processar_api_data(df, col_data, col_valor, funcao)
                valid_dfs.append(df)
        except Exception as e:
            st.warning(f"⚠️ {funcao}: {e}")
    
    # APIs de manutenção
    for modulo, funcao, col_data, col_valor in manutencao_apis:
        try:
            exec(f"from {modulo} import {funcao}")
            df = eval(f"{funcao}('{inicio_str}', '{fim_str}')")
            if df is not None and not df.empty:
                df = processar_api_data(df, col_data, col_valor, funcao)
                valid_dfs.append(df)
        except Exception as e:
            st.warning(f"⚠️ {funcao}: {e}")
    
    if not valid_dfs:
        return pd.DataFrame()
    
    df_final = pd.concat(valid_dfs, ignore_index=True)
    df_final = df_final.dropna(subset=['DATA', 'LOJA', 'VALOR'])
    df_final['LOJA'] = df_final['LOJA'].astype(int)
    df_final['LOJA_NOME'] = df_final['LOJA'].map(LOJA_DICT)
    return df_final

def processar_api_data(df, col_data, col_valor, nome_api):
    """Processa dados de uma API específica."""
    if col_data in df.columns:
        if isinstance(df[col_data].dtype, pd.PeriodDtype):
            df["DATA"] = df[col_data].dt.to_timestamp().dt.date
        else:
            df["DATA"] = pd.to_datetime(df[col_data]).dt.date
    
    if col_valor in df.columns:
        df["VALOR"] = df[col_valor]
    elif "VALOR_TOTAL" in df.columns:
        df["VALOR"] = df["VALOR_TOTAL"]
    
    if "LOJA_VEICULO" in df.columns:
        df["LOJA"] = df["LOJA_VEICULO"]
    
    return df[['DATA', 'LOJA', 'VALOR']].copy()

# -----------------------
# 2. Processamento e Visualização
# -----------------------
def consolidar_dados(df_despesas, df_entregas):
    """junta dados de despesas e entregas."""
    resultado = {}
    
    if not df_despesas.empty:
        resultado['despesas'] = df_despesas.groupby('LOJA_NOME')['VALOR'].sum()
    
    if not df_entregas.empty:
        resultado['entregas'] = df_entregas.groupby('LOJA_NOME')['TOTAL_ENTREGAS'].sum()
    
    if 'despesas' in resultado and 'entregas' in resultado:
        df_consolidado = pd.DataFrame({
            'TOTAL_DESPESAS': resultado['despesas'],
            'TOTAL_ENTREGAS': resultado['entregas']
        }).fillna(0)
        
        df_consolidado['CUSTO_POR_ENTREGA'] = np.where(
            df_consolidado['TOTAL_ENTREGAS'] > 0,
            df_consolidado['TOTAL_DESPESAS'] / df_consolidado['TOTAL_ENTREGAS'],
            0
        )
        resultado['consolidado'] = df_consolidado
    
    return resultado

def criar_grafico_otimizado(dados, titulo, y_label):
    """Cria gráfico de barras otimizado."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    if isinstance(dados, pd.Series) and not dados.empty:
        if 'Entrega' in titulo and 'Quantidade' in y_label:
            colors = ['red' if x == dados.min() else 'green' if x == dados.max() else 'lightblue' for x in dados.values]
        elif 'Custo' in titulo or 'R$' in y_label:
            colors = ['green' if x == dados.min() else 'red' if x == dados.max() else 'lightblue' for x in dados.values]
        else:
            colors = ['lightblue'] * len(dados)
        
        bars = ax.bar(dados.index, dados.values, color=colors)
        
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

def exibir_analise_unificada(dados, tipo_analise):
    """Exibe análise unificada."""
    st.header(tipo_analise)
    
    if tipo_analise == "📈 Custo das Despesas" and 'despesas' in dados:
        col1, col2, col3 = st.columns(3)
        despesas = dados['despesas']
        with col1:
            st.metric("💰 Total", f"R$ {despesas.sum():,.2f}")
        with col2:
            st.metric("📊 Média", f"R$ {despesas.mean():,.2f}")
        with col3:
            st.metric("🏆 Maior", despesas.idxmax(), f"R$ {despesas.max():,.2f}")
        
        fig = criar_grafico_otimizado(despesas, "Total de Despesas por Loja", "Valor (R$)")
        st.pyplot(fig)
        st.dataframe(despesas.to_frame().style.format("R$ {:.2f}"), use_container_width=True)
    
    elif tipo_analise == "🚚 Custo de Entrega" and 'consolidado' in dados:
        df_cons = dados['consolidado']
        df_valido = df_cons[df_cons['CUSTO_POR_ENTREGA'] > 0]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            custo_medio = df_cons['TOTAL_DESPESAS'].sum() / df_cons['TOTAL_ENTREGAS'].sum()
            st.metric("🎯 Custo Médio", f"R$ {custo_medio:.2f}")
        with col2:
            if not df_valido.empty:
                melhor = df_valido['CUSTO_POR_ENTREGA'].idxmin()
                st.metric("⭐ Melhor", melhor, f"R$ {df_valido.loc[melhor, 'CUSTO_POR_ENTREGA']:.2f}")
        with col3:
            if not df_valido.empty:
                pior = df_valido['CUSTO_POR_ENTREGA'].idxmax()
                st.metric("⚠️ Pior", pior, f"R$ {df_valido.loc[pior, 'CUSTO_POR_ENTREGA']:.2f}")
        
        df_custo = df_cons[df_cons['CUSTO_POR_ENTREGA'] > 0]['CUSTO_POR_ENTREGA'].sort_values()
        if not df_custo.empty:
            fig = criar_grafico_otimizado(df_custo, "Custo por Entrega - Ranking", "Custo (R$)")
            st.pyplot(fig)
            st.dataframe(df_cons.style.format({'TOTAL_DESPESAS': 'R$ {:.2f}', 'TOTAL_ENTREGAS': '{:.0f}', 'CUSTO_POR_ENTREGA': 'R$ {:.2f}'}), use_container_width=True)

def configurar_periodo():
    """Configura período via sidebar."""
    st.sidebar.subheader("📅 Período")
    tipo_periodo = st.sidebar.radio("Tipo:", ["Ano", "Meses", "Personalizado"])
    
    if tipo_periodo == "Ano":
        ano = st.sidebar.selectbox("Ano:", range(datetime.now().year, datetime.now().year - 5, -1))
        return f"{ano}-01-01 00:00:00", f"{ano}-12-31 23:59:59"
    elif tipo_periodo == "Meses":
        ano = st.sidebar.selectbox("Ano:", range(datetime.now().year, datetime.now().year - 5, -1))
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
# 4. Interface Principal
# -----------------------
def main():
    """Função principal."""
    st.set_page_config(page_title="Sistema de Custo de Entrega", layout="wide")
    st.title("📊 Sistema de Análise de Custo de Entrega")
    
    # Sidebar - Configurações
    st.sidebar.header("⚙️ Configurações")
    
    # Novo: Tipo de Entrega
    tipo_entrega = st.sidebar.selectbox(
        "Tipo de Entrega:",
        ["TODAS ENTREGAS", "ENTREGA PARA CLIENTES", "ROTA"]
    )
    
    tipo_analise = st.sidebar.selectbox(
        "Tipo de Análise:",
        ["📈 Custo das Despesas", "🚚 Custo de Entrega"]
    )
    
    inicio_str, fim_str = configurar_periodo()
    
    if st.sidebar.button("🔄 Processar", type="primary"):
        st.info(f"📅 Período: {inicio_str.split()[0]} até {fim_str.split()[0]} | Tipo: {tipo_entrega}")
        
        with st.spinner("Carregando dados..."):
            engine = criar_conexao()
            df_despesas = obter_despesas(inicio_str, fim_str)
            df_entregas = obter_entregas(engine, inicio_str, fim_str, tipo_entrega)
        
        if df_despesas.empty and df_entregas.empty:
            st.error("❌ Nenhum dado encontrado")
            return
        
        dados = consolidar_dados(df_despesas, df_entregas)
        
        if tipo_analise == "📈 Custo das Despesas" and 'despesas' not in dados:
            st.warning("⚠️ Sem dados de despesas")
            return
        elif tipo_analise == "🚚 Custo de Entrega" and 'consolidado' not in dados:
            st.warning("⚠️ Sem dados suficientes para custo de entrega")
            return
        
        exibir_analise_unificada(dados, tipo_analise)
    
    # Informações
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### ℹ️ Tipos de Entrega
    - **TODAS:** Todas as entregas
    - **CLIENTES:** Sem AUTO GERAL AUTO
    - **ROTA:** TODAS - CLIENTES
    
    ### APIs Incluídas
     Cobli |  Manutenção |  Motoboy |  Combustível |  Pedágio
    """)

if __name__ == "__main__":
    main()