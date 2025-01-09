import streamlit as st 
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from datetime import datetime

# Título e configuração da página
titulo = 'Romaneios cancelados por loja e data de cadastro'
st.set_page_config(page_title=titulo, layout="wide")
st.title(titulo)

# Selecionar período no Streamlit
st.subheader("Selecione o Período de Entrega")
data_inicio = st.date_input("Data Início", value=pd.to_datetime('2024-01-01'))
data_fim = st.date_input("Data Fim", value=pd.to_datetime('2024-12-31'))

# Conectar ao banco de dados
engine = create_engine('mysql+pymysql://root:root@10.50.1.252:3306/autogeral')

# Definir a consulta SQL, substituindo a data pelo valor selecionado
query = f"""
    SELECT CONCAT_WS(' ', LPAD(l.CODIGO, 2, '0'), l.NOME) AS Loja,
           LAST_DAY(r.CADASTRO) AS `Mês`,
           r.situacao AS `Situação`,
           COUNT(1) AS Romaneios,
           SUM(valor_total) AS Valor
      FROM romaneios_dbf r 
      LEFT JOIN lojas l ON r.LOJA = l.CODIGO
     WHERE r.situacao IN ('FECHADO', 'CANCELADO')
       AND r.CADASTRO  BETWEEN '{data_inicio}' AND '{data_fim}'
     GROUP BY r.LOJA, LAST_DAY(r.CADASTRO), r.situacao;
"""

# Consultar os dados e criar o DataFrame
df = pd.read_sql(query, con=engine)

# Fechar a conexão com o banco de dados
engine.dispose()

# Mostrar o DataFrame no Streamlit
st.write(df)# Converter a coluna 'Ano' para o formato datetime, com o valor correspondente ao primeiro dia do ano
# # Primeiro, certifique-se de que a coluna 'Mês' está em formato de data
df['Mês'] = pd.to_datetime(df['Mês'], format='%Y-%m')  # Ajuste o formato conforme necessário

# Extraia o ano da coluna 'Mês' para uma nova coluna 'Ano'
df['Ano'] = df['Mês'].dt.year

# Calcular índice de Fechado e Cancelado por loja e por ano
indices_por_loja = df.pivot_table(index=['Loja', 'Ano'], columns='Situação', values='Romaneios', aggfunc='sum', fill_value=0).reset_index()
indices_por_loja['Total'] = indices_por_loja['CANCELADO'] + indices_por_loja['FECHADO']
indices_por_loja['Índice de Cancelados (%)'] = (indices_por_loja['CANCELADO'] / indices_por_loja['Total']) * 100
indices_por_loja['Índice de Fechados (%)'] = (indices_por_loja['FECHADO'] / indices_por_loja['Total']) * 100

# Filtrar as colunas necessárias para a nova tabela
df_indices = indices_por_loja[['Loja', 'Ano', 'Índice de Cancelados (%)', 'Índice de Fechados (%)']]
# Formatar colunas de índice
df_indices['Índice de Cancelados (%)'] = df_indices['Índice de Cancelados (%)'].apply(lambda x: f"{x:.2f}%")
df_indices['Índice de Fechados (%)'] = df_indices['Índice de Fechados (%)'].apply(lambda x: f"{x:.2f}%")

# Converter a coluna 'Ano' para o formato datetime, com o valor correspondente ao primeiro dia do ano
df_indices['Ano'] = pd.to_datetime(df_indices['Ano'], format='%Y')

# Criar a tabela onde o índice será o ano, as colunas serão as lojas, e os valores serão os índices
tabela_cancelados = df_indices.pivot(index='Ano', columns='Loja', values='Índice de Cancelados (%)')
tabela_fechados = df_indices.pivot(index='Ano', columns='Loja', values='Índice de Fechados (%)')

# Formatando a coluna 'Ano' para mostrar apenas o ano, sem as horas
tabela_cancelados.index = tabela_cancelados.index.strftime('%Y')
tabela_fechados.index = tabela_fechados.index.strftime('%Y')

# Mostrar os resultados no Streamlit
st.write("### Índice de Cancelados por Loja e Ano")
st.dataframe(tabela_cancelados)

st.write("### Índice de Fechados por Loja e Ano")
st.dataframe(tabela_fechados)


