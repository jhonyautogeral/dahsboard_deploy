import streamlit as st
import pandas as pd
from datetime import datetime

titulo = 'Apuração do ICMS'
st.set_page_config(page_title=titulo, layout="wide")
st.title(titulo)
st.sidebar.title(titulo)

# Initialize connection.
conn = st.connection('mysql', type='sql')

# Perform query.
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

st.write(f"Você selecionou {tipo} da loja {loja}, {loja_dict[loja]}")
st.write(f"Data de início {inicio_periodo.strftime('%d/%m/%Y')} e data de término {termino_periodo.strftime('%d/%m/%Y')}.")

def formatar_cfop(valor):
    return f"{valor}".replace(",", ".")

def formatar_valores(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


if gerar_relatorio:
    query = f"""select b.CFOP_EMPRESA CFOP
                     , SUM(VALOR_UNIDADE_TRIBUTADA*QUANTIDADE_TRIBUTADA) valor_contabil
                     -- , SUM(VALOR_TOTAL_BRUTO) valor_contabil, SUM(VALOR_TOTAL_BRUTO) valor_contabil
                     , SUM(ICMS_BASE_EMPRESA) base_icms
                     , SUM(ICMS_VALOR_EMPRESA) valor_icms
                  from compras_dbf a join compras_itens_dbf b on a.compra=b.compra and a.loja=b.loja
                 where a.cadastro between '{inicio_periodo_str}' and '{termino_periodo_str}'
                   and a.loja={loja} 
                 group by b.CFOP_EMPRESA
                """
    dfc = conn.query(query, ttl=600)

    query = f"""select CASE WHEN c.TIPO='NFE' THEN d.CFOP
            WHEN c.TIPO='SAT' THEN e.CFOP
            WHEN c.TIPO='NFCE' THEN f.CFOP
            ELSE 0
		END CFOP
     , sum(c.QUANTIDADE*c.VALOR_UNIDADE) valor_contabil 
     , sum(CASE WHEN c.TIPO='NFE' THEN d.BASE_ICMS_VALOR
            WHEN c.TIPO='SAT' THEN e.BASE_ICMS_VALOR
            WHEN c.TIPO='NFCE' THEN f.BASE_ICMS_VALOR
            ELSE 0
		END) base_icms
	, sum(CASE WHEN c.TIPO='NFE' THEN d.ICMS_VALOR
            WHEN c.TIPO='SAT' THEN e.ICMS_VALOR
            WHEN c.TIPO='NFCE' THEN f.ICMS_VALOR
            ELSE 0
		END) valor_icms
  from vendas a join movimentos_operacoes b on a.operacao_codigo=b.codigo 
				join vendas_itens c on a.tipo=c.tipo and a.loja=c.loja and a.codigo=c.codigo
                left join nfes_itens d on c.item=d.item and c.loja=d.loja and c.codigo=d.nfe and c.tipo='NFE'
                left join sats_itens e on c.item=e.item and c.loja=e.loja and c.codigo=e.sat and c.tipo='SAT'
                left join nfces_itens f on c.item=f.item and c.loja=f.loja and c.codigo=f.NFCE and c.tipo='NFCE'
where a.cadastro between '{inicio_periodo_str}' and '{termino_periodo_str}'
  and a.situacao='NORMAL'
  and a.loja={loja}
  and b.saida=0
   and a.tipo in ('NFE','NFCE','NF','CUPOM','SAT')
group by CFOP
                """
    dfv = conn.query(query, ttl=600)

    dft = pd.concat([dfc, dfv], axis=0);
    dft.set_index('CFOP', inplace=True)

    # Aplicar GroupBy pelo índice e somar os valores das colunas
    dft_grouped = dft.groupby(dft.index).sum()

    dft_grouped.rename(columns={'valor_contabil': 'Valor Contábil', 'base_icms': 'Base ICMS', 'valor_icms': 'Valor ICMS'}, inplace=True)

    dft_grouped_style = dft_grouped.style.format({
#        'CFOP': formatar_cfop,
        'Valor Contábil': formatar_valores,
        'Base ICMS': formatar_valores,
        'Valor ICMS': formatar_valores
    })

    
    st.dataframe(dft_grouped_style)
    st.write(f"Total de linhas: {dft_grouped.shape[0]}")


