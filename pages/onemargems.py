import streamlit as st
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página
    
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

# Criar a conexão com o banco de dados usando SQLAlchemy
engine = create_engine('mysql+pymysql://erpj-ws:erpj-ws-homologacao@10.50.1.252:3306/autogeral')

if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
# Consultar dados do banco para o período selecionado
query = """
SELECT V.TIPO, V.CODIGO, V.LOJA AS LOJA_REQUERENTE
     , O.DESCRICAO_SIMPLIFICADA OPERACAO
     , E.GIRO, E.QUANTIDADE_MINIMA, E.CURVA
     , V.EMISSAO, V.SITUACAO, VD.DESCRICAO AS VENDEDOR
     , P.CODIGO_X, P.CODIGO_SEQUENCIA, P.DESCRICAO
     , VI.QUANTIDADE
     , VI.VALOR_UNIDADE, VI.CUSTO_UNIDADE, VI.VALOR_UNIDADE-VI.CUSTO_UNIDADE MARGEM
     , L.DESCRICAO AS LINHA
FROM vendas V LEFT JOIN vendedores_dbf VD ON V.VENDEDOR_CODIGO=VD.CODIGO
              JOIN movimentos_operacoes O ON V.OPERACAO_CODIGO=O.CODIGO
			  LEFT JOIN vendas_itens VI ON V.TIPO = VI.TIPO and V.CODIGO = VI.CODIGO and  V.LOJA = VI.LOJA
              LEFT JOIN produtos_dbf P ON VI.PRODUTO_CODIGO=P.CODIGO
              LEFT JOIN produto_estoque E ON P.CODIGO=E.PRODUTO_CODIGO AND E.LOJA=V.LOJA
              LEFT JOIN produto_linha L on P.LINHA_CODIGO = L.CODIGO
WHERE V.OPERACAO_CODIGO IN (1,2,3,8,9)
  AND V.SITUACAO='NORMAL'
  AND V.LOJA=8
  AND V.EMISSAO BETWEEN '2024-01-01' AND '2024-11-15' ;
"""

data = pd.read_sql(query, engine)

# Exemplo de processamento ou visualização dos dados
# st.write(data.head())
# Streamlit layout

st.set_page_config(page_title="Análise Financeira")
st.title("Dashboard de Análise de Margens")

# Transformações para análise
data['EMISSAO'] = pd.to_datetime(data['EMISSAO'])  # Converter para datetime

data['MES'] = data['EMISSAO'].dt.month_name()
data['ANO'] = data['EMISSAO'].dt.year
data['DIA_SEMANA'] = data['EMISSAO'].dt.day_name()

# Ordenar os dias da semana corretamente
dias_ordenados = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Filtrar dados para as linhas LEVE e PESADO
data_leve = data[data['LINHA'] == 'LEVE']
data_pesado = data[data['LINHA'] == 'Pesada']

# Filtrar dados para as OPERACAO Venda e Devolução do cliente
venda = data[data['OPERACAO'] == 'Venda']
devolucao_cliente = data[data['OPERACAO'] == 'Devolução do cliente']

# Agrupamentos para gráfico de barras e mapa de calor
margem_por_mes_leve = data_leve.groupby('MES')['MARGEM'].mean().reset_index()
margem_por_mes_pesado = data_pesado.groupby('MES')['MARGEM'].mean().reset_index()
margem_por_mes_venda = venda.groupby('MES')['MARGEM'].mean().reset_index()
margem_por_mes_devolucao = devolucao_cliente.groupby('MES')['MARGEM'].mean().reset_index()

margem_por_dia_semana_leve = data_leve.groupby(['MES', 'DIA_SEMANA'])['MARGEM'].mean().unstack().reindex(columns=dias_ordenados)
margem_por_dia_semana_pesado = data_pesado.groupby(['MES', 'DIA_SEMANA'])['MARGEM'].mean().unstack().reindex(columns=dias_ordenados)
margem_por_dia_semana_venda = venda.groupby(['MES', 'DIA_SEMANA'])['MARGEM'].mean().unstack().reindex(columns=dias_ordenados)
margem_por_dia_semana_devolucao = devolucao_cliente.groupby(['MES', 'DIA_SEMANA'])['MARGEM'].mean().unstack().reindex(columns=dias_ordenados)

# Seção: DataFrames
st.header("Tabelas de Resumo")

