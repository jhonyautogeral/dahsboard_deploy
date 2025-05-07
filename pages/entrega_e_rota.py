import streamlit as st
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página
    
from click import group
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine
import plotly.graph_objects as go
from sqlalchemy.exc import SQLAlchemyError
import seaborn as sns

if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
st.set_page_config(page_title="Entrega e suas métricas", layout="wide")

# Função para criar conexão com o banco de dados
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

# Função para consultar dados de lojas
@st.cache_data(ttl=3600)
def consultar_lojas(_engine):
    query = "SELECT codigo, nome FROM autogeral.lojas ORDER BY codigo"
    return pd.read_sql(query, _engine)

# Função para consultar dados de entregas
@st.cache_data(ttl=3600)
def consultar_entregas(_engine, loja, inicio_periodo_str, termino_periodo_str):
    query = f""" SELECT a.cadastro, a.LOJA, d.DESCRICAO 'Entregador'
     , b.PLACA, a.KM_RETORNO - a.KM_SAIDA KMS
     , IF(24*60*60 >= (IF(a.HORA_SAIDA < a.HORA_RETORNO, TIMEDIFF(a.HORA_RETORNO, a.HORA_SAIDA), TIMEDIFF(a.HORA_SAIDA, a.HORA_RETORNO))),
            IF(a.HORA_SAIDA < a.HORA_RETORNO, TIMEDIFF(a.HORA_RETORNO, a.HORA_SAIDA), TIMEDIFF(a.HORA_SAIDA, a.HORA_RETORNO)),
            '23:59:59') TEMPO_MARCACAO
     , e.EXPEDICAO_TIPO
     , e.ROTA_STATUS
  FROM expedicao_itens e
  JOIN expedicao a ON e.EXPEDICAO_CODIGO = a.EXPEDICAO AND e.EXPEDICAO_LOJA = a.LOJA
  JOIN cadastros_veiculos b ON a.cada_veic_id = b.cada_veic_id
  JOIN produto_veiculo c ON b.veiculo_codigo = c.codigo
  JOIN entregador d ON a.ENTREGADOR_CODIGO = d.CODIGO
 WHERE a.ROTA_METROS IS NOT NULL AND a.LOJA = {loja}
   AND a.cadastro BETWEEN '{inicio_periodo_str}' AND '{termino_periodo_str}'
 ORDER BY a.LOJA, a.cadastro;
    """
    return pd.read_sql(query, _engine)

# Função para calcular índices de entrega
def calcular_indices(entrega_df):
    entrega_df['cadastro'] = pd.to_datetime(entrega_df['cadastro']).dt.to_period('M')

    entrega_sucesso = entrega_df[
        (entrega_df['TEMPO_MARCACAO'] <= '00:40:00') &
        (entrega_df['EXPEDICAO_TIPO'] == 'ENTREGA') &
        (entrega_df['ROTA_STATUS'] == 'ENTREGUE')
    ]
    entregas_agrupadas = entrega_sucesso.groupby(['cadastro', 'PLACA', 'LOJA']).size().reset_index(name='TOTAL_ENTREGAS')

    entrega_nao_sucesso = entrega_df[
        (entrega_df['TEMPO_MARCACAO'] <= '00:40:00') &
        (entrega_df['EXPEDICAO_TIPO'] == 'ENTREGA') &
        (entrega_df['ROTA_STATUS'] == 'NAO_ENTREGUE')
    ]
    nao_entregas_agrupadas = entrega_nao_sucesso.groupby(['cadastro', 'PLACA', 'LOJA']).size().reset_index(name='TOTAL_NAO_ENTREGUES')

    entrega_indices = pd.merge(entregas_agrupadas, nao_entregas_agrupadas, on=['cadastro', 'PLACA', 'LOJA'], how='outer').fillna(0)
    entrega_indices['TOTAL_TENTATIVAS'] = entrega_indices['TOTAL_ENTREGAS'] + entrega_indices['TOTAL_NAO_ENTREGUES']
    entrega_indices['INDICE_ENTREGA_%'] = (entrega_indices['TOTAL_ENTREGAS'] / entrega_indices['TOTAL_TENTATIVAS']) * 100
    entrega_indices['INDICE_NAO_ENTREGA_%'] = (entrega_indices['TOTAL_NAO_ENTREGUES'] / entrega_indices['TOTAL_TENTATIVAS']) * 100

    return entrega_indices[['cadastro', 'LOJA', 'PLACA', 'TOTAL_NAO_ENTREGUES', 'TOTAL_ENTREGAS', 'INDICE_ENTREGA_%', 'INDICE_NAO_ENTREGA_%']]