# Agrupar os dados por Loja, Mês e Situação para calcular índices por mês
df_grouped = df.groupby(['Loja', 'Mês', 'Situação'])['Romaneios'].sum().unstack(fill_value=0).reset_index()
df_grouped['TOTAL'] = df_grouped['CANCELADO'] + df_grouped['FECHADO']
df_grouped['INDICE DE CANCELADO'] = (df_grouped['CANCELADO'] / df_grouped['TOTAL']) * 100
df_grouped['INDICE DE FECHADO'] = (df_grouped['FECHADO'] / df_grouped['TOTAL']) * 100

# Criar a nova tabela "Índice de Cancelados e Fechados por Mês"
df_indices = df_grouped[['Loja', 'Mês', 'CANCELADO', 'FECHADO', 'TOTAL', 'INDICE DE CANCELADO', 'INDICE DE FECHADO']].copy()

# Garantir que a coluna 'Mês' esteja no formato datetime, apenas com ano e mês
df_indices.loc[:, 'Mês'] = pd.to_datetime(df_indices['Mês'], format='%Y-%m').dt.to_period('M').dt.to_timestamp()

# Índice de Fechado por loja, por mês e ano
st.write("### Índice de Fechado por loja por mês e ano")
df_grouped_agg = df_indices.groupby(['Mês', 'Loja'], as_index=False).agg({'INDICE DE FECHADO': 'first'})
df_grouped_pivot = df_grouped_agg.pivot(index='Loja', columns='Mês', values='INDICE DE FECHADO')

# Formatar a coluna 'Mês' no pivot table para aparecer sem hora
df_grouped_pivot.columns = df_grouped_pivot.columns.strftime('%Y-%m')

# Exibir os dados no Streamlit, formatando o índice como string para apresentação
st.dataframe(df_grouped_pivot.applymap(lambda x: f"{x:.2f}%" if pd.notnull(x) else x))

# Índice de Cancelados por loja, por mês e ano
st.write("### Índice de Cancelados por loja por mês e ano")
df_grouped_agg = df_indices.groupby(['Mês', 'Loja'], as_index=False).agg({'INDICE DE CANCELADO': 'first'})
df_grouped_pivot = df_grouped_agg.pivot(index='Loja', columns='Mês', values='INDICE DE CANCELADO')

# Formatar a coluna 'Mês' no pivot table para aparecer sem hora
df_grouped_pivot.columns = df_grouped_pivot.columns.strftime('%Y-%m')

# Exibir os dados no Streamlit, formatando o índice como string para apresentação
st.dataframe(df_grouped_pivot.applymap(lambda x: f"{x:.2f}%" if pd.notnull(x) else x))



# Agrupar por loja e contar o número de cancelamentos e calcular o valor total de cancelamento
cancelamentos_por_loja = df[df['Situação'] == 'CANCELADO'].groupby('Loja').agg(
    Quantidade=('Situação', 'size'),
    Valor_total=('Valor', 'sum')
).reset_index()
cancelamentos_por_loja.rename(columns={'Loja': 'LOJAS', 'Quantidade': 'qtd cancelado por loja', 'Valor_total': 'Valor total de cancelamento'}, inplace=True)
cancelamentos_por_loja['Valor total de cancelamento'] = cancelamentos_por_loja['Valor total de cancelamento'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

# Exibir a tabela de cancelamentos por loja
st.write("### Valor Cancelado por Loja")
st.dataframe(cancelamentos_por_loja)

# Agrupar por loja e contar o número de 'FECHADO' e calcular o valor total de fechado
fechados_por_loja = df[df['Situação'] == 'FECHADO'].groupby('Loja').agg(
    Quantidade=('Situação', 'size'),
    Valor_total=('Valor', 'sum')
).reset_index()
fechados_por_loja.rename(columns={'Loja': 'LOJAS', 'Quantidade': 'qtd fechado por loja', 'Valor_total': 'Valor total de Fechado'}, inplace=True)
fechados_por_loja['Valor total de Fechado'] = fechados_por_loja['Valor total de Fechado'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

# Exibir a tabela de fechados por loja
st.write("### Valor Fechados por Loja")
st.dataframe(fechados_por_loja)


