import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
from datetime import datetime, date

# Configuração da página
st.set_page_config(page_title="Dashboard de Entregas", layout="wide")

if st.sidebar.button("Voltar"):
    st.switch_page("app.py")

# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

# Função de conexão
@st.cache_resource
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

# Função para obter lojas
@st.cache_data
def obter_lojas_disponiveis():
    try:
        engine = criar_conexao()
        query = """
            SELECT DISTINCT E.LOJA 
            FROM expedicao_itens EI 
            LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao 
                AND EI.EXPEDICAO_LOJA = E.LOJA
            WHERE E.LOJA IS NOT NULL
            ORDER BY E.LOJA
        """
        result = pd.read_sql_query(query, engine)
        return result['LOJA'].tolist()
    except:
        return list(range(1, 14))

# Função para executar queries principais
def executar_query(query_tipo, loja_filtro, data_inicio, data_fim):
    engine = criar_conexao()
    
    if query_tipo == "TOTAL ENTREGAS":
        query = f"""
        SELECT E.LOJA, COUNT(EI.ITEM) AS ENTREGA, E.SITUACAO, EI.EXPEDICAO_TIPO,
               N.DESCRICAO AS ENTREGADOR_NOME, C.NOME AS CLIENTE, E.HORA_SAIDA, E.CADASTRO
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN entregador N ON E.ENTREGADOR_CODIGO = N.CODIGO
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO 
               AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'
        {f"AND E.LOJA IN ({','.join(map(str, loja_filtro))})" if loja_filtro else ""}
        GROUP BY E.LOJA, E.SITUACAO, EI.EXPEDICAO_TIPO, N.DESCRICAO, C.NOME, E.HORA_SAIDA, E.CADASTRO
        """
    
    elif query_tipo == "ENTREGAS CLIENTES":
        query = f"""
        SELECT E.LOJA, COUNT(EI.ITEM) AS ENTREGA, E.SITUACAO, EI.EXPEDICAO_TIPO,
               N.DESCRICAO AS ENTREGADOR_NOME, C.NOME AS CLIENTE, E.HORA_SAIDA, E.CADASTRO
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN entregador N ON E.ENTREGADOR_CODIGO = N.CODIGO
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO 
               AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'
        AND C.NOME NOT LIKE 'AUTO GERAL AUTOPECA%%'
        AND C.NOME IS NOT NULL
        {f"AND E.LOJA IN ({','.join(map(str, loja_filtro))})" if loja_filtro else ""}
        GROUP BY E.LOJA, E.SITUACAO, EI.EXPEDICAO_TIPO, N.DESCRICAO, C.NOME, E.HORA_SAIDA, E.CADASTRO
        """
    
    else:  # ENTREGAS ROTA
        query = f"""
        SELECT E.LOJA, COUNT(EI.ITEM) AS ENTREGA, E.SITUACAO, EI.EXPEDICAO_TIPO,
               N.DESCRICAO AS ENTREGADOR_NOME, C.NOME AS CLIENTE, E.HORA_SAIDA, E.CADASTRO
        FROM expedicao_itens EI
        LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN entregador N ON E.ENTREGADOR_CODIGO = N.CODIGO
        LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO 
               AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
        LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
        WHERE E.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'
        AND (C.NOME LIKE 'AUTO GERAL AUTOPECA%%' OR C.NOME IS NULL)
        {f"AND E.LOJA IN ({','.join(map(str, loja_filtro))})" if loja_filtro else ""}
        GROUP BY E.LOJA, E.SITUACAO, EI.EXPEDICAO_TIPO, N.DESCRICAO, C.NOME, E.HORA_SAIDA, E.CADASTRO
        """
    
    return pd.read_sql_query(query, engine)

# Função para obter dados de venda casada
def obter_venda_casada(loja_filtro, data_inicio, data_fim):
    engine = criar_conexao()
    
    query = f"""
    SELECT b.LOJA, DATE_FORMAT(b.cadastro, '%%Y-%%m') as MES_ANO, 
           SUM(CASE WHEN a.COMPRA_PEDIDO IS NOT NULL THEN 1 ELSE 0 END) AS VENDA_CASADA
    FROM romaneios_dbf b
    LEFT JOIN compras_pedidos a ON a.romaneio_codigo = b.ROMANEIO 
        AND a.ROMANEIO_LOJA = b.LOJA
    JOIN movimentos_operacoes o ON b.OPERACAO_CODIGO = o.CODIGO
    WHERE b.cadastro BETWEEN '{data_inicio}' AND '{data_fim}'
    {f"AND b.LOJA IN ({','.join(map(str, loja_filtro))})" if loja_filtro else ""}
    GROUP BY b.LOJA, DATE_FORMAT(b.cadastro, '%%Y-%%m')
    """
    
    return pd.read_sql_query(query, engine)