# Criar conexão com o banco de dados
engine = criar_conexao()

# Consultar dados do banco para o período selecionado
df = consultar_lojas(engine)
loja_dict = dict(zip(df['codigo'], df['nome']))
# st.write(loja_dict)

# Selecionar unidade e período
loja = st.sidebar.selectbox("Unidade", options=list(loja_dict.keys()), format_func=lambda x: loja_dict[x])
inicio_periodo = st.sidebar.date_input("Início do período", value=datetime(2024, 1, 1), format="DD/MM/YYYY")
termino_periodo = st.sidebar.date_input("Término do período", value=datetime(2024, 12, 31), format="DD/MM/YYYY")

# Convertendo as datas
inicio_periodo_dt = datetime.combine(inicio_periodo, datetime.min.time())
termino_periodo_dt = datetime.combine(termino_periodo, datetime.max.time())
inicio_periodo_str = inicio_periodo_dt.strftime("%Y-%m-%d %H:%M:%S")
termino_periodo_str = termino_periodo_dt.strftime("%Y-%m-%d %H:%M:%S")

# Gerar relatório
gerar_relatorio = True

st.write(f"Você selecionou as entregas da loja {loja}, {loja_dict[loja]}")
st.write(f"Data de início {inicio_periodo.strftime('%d/%m/%Y')} e data de término {termino_periodo.strftime('%d/%m/%Y')}")

if gerar_relatorio:
    entrega_df = consultar_entregas(engine, loja, inicio_periodo_str, termino_periodo_str)
    indice_entrega = calcular_indices(entrega_df)
    # Opção para visualizar os dados 
    if st.checkbox("Mostrar Dados filtrados com entregas no tempo até 40 min:"):
        st.dataframe(indice_entrega)

    entrega_40 = entrega_df[
        (entrega_df['TEMPO_MARCACAO'] <= '00:40:00') &
        (entrega_df['EXPEDICAO_TIPO'] == 'ENTREGA') &
        (entrega_df['ROTA_STATUS'] == 'ENTREGUE')
    ].groupby(['cadastro', 'LOJA']).size().reset_index(name='TOTAL_ENTREGAS')
    entrega_40 = entrega_40.pivot(index='LOJA', columns='cadastro', values='TOTAL_ENTREGAS').fillna(0)
    # st.write('Total entregue em 40')
    # st.dataframe(entrega_40)

    entrega_filtrada = entrega_df[
        (entrega_df['EXPEDICAO_TIPO'] == 'ENTREGA') &
        (entrega_df['ROTA_STATUS'].isin(['ENTREGUE', 'NAO_ENTREGUE']))
    ].copy()
    entrega_filtrada.loc[:, 'TOTAL_ENTREGAS'] = entrega_filtrada['ROTA_STATUS'].apply(lambda x: 1 if x == 'ENTREGUE' else 0)
    entrega_filtrada.loc[:, 'TOTAL_NAO_ENTREGUES'] = entrega_filtrada['ROTA_STATUS'].apply(lambda x: 1 if x == 'NAO_ENTREGUE' else 0)

    total_entrega_por_loja_mes = entrega_filtrada.groupby(['LOJA', 'cadastro']).agg({
        'TOTAL_ENTREGAS': 'sum',
        'TOTAL_NAO_ENTREGUES': 'sum'
    }).reset_index()
    total_entrega_por_loja_mes['TOTAL_TENTATIVAS'] = total_entrega_por_loja_mes['TOTAL_ENTREGAS'] + total_entrega_por_loja_mes['TOTAL_NAO_ENTREGUES']
    total_entrega_por_loja_mes['INDICE_ENTREGA_%'] = (total_entrega_por_loja_mes['TOTAL_ENTREGAS'] / total_entrega_por_loja_mes['TOTAL_TENTATIVAS']) * 100
    total_entrega_por_loja_mes['INDICE_NAO_ENTREGA_%'] = (total_entrega_por_loja_mes['TOTAL_NAO_ENTREGUES'] / total_entrega_por_loja_mes['TOTAL_TENTATIVAS']) * 100

    # Opção para visualizar os dados 
    if st.checkbox("Mostrar Índice total de entrega por loja e mês:"):
        st.dataframe(total_entrega_por_loja_mes)

    total_entrega = entrega_df[
        (entrega_df['EXPEDICAO_TIPO'] == 'ENTREGA') &
        (entrega_df['ROTA_STATUS'] == 'ENTREGUE')
    ].groupby(['cadastro', 'LOJA']).size().reset_index(name='TOTAL_ENTREGAS')
    total_entrega = total_entrega.pivot(index='LOJA', columns='cadastro', values='TOTAL_ENTREGAS').fillna(0)
    # st.write('Total de entregas ao mês')
    # st.dataframe(total_entrega)

