import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import calendar

# Configuração da página
st.set_page_config(page_title="Análise de Performance Logística", layout="wide", page_icon="📊")



# Configurações globais
dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# Funções de conexão e consulta
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

def executar_query(engine, query):
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Erro ao executar a query: {e}")
        return pd.DataFrame()

def consultar_lojas(engine):
    query = "SELECT codigo, nome FROM autogeral.lojas ORDER BY codigo"
    return executar_query(engine, query)

# Funções de data
def obter_ultimos_anos():
    ano_atual = datetime.now().year
    return [ano_atual - i for i in range(3)]

def obter_meses():
    return list(calendar.month_name)[1:]

def obter_semanas(ano, mes):
    return len(calendar.monthcalendar(ano, mes))

# Query principal
def gerar_query_dados(inicio, fim, loja):
    return f"""
        SELECT a.expedicao, r.ROMANEIO, a.LOJA, a.CADASTRO,
               d.DESCRICAO AS 'Entregador',
               a.KM_RETORNO - a.KM_SAIDA AS KMS,
               a.ROTA_METROS/1000 AS KM_DISTANCIA,
               a.HORA_SAIDA, a.HORA_RETORNO,
               r.TERMINO_SEPARACAO,
               TIMESTAMPDIFF(MINUTE, r.CADASTRO, r.TERMINO_SEPARACAO) AS MINUTOS_SEPARACAO,
               TIMESTAMPDIFF(MINUTE, r.CADASTRO, e.ROTA_HORARIO_REALIZADO) AS MINUTOS_ENTREGA_TOTAL,
               TIMESTAMPDIFF(MINUTE, a.HORA_SAIDA, e.ROTA_HORARIO_REALIZADO) AS MINUTOS_ENTREGA_ROTA,
               e.ROTA_STATUS,
               e.ROTA_HORARIO_PREVISTO,
               e.ROTA_HORARIO_REALIZADO,
               CASE 
                   WHEN (a.ROTA_METROS/1000) <= 7 THEN 'Até 7km'
                   WHEN (a.ROTA_METROS/1000) > 40 THEN 'Mais de 40km'
                   ELSE 'Entre 7km e 40km'
               END AS CATEGORIA_DISTANCIA
        FROM expedicao_itens e
        JOIN expedicao a ON e.EXPEDICAO_CODIGO = a.EXPEDICAO AND e.EXPEDICAO_LOJA = a.LOJA
        JOIN entregador d ON a.ENTREGADOR_CODIGO = d.CODIGO
        LEFT JOIN romaneios_dbf r ON e.VENDA_TIPO = 'ROMANEIO' AND e.CODIGO_VENDA = r.ROMANEIO AND e.LOJA_VENDA = r.LOJA
        WHERE a.ROTA_METROS IS NOT NULL
          AND a.LOJA = {loja}
          AND e.ROTA_STATUS = 'ENTREGUE'
          AND r.CADASTRO BETWEEN '{inicio}' AND '{fim}'
          AND TIMESTAMPDIFF(MINUTE, r.CADASTRO, r.TERMINO_SEPARACAO) > 0
          AND TIMESTAMPDIFF(MINUTE, r.CADASTRO, e.ROTA_HORARIO_REALIZADO) > 0;
    """

