import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
import re

# Configuração do Streamlit
st.set_page_config(page_title="Custo da Frota", layout="wide")
st.title("Custo Frota")

# Seleção de período
st.subheader("Selecione o Período")
data_inicio = st.date_input("Data Início", value=pd.to_datetime('2024-01-01'))
data_fim = st.date_input("Data Fim", value=pd.to_datetime('2024-12-31'))

# Função para criar conexão com o banco de dados com cache
@st.cache_resource
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

# Função para executar consultas SQL com segurança
@st.cache_data(ttl=600)
def consultar_dados(query, params=None):
    engine = criar_conexao()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

# Consulta de dados do banco
query = """
    SELECT cv.PLACA, 
           cva.CADASTRO, 
           cva.COMBUSTIVEL_1_LITROS, 
           cva.COMBUSTIVEL_1_TIPO, 
           cva.COMBUSTIVEL_1_VALOR_TOTAL,
           cva.COMBUSTIVEL_2_LITROS, 
           cva.COMBUSTIVEL_2_TIPO, 
           cva.COMBUSTIVEL_2_VALOR_TOTAL, 
           cva.LOJA,
           cva.KM
    FROM cadastros_veiculos_abastecimentos cva
    JOIN cadastros_veiculos cv
      ON cva.CADASTRO_CODIGO = cv.CADASTRO_CODIGO
    WHERE cva.CADASTRO BETWEEN :data_inicio AND :data_fim
    ORDER BY cva.CADASTRO ASC;
"""

expedicao_df = consultar_dados(query, params={"data_inicio": data_inicio, "data_fim": data_fim})

# Manipulação do DataFrame
expedicao_df['CADASTRO'] = pd.to_datetime(expedicao_df['CADASTRO'])
expedicao_df['ANO_MES'] = expedicao_df['CADASTRO'].dt.to_period('M')

# Agrupamento por PLACA e LOJA
agrupado_df = expedicao_df.groupby(['PLACA', 'LOJA', 'ANO_MES']).agg({
    'COMBUSTIVEL_1_LITROS': 'sum',
    'COMBUSTIVEL_1_VALOR_TOTAL': 'sum'
}).reset_index()

# Exibição do DataFrame no Streamlit
st.subheader("Consumo de Combustível")
st.dataframe(agrupado_df)

# Soma por LOJA e Mês
agrupado_loja_df = expedicao_df.groupby(['LOJA', 'ANO_MES']).agg({
    'COMBUSTIVEL_1_VALOR_TOTAL': 'sum'
}).reset_index()

st.subheader("Consumo Total de Combustível por Loja")
st.dataframe(agrupado_loja_df)

# Pivot para visualização
pivot_df = agrupado_df.pivot(index='PLACA', columns='ANO_MES', values='COMBUSTIVEL_1_VALOR_TOTAL').fillna(0)

st.subheader("Tabela Pivotada: Consumo por Placa e Mês")
st.dataframe(pivot_df)

# Gráfico de Consumo por Placa
st.subheader("Gráfico de Consumo por Placa e Mês")
st.line_chart(pivot_df)

