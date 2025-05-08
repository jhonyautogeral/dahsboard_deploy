import streamlit as st
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)  # Opta pelo novo comportamento de downcasting

# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página


import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import calendar
from datetime import datetime, timedelta
from sqlalchemy import create_engine

# =======================
# 1. Funções de Conexão e Consulta ao Banco
# =======================
def criar_conexao():
    """Cria e retorna a conexão com o banco de dados."""
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@" \
          f"{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

def executar_query(engine, query):
    """Executa a query no banco de dados e retorna um DataFrame."""
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Erro ao executar a query: {e}")
        return pd.DataFrame()

def consultar_lojas(engine):
    """Consulta e retorna os dados das lojas."""
    query = "SELECT codigo, nome FROM autogeral.lojas ORDER BY codigo"
    return executar_query(engine, query)

# =======================
# 2. Funções Auxiliares para Datas
# =======================
def obter_ultimos_anos(n=3):
    """Retorna os últimos n anos, incluindo o ano atual."""
    ano_atual = datetime.now().year
    return [ano_atual - i for i in range(n)]

def obter_meses():
    """Retorna a lista dos meses em português."""
    return ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

def obter_semanas_do_mes(data):
    """
    Calcula a semana do mês para uma determinada data.
    Divide o dia do mês por 7 e arredonda para cima.
    """
    return ((data.day - 1) // 7) + 1

# =======================
# 3. Função para Gerar a Query de Dados
# =======================
def gerar_query_dados(inicio, fim, loja, custom_query=None):
    """
    Gera a query SQL para extrair os dados.
    Se 'custom_query' for fornecida, ela deve ter os placeholders {inicio}, {fim} e {loja}.
    """
    if custom_query:
        return custom_query.format(inicio=inicio.strftime("%Y-%m-%d"),
                                     fim=fim.strftime("%Y-%m-%d"),
                                     loja=loja)
    inicio_str = inicio.strftime("%Y-%m-%d")
    fim_str = fim.strftime("%Y-%m-%d")
    query = f"""
    SELECT K.CADASTRO, K.CODIGO, K.LOJA, A.DESCRICAO AS MODELO,
           V.PLACA, C.NOME AS POSTO,
           K.ENTREGADOR_CODIGO,
           K.VALOR_TOTAL, 
           K.COMBUSTIVEL_1_LITROS, K.COMBUSTIVEL_2_LITROS,
           K.CRIADO_POR, K.ALTERADO, K.ALTERADO_POR
      FROM cadastros_veiculos_abastecimentos K 
           JOIN cadastros_veiculos V ON K.CADA_VEIC_ID = V.CADA_VEIC_ID
           LEFT JOIN cadastros C ON K.CADASTRO_CODIGO = C.CODIGO AND K.CADASTRO_LOJA = C.LOJA
           LEFT JOIN produto_veiculo A ON V.VEICULO_CODIGO = A.CODIGO
           LEFT JOIN produto_montadora B ON A.MONTADORA_CODIGO = B.CODIGO
     WHERE K.CADASTRO BETWEEN '{inicio_str} 00:00:00' AND '{fim_str} 23:59:59'
       AND K.LOJA = {loja};
    """
    return query

# =======================
# 4. Funções de Processamento dos Dados
# =======================
def process_data_year_mode(df, anos_interesse):
    """Processa os dados para o modo 'Ano' ou 'Selecione data'."""
    df = df.copy()
    df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
    df['CADASTRO'] = df['CADASTRO'].dt.to_period('M')
    df.drop_duplicates(keep='first', inplace=True)
    drop_cols = ['CRIADO_POR', 'ALTERADO', 'ALTERADO_POR']
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True, errors='ignore')

    df_final = df.groupby(['CADASTRO'], as_index=False).agg({
         'VALOR_TOTAL': 'sum',
         'COMBUSTIVEL_1_LITROS': 'sum',
         'COMBUSTIVEL_2_LITROS': 'sum'
    })
    df_final['COMBUSTIVEL_1_LITROS'] = df_final['COMBUSTIVEL_1_LITROS'].fillna(0).infer_objects()
    df_final['COMBUSTIVEL_2_LITROS'] = df_final['COMBUSTIVEL_2_LITROS'].fillna(0).infer_objects()
    df_final['TOTAL_COMBUSTIVEL'] = df_final['COMBUSTIVEL_1_LITROS'] + df_final['COMBUSTIVEL_2_LITROS']
    df_final['CADASTRO'] = df_final['CADASTRO'].dt.to_timestamp()
    df_final['ANO'] = df_final['CADASTRO'].dt.year
    df_final['MES'] = df_final['CADASTRO'].dt.month
    df_final = df_final[df_final['ANO'].isin(anos_interesse)]
    return df_final

def process_data_month_mode(df, anos_interesse):
    """Processa os dados para o modo 'Mês'."""
    df = df.copy()
    df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
    df.drop_duplicates(keep='first', inplace=True)
    drop_cols = ['CRIADO_POR', 'ALTERADO', 'ALTERADO_POR']
    df.drop(columns=[c for c in drop_cols if c in df.columns], axis=1, inplace=True, errors='ignore')
    df_grouped = df.groupby(['CADASTRO'], as_index=False).agg({
         'VALOR_TOTAL': 'sum',
         'COMBUSTIVEL_1_LITROS': 'sum',
         'COMBUSTIVEL_2_LITROS': 'sum'
    })
    df_grouped['COMBUSTIVEL_1_LITROS'] = df_grouped['COMBUSTIVEL_1_LITROS'].fillna(0).infer_objects()
    df_grouped['COMBUSTIVEL_2_LITROS'] = df_grouped['COMBUSTIVEL_2_LITROS'].fillna(0).infer_objects()
    df_grouped['TOTAL_COMBUSTIVEL'] = df_grouped['COMBUSTIVEL_1_LITROS'] + df_grouped['COMBUSTIVEL_2_LITROS']
    df_grouped['ANO'] = df_grouped['CADASTRO'].dt.year
    df_grouped['MES'] = df_grouped['CADASTRO'].dt.month
    df_grouped = df_grouped[df_grouped['ANO'].isin(anos_interesse)]
    return df_grouped

# =======================
# 5. Funções de Visualização para Modo "Ano"
# =======================
def generate_yearly_value_chart(df):
    """Gera gráfico de barras comparando o Valor Total por mês e por ano."""
    df_pivot = df.pivot_table(
        index='MES',
        columns='ANO',
        values='VALOR_TOTAL',
        aggfunc='sum'
    ).fillna(0)
    df_pivot = df_pivot.reindex(sorted(df_pivot.columns), axis=1)
    df_pivot.index = df_pivot.index.map(lambda x: calendar.month_name[x])
    
    fig = px.bar(
        df_pivot.reset_index(),
        x='MES',
        y=[col for col in df_pivot.columns if isinstance(col, int)],
        barmode='group',
        labels={'value': 'Valor Total', 'MES': 'Mês'},
        title='Comparativo de custo em reais por Mês (Últimos 3 Anos)'
    )
    fig.update_traces(texttemplate='%{value:,.2f}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    return fig

def generate_yearly_value_table(df, anos_interesse):
    """Gera tabela pivot para o Valor Total com Total Ano, YTD e variação percentual."""
    df_pivot = df.pivot_table(
        index='ANO',
        columns='MES',
        values='VALOR_TOTAL',
        aggfunc='sum'
    ).fillna(0)
    meses_map = {i: calendar.month_name[i] for i in range(1, 13)}
    df_pivot.rename(columns=meses_map, inplace=True)
    df_pivot['Total Ano'] = df_pivot.sum(axis=1)
    ultimo_mes = df['MES'].max()
    colunas_ytd = [meses_map[m] for m in range(1, ultimo_mes + 1) if m in meses_map]
    df_pivot['YTD'] = df_pivot[colunas_ytd].sum(axis=1)
    ordem = list(meses_map.values()) + ['Total Ano', 'YTD']
    df_pivot = df_pivot[[c for c in ordem if c in df_pivot.columns]]
    
    df_final = df_pivot.copy()
    anos_existentes = sorted(df_final.index)
    for i in range(1, len(anos_existentes)):
        ano_atual = anos_existentes[i]
        ano_ant = anos_existentes[i - 1]
        rotulo = f"Var% {ano_atual}x{ano_ant}"
        diff = df_final.loc[ano_atual] - df_final.loc[ano_ant]
        perc = (diff / df_final.loc[ano_ant].replace(0, np.nan)) * 100
        df_final.loc[rotulo] = perc

    # Converter índice e colunas para string
    df_final.index = df_final.index.map(str)
    df_final.columns = df_final.columns.map(str)
    return df_final.round(2)

def generate_yearly_combustible_chart(df):
    """Gera gráfico de barras comparando o Total Combustível por mês e por ano."""
    df_pivot = df.pivot_table(
        index='MES',
        columns='ANO',
        values='TOTAL_COMBUSTIVEL',
        aggfunc='sum'
    ).fillna(0)
    df_pivot = df_pivot.reindex(sorted(df_pivot.columns), axis=1)
    df_pivot.index = df_pivot.index.map(lambda x: calendar.month_name[x])
    
    col_anos = [col for col in df_pivot.columns if isinstance(col, int)]
    for i in range(1, len(col_anos)):
        ano_atual = col_anos[i]
        ano_ant = col_anos[i - 1]
        col_name = f"Var% {ano_atual}x{ano_ant}"
        df_pivot[col_name] = ((df_pivot[ano_atual] - df_pivot[ano_ant]) /
                              df_pivot[ano_ant].replace(0, np.nan)) * 100
    df_pivot = df_pivot.round(2)
    
    fig = px.bar(
        df_pivot.reset_index(),
        x='MES',
        y=col_anos,
        barmode='group',
        labels={'value': 'Total Combustível', 'MES': 'Mês'},
        title='Comparativo de Total de Combustível (Litros) por Mês (Últimos 3 Anos)'
    )
    fig.update_traces(texttemplate='%{value:,.2f}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    return fig

def generate_yearly_combustible_table(df, anos_interesse):
    """Gera tabela pivot para o Total Combustível com Total Ano, YTD e variação percentual."""
    df_pivot = df.pivot_table(
        index='ANO',
        columns='MES',
        values='TOTAL_COMBUSTIVEL',
        aggfunc='sum'
    ).fillna(0)
    meses_map = {i: calendar.month_name[i] for i in range(1, 13)}
    df_pivot.rename(columns=meses_map, inplace=True)
    df_pivot['Total Ano'] = df_pivot.sum(axis=1)
    ultimo_mes = df['MES'].max()
    colunas_ytd = [meses_map[m] for m in range(1, ultimo_mes + 1) if m in meses_map]
    df_pivot['YTD'] = df_pivot[colunas_ytd].sum(axis=1)
    ordem = list(meses_map.values()) + ['Total Ano', 'YTD']
    df_pivot = df_pivot[[c for c in ordem if c in df_pivot.columns]]
    
    df_final = df_pivot.copy()
    anos_existentes = sorted(df_final.index)
    for i in range(1, len(anos_existentes)):
        ano_atual = anos_existentes[i]
        ano_ant = anos_existentes[i - 1]
        rotulo = f"Var% {ano_atual}x{ano_ant}"
        diff = df_final.loc[ano_atual] - df_final.loc[ano_ant]
        perc = (diff / df_final.loc[ano_ant].replace(0, np.nan)) * 100
        df_final.loc[rotulo] = perc

    df_final.index = df_final.index.map(str)
    df_final.columns = df_final.columns.map(str)
    return df_final.round(2)

# =======================
# 6. Funções de Visualização para Modo "Mês"
# =======================
def generate_weekly_value_chart(df_mes, mes_selecionado):
    """Gera gráfico de barras comparando o Valor Total por semana para o mês selecionado."""
    df_mes = df_mes.copy()
    df_mes['SEMANA'] = df_mes['CADASTRO'].apply(obter_semanas_do_mes)
    df_pivot = df_mes.pivot_table(
        index='SEMANA',
        columns='ANO',
        values='VALOR_TOTAL',
        aggfunc='sum'
    ).fillna(0)
    
    fig = px.bar(
        df_pivot.reset_index(),
        x='SEMANA',
        y=[col for col in df_pivot.columns if isinstance(col, int)],
        barmode='group',
        labels={'value': 'Valor Total', 'SEMANA': 'Semana do Mês'},
        title=f'Comparativo de custo em reais de combustivel por Semana - {mes_selecionado}'
    )
    fig.update_traces(texttemplate='%{value:,.2f}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    return fig

def generate_weekly_combustible_chart(df_mes, mes_selecionado):
    """Gera gráfico de barras comparando o Total Combustível por semana para o mês selecionado."""
    df_mes = df_mes.copy()
    df_mes['SEMANA'] = df_mes['CADASTRO'].apply(obter_semanas_do_mes)
    df_pivot = df_mes.pivot_table(
        index='SEMANA',
        columns='ANO',
        values='TOTAL_COMBUSTIVEL',
        aggfunc='sum'
    ).fillna(0)
    
    fig = px.bar(
        df_pivot.reset_index(),
        x='SEMANA',
        y=[col for col in df_pivot.columns if isinstance(col, int)],
        barmode='group',
        labels={'value': 'Total Combustível (Litros)', 'SEMANA': 'Semana do Mês'},
        title=f'Comparativo de Total de Combustível (Litros) por Semana - {mes_selecionado}'
    )
    fig.update_traces(texttemplate='%{value:,.2f}', textposition='outside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    return fig

def generate_weekly_value_table(df_mes):
    """Gera tabela comparativa semanal para o Valor Total."""
    df_mes = df_mes.copy()
    df_mes['SEMANA'] = df_mes['CADASTRO'].apply(obter_semanas_do_mes)
    df_pivot = df_mes.pivot_table(
        index='ANO',
        columns='SEMANA',
        values='VALOR_TOTAL',
        aggfunc='sum'
    ).fillna(0)
    df_pivot['Total Mês'] = df_pivot.sum(axis=1)
    
    df_final = df_pivot.copy()
    anos_existentes = sorted(df_final.index)
    for i in range(1, len(anos_existentes)):
        ano_atual = anos_existentes[i]
        ano_ant = anos_existentes[i - 1]
        rotulo = f"Var% {ano_atual}x{ano_ant}"
        diff = df_final.loc[ano_atual] - df_final.loc[ano_ant]
        perc = (diff / df_final.loc[ano_ant].replace(0, np.nan)) * 100
        df_final.loc[rotulo] = perc

    df_final.index = df_final.index.map(str)
    df_final.columns = df_final.columns.map(str)
    return df_final.round(2)

def generate_weekly_combustible_table(df_mes):
    """Gera tabela comparativa semanal para o Total Combustível."""
    df_mes = df_mes.copy()
    df_mes['SEMANA'] = df_mes['CADASTRO'].apply(obter_semanas_do_mes)
    df_pivot = df_mes.pivot_table(
        index='ANO',
        columns='SEMANA',
        values='TOTAL_COMBUSTIVEL',
        aggfunc='sum'
    ).fillna(0)
    df_pivot['Total Mês'] = df_pivot.sum(axis=1)
    
    df_final = df_pivot.copy()
    anos_existentes = sorted(df_final.index)
    for i in range(1, len(anos_existentes)):
        ano_atual = anos_existentes[i]
        ano_ant = anos_existentes[i - 1]
        rotulo = f"Var% {ano_atual}x{ano_ant}"
        diff = df_final.loc[ano_atual] - df_final.loc[ano_ant]
        perc = (diff / df_final.loc[ano_ant].replace(0, np.nan)) * 100
        df_final.loc[rotulo] = perc

    df_final.index = df_final.index.map(str)
    df_final.columns = df_final.columns.map(str)
    return df_final.round(2)

# =======================
# 7. Execução Principal
# =======================
def main():
    st.set_page_config("Custo combustivel frota", layout="wide")
    if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
    # Conexão e seleção da loja
    engine = criar_conexao()
    df_lojas = consultar_lojas(engine)
    loja_dict = dict(zip(df_lojas['codigo'], df_lojas['nome']))
    
    st.sidebar.write("## Selecione os parâmetros")

    loja_selecionada = st.sidebar.selectbox(
        "Selecione a loja",
        options=list(loja_dict.keys()),
        format_func=lambda x: loja_dict[x],
        key="select_loja"
    )
    
    navegacao = st.sidebar.radio(
        "Navegação", 
        options=["Ano", "Mês"], # removi a opção , "Selecione data" po enquanto
        key="select_navegacao"
    )
    
    # Definição do intervalo de datas e anos de interesse
    if navegacao == "Ano":
        anos_interesse = sorted(obter_ultimos_anos(), reverse=True)
        inicio = datetime(min(anos_interesse), 1, 1)
        fim = datetime(max(anos_interesse), 12, 31)
    elif navegacao == "Mês":
        anos_disponiveis = sorted(obter_ultimos_anos(), reverse=True)
        ano_selecionado = st.sidebar.selectbox("Selecione o ano base", options=anos_disponiveis, key="select_ano_mes")
        mes_selecionado = st.sidebar.selectbox("Selecione o mês", options=obter_meses(), key="select_mes")
        anos_interesse = sorted([ano_selecionado, ano_selecionado - 1, ano_selecionado - 2])
        inicio = datetime(min(anos_interesse), 1, 1)
        fim = datetime(max(anos_interesse), 12, 31)
    else:  # "Selecione data"
        anos_interesse = sorted(obter_ultimos_anos(), reverse=True)
        inicio = datetime(min(anos_interesse), 1, 1)
        fim = datetime(max(anos_interesse), 12, 31)
    
    # Execução da query para obter os dados
    query = gerar_query_dados(inicio, fim, loja_selecionada)
    df_raw = executar_query(engine, query)
    
    if df_raw.empty:
        st.error("Nenhum dado retornado da consulta.")
        return

    # Processamento e visualização conforme o modo de navegação
    if navegacao in ["Ano", "Selecione data"]:
        df_processado = process_data_year_mode(df_raw, anos_interesse)
        
        st.title("Custo de combustivel - Modo Ano")
        
        fig_valor = generate_yearly_value_chart(df_processado)
        st.plotly_chart(fig_valor, use_container_width=True)
        
        df_tab_valor = generate_yearly_value_table(df_processado, anos_interesse)
        st.dataframe(df_tab_valor.style.format("{:,.2f}"))
        
        fig_comb = generate_yearly_combustible_chart(df_processado)
        st.plotly_chart(fig_comb, use_container_width=True)
        
        df_tab_comb = generate_yearly_combustible_table(df_processado, anos_interesse)
        st.dataframe(df_tab_comb.style.format("{:,.2f}"))
    
    elif navegacao == "Mês":
        df_processado = process_data_month_mode(df_raw, anos_interesse)
        
        # Mapeia o nome do mês para número
        meses_dict = {nome: i for i, nome in enumerate(obter_meses(), start=1)}
        mes_numero = meses_dict[mes_selecionado]
        df_mes = df_processado[df_processado['MES'] == mes_numero].copy()
        
        st.title(f"Custo de combustivel - Modo Mês: {mes_selecionado}")
        
        fig_semana_valor = generate_weekly_value_chart(df_mes, mes_selecionado)
        st.plotly_chart(fig_semana_valor, use_container_width=True)
        
        fig_semana_comb = generate_weekly_combustible_chart(df_mes, mes_selecionado)
        st.plotly_chart(fig_semana_comb, use_container_width=True)
        
        df_weekly_valor = generate_weekly_value_table(df_mes)
        st.dataframe(df_weekly_valor.style.format("{:,.2f}"))
        
        df_weekly_comb = generate_weekly_combustible_table(df_mes)
        st.dataframe(df_weekly_comb.style.format("{:,.2f}"))

if __name__ == "__main__":
    main()