# Função para eficiência dos entregadores
def analise_eficiencia_entregadores(df):
    st.subheader("📈 Eficiência dos Entregadores")
    
    # Calcular métricas por entregador
    metricas = df.groupby('Entregador').agg({
        'ROMANEIO': 'count',
        'MINUTOS_ENTREGA_TOTAL': 'mean',
        'MINUTOS_SEPARACAO': 'mean',
        'KM_DISTANCIA': 'mean',
        'KMS': 'sum'
    }).round(2)
    
    metricas.columns = ['Total Entregas', 'Tempo Médio Total (min)', 'Tempo Médio Separação (min)', 'Distância Média (km)', 'KM Total']
    metricas['Entregas/Hora'] = round(60 / metricas['Tempo Médio Total (min)'], 2)
    
    # Tabela
    st.write("**Tabela de Eficiência por Entregador:**")
    st.dataframe(metricas.sort_values('Total Entregas', ascending=False))
    
    # Gráfico de barras
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(metricas.reset_index(), 
                     x='Entregador', 
                     y='Total Entregas',
                     title='Total de Entregas por Entregador',
                     color='Total Entregas',
                     color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(metricas.reset_index(), 
                     x='Entregador', 
                     y='Entregas/Hora',
                     title='Entregas por Hora por Entregador',
                     color='Entregas/Hora',
                     color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)

# Função para mapa de calor genérico
def gerar_mapa_calor(df, coluna, titulo, formato='.1f'):
    df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
    df['DIA_DA_SEMANA'] = df['CADASTRO'].dt.dayofweek.map(lambda x: dias_semana[x] if x < 6 else 'Domingo')
    df['HORA'] = df['CADASTRO'].dt.hour
    
    # Agrupar por hora e dia da semana
    pivot_data = df.groupby(['HORA', 'DIA_DA_SEMANA'])[coluna].median().unstack(fill_value=0)
    
    # Garantir ordem dos dias
    dias_ordenados = [dia for dia in dias_semana if dia in pivot_data.columns]
    pivot_data = pivot_data[dias_ordenados]
    
    # Criar mapa de calor
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(pivot_data, annot=True, fmt=formato, cmap='Blues', ax=ax)
    ax.set_title(titulo)
    ax.set_xlabel('Dia da Semana')
    ax.set_ylabel('Hora do Dia')
    
    return fig

# Função para tempo de entrega
def analise_tempo_entrega(df):
    st.subheader("⏱️ Tempo de Entrega")
    
    # Estatísticas gerais
    stats = df['MINUTOS_ENTREGA_TOTAL'].describe().round(2)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tempo Médio", f"{stats['mean']:.1f} min")
    with col2:
        st.metric("Tempo Mediano", f"{stats['50%']:.1f} min")
    with col3:
        st.metric("Tempo Mínimo", f"{stats['min']:.1f} min")
    with col4:
        st.metric("Tempo Máximo", f"{stats['max']:.1f} min")
    
    # Tabela por hora
    df_hora = df.copy()
    df_hora['HORA'] = pd.to_datetime(df_hora['CADASTRO']).dt.hour
    tabela_hora = df_hora.groupby('HORA')['MINUTOS_ENTREGA_TOTAL'].agg(['count', 'mean', 'median']).round(2)
    tabela_hora.columns = ['Quantidade', 'Média (min)', 'Mediana (min)']
    
    st.write("**Tempo de Entrega por Hora:**")
    st.dataframe(tabela_hora)
    
    # Mapa de calor
    fig = gerar_mapa_calor(df, 'MINUTOS_ENTREGA_TOTAL', 'Mapa de Calor - Tempo de Entrega (minutos)')
    st.pyplot(fig)

# Função para tempo de separação
def analise_tempo_separacao(df):
    st.subheader("📦 Tempo de Separação")
    
    # Estatísticas gerais
    stats = df['MINUTOS_SEPARACAO'].describe().round(2)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tempo Médio", f"{stats['mean']:.1f} min")
    with col2:
        st.metric("Tempo Mediano", f"{stats['50%']:.1f} min")
    with col3:
        st.metric("Tempo Mínimo", f"{stats['min']:.1f} min")
    with col4:
        st.metric("Tempo Máximo", f"{stats['max']:.1f} min")
    
    # Tabela por hora
    df_hora = df.copy()
    df_hora['HORA'] = pd.to_datetime(df_hora['CADASTRO']).dt.hour
    tabela_hora = df_hora.groupby('HORA')['MINUTOS_SEPARACAO'].agg(['count', 'mean', 'median']).round(2)
    tabela_hora.columns = ['Quantidade', 'Média (min)', 'Mediana (min)']
    
    st.write("**Tempo de Separação por Hora:**")
    st.dataframe(tabela_hora)
    
    # Mapa de calor
    fig = gerar_mapa_calor(df, 'MINUTOS_SEPARACAO', 'Mapa de Calor - Tempo de Separação (minutos)')
    st.pyplot(fig)

# Função para entregas até 7km
def analise_entregas_7km(df):
    st.subheader("🎯 Entregas até 7km - Meta 40 minutos")
    
    # Filtrar entregas até 7km
    df_7km = df[df['CATEGORIA_DISTANCIA'] == 'Até 7km'].copy()
    
    if df_7km.empty:
        st.warning("Nenhuma entrega encontrada para distâncias até 7km.")
        return
    
    # Classificar entregas pela meta
    df_7km['DENTRO_META'] = df_7km['MINUTOS_ENTREGA_TOTAL'] <= 40
    
    # Métricas gerais
    total_entregas = len(df_7km)
    dentro_meta = df_7km['DENTRO_META'].sum()
    fora_meta = total_entregas - dentro_meta
    percentual_meta = (dentro_meta / total_entregas) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Entregas ≤7km", total_entregas)
    with col2:
        st.metric("Dentro da Meta", dentro_meta)
    with col3:
        st.metric("Fora da Meta", fora_meta)
    with col4:
        st.metric("% Meta Atingida", f"{percentual_meta:.1f}%")
    
    # Tabela detalhada
    tabela_meta = df_7km.groupby('DENTRO_META').agg({
        'ROMANEIO': 'count',
        'MINUTOS_ENTREGA_TOTAL': ['mean', 'median'],
        'KM_DISTANCIA': 'mean'
    }).round(2)
    
    tabela_meta.columns = ['Quantidade', 'Tempo Médio', 'Tempo Mediano', 'Distância Média']
    tabela_meta.index = ['Fora da Meta (>40min)', 'Dentro da Meta (≤40min)']
    
    st.write("**Análise por Meta:**")
    st.dataframe(tabela_meta)
    
    # Gráfico de barras
    fig = px.bar(x=['Dentro da Meta', 'Fora da Meta'], 
                 y=[dentro_meta, fora_meta],
                 title='Entregas até 7km - Cumprimento da Meta de 40 minutos',
                 color=['Dentro da Meta', 'Fora da Meta'],
                 color_discrete_map={'Dentro da Meta': 'green', 'Fora da Meta': 'red'})
    st.plotly_chart(fig, use_container_width=True)
    
    # Mapa de calor para entregas dentro da meta
    fig = gerar_mapa_calor(df_7km[df_7km['DENTRO_META']], 'MINUTOS_ENTREGA_TOTAL', 
                          'Mapa de Calor - Entregas ≤7km Dentro da Meta (≤40min)')
    st.pyplot(fig)

# Função para entregas mais de 40km
def analise_entregas_40km(df):
    st.subheader("🚛 Entregas acima de 40km")
    
    # Filtrar entregas acima de 40km
    df_40km = df[df['CATEGORIA_DISTANCIA'] == 'Mais de 40km'].copy()
    
    if df_40km.empty:
        st.warning("Nenhuma entrega encontrada para distâncias acima de 40km.")
        return
    
    # Estatísticas gerais
    total_entregas = len(df_40km)
    tempo_medio = df_40km['MINUTOS_ENTREGA_TOTAL'].mean()
    distancia_media = df_40km['KM_DISTANCIA'].mean()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Entregas >40km", total_entregas)
    with col2:
        st.metric("Tempo Médio", f"{tempo_medio:.1f} min")
    with col3:
        st.metric("Distância Média", f"{distancia_media:.1f} km")
    
    # Tabela por entregador
    tabela_entregador = df_40km.groupby('Entregador').agg({
        'ROMANEIO': 'count',
        'MINUTOS_ENTREGA_TOTAL': 'mean',
        'KM_DISTANCIA': 'mean'
    }).round(2)
    
    tabela_entregador.columns = ['Quantidade', 'Tempo Médio (min)', 'Distância Média (km)']
    
    st.write("**Entregas >40km por Entregador:**")
    st.dataframe(tabela_entregador.sort_values('Quantidade', ascending=False))
    
    # Gráfico de barras por entregador
    fig = px.bar(tabela_entregador.reset_index(), 
                 x='Entregador', 
                 y='Quantidade',
                 title='Quantidade de Entregas >40km por Entregador',
                 color='Quantidade',
                 color_continuous_scale='Reds')
    st.plotly_chart(fig, use_container_width=True)
    
    # Mapa de calor para entregas >40km por hora e dia da semana
    st.write("**Distribuição de Entregas >40km por Hora e Dia da Semana:**")
    
    # Preparar dados para o mapa de calor
    df_40km['CADASTRO'] = pd.to_datetime(df_40km['CADASTRO'])
    df_40km['DIA_DA_SEMANA'] = df_40km['CADASTRO'].dt.dayofweek.map(lambda x: dias_semana[x] if x < 6 else 'Domingo')
    df_40km['HORA'] = df_40km['CADASTRO'].dt.hour
    
    # Criar tabela para hora e dia da semana
    tabela_hora_dia = df_40km.groupby(['HORA', 'DIA_DA_SEMANA']).size().unstack(fill_value=0)
    
    # Garantir ordem dos dias
    dias_ordenados = [dia for dia in dias_semana if dia in tabela_hora_dia.columns]
    if dias_ordenados:
        tabela_hora_dia = tabela_hora_dia[dias_ordenados]
        
        st.dataframe(tabela_hora_dia)
        
        # Criar mapa de calor
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(tabela_hora_dia, annot=True, fmt='d', cmap='Blues', ax=ax)
        ax.set_title('Mapa de Calor - Entregas >40km por Hora e Dia da Semana')
        ax.set_xlabel('Dia da Semana')
        ax.set_ylabel('Hora do Dia')
        st.pyplot(fig)
    else:
        st.info("Dados insuficientes para gerar o mapa de calor.")

# Função principal
def main():
    st.title("📊 Análise de Performance Logística")
    
    # Criar conexão
    engine = criar_conexao()
    
    # Sidebar para filtros
    st.sidebar.header("Filtros")
    
    # Seleção de loja
    df_lojas = consultar_lojas(engine)
    loja_dict = dict(zip(df_lojas['codigo'], df_lojas['nome']))
    loja_selecionada = st.sidebar.selectbox("Selecione a loja", 
                                           options=loja_dict.keys(), 
                                           format_func=lambda x: loja_dict[x])
    
    # Navegação por período
    periodo = st.sidebar.radio("Período de Análise", ["Ano", "Mês", "Semana"])
    
    # Configurar datas baseado no período
    if periodo == "Ano":
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Ano", anos)
        data_inicio = datetime(ano_selecionado, 1, 1)
        data_fim = datetime(ano_selecionado, 12, 31)
        titulo_periodo = f"Ano {ano_selecionado}"
        
    elif periodo == "Mês":
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Ano", anos)
        meses = obter_meses()
        mes_selecionado = st.sidebar.selectbox("Mês", meses)
        
        mes_index = meses.index(mes_selecionado) + 1
        data_inicio = datetime(ano_selecionado, mes_index, 1)
        _, ultimo_dia = calendar.monthrange(ano_selecionado, mes_index)
        data_fim = datetime(ano_selecionado, mes_index, ultimo_dia)
        titulo_periodo = f"{mes_selecionado}/{ano_selecionado}"
        
    else:  # Semana
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Ano", anos)
        meses = obter_meses()
        mes_selecionado = st.sidebar.selectbox("Mês", meses)
        
        mes_index = meses.index(mes_selecionado) + 1
        semanas = obter_semanas(ano_selecionado, mes_index)
        semana_selecionada = st.sidebar.selectbox("Semana", range(1, semanas + 1))
        
        calendario_mes = calendar.monthcalendar(ano_selecionado, mes_index)
        semana = calendario_mes[semana_selecionada - 1]
        
        primeiro_dia = [d for d in semana if d != 0][0]
        ultimo_dia = [d for d in semana if d != 0][-1]
        
        data_inicio = datetime(ano_selecionado, mes_index, primeiro_dia)
        data_fim = datetime(ano_selecionado, mes_index, ultimo_dia)
        titulo_periodo = f"Semana {semana_selecionada} - {mes_selecionado}/{ano_selecionado}"
    
    # Executar query
    st.info(f"Analisando dados para: {loja_dict[loja_selecionada]} - {titulo_periodo}")
    
    query = gerar_query_dados(data_inicio, data_fim, loja_selecionada)
    df = executar_query(engine, query)
    
    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return
    
    # Exibir resumo geral
    st.subheader("📋 Resumo Geral")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Entregas", len(df))
    with col2:
        st.metric("Entregadores Ativos", df['Entregador'].nunique())
    with col3:
        st.metric("Tempo Médio Total", f"{df['MINUTOS_ENTREGA_TOTAL'].mean():.1f} min")
    with col4:
        st.metric("Distância Média", f"{df['KM_DISTANCIA'].mean():.1f} km")
    
    # Tabs para diferentes análises
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Eficiência Entregadores", 
        "⏱️ Tempo Entrega", 
        "📦 Tempo Separação", 
        "🎯 Entregas ≤7km", 
        "🚛 Entregas >40km"
    ])
    
    with tab1:
        analise_eficiencia_entregadores(df)
    
    with tab2:
        analise_tempo_entrega(df)
    
    with tab3:
        analise_tempo_separacao(df)
    
    with tab4:
        analise_entregas_7km(df)
    
    with tab5:
        analise_entregas_40km(df)

if __name__ == "__main__":
    main()