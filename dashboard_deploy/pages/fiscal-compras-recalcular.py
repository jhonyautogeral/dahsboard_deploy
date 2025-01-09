import streamlit as st
import pandas as pd
from datetime import datetime

title = 'Compras a recalcular a triburação'
st.set_page_config(page_title=title, layout="wide")
st.title(title)
st.sidebar.title(title)

# Initialize connection.
conn = st.connection('mysql', type='sql')

inicio_periodo = st.sidebar.date_input("Início do período", format="DD/MM/YYYY")
termino_periodo = st.sidebar.date_input("Término do período", format="DD/MM/YYYY")

# Convert dates to datetime with specific times
inicio_periodo_dt = datetime.combine(inicio_periodo, datetime.min.time())
termino_periodo_dt = datetime.combine(termino_periodo, datetime.max.time())

# Convert datetime to string format
inicio_periodo_str = inicio_periodo_dt.strftime("%Y-%m-%d %H:%M:%S")
termino_periodo_str = termino_periodo_dt.strftime("%Y-%m-%d %H:%M:%S")


gerar_relatorio = st.button("Gerar relatório")

st.write(f"Você selecionou a data de inicio {inicio_periodo} e data de término {termino_periodo}.")

if gerar_relatorio:
    query = f"""SELECT 
    b.LOJA,
    b.COMPRA,
    b.NUMERO_NOTA,
    b.FORNECEDOR_NOME,
    a.CLASSE_FISCAL 'NCM', 
    a.EXCESSAO_IPI 'Ex.NCM',
    c.DESCRICAO_SIMPLIFICADA 'Operação', 
    a.ICMS_CST_EMPRESA AS 'CST ICMS',
    a.CFOP_EMPRESA AS CFOP,
    a.PIS_CST_EMPRESA AS 'CST PIS',
    a.COFINS_CST_EMPRESA AS 'CST COFINS'
FROM 
    compras_itens_dbf a
JOIN 
    compras_dbf b ON a.COMPRA = b.COMPRA AND b.loja = a.loja 
JOIN 
    movimentos_operacoes c ON b.OPERACAO_CODIGO = c.CODIGO 
WHERE (a.PIS_CST_EMPRESA IS NULL OR a.COFINS_CST_EMPRESA IS NULL OR a.CFOP_EMPRESA IS NULL)
    AND b.CADASTRO BETWEEN '{inicio_periodo_str}' AND '{termino_periodo_str}' 
                """
    dados = conn.query(query, ttl=600)
    # dados = pd.read_sql_query(query, conn)
    st.dataframe(dados)
    st.write(f"Total de linhas: {dados.shape[0]}")



