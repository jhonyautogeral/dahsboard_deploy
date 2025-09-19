import pandas as pd
from sqlalchemy import create_engine
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

@st.cache_resource
def criar_conexao():
    """Cria conexão com MySQL - usando cache para performance"""
    config = st.secrets["connections"]["mysql"]
    url = (f"{config['dialect']}://{config['username']}:{config['password']}@"
           f"{config['host']}:{config['port']}/{config['database']}")
    return create_engine(url)

def obter_descricoes_disponiveis():
    """Obtém todas as descrições disponíveis"""
    engine = criar_conexao()
    query = "SELECT DISTINCT DSCR FROM comp_rate_ativ ORDER BY DSCR"
    result = pd.read_sql_query(query, engine)
    return result['DSCR'].tolist()

def obter_lojas_disponiveis():
    """Obtém todas as lojas disponíveis"""
    engine = criar_conexao()
    query = "SELECT DISTINCT COMP_LOJA FROM comp_rate_ativ ORDER BY COMP_LOJA"
    result = pd.read_sql_query(query, engine)
    return result['LOJA'].tolist()

def consulta_custos_totais(data_inicio, data_fim, lojas_selecionadas=None, descricoes_selecionadas=None):
    """Consulta custos totais entre datas com filtros"""
    where_conditions = [f"a.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'"]
    
    if lojas_selecionadas:
        lojas_str = ','.join(map(str, lojas_selecionadas))
        where_conditions.append(f"c.LOJA IN ({lojas_str})")
    
    if descricoes_selecionadas:
        descricoes_str = "','".join(descricoes_selecionadas)
        where_conditions.append(f"c.DSCR IN ('{descricoes_str}')")
    
    query = f"""
    SELECT DISTINCT
        cvu.LOJA AS LOJA,
        c.COMP_CODI AS COMPRA,
        c.CADA_ATIV_ID AS CADASTRO_VEICULO,
        cv.PLACA,
        c.VALR_RATE AS VALOR_UNITARIO_CUSTO,
        c.DSCR AS DESCRICAO,
        a.CADASTRO,
        a.VALOR_TOTAL_NOTA
    FROM comp_rate_ativ c
    LEFT JOIN compras_dbf a ON c.COMP_CODI = a.COMPRA AND c.COMP_LOJA = a.LOJA
    LEFT JOIN cadastros_ativos ca ON c.CADA_ATIV_ID = ca.CADA_ATIV_ID 
    LEFT JOIN cadastros_veiculos cv ON ca.CADA_VEIC_ID = cv.CADA_VEIC_ID
    LEFT JOIN cadastros_veiculos_ultilizacao cvu ON ca.CADA_VEIC_ID = cvu.CADA_VEIC_ID
    WHERE {' AND '.join(where_conditions)}
    ORDER BY a.CADASTRO, c.COMP_LOJA
    """
    
    engine = criar_conexao()
    return pd.read_sql_query(query, engine)

