import streamlit as st
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import plotly.graph_objects as go
from datetime import datetime

@st.cache_resource
def get_engine():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url, poolclass=NullPool, connect_args={'connect_timeout': 60})

@st.cache_data(ttl=3600)
def executar_query(_engine, query):
    tentativas = 3
    for i in range(tentativas):
        try:
            with _engine.connect() as conn:
                return pd.read_sql(text(query), conn)
        except Exception as e:
            if i == tentativas - 1:
                raise e
            st.warning(f"Reconectando... tentativa {i+1}")

@st.cache_data(ttl=3600)
def consultar_lojas(_engine):
    query = "SELECT DISTINCT LOJA FROM romaneios_dbf ORDER BY LOJA"
    return executar_query(_engine, query)

def semanas_do_mes(ano, mes):
    query = f"""
        SELECT DISTINCT WEEK(CADASTRO, 1) as semana
        FROM romaneios_dbf
        WHERE YEAR(CADASTRO) = {ano} AND MONTH(CADASTRO) = {mes}
        ORDER BY semana
    """
    engine = get_engine()
    df = executar_query(engine, query)
    return df['semana'].tolist() if not df.empty else [1]

def remover_outliers(df, coluna):
    Q1 = df[coluna].quantile(0.25)
    Q3 = df[coluna].quantile(0.75)
    IQR = Q3 - Q1
    return df[(df[coluna] >= Q1 - 1.5*IQR) & (df[coluna] <= Q3 + 1.5*IQR)]

def preencher_horas_dias(pivot):
    dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
    horas = range(7, 20)
    return pivot.reindex(index=horas, columns=dias, fill_value=0).fillna(0)

def gerar_subtitulo(periodo, ano, mes, semana):
    if periodo == "ANO":
        return f"Ano {ano}"
    elif periodo == "MÊS":
        return f"{datetime(ano, mes, 1).strftime('%B')} de {ano}"
    elif periodo == "SEMANA":
        return f"Semana {semana} de {datetime(ano, mes, 1).strftime('%B')} de {ano}"
    return ""

def converter_minutos_para_tempo(minutos):
    if pd.isna(minutos) or minutos == 0:
        return "0m"
    
    minutos = int(minutos)
    dias = minutos // 1440
    horas = (minutos % 1440) // 60
    mins = minutos % 60
    
    partes = []
    if dias > 0:
        partes.append(f"{dias}d")
    if horas > 0:
        partes.append(f"{horas}h")
    if mins > 0 or len(partes) == 0:
        partes.append(f"{mins}m")
    
    return " ".join(partes)

