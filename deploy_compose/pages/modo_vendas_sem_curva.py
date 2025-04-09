import streamlit as st
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página

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
    WITH CTE AS (
    SELECT 
           R.CADASTRO,
           (R.ROMANEIO*100+R.LOJA) AS ROMANEIO,
           R.LOJA,
           IF(R.OPERACAO_CODIGO=45, 'FUTURA', 'PRONTA_ENTREGA') AS MODO,
           P.CODIGO AS PRODUTO_CODIGO,
           P.CODIGO_X,
           P.CODIGO_SEQUENCIA,
           P.CURVA_PRODUTO,
           E.CURVA AS LOJA_CURVA,
           RI.QUANTIDADE,
           RI.VALOR_UNIDADE,
           ROW_NUMBER() OVER (PARTITION BY (R.ROMANEIO*100 + R.LOJA) ORDER BY R.CADASTRO) AS RN
    FROM romaneios_dbf R
    JOIN romaneios_itens_dbf RI ON RI.ROMANEIO = R.ROMANEIO AND RI.LOJA = R.LOJA
    JOIN produtos_dbf P ON RI.PRODUTO_CODIGO = P.CODIGO
    JOIN produto_estoque E ON P.CODIGO = E.PRODUTO_CODIGO AND E.LOJA = R.LOJA
    WHERE R.LOJA = {loja}
      AND R.OPERACAO_CODIGO IN (1,2,3,45)
      AND R.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}'
      AND R.SITUACAO = 'FECHADO'
    UNION
    SELECT 
           R.CADASTRO,
           (R.ROMANEIO*100+R.LOJA) AS ROMANEIO,
           R.LOJA,
           'CASADA' AS MODO,
           P.CODIGO AS PRODUTO_CODIGO,
           P.CODIGO_X,
           P.CODIGO_SEQUENCIA,
           P.CURVA_PRODUTO,
           E.CURVA AS LOJA_CURVA,
           VI.QUANTIDADE,
           VI.VALOR_REVENDA,
           ROW_NUMBER() OVER (PARTITION BY (R.ROMANEIO*100 + R.LOJA) ORDER BY R.CADASTRO) AS RN
    FROM romaneios_dbf R
    JOIN compras_pedidos CP ON CP.ROMANEIO_CODIGO = R.ROMANEIO AND CP.ROMANEIO_LOJA = R.LOJA
    JOIN compras_pedidos_itens VI ON CP.COMPRA_PEDIDO = VI.COMPRA_PEDIDO AND CP.LOJA = VI.LOJA
    JOIN produtos_dbf P ON VI.PRODUTO_CODIGO = P.CODIGO
    JOIN produto_estoque E ON P.CODIGO = E.PRODUTO_CODIGO AND E.LOJA = R.LOJA
    WHERE R.LOJA = {loja}
      AND R.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}'
      AND R.SITUACAO = 'FECHADO'
)
SELECT 
    CADASTRO,
    ROMANEIO,
    LOJA,
    MODO,
    PRODUTO_CODIGO,
    CODIGO_X,
    CODIGO_SEQUENCIA,
    CURVA_PRODUTO,
    LOJA_CURVA,
    QUANTIDADE,
    VALOR_UNIDADE
