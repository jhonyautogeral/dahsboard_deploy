import streamlit as st
import pandas as pd
from datetime import datetime

titulo = 'Compra Pit Stop'
# st.set_page_config(page_title=titulo, layout="wide")
st.title(titulo)
st.sidebar.title(titulo)

# Initialize connection.
conn = st.connection('mysql', type='sql')

# Perform query.
df = conn.query("""select a.LOJA 'Loja'
     , c.DESCRICAO 'Grupo'
     , extract(YEAR_MONTH FROM a.EMISSAO) 'Mês'
     , sum(a.VALOR_TOTAL_NOTA) VALOR
  from compras_dbf a join cadastros b on a.CADASTRO_CODIGO=b.CODIGO and a.CADASTRO_LOJA=b.LOJA
					 join cadastros_grupos c on b.CADASTRO_GRUPO=c.CODIGO
 where a.OPERACAO_CODIGO  in (32,33)
   and a.CADASTRO>'2023-01-01 00:00:00'
   and b.CADASTRO_GRUPO IN (7, 10, 30)
 GROUP BY a.LOJA
     , c.DESCRICAO
     , extract(YEAR_MONTH FROM a.EMISSAO)
 ORDER BY extract(YEAR_MONTH FROM a.EMISSAO) DESC""", ttl=600)

dados_pivot = df.pivot(index=['Loja', 'Grupo'], columns='Mês', values='VALOR').fillna(0)
st.dataframe(dados_pivot)


df = conn.query("""select c.DESCRICAO 'Grupo'
     , extract(YEAR_MONTH FROM a.EMISSAO) 'Mês'
     , sum(a.VALOR_TOTAL_NOTA) VALOR
  from compras_dbf a join cadastros b on a.CADASTRO_CODIGO=b.CODIGO and a.CADASTRO_LOJA=b.LOJA
					 join cadastros_grupos c on b.CADASTRO_GRUPO=c.CODIGO
 where a.OPERACAO_CODIGO  in (32,33)
   and a.CADASTRO>'2023-01-01 00:00:00'
   and b.CADASTRO_GRUPO IN (7, 10, 30)
 GROUP BY c.DESCRICAO
     , extract(YEAR_MONTH FROM a.EMISSAO)
 ORDER BY extract(YEAR_MONTH FROM a.EMISSAO) DESC""", ttl=600)

dados_pivot = df.pivot(index='Grupo', columns='Mês', values='VALOR').fillna(0)
st.dataframe(dados_pivot)

