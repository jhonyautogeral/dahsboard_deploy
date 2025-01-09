import streamlit as st 
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine , text
from datetime import datetime
import re

# Título e configuração da página
titulo = 'Custo com Estacionamento Por Loja'
st.set_page_config(page_title=titulo, layout="wide")
st.title(titulo)

# Selecionar período no Streamlit
st.subheader("Selecione o Período de Entrega")
data_inicio = st.date_input("Data Início", value=pd.to_datetime('2023-01-01'))
data_fim = st.date_input("Data Fim", value=pd.to_datetime('2023-12-31'))

# Conectar ao banco de dados
engine = create_engine('mysql+pymysql://root:root@10.50.1.252:3306/autogeral')


# Definir a consulta SQL com parâmetros para consultar pedagios em t
query = text("""
    SELECT D.DATA, D.LOJA, D.VALOR, CC.DESCRICAO AS CENTRO_CUSTO_DESCRICAO, D.DESCRICAO
    FROM despesas D
    LEFT JOIN centros_custo CC ON D.CENTRO_CUSTO_CODIGO = CC.CODIGO
    WHERE CC.DESCRICAO = 'ESTACIONAMENTO' 
	AND D.DATA BETWEEN :data_inicio AND :data_fim
	GROUP BY D.DATA, D.LOJA, D.VALOR, CC.DESCRICAO, D.DESCRICAO
	ORDER BY D.LOJA;
""")

# Consultar dados do banco para o período selecionado
with engine.connect() as connection:
    estacionamento = pd.read_sql(query, con=connection, params={"data_inicio": data_inicio, "data_fim": data_fim})


# Criar o DataFrame 'filtra_placa' com as colunas especificadas
estacionamento = estacionamento[['DATA','LOJA','VALOR','CENTRO_CUSTO_DESCRICAO','DESCRICAO']].copy()

# Logs de verificacao
print(estacionamento)
# st.dataframe(estacionamento)

# Converter a coluna 'DATA' para datetime e criar coluna de DATA-MES
estacionamento['DATA'] = pd.to_datetime(estacionamento['DATA'])
estacionamento['DATA'] = estacionamento['DATA'].dt.to_period('M')

# Agrupar por colunas 'LOJA', 'mes', 'placa', 'CENTRO_CUSTO_DESCRICAO' e somar os valores
resultado_df = estacionamento.groupby(['DATA','LOJA', 'CENTRO_CUSTO_DESCRICAO']).agg({'VALOR': 'sum'}).reset_index()

resultado_df = resultado_df[['DATA','LOJA','VALOR','CENTRO_CUSTO_DESCRICAO']].copy()
st.dataframe(resultado_df)