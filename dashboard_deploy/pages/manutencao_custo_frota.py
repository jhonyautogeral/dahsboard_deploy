import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import re

# Configuração da página do Streamlit
st.set_page_config(page_title="Custo Manutenção Frota", layout="wide")
st.title("Custo Manutenção Frota")

# Seleção de período
st.subheader("Selecione o Período de Entrega")
data_inicio = st.date_input("Data Início", value=pd.to_datetime('2024-10-01'))
data_fim = st.date_input("Data Fim", value=pd.to_datetime('2024-10-31'))

# Função para criar a conexão com o banco de dados com cache
@st.cache_resource
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

# Consulta SQL segura e cacheada
@st.cache_data(ttl=600)
def consultar_dados(query, params=None):
    engine = criar_conexao()
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params=params)

# Query SQL com placeholders para segurança
query = text("""
    SELECT P.LOJA, P.EMISSAO, P.OPERACAO_CODIGO, P.OPERACAO_DESCRICAO, 
           P.CLIENTE_NOME, P.VALOR_TOTAL, A.DESCRICAO AS CENTRO_CUSTO, P.OBS
    FROM pedidos_dbf AS P
    LEFT JOIN vendas V ON (V.TIPO = 'PEDIDO' AND P.PEDIDO = V.CODIGO AND P.LOJA = V.LOJA)
    LEFT JOIN cadastros C ON (P.CADASTRO_CODIGO = C.CODIGO AND P.CADASTRO_LOJA = C.LOJA)
    LEFT JOIN centros_custo A ON P.CENTRO_CUSTO_CODIGO = A.CODIGO
    WHERE P.OPERACAO_DESCRICAO = 'BAIXA PARA CONSUMO' 
      AND A.DESCRICAO LIKE '%FROTA%'
      AND P.EMISSAO BETWEEN :data_inicio AND :data_fim
    ORDER BY P.LOJA;
""")

# Executando a consulta
manutencao_df = consultar_dados(query, params={"data_inicio": data_inicio, "data_fim": data_fim})

# Manipulação dos dados
manutencao_df['EMISSAO'] = pd.to_datetime(manutencao_df['EMISSAO']).dt.to_period('M')

# Agrupamento por colunas relevantes
resultado_df = manutencao_df.groupby(['EMISSAO', 'LOJA', 'OPERACAO_CODIGO', 'OPERACAO_DESCRICAO', 'CENTRO_CUSTO']).agg({
    'VALOR_TOTAL': 'sum'
}).reset_index()

# Exibição do DataFrame agrupado
st.subheader("Resumo de Manutenção")
st.dataframe(resultado_df)

# Função otimizada para extrair placas
@st.cache_data
def extrair_placa(texto):
    placa_pattern = r'\b[A-Z]{3}\s?-?\d{4}\b'
    match = re.search(placa_pattern, texto or "")
    return match.group(0).replace('-', '').replace(' ', '') if match else None

# Aplicação da função de extração de placas
manutencao_df['PLACA'] = manutencao_df['OBS'].apply(extrair_placa)

# DataFrame final com colunas relevantes
custo_por_placa_df = manutencao_df[['EMISSAO', 'LOJA', 'VALOR_TOTAL', 'PLACA']].dropna(subset=['PLACA'])

# Exibição do DataFrame final
st.subheader("Custos por Placa")
st.dataframe(custo_por_placa_df)

