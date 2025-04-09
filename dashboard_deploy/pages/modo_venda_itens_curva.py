import streamlit as st
# Proteção de acesso
# if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
#     st.warning("Você não está logado. Redirecionando para a página de login...")
#     st.switch_page("app.py")
#     st.stop()  # Interrompe a execução para evitar continuar carregando esta página

import pandas as pd
import calendar
from sqlalchemy import create_engine
from datetime import datetime
import plotly.express as px

# =======================
# CONSTANTES E CONFIGURAÇÃO
# =======================
DIAS_SEMANA = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado']
MODOS = ['PRONTA_ENTREGA', 'CASADA', 'FUTURA']

# Cores para o gráfico de área (valores absolutos)
CORES = {
    'CASADA': '#636EFA',
    'FUTURA': '#EF553B',
    'PRONTA_ENTREGA': '#00CC96'
}

# Cores para o gráfico de barras empilhadas (colunas PERC_*)
CORES_PERC = {
    'PERC_CASADA': '#636EFA',
    'PERC_FUTURA': '#EF553B',
    'PERC_PRONTA_ENTREGA': '#00CC96'
}

# =======================
# CONEXÃO E EXECUÇÃO DE QUERIES
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
# FUNÇÕES AUXILIARES DE DATAS E CONFIGURAÇÃO
# =======================
def obter_ultimos_anos(n=3):
    """Retorna os últimos n anos, incluindo o ano atual."""
    ano_atual = datetime.now().year
    return [ano_atual - i for i in range(n)]

def obter_meses():
    """Retorna a lista dos meses em português."""
    return ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

def obter_semanas(ano, mes):
    """Retorna a quantidade de semanas em um mês para um determinado ano."""
    return len(calendar.monthcalendar(ano, mes))

def gerar_query_dados(inicio, fim, loja):
    """Gera e retorna a query SQL para extrair os dados."""
    inicio_str = inicio.strftime("%Y-%m-%d")
    fim_str = fim.strftime("%Y-%m-%d")
    query = f"""
    SELECT R.CADASTRO,
           (R.ROMANEIO*100+R.LOJA) AS ROMANEIO,
           R.LOJA,
           IF(R.OPERACAO_CODIGO=45, 'FUTURA', 'PRONTA_ENTREGA') AS MODO,
           P.CODIGO AS PRODUTO_CODIGO,
           P.CODIGO_X,
           P.CODIGO_SEQUENCIA,
           P.CURVA_PRODUTO,
           E.CURVA AS LOJA_CURVA,
           RI.QUANTIDADE,
           RI.VALOR_UNIDADE 
    FROM romaneios_dbf R 
    JOIN romaneios_itens_dbf RI ON RI.ROMANEIO = R.ROMANEIO AND RI.LOJA = R.LOJA
    JOIN produtos_dbf P ON RI.PRODUTO_CODIGO = P.CODIGO
    JOIN produto_estoque E ON P.CODIGO = E.PRODUTO_CODIGO AND E.LOJA = R.LOJA
    WHERE R.LOJA = {loja}
      AND R.OPERACAO_CODIGO IN (1,2,3,45)
      AND R.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}'
      AND R.SITUACAO = 'FECHADO'      
    UNION
    SELECT R.CADASTRO,
           (R.ROMANEIO*100+R.LOJA) AS ROMANEIO,
           R.LOJA,
           'CASADA' AS MODO,
           P.CODIGO AS PRODUTO_CODIGO,
           P.CODIGO_X,
           P.CODIGO_SEQUENCIA,
           P.CURVA_PRODUTO,
           E.CURVA AS LOJA_CURVA,
           VI.QUANTIDADE,
           VI.VALOR_REVENDA
    FROM romaneios_dbf R 
    JOIN compras_pedidos CP ON CP.ROMANEIO_CODIGO = R.ROMANEIO AND CP.ROMANEIO_LOJA = R.LOJA
    JOIN compras_pedidos_itens VI ON CP.COMPRA_PEDIDO = VI.COMPRA_PEDIDO AND CP.LOJA = VI.LOJA
    JOIN produtos_dbf P ON VI.PRODUTO_CODIGO = P.CODIGO
    JOIN produto_estoque E ON P.CODIGO = E.PRODUTO_CODIGO AND E.LOJA = R.LOJA
    WHERE R.LOJA = {loja}
      AND R.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}'
      AND R.SITUACAO = 'FECHADO';
    """
    return query

