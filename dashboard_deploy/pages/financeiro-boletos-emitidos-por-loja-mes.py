import streamlit as st
import pandas as pd
from datetime import datetime

titulo = 'Boletos emitidos por loja/mês'
st.set_page_config(page_title=titulo, layout="wide")
st.title(titulo)
st.sidebar.title(titulo)

# Initialize connection.
conn = st.connection('mysql', type='sql')


query = """SELECT LAST_DAY(a.CADASTRO) 'Mês', concat_ws(' ', LPAD(a.LOJA, 2, '0'), l.NOME) Loja, COUNT(a.CODIGO) Boletos
  FROM boletos a JOIN lojas l on a.LOJA=l.CODIGO
 WHERE YEAR(a.CADASTRO)>=2023
GROUP BY LAST_DAY(a.CADASTRO), concat_ws(' ', LPAD(a.LOJA, 2, '0'), l.NOME);"""

dados = conn.query(query, ttl=600)

#dados_pivot = dados.pivot(index=['Loja','Nome'], columns='Mês', values='Boletos')
dados_pivot = dados.pivot(index='Loja', columns='Mês', values='Boletos').fillna(0)

dados_pivot.columns = pd.to_datetime(dados_pivot.columns).strftime('%Y/%m')

st.dataframe(dados_pivot)
st.write(f"Total de linhas: {dados_pivot.shape[0]}")

st.line_chart(dados_pivot.T)
