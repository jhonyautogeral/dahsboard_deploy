import streamlit as st
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Análise de Entregas", layout="wide")

def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

def executar_query(engine, query):
    try:
        df = pd.read_sql(query, engine)
        return df.fillna(0)
    except Exception as e:
        st.error(f"Erro ao executar a query: {e}")
        return pd.DataFrame()

def criar_filtros_sidebar(engine):
    st.sidebar.header("Filtros")
    
    tipo_analise = st.sidebar.selectbox(
        "Tipo de Análise",
        ["Análise de Entregas", "Análise de Separação", "Análise de Separação Mediana por Mês/Ano"]
    )
    
    col1, col2 = st.sidebar.columns(2)
    data_inicio = col1.date_input("Data Início")
    data_fim = col2.date_input("Data Fim")
    data_inicio_str = f"{data_inicio} 00:00:00"
    data_fim_str = f"{data_fim} 23:59:59"
    
    df_lojas = executar_query(engine, "SELECT DISTINCT LOJA FROM autogeral.expedicao ORDER BY LOJA")
    loja = st.sidebar.selectbox("Selecione a Loja", df_lojas['LOJA'].tolist() if not df_lojas.empty else [])
    
    consultar = st.sidebar.button("Consultar")

    # Documentação
    with st.sidebar.expander("- LEIA - ME Sobre este Dashboard", expanded=False):
        st.markdown("""
        ### - Análise de Entregas
        
        **O que este dashboard faz:**
        
        #### - Análise de Entregas
        - Mostra tempo médio de entrega por distância (< 7km e ≥ 7km)
        - Gráficos de quantidade de entregas
        - Mapas de calor por dia da semana e hora
        
        #### - Análise de Separação
        - Mediana do tempo de separação
        - Análise por dia da semana e hora
        - Remove outliers automaticamente
        
        #### - Análise de Separação Mediana por Mês/Ano
        - Visão temporal da mediana de separação
        - Comparação entre meses
        
        **Como usar:**
        1. Escolha o tipo de análise
        2. Selecione o período (data início/fim)
        3. Escolha a loja
        4. Clique em "Consultar"
        """)

    return tipo_analise, data_inicio_str, data_fim_str, loja, consultar

def exibir_tabela(df, titulo):
    st.subheader(titulo)
    st.dataframe(df, use_container_width=True)

