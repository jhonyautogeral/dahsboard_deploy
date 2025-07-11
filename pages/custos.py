import pandas as pd
from sqlalchemy import create_engine
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página

def criar_conexao():
    """Cria conexão com MySQL"""
    config = st.secrets["connections"]["mysql"]
    url = (f"{config['dialect']}://{config['username']}:{config['password']}@"
           f"{config['host']}:{config['port']}/{config['database']}")
    return create_engine(url)

def obter_descricoes_disponiveis(engine):
    """Obtém todas as descrições disponíveis"""
    query = "SELECT DISTINCT DSCR FROM comp_rate_ativ ORDER BY DSCR"
    result = pd.read_sql_query(query, engine)
    return result['DSCR'].tolist()

def obter_lojas_disponiveis(engine):
    """Obtém todas as lojas disponíveis"""
    query = "SELECT DISTINCT COMP_LOJA FROM comp_rate_ativ ORDER BY COMP_LOJA"
    result = pd.read_sql_query(query, engine)
    return result['COMP_LOJA'].tolist()

def consulta_custos_totais(data_inicio, data_fim, engine, lojas_selecionadas=None, descricoes_selecionadas=None):
    """Consulta custos totais entre datas com filtros"""
    where_conditions = [f"a.CADASTRO BETWEEN '{data_inicio}' AND '{data_fim}'"]
    
    if lojas_selecionadas:
        lojas_str = ','.join(map(str, lojas_selecionadas))
        where_conditions.append(f"c.COMP_LOJA IN ({lojas_str})")
    
    if descricoes_selecionadas:
        descricoes_str = "','".join(descricoes_selecionadas)
        where_conditions.append(f"c.DSCR IN ('{descricoes_str}')")
    
    query = f"""
    SELECT
        c.COMP_LOJA AS LOJA,
        c.COMP_CODI AS COMPRA,
        c.CADA_ATIV_ID AS CADASTRO_VEICULO,
        c.VALR_RATE AS VALOR_UNITARIO_CUSTO,
        (c.VALR_RATE / a.VALOR_TOTAL_NOTA) AS PERC,
        c.DSCR AS DESCRICAO,
        a.CADASTRO,
        a.VALOR_TOTAL_NOTA
    FROM comp_rate_ativ c
    LEFT JOIN compras_dbf a ON c.COMP_CODI = a.COMPRA
    AND c.COMP_LOJA = a.LOJA
    WHERE {' AND '.join(where_conditions)}
    ORDER BY a.CADASTRO, c.COMP_LOJA
    """
    return pd.read_sql_query(query, engine)

