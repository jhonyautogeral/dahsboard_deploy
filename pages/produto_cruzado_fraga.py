import pandas as pd
from sqlalchemy import create_engine
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

def conectar_db(usar_streamlit=True):
    """Conecta ao banco de dados MySQL"""
    try:
        if usar_streamlit:
            config = st.secrets["connections"]["mysql"]
        else:
            # Para Jupyter, defina suas configurações aqui ou use arquivo de config
            config = {
                'dialect': 'mysql+pymysql',
                'username': 'seu_usuario',
                'password': 'sua_senha', 
                'host': 'localhost',
                'port': 3306,
                'database': 'seu_banco'
            }
        
        engine = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        return create_engine(engine)
    except Exception as e:
        if usar_streamlit:
            st.error(f"Erro na conexão: {e}")
        else:
            print(f"Erro na conexão: {e}")
        return None

def executar_query(engine, query):
    """Executa query no banco e retorna DataFrame"""
    try:
        df = pd.read_sql(query, con=engine)
        return df
    except Exception as e:
        st.error(f"Erro na query: {e}")
        return None

def processar_dados_produtos(df):
    """Processa os dados dos produtos"""
    # Substitui valores vazios por 'Z'
    df['Curva'] = df['Curva'].replace('', 'Z')
    
    # Cria pivot table
    df_agg = df.pivot_table(index='Curva', columns='TemCodigoFraga', values='Registros', aggfunc='sum')
    df_agg = df_agg.fillna(0)
    df_agg.columns = ['Sem Fraga', 'Com Fraga']
    
    # Calcula totais e cobertura
    df_agg['Total Itens'] = df_agg.sum(axis=1)
    df_agg['Cobertura %'] = ((df_agg['Com Fraga'] / df_agg['Total Itens']) * 100).round(2)
    
    # Reordena colunas
    df_agg = df_agg[['Sem Fraga', 'Com Fraga', 'Total Itens', 'Cobertura %']]
    
    # Adiciona linha de total
    soma = df_agg[['Sem Fraga', 'Com Fraga', 'Total Itens']].sum()
    soma['Cobertura %'] = ((soma['Com Fraga'] / soma['Total Itens']) * 100).round(2)
    df_agg.loc['TOTAL'] = soma
    
    return df_agg

def criar_graficos(df_todos, df_disponivel):
    """Cria gráficos para visualização"""
    
    # Gráfico 1: Cobertura por Curva - Barras
    fig1 = go.Figure()
    
    # Remove linha TOTAL para os gráficos
    df_todos_graf = df_todos.drop('TOTAL')
    df_disponivel_graf = df_disponivel.drop('TOTAL')
    
    fig1.add_trace(go.Bar(
        name='Todos os Produtos',
        x=df_todos_graf.index,
        y=df_todos_graf['Cobertura %'],
        text=df_todos_graf['Cobertura %'].astype(str) + '%',
        textposition='auto',
        marker_color='lightblue'
    ))
    
    fig1.add_trace(go.Bar(
        name='Produtos Disponíveis',
        x=df_disponivel_graf.index,
        y=df_disponivel_graf['Cobertura %'],
        text=df_disponivel_graf['Cobertura %'].astype(str) + '%',
        textposition='auto',
        marker_color='darkblue'
    ))
    
    fig1.update_layout(
        title='Cobertura de Código Fraga por Curva ABC',
        xaxis_title='Curva ABC',
        yaxis_title='Cobertura (%)',
        barmode='group',
        height=500
    )
    
    # Gráfico 2: Distribuição de Produtos - Pizza
    fig2 = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "domain"}, {"type": "domain"}]],
        subplot_titles=('Todos os Produtos', 'Produtos Disponíveis')
    )
    
    fig2.add_trace(go.Pie(
        labels=['Com Fraga', 'Sem Fraga'],
        values=[df_todos.loc['TOTAL', 'Com Fraga'], df_todos.loc['TOTAL', 'Sem Fraga']],
        name="Todos",
        marker_colors=['green', 'red']
    ), 1, 1)
    
    fig2.add_trace(go.Pie(
        labels=['Com Fraga', 'Sem Fraga'],
        values=[df_disponivel.loc['TOTAL', 'Com Fraga'], df_disponivel.loc['TOTAL', 'Sem Fraga']],
        name="Disponíveis",
        marker_colors=['green', 'red']
    ), 1, 2)
    
    fig2.update_layout(height=400, title_text="Distribuição Geral - Com/Sem Fraga")
    
    return fig1, fig2