def processar_dados_custos(data_inicio, data_fim, lojas_selecionadas=None, descricoes_selecionadas=None):
    """Processa dados de custos totais"""
    df = consulta_custos_totais(data_inicio, data_fim, lojas_selecionadas, descricoes_selecionadas)
    
    if df.empty:
        return None
    
    # Remove duplicatas
    df = df.drop_duplicates(subset=['LOJA', 'CADASTRO', 'VALOR_UNITARIO_CUSTO'])
    
    # Preparar dados
    df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
    df['DATA'] = df['CADASTRO'].dt.date
    df['MES_ANO'] = df['CADASTRO'].dt.to_period('M')
    
    # Resumos
    resumos = {
        'original': df,
        'por_loja': df.groupby('LOJA')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index(),
        'por_dia': df.groupby('DATA')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index(),
        'por_mes': df.groupby('MES_ANO')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index(),
        'por_desc': df.groupby('DESCRICAO')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index(),
        'por_ativ': df.groupby('CADASTRO_VEICULO')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index()
    }
    
    # Renomear colunas
    for key in ['por_loja', 'por_dia', 'por_mes', 'por_desc', 'por_ativ']:
        resumos[key].columns = [resumos[key].columns[0], 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    # Converter MES_ANO para string
    resumos['por_mes']['MES_ANO'] = resumos['por_mes']['MES_ANO'].astype(str)
    resumos['por_mes'].columns = ['MES', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    return resumos

def gerar_cores_neutrals(num_items):
    """Gera cores neutras para gráficos"""
    cores_base = [
        '#4A90E2', '#50C878', '#9B59B6', '#F39C12', '#1ABC9C',
        '#34495E', '#95A5A6', '#16A085', '#8E44AD', '#2980B9',
        '#27AE60', '#E67E22', '#3498DB'
    ]
    return (cores_base * ((num_items // len(cores_base)) + 1))[:num_items]

def gerar_grafico_custos(dados, tipo_grafico, tipo_analise):
    """Gera gráfico baseado nas seleções"""
    if tipo_analise == "Por Loja":
        df_plot = dados['por_loja'].sort_values('LOJA')
        cores = gerar_cores_neutrals(len(df_plot))
        
        fig = go.Figure()
        for i, row in df_plot.iterrows():
            fig.add_trace(go.Bar(
                x=[row['LOJA']], y=[row['TOTAL']],
                name=f'Loja {row["LOJA"]}',
                marker_color=cores[i],
                text=[f'R$ {row["TOTAL"]:,.2f}'],
                textposition='auto'
            ))
        
        fig.update_layout(
            title='Custos Totais por Loja',
            xaxis_title='Loja', yaxis_title='Valor Total (R$)'
        )
        return fig
    
    # Outros tipos de análise
    df_map = {
        "Por Dia": (dados['por_dia'], 'DATA', 'Custos Totais por Dia'),
        "Por Mês": (dados['por_mes'], 'MES', 'Custos Totais por Mês')
    }
    
    df_plot, x_col, title = df_map[tipo_analise]
    
    if tipo_grafico == "Pizza":
        return px.pie(df_plot, values='TOTAL', names=x_col, title=title)
    
    grafico_map = {
        "Barras": px.bar, "Linha": px.line, "Área": px.area
    }
    
    return grafico_map[tipo_grafico](
        df_plot, x=x_col, y='TOTAL', title=title,
        labels={'TOTAL': 'Valor Total (R$)', x_col: x_col}
    )

def main():
    st.set_page_config(page_title="Análise de Custos Totais", layout="wide")
    st.title("💰 Análise de Custos Totais por Loja")
    
    if st.sidebar.button("Voltar"):
        st.switch_page("app.py")

    # Sidebar para filtros
    st.sidebar.header("🔍 Filtros")
    
    # Datas
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início", value=datetime.now() - timedelta(days=30))
    with col2:
        data_fim = st.date_input("Data Fim", value=datetime.now())
    
    # Obter opções com tratamento de erro
    try:
        descricoes_disponiveis = obter_descricoes_disponiveis()
        lojas_disponiveis = obter_lojas_disponiveis()
    except Exception as e:
        st.error(f"Erro ao carregar opções: {e}")
        descricoes_disponiveis = []
        lojas_disponiveis = list(range(1, 14))
    
    # Filtros
    lojas_selecionadas = st.sidebar.multiselect(
        "Selecionar Lojas", options=lojas_disponiveis, default=[],
        help="Deixe vazio para mostrar todas as lojas"
    )
    
    descricoes_selecionadas = st.sidebar.multiselect(
        "Selecionar Descrições", options=descricoes_disponiveis, default=[],
        help="Deixe vazio para mostrar todas as descrições"
    )
    
    # Visualização
    st.sidebar.header("📊 Visualização")
    tipo_analise = st.sidebar.selectbox("Tipo de Análise", ["Por Loja", "Por Dia", "Por Mês"])
    tipo_grafico = st.sidebar.selectbox("Tipo de Gráfico", ["Barras", "Linha", "Área", "Pizza"])
    
    # Processamento de dados
    with st.spinner("Carregando dados..."):
        try:
            dados = processar_dados_custos(
                data_inicio.strftime('%Y-%m-%d'), 
                data_fim.strftime('%Y-%m-%d'),
                lojas_selecionadas or None,
                descricoes_selecionadas or None
            )
            
            if dados is None:
                st.error("❌ Nenhum dado encontrado para o período selecionado.")
                return
            
        except Exception as e:
            st.error(f"Erro ao processar dados: {e}")
            return
        
        # Métricas principais
        st.header("📈 Resumo Geral")
        col1, col2, col3, col4 = st.columns(4)
        
        total_geral = dados['original']['VALOR_UNITARIO_CUSTO'].sum()
        media_geral = dados['original']['VALOR_UNITARIO_CUSTO'].mean()
        total_registros = len(dados['original'])
        lojas_ativas = dados['original']['LOJA'].nunique()
        
        with col1:
            st.metric("Total Geral", f"R$ {total_geral:,.2f}")
        with col2:
            st.metric("Média", f"R$ {media_geral:,.2f}")
        with col3:
            st.metric("Registros", f"{total_registros:,}")
        with col4:
            st.metric("Lojas Ativas", lojas_ativas)

        # Análise Visual Principal
        st.header("📊 Análise Visual Principal")
        try:
            fig_principal = gerar_grafico_custos(dados, tipo_grafico, tipo_analise)
            st.plotly_chart(fig_principal, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar gráfico: {e}")
        
        # Dados Detalhados com filtros
        st.header("📋 Dados Detalhados")
        col1, col2 = st.columns(2)

        with col1:
            filtro_placa = st.text_input("🔍 Filtrar por Placa", placeholder="Digite parte da placa")
        with col2:
            filtro_desc = st.text_input("🔍 Filtrar por Descrição", placeholder="Digite a descrição")

        # Aplicar filtros
        df_filtrado = dados['original'].copy()
        
        if filtro_placa:
            df_filtrado = df_filtrado[
                df_filtrado['PLACA'].str.contains(filtro_placa, case=False, na=False)
            ]
        
        if filtro_desc:
            df_filtrado = df_filtrado[
                df_filtrado['DESCRICAO'].str.contains(filtro_desc, case=False, na=False)
            ]

        # Info dos filtros
        filtros = []
        if filtro_placa: filtros.append(f"Placa: '{filtro_placa}'")
        if filtro_desc: filtros.append(f"Descrição: '{filtro_desc}'")
        
        if filtros:
            st.info(f"📊 {len(df_filtrado)} registros filtrados por {' e '.join(filtros)}")

        st.dataframe(df_filtrado, use_container_width=True)
        
        # Resumos em tabs
        st.header("📋 Resumos Detalhados")
        tab1, tab2, tab3, tab4 = st.tabs(["Por Loja", "Por Descrição", "Por Atividade", "Por Dia"])
        
        with tab1:
            st.dataframe(dados['por_loja'], use_container_width=True)
        with tab2:
            st.dataframe(dados['por_desc'], use_container_width=True)
        with tab3:
            st.dataframe(dados['por_ativ'].head(20), use_container_width=True)
        with tab4:
            st.dataframe(dados['por_dia'], use_container_width=True)
        
        # Insights
        st.header("💡 Insights")
        
        loja_top = dados['por_loja'].loc[dados['por_loja']['TOTAL'].idxmax()]
        dia_top = dados['por_dia'].loc[dados['por_dia']['TOTAL'].idxmax()]
        desc_top = dados['por_desc'].loc[dados['por_desc']['TOTAL'].idxmax()]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"🏆 **Loja Top**: {loja_top.iloc[0]}\nR$ {loja_top['TOTAL']:,.2f}")
        with col2:
            st.info(f"📅 **Dia Top**: {dia_top.iloc[0]}\nR$ {dia_top['TOTAL']:,.2f}")
        with col3:
            st.info(f"💰 **Descrição Top**: {str(desc_top.iloc[0])[:20]}...\nR$ {desc_top['TOTAL']:,.2f}")
        
        # Download
        st.header("💾 Download")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            dados['original'].to_excel(writer, sheet_name='Dados', index=False)
            dados['por_loja'].to_excel(writer, sheet_name='Por Loja', index=False)
        buffer.seek(0)

        st.download_button(
            "📥 Baixar Excel",
            data=buffer,
            file_name=f"custos_{data_inicio}_{data_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()