# Função para obter dados para gráfico comparativo (ATUALIZADA - TOTAL = CLIENTES + ROTA + VENDA_CASADA)
def obter_dados_comparativo(loja_filtro, data_inicio, data_fim):
    engine = criar_conexao()

    # IMPORTANTE: Não mais calculamos TOTAL diretamente.
    # TOTAL será calculado como: CLIENTES + ROTA + VENDA_CASADA
    
    # NOVA Query para entregas 40 (substituindo a anterior)
    query_40 = f"""
    SELECT a.LOJA, DATE_FORMAT(r.CADASTRO, '%%Y-%%m') as MES_ANO,
           SUM(if((a.KM_RETORNO - a.KM_SAIDA) <= 7 and TIMESTAMPDIFF(minute, r.CADASTRO, e.ROTA_HORARIO_REALIZADO) <= 40, 1, 0)) as ENTREGA_40
    FROM expedicao_itens e
    JOIN expedicao a ON e.EXPEDICAO_CODIGO = a.EXPEDICAO AND e.EXPEDICAO_LOJA = a.LOJA
    JOIN cadastros_veiculos b ON a.cada_veic_id = b.cada_veic_id
    JOIN produto_veiculo c ON b.veiculo_codigo = c.codigo
    JOIN entregador d ON a.ENTREGADOR_CODIGO = d.CODIGO
    LEFT JOIN romaneios_dbf r ON e.VENDA_TIPO = 'ROMANEIO'
        AND e.CODIGO_VENDA = r.ROMANEIO
        AND e.LOJA_VENDA = r.LOJA
    WHERE a.ROTA_METROS IS NOT NULL
    AND r.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'
    AND e.ROTA_HORARIO_REALIZADO IS NOT NULL
    AND e.ROTA_STATUS = 'ENTREGUE'
    {f"AND a.LOJA IN ({','.join(map(str, loja_filtro))})" if loja_filtro else ""}
    GROUP BY a.LOJA, DATE_FORMAT(r.CADASTRO, '%%Y-%%m')
    """
    
    # Query para clientes (corrigida - conta registros distintos)
    query_clientes = f"""
    SELECT E.LOJA, DATE_FORMAT(E.CADASTRO, '%%Y-%%m') as MES_ANO,
           COUNT(DISTINCT CONCAT(EI.EXPEDICAO_CODIGO, '-', EI.EXPEDICAO_LOJA, '-', EI.ITEM)) AS CLIENTES
    FROM expedicao_itens EI
    LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
    LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO
           AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
    LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
    WHERE E.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'
    AND C.NOME NOT LIKE 'AUTO GERAL AUTOPECA%%'
    AND C.NOME IS NOT NULL
    {f"AND E.LOJA IN ({','.join(map(str, loja_filtro))})" if loja_filtro else ""}
    GROUP BY E.LOJA, DATE_FORMAT(E.CADASTRO, '%%Y-%%m')
    """
    
    # Query para rota (corrigida - conta registros distintos)
    query_rota = f"""
    SELECT E.LOJA, DATE_FORMAT(E.CADASTRO, '%%Y-%%m') as MES_ANO,
           COUNT(DISTINCT CONCAT(EI.EXPEDICAO_CODIGO, '-', EI.EXPEDICAO_LOJA, '-', EI.ITEM)) AS ROTA
    FROM expedicao_itens EI
    LEFT JOIN expedicao E ON EI.EXPEDICAO_CODIGO = E.expedicao AND EI.EXPEDICAO_LOJA = E.LOJA
    LEFT JOIN cadastros_enderecos CE ON EI.ENDERECO_ENTREGA_CODIGO = CE.ENDERECO_CODIGO
           AND EI.ENDERECO_ENTREGA_LOJA = CE.ENDERECO_LOJA
    LEFT JOIN cadastros C ON CE.CADASTRO_CODIGO = C.CODIGO AND CE.CADASTRO_LOJA = C.LOJA
    WHERE E.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'
    AND (C.NOME LIKE 'AUTO GERAL AUTOPECA%%' OR C.NOME IS NULL)
    {f"AND E.LOJA IN ({','.join(map(str, loja_filtro))})" if loja_filtro else ""}
    GROUP BY E.LOJA, DATE_FORMAT(E.CADASTRO, '%%Y-%%m')
    """
    
    df_40 = pd.read_sql_query(query_40, engine)
    df_clientes = pd.read_sql_query(query_clientes, engine)
    df_rota = pd.read_sql_query(query_rota, engine)

    # Obter dados de venda casada
    df_venda_casada = obter_venda_casada(loja_filtro, data_inicio, data_fim)

    # Calcular TOTAL como CLIENTES + ROTA + VENDA_CASADA
    # Primeiro, criar um DataFrame com todas as combinações de LOJA e MES_ANO
    all_combinations = set()
    for df in [df_clientes, df_rota, df_venda_casada]:
        if not df.empty:
            for _, row in df.iterrows():
                all_combinations.add((row['LOJA'], row['MES_ANO']))

    # Criar DataFrame de totais
    total_data = []
    for loja, mes_ano in all_combinations:
        clientes_val = df_clientes[(df_clientes['LOJA'] == loja) & (df_clientes['MES_ANO'] == mes_ano)]['CLIENTES'].sum()
        rota_val = df_rota[(df_rota['LOJA'] == loja) & (df_rota['MES_ANO'] == mes_ano)]['ROTA'].sum()
        venda_casada_val = df_venda_casada[(df_venda_casada['LOJA'] == loja) & (df_venda_casada['MES_ANO'] == mes_ano)]['VENDA_CASADA'].sum()

        total = clientes_val + rota_val + venda_casada_val
        total_data.append({'LOJA': loja, 'MES_ANO': mes_ano, 'TOTAL': total})

    df_total = pd.DataFrame(total_data)

    return df_total, df_40, df_clientes, df_rota, df_venda_casada

