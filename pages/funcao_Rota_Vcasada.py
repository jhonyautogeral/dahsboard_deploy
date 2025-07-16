import streamlit as st
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import calendar

if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
# Funções de conexão e consulta
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

# Função genérica para realizar consultas ao banco de dados
def executar_query(engine, query):
    return pd.read_sql(query, engine)

# Função para consultar dados de lojas no banco de dados
def consultar_lojas(engine):
    query = "SELECT codigo, nome FROM autogeral.lojas ORDER BY codigo"
    return executar_query(engine, query)

def gerar_query_dados_vr(inicio, fim, loja):
    return f""" 
    SELECT b.cadastro, b.ROMANEIO, b.LOJA, o.DESCRICAO_SIMPLIFICADA, a.COMPRA_PEDIDO, b.ENTREGA,
           CASE WHEN o.DESCRICAO_SIMPLIFICADA = 'Transferência' THEN 1 ELSE 0 END AS ROTA,
           CASE WHEN a.COMPRA_PEDIDO IS NOT NULL THEN 1 ELSE 0 END AS "Venda casada"
    FROM romaneios_dbf b
    LEFT JOIN compras_pedidos a ON a.romaneio_codigo = b.ROMANEIO AND a.ROMANEIO_LOJA = b.LOJA
    JOIN movimentos_operacoes o ON b.OPERACAO_CODIGO = o.CODIGO
    WHERE b.cadastro BETWEEN '{inicio}' AND '{fim}'
        and b.LOJA = {loja};
    """
# Carregar dados
rota_df = gerar_query_dados_vr()

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

    engine = criar_conexao()

    # Consultar dados das lojas
    df_lojas = consultar_lojas(engine)
    loja_dict = dict(zip(df_lojas['codigo'], df_lojas['nome']))
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
