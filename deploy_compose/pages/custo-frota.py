import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página

import matplotlib.pyplot as plt
import re


# Configurar a página do Streamlit
st.set_page_config(page_title="Custo da Frota")

# Título do dashboard
st.title("Custo Frota")

# Selecionar período no Streamlit
st.subheader("Selecione o Período ")
data_inicio = st.date_input("Data Início", value=pd.to_datetime('2024-01-01'))
data_fim = st.date_input("Data Fim", value=pd.to_datetime('2024-12-31'))

# Criar a conexão com o banco de dados usando SQLAlchemy
# Função para criar conexão com o banco de dados
def criar_conexao():
    """Cria e retorna a conexão com o banco de dados."""
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@" \
          f"{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

engine = criar_conexao()
# Consultar dados do banco para o período selecionado
expedicao_df = pd.read_sql(
    f"""SELECT cv.PLACA, 
       cva.CADASTRO, 
       cva.COMBUSTIVEL_1_LITROS, 
       cva.COMBUSTIVEL_1_TIPO, 
       cva.COMBUSTIVEL_1_VALOR_TOTAL,
       cva.COMBUSTIVEL_2_LITROS, 
       cva.COMBUSTIVEL_2_TIPO, 
       cva.COMBUSTIVEL_2_VALOR_TOTAL, 
       cva.LOJA,
       cva.KM
    FROM cadastros_veiculos_abastecimentos cva
    JOIN cadastros_veiculos cv
      ON cva.CADASTRO_CODIGO = cv.CADASTRO_CODIGO
    WHERE cva.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'
    ORDER BY cva.CADASTRO ASC;""", 
    con=engine
)

# Fechar a conexão com o banco de dados
engine.dispose()

# Converter a coluna CADASTRO para datetime
expedicao_df['CADASTRO'] = pd.to_datetime(expedicao_df['CADASTRO'])

# Adicionar colunas de ano e mês
expedicao_df['ANO_MES'] = expedicao_df['CADASTRO'].dt.to_period('M')

# Ordenar o dataframe por "ANO_MES"
expedicao_df = expedicao_df.sort_values(by='ANO_MES')

# Exibir o dataframe no Streamlit
# st.dataframe(expedicao_df)

# Converter a coluna 'CADASTRO' para o formato de data
expedicao_df['CADASTRO'] = pd.to_datetime(expedicao_df['CADASTRO'])

# Extrair o ano e o mês da coluna 'CADASTRO' para criar uma nova coluna 'MES_ANO'
expedicao_df['MES_ANO'] = expedicao_df['CADASTRO'].dt.to_period('M')

# Agrupar por 'PLACA' e 'MES_ANO' e somar as colunas 'COMBUSTIVEL_1_LITROS' e 'COMBUSTIVEL_1_VALOR_TOTAL'
agrupado_df = expedicao_df.groupby(['PLACA', 'MES_ANO','LOJA']).agg({
    'COMBUSTIVEL_1_LITROS': 'sum',
    'COMBUSTIVEL_1_VALOR_TOTAL': 'sum'
}).reset_index()

# Ordenar o dataframe agrupado por "ANO_MES"
agrupado_df = agrupado_df.sort_values(by='LOJA')

# Exibir a tabela  agrupada no Streamlit
st.subheader("Consumo de Combustível")
st.dataframe(agrupado_df)

# Soma Total de Custo Por placa de cada Loja
agrupado_loja_df = expedicao_df.groupby(['LOJA','MES_ANO']).agg({
    'COMBUSTIVEL_1_VALOR_TOTAL' : 'sum'
}).reset_index()

# Ordenar o dataframe agrupado por "LOJA" e "PLACA"
agrupado_loja_df = agrupado_loja_df.sort_values(by=['LOJA'])

st.subheader("Consumo Total de Combustível por Placa e Loja")
st.dataframe(agrupado_loja_df)

agrupado_df = agrupado_df.pivot(index='PLACA', columns='MES_ANO', values='COMBUSTIVEL_1_VALOR_TOTAL')

# Exibir a tabela pivotada agrupada no Streamlit
agrupado_df = agrupado_df.fillna(0)
st.subheader("Consumo de Combustível Mes, Placa e Valor")
st.dataframe(agrupado_df)

# #  #Criando um gráfico de linha usando os valores pivotados
# st.subheader("Gráfico do Valor Total de Combustível por Placa e Mês")
# grafico_df = agrupado_df.pivot(index='MES_ANO', columns='PLACA', values='COMBUSTIVEL_1_VALOR_TOTAL')
# agrupado_df.fillna(0,inplace=True)
# st.bar_chart(agrupado_df)

engine = criar_conexao()

# Fazendo conexao para puxar dados de pedagio
veloe_df = pd.read_sql(f"""
      select id_transacao, placa, data_utilizacao, hora_utilizacao, endereco_estabelecimento, valor_cobrado 
      from veloe_extrato
      WHERE data_utilizacao  BETWEEN '{data_inicio}' AND '{data_fim}'
      order by data_utilizacao; """,
      con=engine
)

engine.dispose()

# Log do select 
print(veloe_df)

# Exibir o dataframe no Streamlit
# st.write('Para visualizar qual foi os dados puxado do select')
# st.dataframe(veloe_df)

# Agrupar por placa e mês, e somar os valores de valor_cobrado
veloe_df['data_utilizacao'] = pd.to_datetime(veloe_df['data_utilizacao']).dt.to_period('M')
agrupado_df = veloe_df.groupby(['placa', 'data_utilizacao'])['valor_cobrado'].sum().reset_index()
agrupado_df = agrupado_df.pivot(index='placa', columns='data_utilizacao', values='valor_cobrado')
agrupado_df = agrupado_df.fillna(0)
# Exibir o dataframe no Streamlit
st.subheader("Gasto Com Pedagio placa com tag")
st.dataframe(agrupado_df)


# Definir a consulta SQL com parâmetros para consultar pedagios em t
query = text("""
    SELECT D.LOJA, D.VENCIMENTO, D.VALOR, D.CENTRO_CUSTO_CODIGO, CC.DESCRICAO AS CENTRO_CUSTO_DESCRICAO, 
           D.DESCRICAO, D.OBS, C.USUARIO
    FROM despesas D
    LEFT JOIN modos_pagamentos M ON D.MODO_PGTO_CODIGO = M.CODIGO
    LEFT JOIN caixas C ON D.CAIXA_CODIGO = C.CODIGO AND D.CAIXA_LOJA = C.LOJA
    LEFT JOIN cadastros F ON D.CADASTRO_CODIGO = F.CODIGO AND D.CADASTRO_LOJA = F.LOJA
    LEFT JOIN cadastros T ON D.TRANSPORTADORA_CODIGO = T.CODIGO AND D.TRANSPORTADORA_LOJA = T.LOJA
    LEFT JOIN centros_custo CC ON D.CENTRO_CUSTO_CODIGO = CC.CODIGO
    WHERE CC.DESCRICAO = 'PEDAGIO' 
      AND D.VENCIMENTO BETWEEN :data_inicio AND :data_fim
      AND (D.DESCRICAO LIKE '%PLACA%' OR D.OBS LIKE '%PLACA%')
    ORDER BY D.VENCIMENTO DESC;
""")

# Consultar dados do banco para o período selecionado
with engine.connect() as connection:
    pedagio_sem_tag_df = pd.read_sql(query, con=connection, params={"data_inicio": data_inicio, "data_fim": data_fim})

# Função para extrair o número da placa
def extrair_placa(texto):
    placa_pattern = r'\b([A-Z]{3}\s?-?\d{4}|[A-Z]{3}\s?\d[A-Z]\d{2}|[a-zA-Z]{3}\d{4})\b'
    match = re.search(placa_pattern, texto)
    if match:
        placa = match.group(0)
        placa = placa.replace(' ', '').replace('-', '')
        return placa
    return None

# Criar o DataFrame 'filtra_placa' com as colunas especificadas
filtra_placa = pedagio_sem_tag_df[['LOJA', 'VENCIMENTO', 'VALOR', 'CENTRO_CUSTO_DESCRICAO', 'DESCRICAO', 'OBS']].copy()

# Extrair a placa da coluna 'DESCRICAO' e 'OBS'
filtra_placa['placa'] = filtra_placa['DESCRICAO'].apply(lambda x: extrair_placa(x) if pd.notnull(x) else None)
filtra_placa['placa'] = filtra_placa['placa'].combine_first(filtra_placa['OBS'].apply(lambda x: extrair_placa(x) if pd.notnull(x) else None))

# Filtrar apenas as linhas que possuem uma placa identificada
filtra_placa = filtra_placa[filtra_placa['placa'].notna()]

# Criar DataFrame 'nv_placa_df'
nv_placa_df = filtra_placa[['LOJA', 'VENCIMENTO', 'VALOR', 'CENTRO_CUSTO_DESCRICAO', 'DESCRICAO', 'OBS','placa']].copy()

# log do codigo
print(nv_placa_df)
# Exibir o DataFrame no Streamlit para ver log  # st.dataframe(nv_placa_df)
# st.dataframe(nv_placa_df)

# Converter a coluna 'VENCIMENTO' para datetime e criar coluna de mês
nv_placa_df['VENCIMENTO'] = pd.to_datetime(nv_placa_df['VENCIMENTO'])
nv_placa_df['mes'] = nv_placa_df['VENCIMENTO'].dt.to_period('M')

# Agrupar por colunas 'LOJA', 'mes', 'placa', 'CENTRO_CUSTO_DESCRICAO' e somar os valores
resultado_df = nv_placa_df.groupby(['LOJA', 'mes', 'placa']).agg({'VALOR': 'sum'}).reset_index()

st.subheader("Gasto Com Pedagio placa sem tag")
st.dataframe(resultado_df)
# fim func


# Pivotar a tabela com índice sendo 'placa' e 'LOJA', colunas sendo 'mes' e valores sendo 'VALOR'
resultado_pivot_df = resultado_df.pivot_table(index=['placa', 'LOJA'], columns='mes', values='VALOR', aggfunc='sum').reset_index()
resultado_pivot_df = resultado_pivot_df.fillna(0)
# Ordenar o dataframe agrupado por "LOJA" e "PLACA"
resultado_pivot_df = resultado_pivot_df.sort_values(by=['LOJA'])
# Mostrar o DataFrame resultante
st.subheader("Gasto Com Pedagio placa sem tag")
st.dataframe(resultado_pivot_df)