FROM CTE
WHERE RN = 1;
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
    # 'derrete' o DataFrame de largo para longo, para Plotly
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
    # df_melted agora terá colunas: [x_col, 'MODO', 'VALOR']

    fig = px.bar(
        df_melted,
        x=x_col,
        y='VALOR',
        color='MODO',
        title=titulo,
        color_discrete_map=cores,
        labels={x_col: x_label, 'VALOR': 'Percentual'}
    )
    # Já estamos em porcentagem, então apenas empilhamos
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
    """
    Gera o gráfico de área (valores absolutos) e, abaixo dele, o gráfico de barras empilhadas (colunas PERC_*).
    Exibe também as tabelas de vendas e percentuais.
    """
    try:
        # Converter datas e filtrar
        df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
        df = df[(df['CADASTRO'] >= pd.Timestamp(data_inicio)) & 
                (df['CADASTRO'] <= pd.Timestamp(data_fim))]
        df['MODO'] = df['MODO'].astype(str)
        
        # Se algum ROMANEIO tiver 'CASADA', todos viram 'CASADA'
        romaneios_casada = df.loc[df['MODO'] == 'CASADA', 'ROMANEIO'].unique()
        df.loc[df['ROMANEIO'].isin(romaneios_casada), 'MODO'] = 'CASADA'
        
        periodo_data_str = f"{data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}"
        
        if periodo == "Ano":
            # 1) Criar as colunas de mês e agrupar
            df['mes'] = df['CADASTRO'].dt.month
            venda_agrupada = df.groupby(['mes', 'LOJA', 'MODO']).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            venda_agrupada['mes_nome'] = venda_agrupada['mes'].apply(lambda m: calendar.month_name[m])
            venda_agrupada = venda_agrupada.sort_values('mes')
            
            # Ordenar colunas e ajustar final
            colunas_final = ['mes_nome', 'LOJA'] + MODOS + ['TOTAL'] + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]
            
            # 2) Dados para o gráfico de Área e Barras Agrupadas
            #    Somamos por 'mes_nome' para ter 1 linha por mês
            venda_agrupada_graph = venda_agrupada.groupby('mes_nome', as_index=False)[MODOS].sum()
            
            # Ordenar o DataFrame pelos meses de 1 a 12
            meses_ordem = [calendar.month_name[i] for i in range(1, 13)]
            venda_agrupada_graph['mes_nome'] = pd.Categorical(
                venda_agrupada_graph['mes_nome'], 
                categories=meses_ordem, 
                ordered=True
            )
            venda_agrupada_graph = venda_agrupada_graph.sort_values('mes_nome')
            
            # 3) Gráfico de Área (Valores Absolutos)
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
            
            # 4) NOVO: Gráfico de Barras Agrupadas (Valores Absolutos)
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
            
            # 5) Gráfico de Barras Empilhadas (Percentuais)
            modos_perc = [f'PERC_{modo}' for modo in MODOS]
            
            # Aqui, fazemos a média das porcentagens por 'mes_nome'
            df_percentual = venda_agrupada.groupby('mes_nome', as_index=False)[modos_perc].mean()

            df_percentual['mes_nome'] = pd.Categorical(df_percentual['mes_nome'], categories=meses_ordem, ordered=True)

            # Agora, ao ordenar, os meses serão exibidos na ordem cronológica
            df_percentual = df_percentual.sort_values('mes_nome')
            
            fig_stack = create_stacked_bar_chart_percent(
                data=df_percentual,
                x_col='mes_nome',
                modos_perc=modos_perc,
                titulo=titulo + " (Percentual)",
                x_label='Mês',
                cores=CORES_PERC
            )
            st.subheader("Gráfico de Barras Empilhadas (Percentuais)")
            st.plotly_chart(fig_stack)
    
            # 6) Tabela com Vendas e Percentuais
            st.text("Tabela com Vendas e Percentuais")
            st.subheader("Tabela com Vendas e Percentuais")
            st.dataframe(
                venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS})
            )
            
            # Tabela com Totais ---------------------------
            df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            for modo in MODOS:
                df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            df_totals.insert(0, 'periodo_data', periodo_data_str)
            st.subheader("Tabela com Totais do Período")
            st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
        
        elif periodo == "Mês":
            # Calcula a semana do mês (1ª semana, 2ª, etc.)
            df['semana'] = ((df['CADASTRO'].dt.day - 1) // 7) + 1

            # Agrupa os dados por semana, LOJA e MODO
            venda_agrupada = df.groupby(['semana', 'LOJA', 'MODO']).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            venda_agrupada = venda_agrupada.sort_values('semana')

            colunas_final = ['semana', 'LOJA'] + MODOS + ['TOTAL'] + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]

            # Gráfico de Área (valores absolutos)
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

            # Gráfico de Barras (Percentuais) - colunas PERC_*
            modos_perc = [f'PERC_{modo}' for modo in MODOS]
            # Média das porcentagens por semana
            df_percentual = venda_agrupada.groupby('semana', as_index=False)[modos_perc].mean()

            fig_stack = create_stacked_bar_chart_percent(
                data=df_percentual,
                x_col='semana',
                modos_perc=modos_perc,
                titulo=titulo + " (Percentual)",
                x_label='Semana',
                cores=CORES_PERC
            )
            st.subheader("Gráfico de Barras Empilhadas (Percentuais)")
            st.plotly_chart(fig_stack)

            
            # # Tabela com Vendas e Percentuais
            st.text("Tabela com Vendas e Percentuais")
            st.subheader("Tabela com Vendas e Percentuais")
            st.dataframe(venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
            
            # Tabela com Totais ------------------------------
            df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            for modo in MODOS:
                df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            df_totals.insert(0, 'periodo_data', periodo_data_str)
            st.subheader("Tabela com Totais do Período")
            st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
        
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
            
            # Gráfico de Área (valores absolutos)
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
            
            # Gráfico de Barras (Percentuais) - colunas PERC_*
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
            st.subheader("Gráfico de Barras Empilhadas (Percentuais)")
            st.plotly_chart(fig_stack)
            
            # # Tabelas
            # df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            # for modo in MODOS:
            #     df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            # df_totals.insert(0, 'periodo_data', periodo_data_str)
            # st.subheader("Tabela com Totais do Período")
            # st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
            
            # st.subheader("Tabela com Vendas e Percentuais")
            # st.dataframe(
            #     venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS})
            # )
        
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