# =======================
# FUNÇÕES DE PROCESSAMENTO E VISUALIZAÇÃO
# =======================
def add_total_and_percentages(df, modos):
    """
    Adiciona colunas de TOTAL e de percentuais para cada modo de venda.
    Caso o modo não esteja presente, é adicionado com valor zero.
    """
    for modo in modos:
        if modo not in df.columns:
            df[modo] = 0
    df['TOTAL'] = df[modos].sum(axis=1)
    for modo in modos:
        df[f'PERC_{modo}'] = (df[modo] / df['TOTAL'].replace(0, 1)) * 100
    df.fillna(0, inplace=True)
    return df

def create_area_chart(data, x_col, modos, titulo, x_label, cores):
    """
    Cria e retorna um gráfico de área utilizando Plotly Express, exibindo os valores de cada ponto.
    """
    fig = px.area(
        data,
        x=x_col,
        y=modos,
        labels={'value': 'Quantidade de Vendas', x_col: x_label},
        title=titulo,
        color_discrete_map=cores
    )
    fig.update_traces(mode='lines+markers+text', texttemplate='%{y}', textposition='top center')
    fig.update_layout(yaxis_title='Quantidade de Vendas', xaxis_title=x_label)
    return fig

def create_grouped_bar_chart(data, x_col, modos, titulo, x_label, cores):
    """
    Cria um gráfico de barras agrupadas (lado a lado).
    data: DataFrame com a coluna x_col e colunas para cada modo (ex.: 'PRONTA_ENTREGA', 'CASADA', 'FUTURA').
    x_col: Nome da coluna para o eixo X (ex.: 'mes_nome', 'dia', 'semana_label').
    modos: Lista com os modos de venda (ex.: ['PRONTA_ENTREGA', 'CASADA', 'FUTURA']).
    titulo: Título do gráfico.
    x_label: Rótulo do eixo X.
    cores: Dicionário {modo: cor}, ex.: {'CASADA': '#636EFA', ...}.
    """
    # 'derrete' o DataFrame de largo para longo, para usar em Plotly
    df_melted = data.melt(
        id_vars=[x_col], 
        value_vars=modos, 
        var_name='MODO', 
        value_name='VALOR'
    )

    import plotly.express as px
    fig = px.bar(
        df_melted,
        x=x_col,
        y='VALOR',
        color='MODO',
        title=titulo,
        barmode='group',
        labels={x_col: x_label, 'VALOR': 'Quantidade de Vendas'},
        color_discrete_map=cores
    )
    # Mostra o valor acima das barras
    fig.update_traces(texttemplate='%{value}', textposition='outside')
    fig.update_layout(
        yaxis_title='Quantidade de Vendas', 
        xaxis_title=x_label
    )
    return fig


def create_stacked_bar_chart_percent(data, x_col, modos_perc, titulo, x_label, cores):
    """
    Cria um gráfico de barras empilhadas usando as colunas PERC_* (que já estão em %).
    data: DataFrame que contém x_col e as colunas modos_perc (ex.: ['PERC_PRONTA_ENTREGA', ...]).
    x_col: Coluna para o eixo X (ex.: 'mes_nome', 'dia', 'semana_label', etc.).
    modos_perc: Lista de colunas de percentual (ex.: ['PERC_PRONTA_ENTREGA', 'PERC_CASADA', 'PERC_FUTURA']).
    """
    # Converte o DF de largo para longo
    df_melted = data.melt(
        id_vars=[x_col], 
        value_vars=modos_perc,
        var_name='MODO',
        value_name='VALOR'
    )

    fig = px.bar(
        df_melted,
        x=x_col,
        y='VALOR',
        color='MODO',
        title=titulo,
        color_discrete_map=cores,
        labels={x_col: x_label, 'VALOR': 'Percentual'}
    )
    # Já em porcentagem, então apenas empilhar as barras
    fig.update_layout(barmode='stack', yaxis=dict(range=[0,100]))
    
    # Exibe o texto do valor (ex.: 30.5%) dentro das barras
    fig.update_traces(
        texttemplate='%{y:.2f}%',
        textposition='inside'
    )
    
    return fig

