import streamlit as st
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import plotly.graph_objects as go
from datetime import datetime

DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
MESES_NOMES = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 
               5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 
               9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}

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

def preencher_meses_dias(pivot):
    meses = list(MESES_NOMES.values())
    pivot = pivot.reindex(index=meses, columns=DIAS_SEMANA, fill_value=0)
    return pivot.fillna(0)

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

def remover_outliers(df, coluna):
    Q1 = df[coluna].quantile(0.25)
    Q3 = df[coluna].quantile(0.75)
    IQR = Q3 - Q1
    return df[(df[coluna] >= Q1 - 1.5*IQR) & (df[coluna] <= Q3 + 1.5*IQR)]

def get_queries():
    return {
        "Quantidade de ROMANEIO": """
            SELECT 
                CASE DAYOFWEEK(r.CADASTRO)
                    WHEN 2 THEN 'Segunda' WHEN 3 THEN 'Terça' WHEN 4 THEN 'Quarta'
                    WHEN 5 THEN 'Quinta' WHEN 6 THEN 'Sexta' WHEN 7 THEN 'Sábado'
                END AS dia_semana,
                MONTH(r.CADASTRO) AS mes_num,
                DATE(r.CADASTRO) as data,
                WEEK(r.CADASTRO, 1) as semana,
                r.ROMANEIO
            FROM romaneios_dbf r
            WHERE r.LOJA = {loja}
              AND YEAR(r.CADASTRO) = {ano}
              AND DAYOFWEEK(r.CADASTRO) BETWEEN 2 AND 7
        """,
        "Mediana MINUTOS_DE_SEPARACAO": """
            SELECT 
                CASE DAYOFWEEK(r.CADASTRO)
                    WHEN 2 THEN 'Segunda' WHEN 3 THEN 'Terça' WHEN 4 THEN 'Quarta'
                    WHEN 5 THEN 'Quinta' WHEN 6 THEN 'Sexta' WHEN 7 THEN 'Sábado'
                END AS dia_semana,
                MONTH(r.CADASTRO) AS mes_num,
                DATE(r.CADASTRO) as data,
                WEEK(r.CADASTRO, 1) as semana,
                r.ROMANEIO,
                TIMESTAMPDIFF(MINUTE, r.CADASTRO, r.TERMINO_SEPARACAO) as valor
            FROM romaneios_dbf r
            WHERE r.LOJA = {loja}
              AND YEAR(r.CADASTRO) = {ano}
              AND DAYOFWEEK(r.CADASTRO) BETWEEN 2 AND 7
        """,
        "Mediana MINUTOS_ENTREGA": """
            SELECT 
                CASE DAYOFWEEK(r.CADASTRO)
                    WHEN 2 THEN 'Segunda' WHEN 3 THEN 'Terça' WHEN 4 THEN 'Quarta'
                    WHEN 5 THEN 'Quinta' WHEN 6 THEN 'Sexta' WHEN 7 THEN 'Sábado'
                END AS dia_semana,
                MONTH(r.CADASTRO) AS mes_num,
                DATE(r.CADASTRO) as data,
                WEEK(r.CADASTRO, 1) as semana,
                r.ROMANEIO,
                ei.ROTA_HORARIO_REALIZADO,
                TIMESTAMPDIFF(MINUTE, r.CADASTRO, ei.ROTA_HORARIO_REALIZADO) as valor
            FROM romaneios_dbf r
            LEFT JOIN expedicao_itens ei ON ei.VENDA_TIPO = 'ROMANEIO' 
                AND ei.CODIGO_VENDA = r.ROMANEIO AND ei.LOJA_VENDA = r.LOJA
            WHERE r.LOJA = {loja}
              AND YEAR(r.CADASTRO) = {ano}
              AND DAYOFWEEK(r.CADASTRO) BETWEEN 2 AND 7
        """,
        "Mediana MINUTOS_ENTREGA_REALIZADA": """
            SELECT 
                CASE DAYOFWEEK(r.CADASTRO)
                    WHEN 2 THEN 'Segunda' WHEN 3 THEN 'Terça' WHEN 4 THEN 'Quarta'
                    WHEN 5 THEN 'Quinta' WHEN 6 THEN 'Sexta' WHEN 7 THEN 'Sábado'
                END AS dia_semana,
                MONTH(r.CADASTRO) AS mes_num,
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
              AND YEAR(r.CADASTRO) = {ano}
              AND DAYOFWEEK(r.CADASTRO) BETWEEN 2 AND 7
        """
    }

def verificar_coluna_vazia(df, tipo_metrica):
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
    
    return coluna_vazia, coluna_problema

def criar_pivot(df, tipo_metrica, coluna_vazia):
    if tipo_metrica == "Quantidade de ROMANEIO":
        pivot = df.groupby(['mes', 'dia_semana'])['ROMANEIO'].nunique().reset_index()
        pivot = pivot.pivot(index='mes', columns='dia_semana', values='ROMANEIO')
    else:
        if not coluna_vazia:
            df_limpo = remover_outliers(df[df['valor'] > 0], 'valor')
            pivot = df_limpo.pivot_table(values='valor', index='mes', columns='dia_semana', aggfunc='median')
        else:
            meses = list(MESES_NOMES.values())
            pivot = pd.DataFrame(0, index=meses, columns=DIAS_SEMANA)
    
    return preencher_meses_dias(pivot)