# Interface do usuário
st.title("📊 Dashboard de Análise de Entregas")

# Sidebar para filtros
st.sidebar.header("🔧 Filtros")

# Selectbox para tipo de análise
tipo_analise = st.sidebar.selectbox(
    "Tipo de Análise:",
    ["TOTAL ENTREGAS", "ENTREGAS CLIENTES", "ENTREGAS ROTA"]
)

# Filtro de data
hoje = datetime.now()
primeiro_dia_mes_anterior = date(hoje.year, hoje.month - 1, 1)
ultimo_dia_mes_anterior = date(hoje.year, hoje.month, 1) - pd.Timedelta(days=1)

data_inicio = st.sidebar.date_input("Data Início:", primeiro_dia_mes_anterior)
data_fim = st.sidebar.date_input("Data Fim:", ultimo_dia_mes_anterior)

# Filtro de lojas
lojas_disponiveis = obter_lojas_disponiveis()
lojas_selecionadas = st.sidebar.multiselect(
    "Selecionar Lojas:",
    options=lojas_disponiveis,
    default=[],
    help="Deixe vazio para mostrar todas as lojas"
)

# Executar query
if st.sidebar.button("🔄 Atualizar Dados"):
    st.rerun()

# Carregar dados
with st.spinner("Carregando dados..."):
    df = executar_query(tipo_analise, lojas_selecionadas, data_inicio, data_fim)

