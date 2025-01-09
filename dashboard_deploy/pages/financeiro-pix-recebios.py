import streamlit as st
import pandas as pd
from datetime import datetime

titulo = 'PIX Recebidos'
st.set_page_config(page_title=titulo, layout="wide")
st.title(titulo)
st.sidebar.title(titulo)

# Initialize connection.
conn = st.connection('mysql', type='sql')

query = """
SELECT YEAR(CRIADO_EM) Ano
     , WEEKOFYEAR(CRIADO_EM) Semana
     , Loja
     , COUNT(1) Registros
     , SUM(VALOR) Valor
FROM autogeral.pix
WHERE CRIADO_EM BETWEEN '2023-01-31 00:00:00' AND '2024-12-23 23:59:59'
AND SITUACAO = 'CONCLUIDA'
GROUP BY YEAR(CRIADO_EM), WEEKOFYEAR(CRIADO_EM), LOJA
"""

dfPixGerado = conn.query(query, ttl=600)

st.dataframe(dfPixGerado)
st.write(f"Total de linhas: {dfPixGerado.shape[0]}")

query = """"
SELECT YEAR(CADASTRO) Ano,
       WEEKOFYEAR(CADASTRO) Semana,
       Loja,
       COUNT(1) Registros,
       SUM(VALOR_TOTAL) Valor
  FROM autogeral.romaneios_dbf
 WHERE CADASTRO BETWEEN '2024-01-01 00:00:00' AND '2024-12-04 23:59:59'
   AND MODO_PGTO_CODIGO = 102
   AND SITUACAO = 'FECHADO'
 GROUP BY YEAR(CADASTRO), WEEKOFYEAR(CADASTRO), LOJA;
"""

dfPixTotal = conn.query(query, ttl=600)

st.dataframe(dfPixTotal)
st.write(f"Total de linhas: {dfPixTotal.shape[0]}")