# Inicio merge do codigo

# Função para consultar dados do banco
# Cachear a consulta por 1 hora para melhorar desempenho
# @st.cache_data(ttl=3600)  Porem não esta carrergando os dados corretamente
def get_data():
    query = f""" 
    SELECT b.cadastro, b.ROMANEIO, b.LOJA, o.DESCRICAO_SIMPLIFICADA, a.COMPRA_PEDIDO, b.ENTREGA,
           CASE WHEN o.DESCRICAO_SIMPLIFICADA = 'Transferência' THEN 1 ELSE 0 END AS ROTA,
           CASE WHEN a.COMPRA_PEDIDO IS NOT NULL THEN 1 ELSE 0 END AS "Venda casada"
    FROM romaneios_dbf b
    LEFT JOIN compras_pedidos a ON a.romaneio_codigo = b.ROMANEIO AND a.ROMANEIO_LOJA = b.LOJA
    JOIN movimentos_operacoes o ON b.OPERACAO_CODIGO = o.CODIGO
    WHERE b.cadastro BETWEEN '{inicio_periodo_str}' AND '{termino_periodo_str}'
        and b.LOJA = {loja};
    """
    engine = criar_conexao()
    if engine:
        try:
            return pd.read_sql(query, engine)
        except SQLAlchemyError as e:
            st.error(f"Erro ao executar a consulta: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# Carregar dados
rota_df = get_data()

if rota_df.empty:
    st.warning("Não há dados disponíveis para exibir.")
else:
    # Converter a coluna 'cadastro' para mês e ano
    rota_df['cadastro'] = pd.to_datetime(rota_df['cadastro']).dt.to_period('M')

    # Filtrar dados
    filtered_df = rota_df[(rota_df['ROTA'] == 1) | (rota_df['Venda casada'] == 1)][['ROMANEIO', 'LOJA', 'cadastro', 'ROTA', 'Venda casada']]

    # Filtrar as linhas onde 'DESCRICAO_SIMPLIFICADA' é 'venda' e 'COMPRA_PEDIDO' está vazio
    vendas_df = rota_df[(rota_df['DESCRICAO_SIMPLIFICADA'] == 'Venda') & (rota_df['COMPRA_PEDIDO'].isna())][['LOJA', 'cadastro']]
    # st.write(vendas_df)

    # Criar um dataframe com a coluna 'clientes', que é a soma das linhas filtradas
    clientes_df = vendas_df.groupby(['LOJA', 'cadastro']).size().reset_index(name='cliente')
    
    # Agrupar por romaneio LOJA e cadastro
    grupoRoma_df = filtered_df.groupby(['ROMANEIO', 'LOJA', 'cadastro']).agg({
        'ROTA': 'sum',
        'Venda casada': 'sum'
    }).reset_index()

    # Agrupar por LOJA e cadastro e somas total de Venda casada e Total de Rota
    grupo_df = filtered_df.groupby(['LOJA', 'cadastro']).agg({
        'ROTA': 'sum',
        'Venda casada': 'sum'
    }).reset_index()

    # Cria colunas pivotada
    soma_total_rota = grupo_df.pivot(index='LOJA', columns='cadastro', values='ROTA').fillna(0)
    soma_total_venda_casada = grupo_df.pivot(index='LOJA', columns='cadastro', values='Venda casada').fillna(0)
    clientes = clientes_df.pivot(index='LOJA', columns='cadastro', values='cliente').fillna(0)

# Fim Merge do codigo

    # Título do App
    st.title(f"Gráfico Dinâmico da loja {loja_dict[loja]}")
    # Construção do Gráfico
    fig = go.Figure()
    if loja in total_entrega.index and loja in entrega_40.index:
        # Formatar valores para 2 casas decimais
        total_entrega_y = total_entrega.loc[loja].round(0)
        entrega_40_y = entrega_40.loc[loja].round(0)
        clientes_y = clientes.loc[loja].round(0)
        soma_total_rota_y = soma_total_rota.loc[loja].round(0)
        soma_total_venda_casada_y = soma_total_venda_casada.loc[loja].round(0)

        fig.add_trace(go.Bar(x=total_entrega.columns.astype(str), y=total_entrega_y, name='Total', text=total_entrega_y, textposition='auto'))
        fig.add_trace(go.Bar(x=entrega_40.columns.astype(str), y=entrega_40_y, name='Entrega 40', text=entrega_40_y, textposition='auto'))
        # Debug Clintes, apresentando erros
        fig.add_trace(go.Bar(x=clientes.columns.astype(str), y=clientes_y, name='Clientes', text=clientes_y, textposition='auto'))
        fig.add_trace(go.Bar(x=soma_total_rota.columns.astype(str), y=soma_total_rota_y, name='Rota', text=soma_total_rota_y, textposition='auto'))
        fig.add_trace(go.Bar(x=soma_total_venda_casada.columns.astype(str), y=soma_total_venda_casada_y, name='Venda Casada', text=soma_total_venda_casada_y, textposition='auto'))
    else:
        st.warning("Não há dados suficientes para a loja selecionada.")
        
    # Layout do Gráfico
    fig.update_layout(
        # title=f'Dados da loja {loja_dict[loja]}',
        xaxis_title='Meses',
        yaxis_title='Valores',
        barmode='group'
    )

    # Exibindo o Gráfico
    st.plotly_chart(fig)

    # entregas em 40 min
    st.write('Total entregue em 40')
    st.dataframe(entrega_40)
    # Entrega total
    st.write('Total de entregas ao mês')
    st.dataframe(total_entrega)

    # Total Rota
    st.write('Total Rota')
    st.dataframe(soma_total_rota)

    # Total Venda Casada
    st.write('Total V.Casada')
    st.dataframe(soma_total_venda_casada)

    # if st.checkbox("Mostrar Mapa de Calor - Soma Total de Rotas:"):
    #     #Gerar o mapa de calor para 'ROTA'
    #     # st.write("Mapa de Calor - Soma Total de Rotas")
    #     fig_rota, ax_rota = plt.subplots(figsize=(10, 8))
    #     sns.heatmap(soma_total_rota, cmap="Reds", annot=True, fmt=",.0f", ax=ax_rota)
    #     st.pyplot(fig_rota)

    # if st.checkbox("Mostrar Mapa de Calor - Soma Total de Venda Casada:"):
    #     # Gerar o mapa de calor para 'Venda Casada'
    #     # st.write("Mapa de Calor - Soma Total de Venda Casada")
    #     fig_venda_casada, ax_venda_casada = plt.subplots(figsize=(10, 8))
    #     sns.heatmap(soma_total_venda_casada, cmap="Reds", annot=True, fmt=",.0f", ax=ax_venda_casada)
    #     st.pyplot(fig_venda_casada)