def main():
    st.sidebar.title("Filtros")
    
    engine = get_engine()
    lojas = consultar_lojas(engine)
    loja_selecionada = st.sidebar.selectbox("Loja", lojas['LOJA'])
    
    tipo_metrica = st.sidebar.selectbox(
        "Métrica",
        ["Quantidade de ROMANEIO", 
         "Mediana MINUTOS_DE_SEPARACAO",
         "Mediana MINUTOS_ENTREGA",
         "Mediana MINUTOS_ENTREGA_REALIZADA"]
    )
    
    periodo = st.sidebar.selectbox("Período", ["ANO", "MÊS", "SEMANA"])
    
    ano_atual = datetime.now().year
    anos = list(range(ano_atual, ano_atual-3, -1))
    ano = st.sidebar.selectbox("Ano", anos)
    
    mes = None
    semana = None
    
    if periodo in ["MÊS", "SEMANA"]:
        mes = st.sidebar.selectbox("Mês", range(1, 13), 
                                   format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
    
    if periodo == "SEMANA":
        semanas_disponiveis = semanas_do_mes(ano, mes)
        semana = st.sidebar.selectbox("Semana", semanas_disponiveis)
    
    queries = {
        "Quantidade de ROMANEIO": """
            SELECT 
                CASE DAYOFWEEK(r.CADASTRO)
                    WHEN 2 THEN 'Segunda' WHEN 3 THEN 'Terça' WHEN 4 THEN 'Quarta'
                    WHEN 5 THEN 'Quinta' WHEN 6 THEN 'Sexta' WHEN 7 THEN 'Sábado'
                END AS dia_semana,
                HOUR(r.CADASTRO) AS hora,
                DATE(r.CADASTRO) as data,
                WEEK(r.CADASTRO, 1) as semana,
                r.ROMANEIO,
                COUNT(DISTINCT r.ROMANEIO) AS quantidade
            FROM romaneios_dbf r
            WHERE r.LOJA = {loja}
              AND YEAR(r.CADASTRO) = {ano} {filtro_mes} {filtro_semana}
              AND DAYOFWEEK(r.CADASTRO) BETWEEN 2 AND 7
              AND HOUR(r.CADASTRO) BETWEEN 7 AND 19
            GROUP BY DAYOFWEEK(r.CADASTRO), HOUR(r.CADASTRO), DATE(r.CADASTRO), WEEK(r.CADASTRO, 1), r.ROMANEIO
        """,
        "Mediana MINUTOS_DE_SEPARACAO": """
            SELECT 
                CASE DAYOFWEEK(r.CADASTRO)
                    WHEN 2 THEN 'Segunda' WHEN 3 THEN 'Terça' WHEN 4 THEN 'Quarta'
                    WHEN 5 THEN 'Quinta' WHEN 6 THEN 'Sexta' WHEN 7 THEN 'Sábado'
                END AS dia_semana,
                HOUR(r.CADASTRO) AS hora,
                DATE(r.CADASTRO) as data,
                WEEK(r.CADASTRO, 1) as semana,
                r.ROMANEIO,
                TIMESTAMPDIFF(MINUTE, r.CADASTRO, r.TERMINO_SEPARACAO) as valor
            FROM romaneios_dbf r
            WHERE r.LOJA = {loja}
              AND YEAR(r.CADASTRO) = {ano} {filtro_mes} {filtro_semana}
              AND DAYOFWEEK(r.CADASTRO) BETWEEN 2 AND 7
              AND HOUR(r.CADASTRO) BETWEEN 7 AND 19
        """,
        "Mediana MINUTOS_ENTREGA": """
            SELECT 
                CASE DAYOFWEEK(r.CADASTRO)
                    WHEN 2 THEN 'Segunda' WHEN 3 THEN 'Terça' WHEN 4 THEN 'Quarta'
                    WHEN 5 THEN 'Quinta' WHEN 6 THEN 'Sexta' WHEN 7 THEN 'Sábado'
                END AS dia_semana,
                HOUR(r.CADASTRO) AS hora,
                DATE(r.CADASTRO) as data,
                WEEK(r.CADASTRO, 1) as semana,
                r.ROMANEIO,
                ei.ROTA_HORARIO_REALIZADO,
                TIMESTAMPDIFF(MINUTE, r.CADASTRO, ei.ROTA_HORARIO_REALIZADO) as valor
            FROM romaneios_dbf r
            LEFT JOIN expedicao_itens ei ON ei.VENDA_TIPO = 'ROMANEIO' 
                AND ei.CODIGO_VENDA = r.ROMANEIO AND ei.LOJA_VENDA = r.LOJA
            WHERE r.LOJA = {loja}
              AND YEAR(r.CADASTRO) = {ano} {filtro_mes} {filtro_semana}
              AND DAYOFWEEK(r.CADASTRO) BETWEEN 2 AND 7
              AND HOUR(r.CADASTRO) BETWEEN 7 AND 19
        """,
        "Mediana MINUTOS_ENTREGA_REALIZADA": """
            SELECT 
                CASE DAYOFWEEK(r.CADASTRO)
                    WHEN 2 THEN 'Segunda' WHEN 3 THEN 'Terça' WHEN 4 THEN 'Quarta'
                    WHEN 5 THEN 'Quinta' WHEN 6 THEN 'Sexta' WHEN 7 THEN 'Sábado'
                END AS dia_semana,
                HOUR(r.CADASTRO) AS hora,
                DATE(r.CADASTRO) as data,
                WEEK(r.CADASTRO, 1) as semana,
                r.ROMANEIO,
                ei.ROTA_HORARIO_REALIZADO,
                a.HORA_SAIDA,
                TIMESTAMPDIFF(MINUTE, a.HORA_SAIDA, ei.ROTA_HORARIO_REALIZADO) as valor
            FROM romaneios_dbf r
            LEFT JOIN expedicao_itens ei ON ei.VENDA_TIPO = 'ROMANEIO' 
                AND ei.CODIGO_VENDA = r.ROMANEIO AND ei.LOJA_VENDA = r.LOJA
            LEFT JOIN expedicao a ON ei.EXPEDICAO_CODIGO = a.EXPEDICAO 
                AND ei.EXPEDICAO_LOJA = a.LOJA
            WHERE r.LOJA = {loja}
              AND YEAR(r.CADASTRO) = {ano} {filtro_mes} {filtro_semana}
              AND DAYOFWEEK(r.CADASTRO) BETWEEN 2 AND 7
              AND HOUR(r.CADASTRO) BETWEEN 7 AND 19
        """
    }
    
    filtro_mes = f"AND MONTH(r.CADASTRO) = {mes}" if mes else ""
    filtro_semana = f"AND WEEK(r.CADASTRO, 1) = {semana}" if semana else ""
    
    query = queries[tipo_metrica].format(
        loja=loja_selecionada,
        ano=ano,
        filtro_mes=filtro_mes,
        filtro_semana=filtro_semana
    )
    
    with st.spinner('Carregando dados...'):
        df = executar_query(engine, query)
    
    if not df.empty:
        subtitulo = gerar_subtitulo(periodo, ano, mes, semana)
        st.title(f"Mapa de calor - {subtitulo}")
        
        coluna_vazia = False
        coluna_problema = None
        
        if tipo_metrica in ["Mediana MINUTOS_ENTREGA", "Mediana MINUTOS_ENTREGA_REALIZADA"]:
            if df['ROTA_HORARIO_REALIZADO'].isna().all():
                coluna_vazia = True
                coluna_problema = "ROTA_HORARIO_REALIZADO"
        
        if tipo_metrica == "Mediana MINUTOS_DE_SEPARACAO":
            if df['valor'].isna().all():
                coluna_vazia = True
                coluna_problema = "TERMINO_SEPARACAO"
        
        if coluna_vazia:
            st.warning(f"⚠️ A coluna '{coluna_problema}' da LOJA {loja_selecionada} não está preenchida. "
                       f"NÃO É POSSÍVEL calcular a mediana de minutos.")
        
        if coluna_vazia:
            st.markdown("### Tabela de Dados")
            tabela = df.groupby(['data', 'semana', 'dia_semana', 'hora']).agg(
                quantidade_romaneio=('ROMANEIO', 'nunique')
            ).reset_index()
            tabela['ano'] = ano
            tabela['mes'] = tabela['data'].apply(lambda x: x.month if hasattr(x, 'month') else mes)
            tabela = tabela[['ano', 'mes', 'semana', 'dia_semana', 'data', 'hora', 'quantidade_romaneio']]
            st.dataframe(tabela)
        
        if tipo_metrica == "Quantidade de ROMANEIO":
            pivot = df.pivot_table(values='quantidade', index='hora', columns='dia_semana', aggfunc='sum', fill_value=0)
        else:
            if not coluna_vazia:
                df_limpo = remover_outliers(df[df['valor'] > 0], 'valor')
                pivot = df_limpo.pivot_table(values='valor', index='hora', columns='dia_semana', aggfunc='median', fill_value=0)
            else:
                dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
                pivot = pd.DataFrame(0, index=range(7, 20), columns=dias)
        
        pivot = preencher_horas_dias(pivot)
        st.markdown(f"### {tipo_metrica}")
        
        valores_texto = pivot.values.astype(int) if tipo_metrica == "Quantidade de ROMANEIO" else pivot.values.round(1)
        formato_hover = '%{y}h - %{x}<br>Quantidade: %{z}<extra></extra>' if tipo_metrica == "Quantidade de ROMANEIO" else '%{y}h - %{x}<br>Minutos: %{z:.1f}<extra></extra>'
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns, y=pivot.index,
            colorscale='Blues', text=valores_texto, texttemplate='%{text}',
            textfont={"size": 11, "color": "black"},
            colorbar=dict(title="", thickness=15, len=0.7, x=1.02),
            xgap=1, ygap=1, hovertemplate=formato_hover
        ))
        
        fig.update_layout(
            xaxis=dict(title="", side="top", tickfont=dict(size=11, color='black'), showgrid=False),
            yaxis=dict(title="Hora", tickfont=dict(size=11, color='black'), showgrid=False, autorange="reversed"),
            height=600, plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(l=50, r=80, t=80, b=50)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Tabela de Dados")
        
        if tipo_metrica == "Quantidade de ROMANEIO":
            tabela = df.groupby(['data', 'semana', 'dia_semana', 'hora']).agg(
                quantidade_romaneio=('ROMANEIO', 'nunique')
            ).reset_index()
        else:
            if not coluna_vazia:
                df_validos = df[df['valor'].notna()]
                tabela = df_validos.groupby(['data', 'semana', 'dia_semana', 'hora']).agg(
                    quantidade_romaneio=('ROMANEIO', 'nunique'),
                    mediana_minutos=('valor', 'median')
                ).reset_index()
            else:
                tabela = df.groupby(['data', 'semana', 'dia_semana', 'hora']).agg(
                    quantidade_romaneio=('ROMANEIO', 'nunique')
                ).reset_index()
        
        tabela['ano'] = ano
        tabela['mes'] = tabela['data'].apply(lambda x: x.month if hasattr(x, 'month') else mes)
        
        if 'mediana_minutos' in tabela.columns:
            tabela['mediana_minutos'] = tabela['mediana_minutos'].apply(converter_minutos_para_tempo)
        
        colunas_base = ['ano', 'mes', 'semana', 'dia_semana', 'data', 'hora', 'quantidade_romaneio']
        if 'mediana_minutos' in tabela.columns:
            colunas_base.append('mediana_minutos')
        
        tabela = tabela[colunas_base]
        st.dataframe(tabela)
        
    else:
        st.warning("Sem dados para o período selecionado")

if __name__ == "__main__":
    main()