def criar_metricas_cards(df_todos, df_disponivel):
    """Cria cards com métricas principais"""
    
    total_produtos = int(df_todos.loc['TOTAL', 'Total Itens'])
    total_disponivel = int(df_disponivel.loc['TOTAL', 'Total Itens'])
    cobertura_todos = df_todos.loc['TOTAL', 'Cobertura %']
    cobertura_disponivel = df_disponivel.loc['TOTAL', 'Cobertura %']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total de Produtos",
            value=f"{total_produtos:,}".replace(',', '.'),
            help="Todos os produtos cadastrados"
        )
    
    with col2:
        st.metric(
            label="Produtos Disponíveis",
            value=f"{total_disponivel:,}".replace(',', '.'),
            help="Produtos com estoque > 0"
        )
    
    with col3:
        st.metric(
            label="Cobertura Geral",
            value=f"{cobertura_todos}%",
            help="% produtos com código Fraga"
        )
    
    with col4:
        st.metric(
            label="Cobertura Disponível",
            value=f"{cobertura_disponivel}%",
            delta=f"+{(cobertura_disponivel - cobertura_todos):.1f}%",
            help="% produtos disponíveis com código Fraga"
        )

def analisar_cobertura_produtos():
    """Função principal para análise de cobertura"""
    
    st.set_page_config(
        page_title="Análise de Cobertura Fraga",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Análise de Cobertura - Código Fraga")

    if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
    st.markdown("---")
    
    # Queries SQL
    query_todos = """
    SELECT IF(a.CURVA_PRODUTO IS NULL, '', a.CURVA_PRODUTO) AS Curva,
           (a.CODIGO_FRAGA IS NOT NULL AND TRIM(a.CODIGO_FRAGA) != '') AS TemCodigoFraga,
           COUNT(1) AS Registros
    FROM produtos_dbf a
    WHERE a.FINALIDADE_CODIGO = 1
    GROUP BY IF(a.CURVA_PRODUTO IS NULL, '', a.CURVA_PRODUTO), 
             (a.CODIGO_FRAGA IS NOT NULL AND TRIM(a.CODIGO_FRAGA) != '');
    """
    
    query_disponivel = """
    SELECT IF(a.CURVA_PRODUTO IS NULL, '', a.CURVA_PRODUTO) AS Curva,
           (a.CODIGO_FRAGA IS NOT NULL AND TRIM(a.CODIGO_FRAGA) != '') AS TemCodigoFraga,
           COUNT(1) AS Registros
    FROM produtos_dbf a 
    JOIN produto_estoque_global b ON a.CODIGO = b.PRODUTO_CODIGO
    WHERE a.FINALIDADE_CODIGO = 1 AND b.DISPONIVEL > 0
    GROUP BY IF(a.CURVA_PRODUTO IS NULL, '', a.CURVA_PRODUTO), 
             (a.CODIGO_FRAGA IS NOT NULL AND TRIM(a.CODIGO_FRAGA) != '');
    """
    
    with st.spinner('Conectando ao banco de dados...'):
        engine = conectar_db()
        if not engine:
            st.stop()
    
    with st.spinner('Executando consultas...'):
        df_todos = executar_query(engine, query_todos)
        df_disponivel = executar_query(engine, query_disponivel)
        
        if df_todos is None or df_disponivel is None:
            st.stop()
    
    with st.spinner('Processando dados...'):
        resultado_todos = processar_dados_produtos(df_todos)
        resultado_disponivel = processar_dados_produtos(df_disponivel)
    
    # Métricas principais
    st.subheader("📈 Métricas Principais")
    criar_metricas_cards(resultado_todos, resultado_disponivel)
    st.markdown("---")
    
    # Gráficos
    st.subheader("📊 Visualizações")
    fig1, fig2 = criar_graficos(resultado_todos, resultado_disponivel)
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    
    # Tabelas detalhadas
    st.subheader("📋 Dados Detalhados")
    
    tab1, tab2 = st.tabs(["🔍 Todos os Produtos", "✅ Produtos Disponíveis"])
    
    with tab1:
        st.markdown("**Análise completa do catálogo de produtos**")
        
        # Formata tabela para melhor visualização
        df_formato = resultado_todos.copy()
        df_formato['Sem Fraga'] = df_formato['Sem Fraga'].astype(int).apply(lambda x: f"{x:,}".replace(',', '.'))
        df_formato['Com Fraga'] = df_formato['Com Fraga'].astype(int).apply(lambda x: f"{x:,}".replace(',', '.'))
        df_formato['Total Itens'] = df_formato['Total Itens'].astype(int).apply(lambda x: f"{x:,}".replace(',', '.'))
        df_formato['Cobertura %'] = df_formato['Cobertura %'].astype(str) + '%'
        
        st.dataframe(
            df_formato,
            use_container_width=True,
            height=300
        )
    
    with tab2:
        st.markdown("**Análise apenas dos produtos em estoque**")
        
        # Formata tabela para melhor visualização
        df_formato2 = resultado_disponivel.copy()
        df_formato2['Sem Fraga'] = df_formato2['Sem Fraga'].astype(int).apply(lambda x: f"{x:,}".replace(',', '.'))
        df_formato2['Com Fraga'] = df_formato2['Com Fraga'].astype(int).apply(lambda x: f"{x:,}".replace(',', '.'))
        df_formato2['Total Itens'] = df_formato2['Total Itens'].astype(int).apply(lambda x: f"{x:,}".replace(',', '.'))
        df_formato2['Cobertura %'] = df_formato2['Cobertura %'].astype(str) + '%'
        
        st.dataframe(
            df_formato2,
            use_container_width=True,
            height=300
        )
    
    # Insights
    st.markdown("---")
    st.subheader("💡 Insights Automáticos")
    
    # Calcula insights dinamicamente
    cobertura_melhoria = resultado_disponivel.loc['TOTAL', 'Cobertura %'] - resultado_todos.loc['TOTAL', 'Cobertura %']
    
    # Remove linha TOTAL para análise das curvas
    df_curvas_todos = resultado_todos.drop('TOTAL')
    df_curvas_disponivel = resultado_disponivel.drop('TOTAL')
    
    # Encontra curva com maior e menor cobertura (disponíveis)
    curva_mais_coberta = df_curvas_disponivel['Cobertura %'].idxmax()
    valor_mais_coberta = df_curvas_disponivel.loc[curva_mais_coberta, 'Cobertura %']
    
    curva_menos_coberta = df_curvas_disponivel['Cobertura %'].idxmin()
    valor_menos_coberta = df_curvas_disponivel.loc[curva_menos_coberta, 'Cobertura %']
    
    # Produtos sem curva (Z)
    produtos_sem_curva = 0
    if 'Z' in df_curvas_disponivel.index:
        produtos_sem_curva = int(df_curvas_disponivel.loc['Z', 'Total Itens'])
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Melhoria na Cobertura**: {cobertura_melhoria:.1f}% nos produtos disponíveis")
        st.info(f"**Curva mais coberta**: Curva {curva_mais_coberta} com {valor_mais_coberta:.1f}%")
    
    with col2:
        st.warning(f"**Curva menos coberta**: Curva {curva_menos_coberta} com {valor_menos_coberta:.1f}%")
        if produtos_sem_curva > 0:
            st.warning(f"**Produtos sem curva**: {produtos_sem_curva:,} itens (Curva Z)".replace(',', '.'))
        else:
            st.success("**Todos os produtos têm curva definida!**")

# Execução principal
if __name__ == "__main__":
    analisar_cobertura_produtos()