st.subheader("Média, Mínima e Máxima de Margens por LINHA")
linha_margem = data.groupby('LINHA')['MARGEM'].agg(['mean', 'min', 'max']).reset_index()
st.dataframe(linha_margem)

st.subheader("Média, Mínima e Máxima de Margens por OPERAÇÃO")
operacao_margem = data.groupby('OPERACAO')['MARGEM'].agg(['mean', 'min', 'max']).reset_index()
st.dataframe(operacao_margem)

# Seção: Gráficos
st.header("Visualizações Gráficas")

# Gráfico de barras: Margens por mês (LEVE)
st.subheader("Margens Médias ao Longo do Tempo - Linha LEVE")
fig, ax = plt.subplots(figsize=(12, 6))
margem_por_mes_leve.plot(x='MES', y='MARGEM', kind='bar', ax=ax, legend=False)
ax.set_ylabel("Média da Margem")
ax.set_xlabel("Mês")
ax.set_title("Média da Margem por Mês - Linha LEVE")
st.pyplot(fig)

# Gráfico de barras: Margens por mês (PESADO)
st.subheader("Margens Médias ao Longo do Tempo - Linha PESADO")
fig, ax = plt.subplots(figsize=(12, 6))
margem_por_mes_pesado.plot(x='MES', y='MARGEM', kind='bar', ax=ax, legend=False)
ax.set_ylabel("Média da Margem")
ax.set_xlabel("Mês")
ax.set_title("Média da Margem por Mês - Linha PESADO")
st.pyplot(fig)

# Gráfico de barras: Margens por mês (Venda)
st.subheader("Margens Médias ao Longo do Tempo - Operação Venda")
fig, ax = plt.subplots(figsize=(12, 6))
margem_por_mes_venda.plot(x='MES', y='MARGEM', kind='bar', ax=ax, legend=False)
ax.set_ylabel("Média da Margem")
ax.set_xlabel("Mês")
ax.set_title("Média da Margem por Mês - Operação Venda")
st.pyplot(fig)

# Gráfico de barras: Margens por mês (Devolução do cliente)
st.subheader("Margens Médias ao Longo do Tempo - Operação Devolução do Cliente")
fig, ax = plt.subplots(figsize=(12, 6))
margem_por_mes_devolucao.plot(x='MES', y='MARGEM', kind='bar', ax=ax, legend=False)
ax.set_ylabel("Média da Margem")
ax.set_xlabel("Mês")
ax.set_title("Média da Margem por Mês - Operação Devolução do Cliente")
st.pyplot(fig)

# Mapa de calor: Margens por dia da semana (LEVE)
st.subheader("Mapa de Calor de Margens por Dia da Semana - Linha LEVE")
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(margem_por_dia_semana_leve, annot=True, fmt=".2f", cmap="Blues", ax=ax)
ax.set_ylabel("Mês")
ax.set_xlabel("Dia da Semana")
ax.set_title("Mapa de Calor das Margens por Dia da Semana - Linha LEVE")
st.pyplot(fig)

# Mapa de calor: Margens por dia da semana (PESADO)
st.subheader("Mapa de Calor de Margens por Dia da Semana - Linha PESADO")
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(margem_por_dia_semana_pesado, annot=True, fmt=".2f", cmap="Blues", ax=ax)
ax.set_ylabel("Mês")
ax.set_xlabel("Dia da Semana")
ax.set_title("Mapa de Calor das Margens por Dia da Semana - Linha PESADO")
st.pyplot(fig)

# Mapa de calor: Margens por dia da semana (Venda)
st.subheader("Mapa de Calor de Margens por Dia da Semana - Operação Venda")
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(margem_por_dia_semana_venda, annot=True, fmt=".2f", cmap="Blues", ax=ax)
ax.set_ylabel("Mês")
ax.set_xlabel("Dia da Semana")
ax.set_title("Mapa de Calor das Margens por Dia da Semana - Operação Venda")
st.pyplot(fig)

# Mapa de calor: Margens por dia da semana (Devolução do cliente)
st.subheader("Mapa de Calor de Margens por Dia da Semana - Operação Devolução do Cliente")
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(margem_por_dia_semana_devolucao, annot=True, fmt=".2f", cmap="Blues", ax=ax)
ax.set_ylabel("Mês")
ax.set_xlabel("Dia da Semana")
ax.set_title("Mapa de Calor das Margens por Dia da Semana - Operação Devolução do Cliente")
st.pyplot(fig)

# Conclusão
st.info("Dashboard finalizado. Explore as análises interativas acima!")

