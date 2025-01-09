import locale
import streamlit as st
import pandas as pd

title = 'Índice de cruzamento do catálogo Fraga'
st.set_page_config(page_title=title)
st.title(title)
st.sidebar.title('Cruzamento do catálogo Fraga')

# Initialize connection.
conn = st.connection('fraga', type='sql')

query = f"""select c.Nome, count(b.Id) produtos_da_marca
  from produto b left join marca c on b.MarcaId=c.Id
group by c.Id, c.Nome;
"""

dfMarcas = conn.query(query, ttl=600, index_col='Nome')

query = f"""select c.Nome, count(b.Id) produtos_cruzados
  from produtodistribuidor a join produto b on a.ProdutoId=b.Id
                             left join marca c on b.MarcaId=c.Id
group by c.Id, c.Nome
"""

dfCruzados = conn.query(query, ttl=600, index_col='Nome')


connAutoGeral = st.connection('mysql', type='sql')

query = f"""select m.marca Nome, count(p.CODIGO) produtos_ag
  from autogeral.produtos_marcas m join autogeral.produtos_dbf p on m.prod_marc_id=p.prod_marc_id
 where p.FINALIDADE_CODIGO=1
 group by m.prod_marc_id, m.marca"""

dfAutoGeral = connAutoGeral.query(query, ttl=600, index_col='Nome')

dfFraga = dfMarcas.merge(dfCruzados, on='Nome', how='left')
dfFraga['Índice de cruzamento'] = dfFraga['produtos_cruzados'] / dfFraga['produtos_da_marca']
dfFraga.sort_values('produtos_da_marca', ascending=False, inplace=True)

dfFraga = dfFraga.merge(dfAutoGeral, on='Nome', how='left')


dicionarioColunas = {
  "produtos_da_marca" : "Cadastros Fraga",
  "produtos_cruzados": "Cadastros Cruzados",
  "produtos_ag": "Cadastros AG"  
}

dfFraga.rename(columns = dicionarioColunas, inplace = True)

def format_number(x):
    return locale.format_string("%.0f", x, grouping=True)

# Aplicar formatação às colunas
dfFraga = dfFraga.style.format({
    'Índice de cruzamento': "{:.2%}",
    'Cadastros Fraga': format_number,
    'Cadastros Cruzados': format_number,
    'Cadastros AG': format_number
})


st.dataframe(dfFraga, height=3000)