def process_visualizacao(engine, data_inicio, data_fim, loja, titulo, periodo):
    """
    Executa a query, processa os dados e chama a função de geração do gráfico e tabelas.
    """
    query = gerar_query_dados(data_inicio, data_fim, loja)
    df = executar_query(engine, query)
    if df.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
    else:
        gerar_grafico(df, titulo, data_inicio, data_fim, periodo)

def gerar_grafico(df, titulo, data_inicio, data_fim, periodo):
    try:
        # Converter datas e filtrar o período
        df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
        df = df[(df['CADASTRO'] >= pd.Timestamp(data_inicio)) & 
                (df['CADASTRO'] <= pd.Timestamp(data_fim))]
        df['MODO'] = df['MODO'].astype(str)
        
        # Se algum ROMANEIO tiver 'CASADA', todos viram 'CASADA'
        romaneios_casada = df.loc[df['MODO'] == 'CASADA', 'ROMANEIO'].unique()
        df.loc[df['ROMANEIO'].isin(romaneios_casada), 'MODO'] = 'CASADA'
        
        periodo_data_str = f"{data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}"
        
        if periodo == "Ano":

            df['mes'] = df['CADASTRO'].dt.month
            venda_agrupada = df.groupby(['mes', 'LOJA', 'MODO']).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            venda_agrupada['mes_nome'] = venda_agrupada['mes'].apply(lambda m: calendar.month_name[m])
            venda_agrupada = venda_agrupada.sort_values('mes')
            colunas_final = ['mes_nome', 'LOJA'] + MODOS + ['TOTAL'] + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]
            
            venda_agrupada_graph = venda_agrupada.groupby('mes_nome', as_index=False)[MODOS].sum()
            meses_ordem = [calendar.month_name[i] for i in range(1, 13)]
            venda_agrupada_graph['mes_nome'] = pd.Categorical(
                venda_agrupada_graph['mes_nome'], 
                categories=meses_ordem, 
                ordered=True
            )
            venda_agrupada_graph = venda_agrupada_graph.sort_values('mes_nome')
            
            fig_area = create_area_chart(
                venda_agrupada_graph, 
                x_col='mes_nome', 
                modos=MODOS, 
                titulo=titulo, 
                x_label='Mês', 
                cores=CORES
            )
            st.subheader("Gráfico de Área (Valores Absolutos)")
            st.plotly_chart(fig_area)
            
            fig_barras = create_grouped_bar_chart(
                venda_agrupada_graph,
                x_col='mes_nome',
                modos=MODOS,
                titulo=titulo + " (Barras Agrupadas)",
                x_label='Mês',
                cores=CORES
            )
            st.subheader("Gráfico de Barras (Valores Absolutos)")
            st.plotly_chart(fig_barras)
            
            modos_perc = [f'PERC_{modo}' for modo in MODOS]
            df_percentual = venda_agrupada.groupby('mes_nome', as_index=False)[modos_perc].mean()
            df_percentual['mes_nome'] = pd.Categorical(df_percentual['mes_nome'], categories=meses_ordem, ordered=True)
            df_percentual = df_percentual.sort_values('mes_nome')
            
            fig_stack = create_stacked_bar_chart_percent(
                data=df_percentual,
                x_col='mes_nome',
                modos_perc=modos_perc,
                titulo=titulo + " (Percentual)",
                x_label='Mês',
                cores=CORES_PERC
            )
            st.subheader("Gráfico de Barras Empilhadas (Percentual de Vendas)")
            st.plotly_chart(fig_stack)
    
            st.subheader("Tabela com Vendas e Percentuais")
            st.dataframe(
                venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS})
            )
            
            df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            for modo in MODOS:
                df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            df_totals.insert(0, 'periodo_data', periodo_data_str)
            st.subheader("Tabela com Totais do Período")
            st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
            
            # -------------------------------
            # NOVA análise: CURVA_PRODUTO para PRONTA_ENTREGA (por Mês)
            # -------------------------------
            df_curva_pronta = df[df['MODO'] == 'PRONTA_ENTREGA'].copy()
            # (1) TRATA VALORES NULOS/VAZIOS EM CURVA_PRODUTO (sem inplace e sem loc encadeado)
            df_curva_pronta['CURVA_PRODUTO'] = (
                df_curva_pronta['CURVA_PRODUTO']
                .fillna('')          # Substitui NaN por string vazia
                .str.strip()        # Remove espaços no início/fim
                .replace({'': 'SEM_CURVA'})  # Substitui '' por 'SEM_CURVA'
            )
            
            df_curva_pronta['mes'] = df_curva_pronta['CADASTRO'].dt.month
            df_curva_pronta['mes_nome'] = df_curva_pronta['mes'].apply(lambda m: calendar.month_name[m])
            
            curva_agrupada_pronta = df_curva_pronta.groupby(['mes_nome', 'CURVA_PRODUTO']).size().reset_index(name='Quantidade')
            curva_pivot_pronta = curva_agrupada_pronta.pivot(index='mes_nome', columns='CURVA_PRODUTO', values='Quantidade').fillna(0).reset_index()
            curva_pivot_pronta['TOTAL'] = curva_pivot_pronta.drop(columns='mes_nome').sum(axis=1)
            for col in curva_pivot_pronta.columns:
                if col not in ['mes_nome', 'TOTAL']:
                    curva_pivot_pronta[f'PERC_{col}'] = (curva_pivot_pronta[col] / curva_pivot_pronta['TOTAL'].replace(0,1)) * 100
            cols_perc_pronta = [col for col in curva_pivot_pronta.columns if col.startswith('PERC_')]
            curva_pivot_pronta['mes_nome'] = pd.Categorical(curva_pivot_pronta['mes_nome'], categories=meses_ordem, ordered=True)
            curva_pivot_pronta = curva_pivot_pronta.sort_values('mes_nome')
            df_percentual_curva_pronta = curva_pivot_pronta[['mes_nome'] + cols_perc_pronta].copy()
            
            fig_curva_pronta = create_stacked_bar_chart_percent(
                data=df_percentual_curva_pronta,
                x_col='mes_nome',
                modos_perc=cols_perc_pronta,
                titulo="Percentual de Curva do Produto (PRONTA_ENTREGA) por Mês",
                x_label="Mês",
                cores={}
            )
            st.subheader("Gráfico de Percentual de Curva do Produto (PRONTA_ENTREGA) - Por Mês")
            st.plotly_chart(fig_curva_pronta)
            st.subheader("Tabela de Percentual de Curva do Produto (PRONTA_ENTREGA)")
            st.dataframe(df_percentual_curva_pronta.style.format({col: "{:.2f}%" for col in cols_perc_pronta}))
            
            # -------------------------------
            # NOVA análise: CURVA_PRODUTO para CASADA (por Mês)
            # -------------------------------
            df_curva_casada = df[df['MODO'] == 'CASADA'].copy()
            # TRATA VALORES NULOS/VAZIOS EM CURVA_PRODUTO
            df_curva_casada['CURVA_PRODUTO'] = (
                df_curva_casada['CURVA_PRODUTO']
                .fillna('')
                .str.strip()
                .replace({'': 'SEM_CURVA'})
            )
            
            df_curva_casada['mes'] = df_curva_casada['CADASTRO'].dt.month
            df_curva_casada['mes_nome'] = df_curva_casada['mes'].apply(lambda m: calendar.month_name[m])
            
            curva_agrupada_casada = df_curva_casada.groupby(['mes_nome', 'CURVA_PRODUTO']).size().reset_index(name='Quantidade')
            curva_pivot_casada = curva_agrupada_casada.pivot(index='mes_nome', columns='CURVA_PRODUTO', values='Quantidade').fillna(0).reset_index()
            curva_pivot_casada['TOTAL'] = curva_pivot_casada.drop(columns='mes_nome').sum(axis=1)
            for col in curva_pivot_casada.columns:
                if col not in ['mes_nome', 'TOTAL']:
                    curva_pivot_casada[f'PERC_{col}'] = (curva_pivot_casada[col] / curva_pivot_casada['TOTAL'].replace(0,1)) * 100
            cols_perc_casada = [col for col in curva_pivot_casada.columns if col.startswith('PERC_')]
            curva_pivot_casada['mes_nome'] = pd.Categorical(curva_pivot_casada['mes_nome'], categories=meses_ordem, ordered=True)
            curva_pivot_casada = curva_pivot_casada.sort_values('mes_nome')
            df_percentual_curva_casada = curva_pivot_casada[['mes_nome'] + cols_perc_casada].copy()
            
            fig_curva_casada = create_stacked_bar_chart_percent(
                data=df_percentual_curva_casada,
                x_col='mes_nome',
                modos_perc=cols_perc_casada,
                titulo="Percentual de Curva do Produto (CASADA) por Mês",
                x_label="Mês",
                cores={}
            )
            st.subheader("Gráfico de Percentual de Curva do Produto (CASADA) - Por Mês")
            st.plotly_chart(fig_curva_casada)
            st.subheader("Tabela de Percentual de Curva do Produto (CASADA)")
            st.dataframe(df_percentual_curva_casada.style.format({col: "{:.2f}%" for col in cols_perc_casada}))
        
        elif periodo == "Mês":

            df['semana'] = ((df['CADASTRO'].dt.day - 1) // 7) + 1
            venda_agrupada = df.groupby(['semana', 'LOJA', 'MODO']).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            venda_agrupada = venda_agrupada.sort_values('semana')
            colunas_final = ['semana', 'LOJA'] + MODOS + ['TOTAL'] + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]
            venda_agrupada_graph = venda_agrupada.groupby('semana', as_index=False)[MODOS].sum()
            venda_agrupada_graph = venda_agrupada_graph.sort_values('semana')
    
            fig_area = create_area_chart(
                venda_agrupada_graph, 
                x_col='semana', 
                modos=MODOS, 
                titulo=titulo, 
                x_label='Semana', 
                cores=CORES
            )
            st.subheader("Gráfico de Área (Valores Absolutos)")
            st.plotly_chart(fig_area)
    
            modos_perc = [f'PERC_{modo}' for modo in MODOS]
            df_percentual = venda_agrupada.groupby('semana', as_index=False)[modos_perc].mean()
    
            fig_stack = create_stacked_bar_chart_percent(
                data=df_percentual,
                x_col='semana',
                modos_perc=modos_perc,
                titulo=titulo + " (Percentual)",
                x_label='Semana',
                cores=CORES_PERC
            )
            st.subheader("Gráfico de Barras Empilhadas (Percentual de Vendas)")
            st.plotly_chart(fig_stack)
    
            st.subheader("Tabela com Vendas e Percentuais")
            st.dataframe(venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
    
            df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            for modo in MODOS:
                df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            df_totals.insert(0, 'periodo_data', periodo_data_str)
            st.subheader("Tabela com Totais do Período")
            st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
            
            # -------------------------------
            # NOVA análise: CURVA_PRODUTO para PRONTA_ENTREGA (por Semana)
            # -------------------------------
            df_curva_pronta = df[df['MODO'] == 'PRONTA_ENTREGA'].copy()
            df_curva_pronta['CURVA_PRODUTO'] = (
                df_curva_pronta['CURVA_PRODUTO']
                .fillna('')
                .str.strip()
                .replace({'': 'SEM_CURVA'})
            )
            
            df_curva_pronta['semana'] = ((df_curva_pronta['CADASTRO'].dt.day - 1) // 7) + 1
            curva_agrupada_pronta = df_curva_pronta.groupby(['semana', 'CURVA_PRODUTO']).size().reset_index(name='Quantidade')
            curva_pivot_pronta = curva_agrupada_pronta.pivot(index='semana', columns='CURVA_PRODUTO', values='Quantidade').fillna(0).reset_index()
            curva_pivot_pronta['TOTAL'] = curva_pivot_pronta.drop(columns='semana').sum(axis=1)
            for col in curva_pivot_pronta.columns:
                if col not in ['semana', 'TOTAL']:
                    curva_pivot_pronta[f'PERC_{col}'] = (curva_pivot_pronta[col] / curva_pivot_pronta['TOTAL'].replace(0,1)) * 100
            cols_perc_pronta = [col for col in curva_pivot_pronta.columns if col.startswith('PERC_')]
            df_percentual_curva_pronta = curva_pivot_pronta[['semana'] + cols_perc_pronta].copy()
            
            fig_curva_pronta = create_stacked_bar_chart_percent(
                data=df_percentual_curva_pronta,
                x_col='semana',
                modos_perc=cols_perc_pronta,
                titulo="Percentual de Curva do Produto (PRONTA_ENTREGA) por Semana",
                x_label="Semana",
                cores={}
            )
            st.subheader("Gráfico de Percentual de Curva do Produto (PRONTA_ENTREGA) - Por Semana")
            st.plotly_chart(fig_curva_pronta)
            st.subheader("Tabela de Percentual de Curva do Produto (PRONTA_ENTREGA)")
            st.dataframe(df_percentual_curva_pronta.style.format({col: "{:.2f}%" for col in cols_perc_pronta}))
            
            # -------------------------------
            # NOVA análise: CURVA_PRODUTO para CASADA (por Semana)
            # -------------------------------
            df_curva_casada = df[df['MODO'] == 'CASADA'].copy()
            df_curva_casada['CURVA_PRODUTO'] = (
                df_curva_casada['CURVA_PRODUTO']
                .fillna('')
                .str.strip()
                .replace({'': 'SEM_CURVA'})
            )
            
            df_curva_casada['semana'] = ((df_curva_casada['CADASTRO'].dt.day - 1) // 7) + 1
            curva_agrupada_casada = df_curva_casada.groupby(['semana', 'CURVA_PRODUTO']).size().reset_index(name='Quantidade')
            curva_pivot_casada = curva_agrupada_casada.pivot(index='semana', columns='CURVA_PRODUTO', values='Quantidade').fillna(0).reset_index()
            curva_pivot_casada['TOTAL'] = curva_pivot_casada.drop(columns='semana').sum(axis=1)
            for col in curva_pivot_casada.columns:
                if col not in ['semana', 'TOTAL']:
                    curva_pivot_casada[f'PERC_{col}'] = (curva_pivot_casada[col] / curva_pivot_casada['TOTAL'].replace(0,1)) * 100
            cols_perc_casada = [col for col in curva_pivot_casada.columns if col.startswith('PERC_')]
            df_percentual_curva_casada = curva_pivot_casada[['semana'] + cols_perc_casada].copy()
            
            fig_curva_casada = create_stacked_bar_chart_percent(
                data=df_percentual_curva_casada,
                x_col='semana',
                modos_perc=cols_perc_casada,
                titulo="Percentual de Curva do Produto (CASADA) por Semana",
                x_label="Semana",
                cores={}
            )
            st.subheader("Gráfico de Percentual de Curva do Produto (CASADA) - Por Semana")
            st.plotly_chart(fig_curva_casada)
            st.subheader("Tabela de Percentual de Curva do Produto (CASADA)")
            st.dataframe(df_percentual_curva_casada.style.format({col: "{:.2f}%" for col in cols_perc_casada}))
        
        elif periodo == "Selecione data":
            
            df['semana_period'] = df['CADASTRO'].dt.to_period('W')
            df['semana'] = df['semana_period'].apply(lambda r: r.start_time)
            df['semana_ano'] = df['CADASTRO'].dt.isocalendar().year
            df['semana_num'] = df['CADASTRO'].dt.isocalendar().week
            df['semana_label'] = df['semana'].dt.strftime('%d/%m/%Y')
            venda_agrupada = df.groupby(
                ['semana', 'semana_ano', 'semana_num', 'semana_label', 'LOJA', 'MODO']
            ).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            venda_agrupada = venda_agrupada.sort_values('semana')
            colunas_final = ['semana', 'semana_ano', 'semana_num', 'semana_label', 'LOJA'] \
                            + MODOS + ['TOTAL'] \
                            + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]
            
            venda_agrupada_graph = venda_agrupada.groupby(
                ['semana', 'semana_ano', 'semana_num', 'semana_label'],
                as_index=False
            )[MODOS].sum()
            venda_agrupada_graph = venda_agrupada_graph.sort_values('semana')
            
            fig_area = create_area_chart(
                venda_agrupada_graph,
                x_col='semana_label',
                modos=MODOS,
                titulo=titulo,
                x_label='Semana',
                cores=CORES
            )
            st.subheader("Gráfico de Área (Valores Absolutos)")
            st.plotly_chart(fig_area)
            
            modos_perc = [f'PERC_{modo}' for modo in MODOS]
            df_percentual = venda_agrupada.groupby('semana_label', as_index=False)[modos_perc].mean()
            
            fig_stack = create_stacked_bar_chart_percent(
                data=df_percentual,
                x_col='semana_label',
                modos_perc=modos_perc,
                titulo=titulo + " (Percentual)",
                x_label='Semana',
                cores=CORES_PERC
            )
            st.subheader("Gráfico de Barras Empilhadas (Percentual de Vendas)")
            st.plotly_chart(fig_stack)
            
            # -------------------------------
            # NOVA análise: CURVA_PRODUTO para PRONTA_ENTREGA (por Data)
            # -------------------------------
            df_curva_pronta = df[df['MODO'] == 'PRONTA_ENTREGA'].copy()
            df_curva_pronta['CURVA_PRODUTO'] = (
                df_curva_pronta['CURVA_PRODUTO']
                .fillna('')
                .str.strip()
                .replace({'': 'SEM_CURVA'})
            )
            
            df_curva_pronta['data'] = df_curva_pronta['CADASTRO'].dt.date
            curva_agrupada_pronta = df_curva_pronta.groupby(['data', 'CURVA_PRODUTO']).size().reset_index(name='Quantidade')
            curva_pivot_pronta = curva_agrupada_pronta.pivot(index='data', columns='CURVA_PRODUTO', values='Quantidade').fillna(0).reset_index()
            curva_pivot_pronta['TOTAL'] = curva_pivot_pronta.drop(columns='data').sum(axis=1)
            for col in curva_pivot_pronta.columns:
                if col not in ['data', 'TOTAL']:
                    curva_pivot_pronta[f'PERC_{col}'] = (curva_pivot_pronta[col] / curva_pivot_pronta['TOTAL'].replace(0,1)) * 100
            cols_perc_pronta = [col for col in curva_pivot_pronta.columns if col.startswith('PERC_')]
            curva_pivot_pronta = curva_pivot_pronta.sort_values('data')
            df_percentual_curva_pronta = curva_pivot_pronta[['data'] + cols_perc_pronta].copy()
            
            fig_curva_pronta = create_stacked_bar_chart_percent(
                data=df_percentual_curva_pronta,
                x_col='data',
                modos_perc=cols_perc_pronta,
                titulo="Percentual de Curva do Produto (PRONTA_ENTREGA) por Data",
                x_label="Data",
                cores={}
            )
            st.subheader("Gráfico de Percentual de Curva do Produto (PRONTA_ENTREGA) - Por Data")
            st.plotly_chart(fig_curva_pronta)
            st.subheader("Tabela de Percentual de Curva do Produto (PRONTA_ENTREGA)")
            st.dataframe(df_percentual_curva_pronta.style.format({col: "{:.2f}%" for col in cols_perc_pronta}))
            
            # -------------------------------
            # NOVA análise: CURVA_PRODUTO para CASADA (por Data)
            # -------------------------------
            df_curva_casada = df[df['MODO'] == 'CASADA'].copy()
            df_curva_casada['CURVA_PRODUTO'] = (
                df_curva_casada['CURVA_PRODUTO']
                .fillna('')
                .str.strip()
                .replace({'': 'SEM_CURVA'})
            )
            
            df_curva_casada['data'] = df_curva_casada['CADASTRO'].dt.date
            curva_agrupada_casada = df_curva_casada.groupby(['data', 'CURVA_PRODUTO']).size().reset_index(name='Quantidade')
            curva_pivot_casada = curva_agrupada_casada.pivot(index='data', columns='CURVA_PRODUTO', values='Quantidade').fillna(0).reset_index()
            curva_pivot_casada['TOTAL'] = curva_pivot_casada.drop(columns='data').sum(axis=1)
            for col in curva_pivot_casada.columns:
                if col not in ['data', 'TOTAL']:
                    curva_pivot_casada[f'PERC_{col}'] = (curva_pivot_casada[col] / curva_pivot_casada['TOTAL'].replace(0,1)) * 100
            cols_perc_casada = [col for col in curva_pivot_casada.columns if col.startswith('PERC_')]
            curva_pivot_casada = curva_pivot_casada.sort_values('data')
            df_percentual_curva_casada = curva_pivot_casada[['data'] + cols_perc_casada].copy()
            
            fig_curva_casada = create_stacked_bar_chart_percent(
                data=df_percentual_curva_casada,
                x_col='data',
                modos_perc=cols_perc_casada,
                titulo="Percentual de Curva do Produto (CASADA) por Data",
                x_label="Data",
                cores={}
            )
            st.subheader("Gráfico de Percentual de Curva do Produto (CASADA) - Por Data")
            st.plotly_chart(fig_curva_casada)
            st.subheader("Tabela de Percentual de Curva do Produto (CASADA)")
            st.dataframe(df_percentual_curva_casada.style.format({col: "{:.2f}%" for col in cols_perc_casada}))
        
        else:
            st.error("Tipo de período inválido.")
    
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")

# =======================
# FUNÇÃO PRINCIPAL
# =======================
def main():
    engine = criar_conexao()
    df_lojas = consultar_lojas(engine)
    loja_dict = dict(zip(df_lojas['codigo'], df_lojas['nome']))
    
    st.sidebar.write("## Selecione os parâmetros")
    loja_selecionada = st.sidebar.selectbox(
        "Selecione a loja",
        options=list(loja_dict.keys()),
        format_func=lambda x: loja_dict[x],
        key="mnavh_loja"
    )
    
    navegacao = st.sidebar.radio("Navegação", options=["Ano", "Mês", "Selecione data"], key="mnavh_navegacao")
    
    if navegacao == "Ano":
        anos = obter_ultimos_anos() 
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="mnavh_ano")
        data_inicio = datetime(ano_selecionado, 1, 1)
        data_fim = datetime(ano_selecionado, 12, 31)
        # if st.sidebar.button("Gerar gráfico e tabela"):
        titulo = f"Vendas por Mês - {ano_selecionado}"
        process_visualizacao(engine, data_inicio, data_fim, loja_selecionada, titulo, "Ano")
                
    elif navegacao == "Mês":
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="mnavh_mes_ano")
        meses = obter_meses()
        mes_selecionado = st.sidebar.selectbox("Selecione o mês", options=meses, key="mnavh_mes_mes")
        mes_index = meses.index(mes_selecionado) + 1
        data_inicio = datetime(ano_selecionado, mes_index, 1)
        _, ultimo_dia = calendar.monthrange(ano_selecionado, mes_index)
        data_fim = datetime(ano_selecionado, mes_index, ultimo_dia)
        # if st.sidebar.button("Gerar gráfico e tabela"):
        titulo = f"Vendas por Semana - {mes_selecionado}/{ano_selecionado}"
        process_visualizacao(engine, data_inicio, data_fim, loja_selecionada, titulo, "Mês")
                
    elif navegacao == "Selecione data":
        st.sidebar.write("### Selecione o intervalo de datas para agrupar por semana")
        data_inicio_input = st.sidebar.date_input("Data Inicial", key="mnavh_semana_data_inicio")
        data_fim_input = st.sidebar.date_input("Data Final", key="mnavh_semana_data_fim")
        
        if not data_inicio_input or not data_fim_input:
            st.error("Selecione as duas datas: Data Inicial e Data Final.")
            return
        
        data_inicio = datetime.combine(data_inicio_input, datetime.min.time())
        data_fim = datetime.combine(data_fim_input, datetime.max.time())
        
        # if st.sidebar.button("Gerar gráfico e tabela"):
        titulo = f"Vendas por Semana: {data_inicio_input.strftime('%d/%m/%Y')} a {data_fim_input.strftime('%d/%m/%Y')}"
        process_visualizacao(engine, data_inicio, data_fim, loja_selecionada, titulo, "Semana")

if __name__ == "__main__":
    main()