if not df.empty:
    # Resumo da análise
    st.header("📈 Resumo da Análise")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_entregas = df['ENTREGA'].sum()
        st.metric("Total de Entregas", f"{total_entregas:,.0f}")
    
    with col2:
        df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
        entregas_por_dia = df.groupby(df['CADASTRO'].dt.date)['ENTREGA'].sum()
        mediana_dia = entregas_por_dia.median()
        st.metric("Mediana por Dia", f"{mediana_dia:.0f}")
    
    with col3:
        ranking_loja_mais = df.groupby('LOJA')['ENTREGA'].sum().sort_values(ascending=False)
        if not ranking_loja_mais.empty:
            loja_mais = ranking_loja_mais.index[0]
            qtd_mais = ranking_loja_mais.iloc[0]
            st.metric("Loja com Mais Entregas", f"Loja {loja_mais}: {qtd_mais}")
    
    with col4:
        ranking_loja_menos = df.groupby('LOJA')['ENTREGA'].sum().sort_values(ascending=True)
        if not ranking_loja_menos.empty:
            loja_menos = ranking_loja_menos.index[0]
            qtd_menos = ranking_loja_menos.iloc[0]
            st.metric("Loja com Menos Entregas", f"Loja {loja_menos}: {qtd_menos}")
    
    # Rankings de entregadores
    col5, col6 = st.columns(2)
    
    with col5:
        ranking_entregador_mais = df.groupby('ENTREGADOR_NOME')['ENTREGA'].sum().sort_values(ascending=False)
        if not ranking_entregador_mais.empty:
            entregador_mais = ranking_entregador_mais.index[0]
            qtd_entregador_mais = ranking_entregador_mais.iloc[0]
            st.metric("Entregador com Mais Entregas", f"{entregador_mais}: {qtd_entregador_mais}")
    
    with col6:
        ranking_entregador_menos = df.groupby('ENTREGADOR_NOME')['ENTREGA'].sum().sort_values(ascending=True)
        if not ranking_entregador_menos.empty:
            entregador_menos = ranking_entregador_menos.index[0]
            qtd_entregador_menos = ranking_entregador_menos.iloc[0]
            st.metric("Entregador com Menos Entregas", f"{entregador_menos}: {qtd_entregador_menos}")
    
    # Tabela com filtros
    st.header("📋 Tabela Completa")
    
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        filtro_loja = st.text_input("Filtrar por Loja:")
    with col_filtro2:
        filtro_entregador = st.text_input("Filtrar por Entregador:")
    with col_filtro3:
        filtro_cliente = st.text_input("Filtrar por Cliente:")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    if filtro_loja:
        df_filtrado = df_filtrado[df_filtrado['LOJA'].astype(str).str.contains(filtro_loja, case=False, na=False)]
    if filtro_entregador:
        df_filtrado = df_filtrado[df_filtrado['ENTREGADOR_NOME'].str.contains(filtro_entregador, case=False, na=False)]
    if filtro_cliente:
        df_filtrado = df_filtrado[df_filtrado['CLIENTE'].str.contains(filtro_cliente, case=False, na=False)]
    
    st.dataframe(df_filtrado, use_container_width=True)
    
    # Gráfico comparativo por loja
    st.header("📊 Gráfico Comparativo por Loja")
    
    with st.spinner("Carregando dados comparativos..."):
        df_total, df_40, df_clientes, df_rota, df_venda_casada = obter_dados_comparativo(lojas_selecionadas, data_inicio, data_fim)
    
    # Seleção de loja para gráfico comparativo
    lojas_para_grafico = sorted(df_total['LOJA'].unique())
    loja_selecionada = st.selectbox("Selecionar Loja para Gráfico Comparativo:", lojas_para_grafico)
    
    if loja_selecionada:
        # Preparar dados para gráfico
        total_entrega = df_total[df_total['LOJA'] == loja_selecionada].set_index('MES_ANO')['TOTAL']
        entrega_40 = df_40[df_40['LOJA'] == loja_selecionada].set_index('MES_ANO')['ENTREGA_40']
        clientes = df_clientes[df_clientes['LOJA'] == loja_selecionada].set_index('MES_ANO')['CLIENTES']
        soma_total_rota = df_rota[df_rota['LOJA'] == loja_selecionada].set_index('MES_ANO')['ROTA']
        soma_total_venda_casada = df_venda_casada[df_venda_casada['LOJA'] == loja_selecionada].set_index('MES_ANO')['VENDA_CASADA']
        
        # Criar DataFrame unificado
        todos_meses = sorted(set(total_entrega.index) | set(entrega_40.index) | set(clientes.index) | 
                           set(soma_total_rota.index) | set(soma_total_venda_casada.index))
        
        fig = go.Figure()
        
        if todos_meses:
            # Reindexar para ter todos os meses
            total_entrega = total_entrega.reindex(todos_meses, fill_value=0)
            entrega_40 = entrega_40.reindex(todos_meses, fill_value=0)
            clientes = clientes.reindex(todos_meses, fill_value=0)
            soma_total_rota = soma_total_rota.reindex(todos_meses, fill_value=0)
            soma_total_venda_casada = soma_total_venda_casada.reindex(todos_meses, fill_value=0)
            
            fig.add_trace(go.Bar(x=todos_meses, y=total_entrega.values, name='Total', 
                               text=total_entrega.values, textposition='auto'))
            fig.add_trace(go.Bar(x=todos_meses, y=entrega_40.values, name='Entrega 40', 
                               text=entrega_40.values, textposition='auto'))
            fig.add_trace(go.Bar(x=todos_meses, y=clientes.values, name='Clientes', 
                               text=clientes.values, textposition='auto'))
            fig.add_trace(go.Bar(x=todos_meses, y=soma_total_rota.values, name='Rota', 
                               text=soma_total_rota.values, textposition='auto'))
            fig.add_trace(go.Bar(x=todos_meses, y=soma_total_venda_casada.values, name='Venda Casada', 
                               text=soma_total_venda_casada.values, textposition='auto'))
        else:
            st.warning("Não há dados suficientes para a loja selecionada.")
        
        fig.update_layout(
            title=f'Dados da Loja {loja_selecionada}',
            xaxis_title='Meses',
            yaxis_title='Valores',
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico adicional baseado na seleção de lojas
    st.header("📊 Gráfico de Análise")
    
    if lojas_selecionadas:
        # Se tem lojas selecionadas: gráfico por mês
        df_filtrado['CADASTRO'] = pd.to_datetime(df_filtrado['CADASTRO'])
        df_filtrado['MES_ANO'] = df_filtrado['CADASTRO'].dt.strftime('%Y-%m')
        
        dados_mes = df_filtrado.groupby('MES_ANO')['ENTREGA'].sum().reset_index()
        
        fig_mes = go.Figure()
        fig_mes.add_trace(go.Bar(
            x=dados_mes['MES_ANO'],
            y=dados_mes['ENTREGA'],
            text=dados_mes['ENTREGA'],
            textposition='auto',
            name='Entregas por Mês'
        ))
        
        fig_mes.update_layout(
            title=f'Entregas por Mês - {tipo_analise} - Lojas Selecionadas: {", ".join(map(str, lojas_selecionadas))}',
            xaxis_title='Mês/Ano',
            yaxis_title='Total de Entregas',
            showlegend=False
        )
        
        st.plotly_chart(fig_mes, use_container_width=True)
    
    else:
        # Se não tem lojas selecionadas: gráfico por loja com cores neutras diferentes
        dados_loja = df_filtrado.groupby('LOJA')['ENTREGA'].sum().reset_index()
        dados_loja = dados_loja.sort_values('LOJA', ascending=True)
        
        # Definir cores neutras para cada loja
        cores_neutras = [
            '#4A90E2',  # Azul claro
            '#50C878',  # Verde esmeralda
            '#9B59B6',  # Roxo suave
            '#F39C12',  # Laranja suave
            '#1ABC9C',  # Turquesa
            '#34495E',  # Azul acinzentado
            '#95A5A6',  # Cinza claro
            '#16A085',  # Verde azulado
            '#8E44AD',  # Roxo médio
            '#2980B9',  # Azul médio
            '#27AE60',  # Verde médio
            '#E67E22',  # Laranja médio
            '#3498DB'   # Azul céu
        ]
        
        # Criar lista de cores baseada no número de lojas
        num_lojas = len(dados_loja)
        cores_barras = cores_neutras[:num_lojas]
        if num_lojas > len(cores_neutras):
            # Se há mais lojas que cores, repetir as cores
            cores_barras = (cores_neutras * ((num_lojas // len(cores_neutras)) + 1))[:num_lojas]
        
        fig_loja = go.Figure()
        
        # Adicionar uma barra para cada loja com cor diferente e legenda
        for i, (_, row) in enumerate(dados_loja.iterrows()):
            fig_loja.add_trace(go.Bar(
                x=[f'Loja {row["LOJA"]}'],
                y=[row['ENTREGA']],
                text=[row['ENTREGA']],
                textposition='auto',
                name=f'Loja {row["LOJA"]}',
                marker=dict(color=cores_barras[i]),
                showlegend=True
            ))
        
        fig_loja.update_layout(
            title=f'{tipo_analise} - Total por Loja (Todas as Lojas)',
            xaxis_title='Loja',
            yaxis_title='Total de Entregas',
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            )
        )
        
        st.plotly_chart(fig_loja, use_container_width=True)
    
else:
    st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")