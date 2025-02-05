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
CORES = {'CASADA': '#636EFA', 'FUTURA': '#EF553B', 'PRONTA_ENTREGA': '#00CC96'}

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
    
    Parâmetros:
      - data: DataFrame com os dados agregados para o gráfico.
      - x_col: Nome da coluna a ser usada no eixo X.
      - modos: Lista de modos a serem plotados.
      - titulo: Título do gráfico.
      - x_label: Rótulo do eixo X.
      - cores: Mapeamento de cores para os modos.
    """
    fig = px.area(
        data,
        x=x_col,
        y=modos,
        labels={'value': 'Quantidade de Vendas', x_col: x_label},
        title=titulo,
        color_discrete_map=cores
    )
    # Atualiza os traces para exibir linhas, marcadores e textos (posição "top center")
    fig.update_traces(
        mode='lines+markers+text',
        texttemplate='%{y}',
        textposition='top center'
    )
    fig.update_layout(yaxis_title='Quantidade de Vendas', xaxis_title=x_label)
    return fig

def process_visualizacao(engine, data_inicio, data_fim, loja, titulo, periodo):
    """
    Executa a query, processa os dados e chama a função de geração do gráfico e tabelas.
    
    Parâmetros:
      - engine: Conexão com o banco.
      - data_inicio, data_fim: Intervalo de datas para a query.
      - loja: Código da loja selecionada.
      - titulo: Título da visualização.
      - periodo: Tipo de agregação ("Ano", "Mês", "Semana" ou "Seleciona data").
    """
    query = gerar_query_dados(data_inicio, data_fim, loja)
    df = executar_query(engine, query)
    if df.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
    else:
        gerar_grafico(df, titulo, data_inicio, data_fim, periodo)

def gerar_grafico(df, titulo, data_inicio, data_fim, periodo):
    """
    Gera o gráfico de área e exibe as tabelas com a agregação das vendas e os totais do período.
    
    Parâmetros:
      - df: DataFrame com os dados extraídos.
      - titulo: Título do gráfico.
      - data_inicio: Data inicial do período.
      - data_fim: Data final do período.
      - periodo: Tipo de agregação: "Ano", "Mês", "Semana" ou "Seleciona data".
    """
    try:
        # Pré-processamento: converter datas e filtrar o período
        df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
        df = df[(df['CADASTRO'] >= pd.Timestamp(data_inicio)) & 
                (df['CADASTRO'] <= pd.Timestamp(data_fim))]
        df['MODO'] = df['MODO'].astype(str)
        
        # Se algum ROMANEIO tiver registro 'CASADA', marca todos como 'CASADA'
        romaneios_casada = df.loc[df['MODO'] == 'CASADA', 'ROMANEIO'].unique()
        df.loc[df['ROMANEIO'].isin(romaneios_casada), 'MODO'] = 'CASADA'
        
        # Variável para o intervalo selecionado (usada na tabela de totais)
        periodo_data_str = f"{data_inicio.strftime('%d/%m/%Y')} - {data_fim.strftime('%d/%m/%Y')}"
        
        if periodo == "Ano":
            df['mes'] = df['CADASTRO'].dt.month
            venda_agrupada = df.groupby(['mes', 'LOJA', 'MODO']).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            venda_agrupada['mes_nome'] = venda_agrupada['mes'].apply(lambda m: calendar.month_name[m])
            venda_agrupada = venda_agrupada.sort_values('mes')
            colunas_final = ['mes_nome', 'LOJA'] + MODOS + ['TOTAL'] + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]
            
            # Agregação para o gráfico: soma sobre as lojas
            venda_agrupada_graph = venda_agrupada.groupby('mes_nome', as_index=False)[MODOS].sum()
            meses_ordem = [calendar.month_name[i] for i in range(1, 13)]
            venda_agrupada_graph['mes_nome'] = pd.Categorical(
                venda_agrupada_graph['mes_nome'], categories=meses_ordem, ordered=True
            )
            venda_agrupada_graph = venda_agrupada_graph.sort_values('mes_nome')
            fig = create_area_chart(venda_agrupada_graph, 'mes_nome', MODOS, titulo, 'Mês', CORES)
            
            st.subheader("Gráfico de Área")
            st.plotly_chart(fig)
            if st.checkbox("Tabela com Vendas e Percentuais"):
                st.subheader("Tabela com Vendas e Percentuais")
                st.dataframe(venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
            
            # Tabela com os totais do período (agrupado por loja)
            df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            for modo in MODOS:
                df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            df_totals.insert(0, 'periodo_data', periodo_data_str)
            st.subheader("Tabela com Totais do Período")
            st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
        
        elif periodo == "Mês":
            df['dia'] = df['CADASTRO'].dt.day
            venda_agrupada = df.groupby(['dia', 'LOJA', 'MODO']).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            venda_agrupada = venda_agrupada.sort_values('dia')
            colunas_final = ['dia', 'LOJA'] + MODOS + ['TOTAL'] + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]
            
            venda_agrupada_graph = venda_agrupada.groupby('dia', as_index=False)[MODOS].sum()
            venda_agrupada_graph = venda_agrupada_graph.sort_values('dia')
            fig = create_area_chart(venda_agrupada_graph, 'dia', MODOS, titulo, 'Dia', CORES)
            
            st.subheader("Gráfico de Área")
            st.plotly_chart(fig)
            if st.checkbox("Tabela com Vendas e Percentuais"):
                st.subheader("Tabela com Vendas e Percentuais")
                st.dataframe(venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
            
            # Tabela com Totais do Período
            df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            for modo in MODOS:
                df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            df_totals.insert(0, 'periodo_data', periodo_data_str)
            st.subheader("Tabela com Totais do Período")
            st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
        
        elif periodo == "Semana":
            df['dia_semana'] = df['CADASTRO'].dt.dayofweek
            df = df[df['dia_semana'] < 6]  # considerar somente segunda a sábado
            venda_agrupada = df.groupby(['dia_semana', 'LOJA', 'MODO']).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            mapping = {0: 'segunda', 1: 'terça', 2: 'quarta', 3: 'quinta', 4: 'sexta', 5: 'sábado'}
            venda_agrupada['dia_nome'] = venda_agrupada['dia_semana'].map(mapping)
            venda_agrupada = venda_agrupada.sort_values('dia_semana')
            colunas_final = ['dia_nome', 'LOJA'] + MODOS + ['TOTAL'] + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]
            
            venda_agrupada_graph = venda_agrupada.groupby('dia_nome', as_index=False)[MODOS].sum()
            venda_agrupada_graph['dia_nome'] = pd.Categorical(
                venda_agrupada_graph['dia_nome'],
                categories=DIAS_SEMANA,
                ordered=True
            )
            venda_agrupada_graph = venda_agrupada_graph.sort_values('dia_nome')
            fig = create_area_chart(venda_agrupada_graph, 'dia_nome', MODOS, titulo, 'Dia da Semana', CORES)
            
            st.subheader("Gráfico de Área")
            st.plotly_chart(fig)
            if st.checkbox("Tabela com Vendas e Percentuais"):
                st.subheader("Tabela com Vendas e Percentuais")
                st.dataframe(venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
            
            # Tabela com Totais do Período
            df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            for modo in MODOS:
                df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            df_totals.insert(0, 'periodo_data', periodo_data_str)
            st.subheader("Tabela com Totais do Período")
            st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
        
        elif periodo == "Seleciona data":
            # Agrupamento diário: cria uma coluna com a data (formato dia/mês/ano)
            df['periodo_data'] = df['CADASTRO'].dt.date
            venda_agrupada = df.groupby(['periodo_data', 'LOJA', 'MODO']).size().unstack(fill_value=0).reset_index()
            venda_agrupada = add_total_and_percentages(venda_agrupada, MODOS)
            venda_agrupada = venda_agrupada.sort_values('periodo_data')
            colunas_final = ['periodo_data', 'LOJA'] + MODOS + ['TOTAL'] + [f'PERC_{modo}' for modo in MODOS]
            venda_agrupada = venda_agrupada[colunas_final]
            
            # Agregação para o gráfico: soma as vendas diárias (soma sobre as lojas)
            venda_agrupada_graph = venda_agrupada.groupby('periodo_data', as_index=False)[MODOS].sum()
            venda_agrupada_graph = venda_agrupada_graph.sort_values('periodo_data')
            
            fig = create_area_chart(venda_agrupada_graph, 'periodo_data', MODOS, titulo, 'Data', CORES)
            st.subheader("Gráfico de Área")
            st.plotly_chart(fig)
            if st.checkbox("Tabela com Vendas e Percentuais"):
                st.subheader("Tabela com Vendas e Percentuais")
                st.dataframe(venda_agrupada.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
            
            # Tabela com os totais do período (agrupado por loja)
            df_totals = venda_agrupada.groupby('LOJA', as_index=False)[MODOS + ['TOTAL']].sum()
            for modo in MODOS:
                df_totals[f'PERC_{modo}'] = (df_totals[modo] / df_totals['TOTAL'].replace(0, 1)) * 100
            df_totals.insert(0, 'periodo_data', periodo_data_str)
            st.subheader("Tabela com Totais do Período")
            st.dataframe(df_totals.style.format({f'PERC_{modo}': "{:.2f}%" for modo in MODOS}))
        
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
    # Seleção da loja
    loja_selecionada = st.sidebar.selectbox(
        "Selecione a loja",
        options=list(loja_dict.keys()),
        format_func=lambda x: loja_dict[x],
        key="mnavh_loja"
    )
    
    # Seleção do tipo de agregação (Ano, Mês, Semana ou Seleciona data)
    navegacao = st.sidebar.radio("Navegação", options=["Ano", "Mês", "Semana", "Seleciona data"], key="mnavh_navegacao")
    
    if navegacao == "Ano":
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="mnavh_ano")
        data_inicio = datetime(ano_selecionado, 1, 1)
        data_fim = datetime(ano_selecionado, 12, 31)
        if st.sidebar.button("Gerar gráfico e tabela"):
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
        if st.sidebar.button("Gerar gráfico e tabela"):
            titulo = f"Vendas por Dia - {mes_selecionado}/{ano_selecionado}"
            process_visualizacao(engine, data_inicio, data_fim, loja_selecionada, titulo, "Mês")
                
    elif navegacao == "Semana":
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="mnavh_semana_ano")
        meses = obter_meses()
        mes_selecionado = st.sidebar.selectbox("Selecione o mês", options=meses, key="mnavh_semana_mes")
        mes_index = meses.index(mes_selecionado) + 1
        total_semanas = obter_semanas(ano_selecionado, mes_index)
        semana_selecionada = st.sidebar.selectbox("Selecione a semana", options=list(range(1, total_semanas + 1)), key="mnavh_semana_semana")
        
        calendario_mes = calendar.monthcalendar(ano_selecionado, mes_index)
        semana = calendario_mes[semana_selecionada - 1]
        valid_days = [d for d in semana if d != 0]
        if not valid_days:
            st.warning("Semana selecionada não possui dias válidos.")
            return
        data_inicio = datetime(ano_selecionado, mes_index, valid_days[0])
        data_fim = datetime(ano_selecionado, mes_index, valid_days[-1])
        if st.sidebar.button("Gerar gráfico e tabela"):
            titulo = f"Vendas por Dia da Semana - Semana {semana_selecionada} de {mes_selecionado}/{ano_selecionado}"
            process_visualizacao(engine, data_inicio, data_fim, loja_selecionada, titulo, "Semana")
    
    elif navegacao == "Seleciona data":
        # Seleção separada de data inicial e data final
        data_inicio_input = st.sidebar.date_input("Data Inicial", key="mnavh_data_inicio")
        data_fim_input = st.sidebar.date_input("Data Final", key="mnavh_data_fim")
        
        if not data_inicio_input or not data_fim_input:
            st.error("Selecione as duas datas: Data Inicial e Data Final.")
            return

        data_inicio = datetime.combine(data_inicio_input, datetime.min.time())
        data_fim = datetime.combine(data_fim_input, datetime.max.time())
        
        if st.sidebar.button("Gerar gráfico e tabela"):
            titulo = f"Vendas no período: {data_inicio_input.strftime('%d/%m/%Y')} a {data_fim_input.strftime('%d/%m/%Y')}"
            process_visualizacao(engine, data_inicio, data_fim, loja_selecionada, titulo, "Seleciona data")

if __name__ == "__main__":
    main()