def processar_dados_custos(data_inicio, data_fim, lojas_selecionadas=None, descricoes_selecionadas=None):
    """Processa dados de custos totais - função reutilizável"""
    engine = criar_conexao()
    df = consulta_custos_totais(data_inicio, data_fim, engine, lojas_selecionadas, descricoes_selecionadas)
    
    if df.empty:
        return None
    
    # Converter data
    df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
    df['DATA'] = df['CADASTRO'].dt.date
    df['MES_ANO'] = df['CADASTRO'].dt.to_period('M')
    
    # Agrupamento por loja, cadastro e descrição
    resumo_agrupado = df.groupby(['LOJA', 'DATA', 'DESCRICAO']).agg({
        'VALOR_UNITARIO_CUSTO': ['sum', 'mean', 'count']
    }).reset_index()
    
    # Achatar colunas
    resumo_agrupado.columns = ['LOJA', 'DATA', 'DESCRICAO', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    # Resumos para análise
    resumo_loja = df.groupby('LOJA')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_loja.columns = ['LOJA', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    resumo_tempo = df.groupby('DATA')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_tempo.columns = ['DATA', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    resumo_mensal = df.groupby('MES_ANO')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_mensal['MES_ANO'] = resumo_mensal['MES_ANO'].astype(str)
    resumo_mensal.columns = ['MES', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    resumo_desc = df.groupby('DESCRICAO')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_desc.columns = ['DESCRICAO', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    resumo_ativ = df.groupby('CADASTRO_VEICULO')['VALOR_UNITARIO_CUSTO'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_ativ.columns = ['ATIV_ID', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    return {
        'original': df,
        'agrupado': resumo_agrupado,
        'por_loja': resumo_loja,
        'por_dia': resumo_tempo,
        'por_mes': resumo_mensal,
        'por_desc': resumo_desc,
        'por_ativ': resumo_ativ
    }

def gerar_grafico_custos(dados, tipo_grafico, tipo_analise):
    """Gera gráfico baseado nas seleções"""
    if tipo_analise == "Por Loja":
        df_plot = dados['por_loja']
        x_col, y_col = 'LOJA', 'TOTAL'
        title = 'Custos Totais por Loja'
    elif tipo_analise == "Por Dia":
        df_plot = dados['por_dia']
        x_col, y_col = 'DATA', 'TOTAL'
        title = 'Custos Totais por Dia'
    else:  # Por Mês
        df_plot = dados['por_mes']
        x_col, y_col = 'MES', 'TOTAL'
        title = 'Custos Totais por Mês'
    
    if tipo_grafico == "Barras":
        fig = px.bar(df_plot, x=x_col, y=y_col, title=title,
                     labels={y_col: 'Valor Total (R$)', x_col: tipo_analise.split()[1]})
    elif tipo_grafico == "Linha":
        fig = px.line(df_plot, x=x_col, y=y_col, title=title,
                      labels={y_col: 'Valor Total (R$)', x_col: tipo_analise.split()[1]})
    elif tipo_grafico == "Área":
        fig = px.area(df_plot, x=x_col, y=y_col, title=title,
                      labels={y_col: 'Valor Total (R$)', x_col: tipo_analise.split()[1]})
    else:  # Pizza
        fig = px.pie(df_plot, values=y_col, names=x_col, title=title)
    
    return fig

def main():
    st.set_page_config(page_title="Análise de Custos Totais", layout="wide")
    st.title("💰 Análise de Custos Totais por Loja")
    
    if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
        
    # Sidebar para filtros
    st.sidebar.header("🔍 Filtros")
    
    # Seleção de datas
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início", 
                                   value=datetime.now() - timedelta(days=30))
    with col2:
        data_fim = st.date_input("Data Fim", 
                                value=datetime.now())
    
    # Obter opções disponíveis
    try:
        engine = criar_conexao()
        descricoes_disponiveis = obter_descricoes_disponiveis(engine)
        lojas_disponiveis = obter_lojas_disponiveis(engine)
    except:
        descricoes_disponiveis = []
        lojas_disponiveis = list(range(1, 14))
    
    # Seleção de lojas
    lojas_selecionadas = st.sidebar.multiselect(
        "Selecionar Lojas", 
        options=lojas_disponiveis,
        default=[],
        help="Deixe vazio para mostrar todas as lojas"
    )
    
    # Seleção de descrições
    descricoes_selecionadas = st.sidebar.multiselect(
        "Selecionar Descrições de Custos",
        options=descricoes_disponiveis,
        default=[],
        help="Deixe vazio para mostrar todas as descrições"
    )
    
    # Configurações de visualização
    st.sidebar.header("📊 Visualização")
    
    tipo_analise = st.sidebar.selectbox(
        "Tipo de Análise",
        ["Por Loja", "Por Dia", "Por Mês"],
        help="Escolha o tipo de agrupamento"
    )
    
    tipo_grafico = st.sidebar.selectbox(
        "Tipo de Gráfico",
        ["Barras", "Linha", "Área", "Pizza"],
        help="Escolha o tipo de visualização"
    )
    
    # Botão para consultar
    if st.sidebar.button("💰 Consultar Custos", type="primary"):
        with st.spinner("Carregando dados de custos..."):
            dados = processar_dados_custos(
                data_inicio.strftime('%Y-%m-%d'), 
                data_fim.strftime('%Y-%m-%d'),
                lojas_selecionadas if lojas_selecionadas else None,
                descricoes_selecionadas if descricoes_selecionadas else None
            )
            
            if dados is None:
                st.error("❌ Nenhum dado encontrado para o período selecionado.")
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
            
            # Dados Detalhados
            st.header("📋 Dados Detalhados")
            st.dataframe(dados['original'].head(100), use_container_width=True)
            
            # Análise Visual Principal
            st.header("📊 Análise Visual Principal")
            fig_principal = gerar_grafico_custos(dados, tipo_grafico, tipo_analise)
            st.plotly_chart(fig_principal, use_container_width=True)
            
            # Gráficos complementares
            st.header("📊 Análises Complementares")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Distribuição por Loja")
                st.bar_chart(dados['por_loja'].set_index('LOJA')['TOTAL'])
            
            with col2:
                st.subheader("Evolução Temporal")
                st.line_chart(dados['por_dia'].set_index('DATA')['TOTAL'])
            
            # Resumos Detalhados
            st.header("📋 Resumos Detalhados")
            
            tab1, tab2, tab3 = st.tabs(["Por Loja", "Por Descrição", "Por Atividade"])
            
            with tab1:
                st.dataframe(dados['por_loja'], use_container_width=True)
            
            with tab2:
                st.dataframe(dados['por_desc'], use_container_width=True)
            
            with tab3:
                st.dataframe(dados['por_ativ'].head(20), use_container_width=True)
            
            # Análises Específicas
            st.header("📊 Análises Específicas")
            
            # Custo por Loja ao Longo do Tempo
            st.subheader("Custo por Loja ao Longo do Tempo")
            df_heatmap = dados['original'].groupby(['LOJA', 'DATA'])['VALOR_UNITARIO_CUSTO'].sum().reset_index()
            fig_heatmap = px.density_heatmap(df_heatmap, x='DATA', y='LOJA', z='VALOR_UNITARIO_CUSTO',
                                           title='Heatmap de Custos por Loja e Data',
                                           labels={'VALOR_UNITARIO_CUSTO': 'Custo Total (R$)'})
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            # Média de Custo por Loja
            st.subheader("Média de Custo por Loja")
            # Calcula a mediana da soma de VALOR_UNITARIO_CUSTO por loja
            soma_por_loja = dados['original'].groupby('LOJA')['VALOR_UNITARIO_CUSTO'].sum()
            mediana_custo = soma_por_loja.median()
            
            # Para visualização, mostra a soma por loja com linha da mediana
            soma_loja_df = soma_por_loja.reset_index()
            soma_loja_df.columns = ['LOJA', 'CUSTO_TOTAL']
            
            fig_media = px.bar(soma_loja_df, x='LOJA', y='CUSTO_TOTAL',
                             title=f'Custo Total por Loja (Mediana: R$ {mediana_custo:,.2f})',
                             labels={'CUSTO_TOTAL': 'Custo Total (R$)'})
            
            # Adiciona linha da mediana
            fig_media.add_hline(y=mediana_custo, line_dash="dash", line_color="red",
                              annotation_text=f"Mediana: R$ {mediana_custo:,.2f}")
            
            st.plotly_chart(fig_media, use_container_width=True)
            
            # Insights automáticos
            st.header("💡 Insights Automáticos")
            
            loja_maior = dados['por_loja'].loc[dados['por_loja']['TOTAL'].idxmax()]
            dia_maior = dados['por_dia'].loc[dados['por_dia']['TOTAL'].idxmax()]
            desc_maior = dados['por_desc'].loc[dados['por_desc']['TOTAL'].idxmax()]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info(f"🏆 **Loja top**: {loja_maior['LOJA']}\nR$ {loja_maior['TOTAL']:,.2f}")
            
            with col2:
                st.info(f"📅 **Dia top**: {dia_maior['DATA']}\nR$ {dia_maior['TOTAL']:,.2f}")
            
            with col3:
                st.info(f"💰 **Descrição top**: {desc_maior['DESCRICAO'][:20]}...\nR$ {desc_maior['TOTAL']:,.2f}")
            
            # Download
            st.header("💾 Download dos Dados")
            csv = dados['original'].to_csv(index=False)
            st.download_button(
                label="📥 Baixar dados em CSV",
                data=csv,
                file_name=f"custos_totais_{data_inicio}_{data_fim}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