def criar_mapa_calor(pivot, tipo_metrica):
    valores_texto = pivot.values.astype(int) if tipo_metrica == "Quantidade de ROMANEIO" else pivot.values.round(1)
    formato_hover = '%{x} - %{y}<br>Quantidade: %{z}<extra></extra>' if tipo_metrica == "Quantidade de ROMANEIO" else '%{x} - %{y}<br>Minutos: %{z:.1f}<extra></extra>'
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale='Blues', text=valores_texto, texttemplate='%{text}',
        textfont={"size": 11, "color": "black"},
        colorbar=dict(title="", thickness=15, len=0.7, x=1.02),
        xgap=1, ygap=1, hovertemplate=formato_hover
    ))
    
    fig.update_layout(
        xaxis=dict(title="Dia da Semana", side="top", tickfont=dict(size=11, color='black'), showgrid=False),
        yaxis=dict(title="Mês", tickfont=dict(size=11, color='black'), showgrid=False),
        height=600, plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=100, r=80, t=80, b=50)
    )
    
    return fig

def criar_tabela_dados(df, tipo_metrica, ano, coluna_vazia):
    if tipo_metrica == "Quantidade de ROMANEIO":
        tabela = df.groupby(['mes', 'data', 'semana', 'dia_semana']).agg(
            quantidade_romaneio=('ROMANEIO', 'nunique')
        ).reset_index()
    else:
        if not coluna_vazia:
            df_validos = df[df['valor'].notna()]
            tabela = df_validos.groupby(['mes', 'data', 'semana', 'dia_semana']).agg(
                quantidade_romaneio=('ROMANEIO', 'nunique'),
                mediana_minutos=('valor', 'median')
            ).reset_index()
            tabela['mediana_minutos'] = tabela['mediana_minutos'].apply(converter_minutos_para_tempo)
        else:
            tabela = df.groupby(['mes', 'data', 'semana', 'dia_semana']).agg(
                quantidade_romaneio=('ROMANEIO', 'nunique')
            ).reset_index()
    
    tabela['ano'] = ano
    tabela['mes_num'] = tabela['mes'].map({v: k for k, v in MESES_NOMES.items()})
    
    colunas = ['ano', 'mes_num', 'mes', 'semana', 'dia_semana', 'data', 'quantidade_romaneio']
    if 'mediana_minutos' in tabela.columns:
        colunas.append('mediana_minutos')
    
    return tabela[colunas]

def main():
    st.sidebar.title("Filtros - Por Meses")
    
    engine = get_engine()
    lojas = consultar_lojas(engine)
    loja_selecionada = st.sidebar.selectbox("Loja", lojas['LOJA'], key="loja_meses")
    
    tipo_metrica = st.sidebar.selectbox(
        "Métrica",
        ["Quantidade de ROMANEIO", "Mediana MINUTOS_DE_SEPARACAO",
         "Mediana MINUTOS_ENTREGA", "Mediana MINUTOS_ENTREGA_REALIZADA"],
        key="metrica_meses"
    )
    
    ano_atual = datetime.now().year
    anos = list(range(ano_atual, ano_atual-3, -1))
    ano = st.sidebar.selectbox("Ano", anos, key="ano_meses")
    
    queries = get_queries()
    query = queries[tipo_metrica].format(loja=loja_selecionada, ano=ano)
    
    with st.spinner('Carregando dados...'):
        df = executar_query(engine, query)
    
    if not df.empty:
        df['mes'] = df['mes_num'].map(MESES_NOMES)
        
        st.title(f"Mapa de calor - Ano {ano}")
        
        coluna_vazia, coluna_problema = verificar_coluna_vazia(df, tipo_metrica)
        
        if coluna_vazia:
            st.warning(f"⚠️ A coluna '{coluna_problema}' da LOJA {loja_selecionada} não está preenchida.")
            st.markdown("### Tabela de Dados")
            tabela = criar_tabela_dados(df, tipo_metrica, ano, coluna_vazia)
            st.dataframe(tabela, use_container_width=True)
        
        pivot = criar_pivot(df, tipo_metrica, coluna_vazia)
        st.markdown(f"### {tipo_metrica}")
        fig = criar_mapa_calor(pivot, tipo_metrica)
        st.plotly_chart(fig, use_container_width=True)
        
        if not coluna_vazia:
            st.markdown("---")
            st.subheader("Tabela de Dados")
            tabela = criar_tabela_dados(df, tipo_metrica, ano, coluna_vazia)
            st.dataframe(tabela, use_container_width=True)
    else:
        st.warning("Sem dados para o período selecionado")

if __name__ == "__main__":
    main()