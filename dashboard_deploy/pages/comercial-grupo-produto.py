import streamlit as st
import pandas as pd
from datetime import datetime

title = 'Análise comercial de grupo de produtos'
# st.set_page_config(page_title=title, layout="wide")
st.title(title)
st.sidebar.title(title)

# Initialize connection.
conn = st.connection('mysql', type='sql')

df = conn.query('select pm.prod_marc_id , pm.marca from produtos_marcas pm order by pm.marca', ttl=600)
marca_dict = dict(zip(df['prod_marc_id'], df['marca']))
marca = st.sidebar.selectbox("Marca", options=list(marca_dict.keys()), format_func=lambda x: marca_dict[x])

df = conn.query('select pgd.codigo , pgd.descricao from produtos_grupos_dbf pgd order by pgd.descricao', ttl=600)
grupo_dict = dict(zip(df['codigo'], df['descricao']))
grupo = st.sidebar.selectbox("Grupo", options=list(grupo_dict.keys()), format_func=lambda x: grupo_dict[x])



inicio_periodo = st.sidebar.date_input("Início do período", format="DD/MM/YYYY")
termino_periodo = st.sidebar.date_input("Término do período", format="DD/MM/YYYY")

# Convert dates to datetime with specific times
inicio_periodo_dt = datetime.combine(inicio_periodo, datetime.min.time())
termino_periodo_dt = datetime.combine(termino_periodo, datetime.max.time())

# Convert datetime to string format
inicio_periodo_str = inicio_periodo_dt.strftime("%Y-%m-%d %H:%M:%S")
termino_periodo_str = termino_periodo_dt.strftime("%Y-%m-%d %H:%M:%S")

st.write(f"Você selecionou a marca: {marca_dict[marca]}")
st.write(f"Você selecionou o grupo: {grupo_dict[grupo]}")
st.write(f"Data de início {inicio_periodo.strftime('%d/%m/%Y')} e data de término {termino_periodo.strftime('%d/%m/%Y')}.")


gerar_relatorio = st.button("Gerar relatório")

def formatar_valores(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if gerar_relatorio:
    sql = f"""select a.CODIGO SKU, a.CODIGO_X X, a.CODIGO_SEQUENCIA S, pm.marca Marca
                   , a.PRECO_PRAZO 'Preço'
                   , a.GIRO_PRODUTO 'Giro'
                   , a.CURVA_PRODUTO 'Curva'
                from produtos_dbf a left join produtos_marcas pm on a.prod_marc_id =pm.prod_marc_id 
                                    left join produtos_grupos_dbf pgd  on a.GRUPO_CODIGO =pgd.CODIGO 
               where a.FINALIDADE_CODIGO=1"""
    
    if marca:
        sql = sql + f'\n   AND a.prod_marc_id={marca}'
    
    if grupo:
        sql = sql + f'\n   AND a.GRUPO_CODIGO={grupo}'


    dfc = conn.query(sql, ttl=600, index_col=['SKU'])
    dfc_formatado = dfc.style.format({
        'Preço': formatar_valores,
        'Giro': formatar_valores
    })
    st.dataframe(dfc_formatado)
    st.write(f"Total de linhas: {dfc.shape[0]}")

##      skus = dfc.index
#    skus = dfc.index.to_numpy
#    st.write(skus)

#    for sku in skus:
#        st.write('SKU : '+ sku)
    