import locale
import streamlit as st
import pandas as pd
from datetime import datetime

title = 'Índice de venda casada'
st.set_page_config(page_title=title)
st.title(title)
st.sidebar.title(title)

# Initialize connection.
conn = st.connection('mysql', type='sql')

df = conn.query('SELECT codigo, nome from autogeral.lojas order by codigo', ttl=600)

loja_dict = dict(zip(df['codigo'], df['nome']))

loja = st.sidebar.selectbox("Unidade", options=list(loja_dict.keys()), format_func=lambda x: loja_dict[x])

tipo = st.sidebar.radio(
    "Tipo",
    ["Entradas", "Saídas"],
    captions=[
        "Entradas",
        "Saídas"
    ],
)

inicio_periodo = st.sidebar.date_input("Início do período", format="DD/MM/YYYY")
termino_periodo = st.sidebar.date_input("Término do período", format="DD/MM/YYYY")

# Convert dates to datetime with specific times
inicio_periodo_dt = datetime.combine(inicio_periodo, datetime.min.time())
termino_periodo_dt = datetime.combine(termino_periodo, datetime.max.time())

# Convert datetime to string format
inicio_periodo_str = inicio_periodo_dt.strftime("%Y-%m-%d %H:%M:%S")
termino_periodo_str = termino_periodo_dt.strftime("%Y-%m-%d %H:%M:%S")

gerar_relatorio = st.button("Gerar relatório")

st.write(f"Você selecionou {tipo} da loja {loja}, {loja_dict[loja]}, data de inicio {inicio_periodo} e data de término {termino_periodo}.")

if gerar_relatorio:
    query = conn.query (f"""select a.romaneio
     , a.loja
     , (a.cadastro_codigo*100+a.cadastro_loja) cada_id
     , a.situacao
     , a.cadastro
     , a.vendedor_codigo
     , b.produto_codigo
     , 'PRONTO'
     , b.quantidade
     , a.cadastro
     , null as forn_id
  from romaneios_dbf a join romaneios_itens_dbf b on a.romaneio=b.romaneio and a.loja=b.loja
where a.LOJA={loja}
  AND a.cadastro BETWEEN '{inicio_periodo_str}' AND '{termino_periodo_str}'
  and a.operacao_codigo in (1,2,3)
union
select a.romaneio, a.loja
     , (a.cadastro_codigo*100+a.cadastro_loja) cada_id
     , a.situacao
     , a.cadastro
     , a.vendedor_codigo
     , d.produto_codigo
     , 'CASADA'
     , d.quantidade
     , a.cadastro
     , (c.CADASTRO_CODIGO*100+c.CADASTRO_LOJA) forn_id
  from romaneios_dbf a join compras_pedidos c on c.ROMANEIO_CODIGO=a.ROMANEIO and c.ROMANEIO_LOJA=a.LOJA
                       join compras_pedidos_itens d on c.COMPRA_PEDIDO=d.COMPRA_PEDIDO and c.LOJA=d.LOJA
where a.LOJA={loja}
  AND a.cadastro BETWEEN '{inicio_periodo_str}' AND '{termino_periodo_str}'
  and a.operacao_codigo in (1,2,3)""", ttl=600)
    
    query_vendas = df = conn.query(f"""  
  SELECT V.TIPO, V.CODIGO, V.LOJA AS LOJA_REQUERENTE, E.GIRO, E.QUANTIDADE_MINIMA
     , E.CURVA, P.PRECO_PRAZO, PC.CUSTO_PONDERADO
     , CP.CADASTRO_CODIGO AS LOJA_REQUERIDA, V.EMISSAO, V.SITUACAO, VD.DESCRICAO AS VENDEDOR
     , VI.CODIGO_X, VI.CODIGO_SEQUENCIA, VI.DESCRICAO, VI.QUANTIDADE
FROM vendas V JOIN vendedores_dbf VD ON V.VENDEDOR_CODIGO=VD.CODIGO
              JOIN romaneios_dbf R ON V.CODIGO=R.DESTINO_CODIGO AND V.LOJA=R.DESTINO_LOJA AND V.TIPO = CASE R.DESTINO_TIPO WHEN 1 THEN 'NFE' WHEN 2 THEN 'NFSE'                              WHEN 3 THEN 'NF' WHEN 4 THEN 'PEDIDO' WHEN 5 THEN 'CUPOM'                              WHEN 8 THEN 'SAT' END
              JOIN compras_pedidos CP ON CP.ROMANEIO_CODIGO=R.ROMANEIO AND CP.ROMANEIO_LOJA=R.LOJA
              JOIN compras_pedidos_itens VI ON CP.COMPRA_PEDIDO=VI.COMPRA_PEDIDO AND V.LOJA=VI.LOJA
              JOIN produtos_dbf P ON VI.PRODUTO_CODIGO=P.CODIGO
              JOIN produto_estoque E ON P.CODIGO=E.PRODUTO_CODIGO AND E.LOJA=V.LOJA
              LEFT JOIN produto_custo PC ON E.PRODUTO_CODIGO=PC.PRODUTO_CODIGO AND E.LOJA=PC.LOJA_CODIGO
WHERE V.LOJA={loja}
  AND V.EMISSAO BETWEEN '{inicio_periodo_str}' AND '{termino_periodo_str}'
  AND CP.ROMANEIO_CODIGO IS NOT NULL
  AND CP.ROMANEIO_CODIGO > 0;
    """, ttl=600)
    # df = conn.query(query, ttl=600)
    st.write(df)
    st.write(f"Relatório gerado com {df.shape[0]} linhas.")
    st.write(f"Relatório gerado com {df.shape[1]} colunas.")
    st.write(f"Relatório gerado com {df.shape[0]} linhas e {df.shape[1]} colunas.")