def criar_grafico_barras(df, x_col, y_cols, labels, colors, titulo, y_label):
    fig = go.Figure()
    
    for y_col, label, color in zip(y_cols, labels, colors):
        fig.add_trace(go.Bar(
            x=df[x_col],
            y=df[y_col],
            name=label,
            marker_color=color,
            text=df[y_col],
            textposition='inside',
            textfont=dict(color='white', size=12),
            texttemplate='%{text:.1f}'
        ))
    
    fig.update_layout(
        title=titulo,
        xaxis_title=x_col,
        yaxis_title=y_label,
        barmode='group',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def converter_minutos_para_texto(minutos):
    """Converte minutos para formato legível: '45' se < 60, '1h 30' se >= 60"""
    if minutos < 60:
        return str(int(minutos))
    else:
        horas = int(minutos // 60)
        mins = int(minutos % 60)
        return f"{horas}h {mins:02d}" if mins > 0 else f"{horas}h"

def criar_mapa_calor(df, col_y, col_x, col_valor, titulo):
    pivot = df.pivot(index=col_y, columns=col_x, values=col_valor)
    pivot = pivot.fillna(0)

    # Cria matriz de texto formatado
    texto_formatado = pivot.applymap(converter_minutos_para_texto)

    fig = px.imshow(
        pivot,
        labels=dict(x=col_x, y=col_y, color="Minutos"),
        x=pivot.columns,
        y=pivot.index,
        color_continuous_scale='Blues',
        text_auto=False,
        aspect='auto'
    )

    # Atualiza os textos das células com o formato customizado
    fig.update_traces(text=texto_formatado.values, texttemplate="%{text}")

    fig.update_layout(title=titulo, height=600)
    st.plotly_chart(fig, use_container_width=True)

def criar_mapa_calor_dia_hora(df, col_valor, titulo):
    dias_map = {
        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado'
    }
    df['DIA_PT'] = df['DIA_SEMANA'].map(dias_map)
    df = df[df['DIA_PT'].notna()]

    pivot = df.pivot(index='HORA', columns='DIA_PT', values=col_valor)
    pivot = pivot.fillna(0)

    ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
    pivot = pivot.reindex(columns=ordem_dias, fill_value=0)

    # Cria matriz de texto formatado
    texto_formatado = pivot.applymap(converter_minutos_para_texto)

    fig = px.imshow(
        pivot,
        labels=dict(x="Dia da Semana", y="Hora", color="Minutos"),
        x=pivot.columns,
        y=pivot.index,
        color_continuous_scale='Blues',
        text_auto=False,
        aspect='auto'
    )

    # Atualiza os textos das células com o formato customizado
    fig.update_traces(text=texto_formatado.values, texttemplate="%{text}")

    fig.update_layout(title=titulo, height=600)
    st.plotly_chart(fig, use_container_width=True)

def query_analise_entregas(inicio, fim, loja):
    return f"""
    SELECT
        E.LOJA,
        DATE_FORMAT(E.CADASTRO, '%%m-%%Y') AS MES_ANO,
        ROUND(AVG(CASE WHEN ROUND(EI.ROTA_METROS / 1000) < 7
            THEN TIMESTAMPDIFF(MINUTE, E.HORA_SAIDA, EI.ROTA_HORARIO_REALIZADO)
        END), 0) AS "TEMPO MÉDIO DE ENTREGA COM DISTANCIA MENOR DE 7KM",
        ROUND(AVG(CASE WHEN ROUND(EI.ROTA_METROS / 1000) >= 7
            THEN TIMESTAMPDIFF(MINUTE, E.HORA_SAIDA, EI.ROTA_HORARIO_REALIZADO)
        END), 0) AS "TEMPO MÉDIO DE ENTREGA COM DISTANCIA MAIOR DE 7KM",
        COUNT(CASE WHEN ROUND(EI.ROTA_METROS / 1000) < 7 THEN 1 END) AS "QTD ENTREGAS COM DISTACIA MENOR DE 7KM",
        COUNT(CASE WHEN ROUND(EI.ROTA_METROS / 1000) >= 7 THEN 1 END) AS "QTD ENTREGAS COM DISTACIA MAIOR DE 7KM"
    FROM expedicao E
    JOIN expedicao_itens EI ON EI.EXPEDICAO_CODIGO = E.EXPEDICAO AND EI.EXPEDICAO_LOJA = E.LOJA
    WHERE E.CADASTRO BETWEEN '{inicio}' AND '{fim}'
        AND EI.ROTA_HORARIO_REALIZADO IS NOT NULL
        AND EI.ROTA_METROS IS NOT NULL
        AND EI.VENDA_TIPO = 'ROMANEIO'
        AND EI.COMPRADOR_NOME NOT LIKE 'AUTO GERAL AUTOPECAS LTDA%%'
        AND E.LOJA = '{loja}'
    GROUP BY E.LOJA, DATE_FORMAT(E.CADASTRO, '%%m-%%Y')
    ORDER BY E.LOJA, MES_ANO
    """

def query_mapa_calor_entregas(inicio, fim, loja):
    return f"""
    SELECT
        E.LOJA,
        DAYNAME(E.CADASTRO) AS DIA_SEMANA,
        HOUR(E.CADASTRO) AS HORA,
        COALESCE(ROUND(AVG(CASE WHEN ROUND(EI.ROTA_METROS / 1000) < 7
            THEN TIMESTAMPDIFF(MINUTE, E.HORA_SAIDA, EI.ROTA_HORARIO_REALIZADO)
        END), 0), 0) AS "TEMPO MÉDIO < 7KM",
        COALESCE(ROUND(AVG(CASE WHEN ROUND(EI.ROTA_METROS / 1000) >= 7
            THEN TIMESTAMPDIFF(MINUTE, E.HORA_SAIDA, EI.ROTA_HORARIO_REALIZADO)
        END), 0), 0) AS "TEMPO MÉDIO >= 7KM"
    FROM expedicao E
    JOIN expedicao_itens EI ON EI.EXPEDICAO_CODIGO = E.EXPEDICAO
        AND EI.EXPEDICAO_LOJA = E.LOJA
    WHERE E.CADASTRO BETWEEN '{inicio}' AND '{fim}'
        AND EI.ROTA_HORARIO_REALIZADO IS NOT NULL
        AND EI.ROTA_METROS IS NOT NULL
        AND EI.VENDA_TIPO = 'ROMANEIO'
        AND EI.COMPRADOR_NOME NOT LIKE 'AUTO GERAL AUTOPECAS LTDA%%'
        AND E.LOJA = '{loja}'
    GROUP BY E.LOJA, DAYNAME(E.CADASTRO), HOUR(E.CADASTRO)
    ORDER BY E.LOJA,
        FIELD(DIA_SEMANA, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
        HORA
    """

def query_mediana_dia_hora(inicio, fim, loja):
    return f"""
    WITH base AS (
    SELECT
        r.LOJA,
        DAYNAME(r.CADASTRO) AS DIA_SEMANA,
        HOUR(r.CADASTRO) AS HORA,
        TIMESTAMPDIFF(MINUTE, r.CADASTRO, r.TERMINO_SEPARACAO) AS diff_min
    FROM expedicao E
    JOIN expedicao_itens EI 
        ON EI.EXPEDICAO_CODIGO = E.EXPEDICAO 
        AND EI.EXPEDICAO_LOJA = E.LOJA
    LEFT JOIN romaneios_dbf r 
        ON EI.VENDA_TIPO = 'ROMANEIO' 
        AND EI.CODIGO_VENDA = r.ROMANEIO 
        AND EI.LOJA_VENDA = r.LOJA
    WHERE 
        r.LOJA = '{loja}'
        AND r.CADASTRO IS NOT NULL
        AND r.CADASTRO BETWEEN '{inicio}' AND '{fim}'
),
quartis AS (
    SELECT
        LOJA,
        DIA_SEMANA,
        HORA,
        diff_min,
        NTILE(4) OVER (
            PARTITION BY LOJA, DIA_SEMANA, HORA 
            ORDER BY diff_min
        ) AS quartil
    FROM base
),
iqr_calc AS (
    SELECT
        LOJA,
        DIA_SEMANA,
        HORA,
        MAX(CASE WHEN quartil = 1 THEN diff_min END) AS Q1,
        MAX(CASE WHEN quartil = 3 THEN diff_min END) AS Q3
    FROM quartis
    GROUP BY LOJA, DIA_SEMANA, HORA
),
sem_outliers AS (
    SELECT 
        b.LOJA,
        b.DIA_SEMANA,
        b.HORA,
        b.diff_min
    FROM base b
    JOIN iqr_calc i 
        ON b.LOJA = i.LOJA 
       AND b.DIA_SEMANA = i.DIA_SEMANA 
       AND b.HORA = i.HORA
    WHERE 
        b.diff_min <= LEAST(i.Q3 + 1.5 * (i.Q3 - i.Q1), 50)
),
ordenado AS (
    SELECT 
        LOJA,
        DIA_SEMANA,
        HORA,
        diff_min,
        ROW_NUMBER() OVER (
            PARTITION BY LOJA, DIA_SEMANA, HORA 
            ORDER BY diff_min
        ) AS rn,
        COUNT(*) OVER (
            PARTITION BY LOJA, DIA_SEMANA, HORA
        ) AS cnt
    FROM sem_outliers
)
SELECT 
    LOJA,
    DIA_SEMANA,
    HORA,
    ROUND(AVG(diff_min), 0) AS MEDIANA_MINUTOS_SEPARACAO
FROM ordenado
WHERE rn IN (FLOOR((cnt + 1)/2), CEIL((cnt + 1)/2))
GROUP BY LOJA, DIA_SEMANA, HORA
ORDER BY 
    LOJA,
    FIELD(DIA_SEMANA, 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'),
    HORA
    """

def query_mediana_mes_ano(inicio, fim, loja):
    return f"""
    WITH diffs AS (
        SELECT
            r.LOJA,
            DATE_FORMAT(r.CADASTRO, '%%m-%%Y') AS MES_ANO,
            TIMESTAMPDIFF(MINUTE, r.CADASTRO, r.TERMINO_SEPARACAO) AS diff_min,
            ROW_NUMBER() OVER (
                PARTITION BY r.LOJA, DATE_FORMAT(r.CADASTRO, '%%m-%%Y')
                ORDER BY TIMESTAMPDIFF(MINUTE, r.CADASTRO, r.TERMINO_SEPARACAO)
            ) AS rn,
            COUNT(*) OVER (
                PARTITION BY r.LOJA, DATE_FORMAT(r.CADASTRO, '%%m-%%Y')
            ) AS cnt
        FROM expedicao E
        JOIN expedicao_itens EI ON EI.EXPEDICAO_CODIGO = E.EXPEDICAO AND EI.EXPEDICAO_LOJA = E.LOJA
        LEFT JOIN romaneios_dbf r ON EI.VENDA_TIPO = 'ROMANEIO' AND EI.CODIGO_VENDA = r.ROMANEIO AND EI.LOJA_VENDA = r.LOJA
        WHERE r.CADASTRO IS NOT NULL AND r.CADASTRO BETWEEN '{inicio}' AND '{fim}'
    )
    SELECT LOJA, MES_ANO, ROUND(AVG(diff_min), 0) AS MEDIANA_MINUTOS
    FROM diffs
    WHERE rn IN (FLOOR((cnt + 1) / 2), CEIL((cnt + 1) / 2))
    GROUP BY LOJA, MES_ANO
    ORDER BY LOJA, MES_ANO
    """

def main():
    st.title("📊 Análise de Entregas")
    if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
    engine = criar_conexao()
    tipo_analise, data_inicio, data_fim, loja, consultar = criar_filtros_sidebar(engine)
    
    if consultar and loja:
        if tipo_analise == "Análise de Entregas":
            query = query_analise_entregas(data_inicio, data_fim, loja)
            df = executar_query(engine, query)
            
            if not df.empty:
                criar_grafico_barras(
                    df=df, x_col='MES_ANO',
                    y_cols=['TEMPO MÉDIO DE ENTREGA COM DISTANCIA MENOR DE 7KM', "TEMPO MÉDIO DE ENTREGA COM DISTANCIA MAIOR DE 7KM"],
                    labels=['< 7km', '≥ 7km'], colors=['darkblue', 'goldenrod'],
                    titulo='- Tempo Médio de Entrega (minutos)', y_label='Tempo (min)'
                )
                criar_grafico_barras(
                    df=df, x_col='MES_ANO',
                    y_cols=['QTD ENTREGAS COM DISTACIA MENOR DE 7KM', 'QTD ENTREGAS COM DISTACIA MAIOR DE 7KM'],
                    labels=['< 7km', '≥ 7km'], colors=['darkblue', 'goldenrod'],
                    titulo='- Quantidade de Entregas', y_label='Quantidade'
                )
                
                # Novos mapas de calor
                query_calor = query_mapa_calor_entregas(data_inicio, data_fim, loja)
                df_calor = executar_query(engine, query_calor)
                
                if not df_calor.empty:
                    criar_mapa_calor_dia_hora(df_calor, 'TEMPO MÉDIO < 7KM', '- Mapa de Calor - TEMPO EM MINUTOS MÉDIO DE ENTREGA COM DISTANCIA MENOR DE 7KM')
                    criar_mapa_calor_dia_hora(df_calor, 'TEMPO MÉDIO >= 7KM', '- Mapa de Calor - TEMPO EM MINUTOS MÉDIO DE ENTREGA COM DISTANCIA MAIOR DE 7KM')
                exibir_tabela(df, f"- Dados - Loja {loja}")
            else:
                st.warning("- Nenhum dado encontrado")
        
        elif tipo_analise == "Análise de Separação":
            query = query_mediana_dia_hora(data_inicio, data_fim, loja)
            df = executar_query(engine, query)
            
            if not df.empty:
                criar_mapa_calor_dia_hora(df, 'MEDIANA_MINUTOS_SEPARACAO', '- Mapa de Calor - Mediana de Tempo de Separação')
                
                dias_map = {
                    'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
                    'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado'
                }
                df['DIA_SEMANA'] = df['DIA_SEMANA'].map(dias_map)
                exibir_tabela(df, f"- Mediana por Dia e Hora - Loja {loja}")
            else:
                st.warning("- Nenhum dado encontrado")
        
        else:
            query = query_mediana_mes_ano(data_inicio, data_fim, loja)
            df = executar_query(engine, query)
            
            if not df.empty:
                criar_mapa_calor(df, 'LOJA', 'MES_ANO', 'MEDIANA_MINUTOS', '- Mapa de Calor - Análise de Separação Mediana por Mês/Ano')
                exibir_tabela(df, f"- Análise de Separação Mediana por Mês/Ano - Loja {loja}")
            else:
                st.warning("- Nenhum dado encontrado")

if __name__ == "__main__":
    main()