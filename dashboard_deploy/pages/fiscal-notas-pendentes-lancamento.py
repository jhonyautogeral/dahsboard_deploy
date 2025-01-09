import streamlit as st

title = 'Notas emitidas contas a Auto Geral pendentes de lançamento'
st.set_page_config(page_title=title, layout="wide")
st.title(title)
st.sidebar.title(title)

conn = st.connection('mysql', type='sql')

query = """select a.LOJA, a.EMISSAO, a.NFE_CHAVE_ACESSO
     , b.NOME FORNECEDOR_NOME
     , concat(substring(a.NFE_CHAVE_ACESSO, 7, 2), '.', substring(a.NFE_CHAVE_ACESSO, 9, 3), '.',  substring(a.NFE_CHAVE_ACESSO, 12, 3), '/', substring(a.NFE_CHAVE_ACESSO, 15, 4), '-', substring(a.NFE_CHAVE_ACESSO, 19, 2)) FORNECEDOR_CNPJ
  from compras_nfe_xml_processar a left join cadastros b on substring(a.NFE_CHAVE_ACESSO, 7, 14)=b.CPF_CNPJ
 where a.LOJA is not null;"""

dados = conn.query(query, ttl=600, index_col=['NFE_CHAVE_ACESSO'])

dicionarioColunas = {
  "LOJA" : "Loja",
  "EMISSAO": "Emissão",
  "FORNECEDOR_NOME": "Emitente",
  "FORNECEDOR_CNPJ": "CNPJ"
}

dados.rename(columns = dicionarioColunas, inplace = True)


st.dataframe(dados)
st.write(f"Total de linhas: {dados.shape[0]}")
