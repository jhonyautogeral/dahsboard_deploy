import streamlit as st
import pandas as pd
from datetime import datetime

titulo = 'Vendas por data de emissão'
st.set_page_config(page_title=titulo, layout="wide")
st.title(titulo)
st.sidebar.title(titulo)

# Initialize connection.
conn = st.connection('mysql', type='sql')


query = """SELECT concat_ws(' ', LPAD(L.CODIGO, 2, '0'), L.NOME) Loja, LAST_DAY(V.EMISSAO) 'Mês', SUM(V.VALOR_TOTAL*M.COMISSAO_FATOR) 'Vlr. Total'
  FROM vendas V LEFT JOIN movimentos_operacoes M ON V.OPERACAO_CODIGO=M.CODIGO 
                LEFT JOIN lojas L                ON V.LOJA=L.CODIGO 
  WHERE V.SITUACAO='NORMAL' AND V.EMISSAO BETWEEN '2022-01-01' AND '2024-12-31'
    AND V.OPERACAO_CODIGO IN (1,2,3,8,9,46) 
GROUP BY V.LOJA, LAST_DAY(V.EMISSAO)"""

dados = conn.query(query, ttl=600)

dados_pivot = dados.pivot(index='Loja', columns='Mês', values='Vlr. Total').fillna(0)

dados_pivot.columns = pd.to_datetime(dados_pivot.columns).strftime('%Y/%m')

st.dataframe(dados_pivot)
st.write(f"Total de linhas: {dados_pivot.shape[0]}")

st.line_chart(dados_pivot.T)

