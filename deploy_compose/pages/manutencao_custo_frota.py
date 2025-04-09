import streamlit as st 
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine , text
from datetime import datetime
import re

# Título e configuração da página
titulo = 'Custo manutencao frota'
st.set_page_config(page_title=titulo, layout="wide")
st.title(titulo)

# Selecionar período no Streamlit
st.subheader("Selecione o Período de Entrega")
data_inicio = st.date_input("Data Início", value=pd.to_datetime('2024-10-01'))
data_fim = st.date_input("Data Fim", value=pd.to_datetime('2024-10-31'))

# Conectar ao banco de dados
engine = create_engine('mysql+pymysql://root:root@10.50.1.252:3306/autogeral')

# Definir a consulta SQL com parâmetros para consultar pedagios em t
query = text("""
      SELECT P.LOJA, P.EMISSAO, P.OPERACAO_CODIGO, P.OPERACAO_DESCRICAO, P.CLIENTE_NOME, P.VALOR_TOTAL, A.DESCRICAO AS CENTRO_CUSTO, P.OBS
      FROM pedidos_dbf AS P
      LEFT JOIN vendas V ON (V.TIPO = 'PEDIDO' AND P.PEDIDO = V.CODIGO AND P.LOJA = V.LOJA)
      LEFT JOIN cadastros C ON (P.CADASTRO_CODIGO = C.CODIGO AND P.CADASTRO_LOJA = C.LOJA)
      LEFT JOIN centros_custo A ON P.CENTRO_CUSTO_CODIGO = A.CODIGO
      WHERE P.OPERACAO_DESCRICAO = 'BAIXA PARA CONSUMO' 
        AND A.DESCRICAO LIKE '%FROTA%'
        AND P.EMISSAO BETWEEN :data_inicio AND :data_fim
      ORDER BY P.LOJA;
""")

# Consultar dados do banco para o período selecionado
with engine.connect() as connection:
    manutencao_df = pd.read_sql(query, con=connection, params={"data_inicio": data_inicio, "data_fim": data_fim})

# Criar o DataFrame 'manutencao' com as colunas especificadas
manutencao = manutencao_df[['LOJA', 'EMISSAO', 'OPERACAO_CODIGO', 'OPERACAO_DESCRICAO', 'CLIENTE_NOME', 'VALOR_TOTAL', 'CENTRO_CUSTO', 'OBS']].copy()

# Logs de verificacao
print(manutencao)

# Converter a coluna 'EMISSAO' para datetime e criar coluna de DATA-MES
manutencao['EMISSAO'] = pd.to_datetime(manutencao['EMISSAO'])
manutencao['EMISSAO'] = manutencao['EMISSAO'].dt.to_period('M')

# Agrupar por colunas 'LOJA', 'EMISSAO', 'OPERACAO_CODIGO', 'OPERACAO_DESCRICAO' e 'CENTRO_CUSTO' e somar os valores
resultado_df = manutencao.groupby(['EMISSAO', 'LOJA', 'OPERACAO_CODIGO', 'OPERACAO_DESCRICAO', 'CENTRO_CUSTO']).agg({'VALOR_TOTAL': 'sum'}).reset_index()

# Selecionar colunas para exibir no Streamlit
resultado_df = resultado_df[['EMISSAO', 'LOJA', 'VALOR_TOTAL', 'OPERACAO_CODIGO', 'OPERACAO_DESCRICAO', 'CENTRO_CUSTO']].copy()
st.dataframe(resultado_df)

# Função para extrair o número da placa
def extrair_placa(texto):
    placa_pattern = r'\b([A-Z]{3}\s?-?\d{4}|[A-Z]{3}\s?\d[A-Z]\d{2}|[a-zA-Z]{3}\d{4})\b'
    match = re.search(placa_pattern, texto)
    if match:
        placa = match.group(0)
        placa = placa.replace(' ', '').replace('-', '')
        return placa
    return None

# Aplicar a função para extrair a placa na coluna 'OBS'
manutencao['PLACA'] = manutencao['OBS'].apply(lambda x: extrair_placa(x) if pd.notnull(x) else None)

# Criar novo DataFrame 'custo_por_placa_df' contendo as colunas 'EMISSAO', 'LOJA', 'VALOR_TOTAL' e 'PLACA'
custo_por_placa_df = manutencao[['EMISSAO', 'LOJA', 'VALOR_TOTAL', 'PLACA']].copy()

# Exibir o novo DataFrame no Streamlit
st.dataframe(custo_por_placa_df)
