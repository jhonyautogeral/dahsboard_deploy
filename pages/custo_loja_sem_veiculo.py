import pandas as pd
from sqlalchemy import create_engine
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

def criar_conexao():
    """Cria conexão com MySQL"""
    config = st.secrets["connections"]["mysql"]
    url = (f"{config['dialect']}://{config['username']}:{config['password']}@"
           f"{config['host']}:{config['port']}/{config['database']}")
    return create_engine(url)

def obter_centros_custo_disponiveis(engine):
    """Obtém todos os centros de custo disponíveis"""
    query = "SELECT DISTINCT DESCRICAO FROM centros_custo ORDER BY DESCRICAO"
    result = pd.read_sql_query(query, engine)
    return result['DESCRICAO'].tolist()

def obter_lojas_disponiveis(engine):
    """Obtém todas as lojas disponíveis"""
    query = "SELECT DISTINCT LOJA FROM despesas ORDER BY LOJA"
    result = pd.read_sql_query(query, engine)
    return result['LOJA'].tolist()

def consulta_custos_totais(data_inicio, data_fim, engine, lojas_selecionadas=None, descricoes_selecionadas=None):
    """Consulta custos totais entre datas com filtros - SEM DUPLICATAS"""
    where_conditions = [f"D.DATA BETWEEN '{data_inicio}' AND '{data_fim}'"]
    
    if lojas_selecionadas:
        lojas_str = ','.join(map(str, lojas_selecionadas))
        where_conditions.append(f"D.LOJA IN ({lojas_str})")
    
    if descricoes_selecionadas:
        descricoes_str = "','".join(descricoes_selecionadas)
        where_conditions.append(f"CC.DESCRICAO IN ('{descricoes_str}')")
    
    query = f"""
        SELECT
            D.CODIGO,
            D.DATA,
            D.LOJA,
            D.VENCIMENTO,
            D.PAGO_EM,
            D.DESCRICAO,
            CC.DESCRICAO AS CENTRO_CUSTO_DESCRICAO,
            D.VALOR,
            D.OBS
        FROM
            despesas D
        LEFT JOIN modos_pagamentos M ON
            D.MODO_PGTO_CODIGO = M.CODIGO
        LEFT JOIN caixas C ON
            D.CAIXA_CODIGO = C.CODIGO
            AND D.CAIXA_LOJA = C.LOJA
        LEFT JOIN cadastros F ON
            D.CADASTRO_CODIGO = F.CODIGO
            AND D.CADASTRO_LOJA = F.LOJA
        LEFT JOIN cadastros T ON
            D.TRANSPORTADORA_CODIGO = T.CODIGO
            AND D.TRANSPORTADORA_LOJA = T.LOJA
        LEFT JOIN centros_custo CC ON
            D.CENTRO_CUSTO_CODIGO = CC.CODIGO
        WHERE
            CC.DESCRICAO != 'FROTA REPAROS/CONSERTOS'
            AND CC.DESCRICAO != 'FROTA COMBUSTIVEL'
            AND CC.DESCRICAO != 'PEDAGIO'
            AND {' AND '.join(where_conditions)}
        ORDER BY D.DATA, D.LOJA
    """
    return pd.read_sql_query(query, engine)

def processar_dados_custos(data_inicio, data_fim, lojas_selecionadas=None, descricoes_selecionadas=None):
    """Processa dados de custos totais - função reutilizável"""
    engine = criar_conexao()
    df = consulta_custos_totais(data_inicio, data_fim, engine, lojas_selecionadas, descricoes_selecionadas)
    
    if df.empty:
        return None
    
    # Remove duplicatas no DataFrame
    df = df.drop_duplicates(subset=['LOJA', 'DATA', 'VALOR'])
    
    # Converter data
    df['DATA'] = pd.to_datetime(df['DATA'])
    df['DATA_FORMATADA'] = df['DATA'].dt.date
    df['MES_ANO'] = df['DATA'].dt.to_period('M')
    
    # Agrupamento por loja, data e descrição
    resumo_agrupado = df.groupby(['LOJA', 'DATA_FORMATADA', 'CENTRO_CUSTO_DESCRICAO']).agg({
        'VALOR': ['sum', 'mean', 'count']
    }).reset_index()
    
    # Achatar colunas
    resumo_agrupado.columns = ['LOJA', 'DATA', 'DESCRICAO', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    # Resumos para análise
    resumo_loja = df.groupby('LOJA')['VALOR'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_loja.columns = ['LOJA', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    resumo_tempo = df.groupby('DATA_FORMATADA')['VALOR'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_tempo.columns = ['DATA', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    resumo_mensal = df.groupby('MES_ANO')['VALOR'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_mensal['MES_ANO'] = resumo_mensal['MES_ANO'].astype(str)
    resumo_mensal.columns = ['MES', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    resumo_desc = df.groupby('CENTRO_CUSTO_DESCRICAO')['VALOR'].agg(['sum', 'mean', 'count']).reset_index()
    resumo_desc.columns = ['DESCRICAO', 'TOTAL', 'MEDIA', 'QUANTIDADE']
    
    # Resumo por LOJA, MES e CÓDIGO
    resumo_loja_mes_codigo = df.groupby(['LOJA', 'MES_ANO', 'CODIGO'])['VALOR'].agg(['sum', 'mean', 'median', 'count']).reset_index()
    resumo_loja_mes_codigo['MES_ANO'] = resumo_loja_mes_codigo['MES_ANO'].astype(str)
    resumo_loja_mes_codigo.columns = ['LOJA', 'MES', 'CODIGO', 'TOTAL', 'MEDIA', 'MEDIANA', 'QUANTIDADE']
    
    return {
        'original': df,
        'agrupado': resumo_agrupado,
        'por_loja': resumo_loja,
        'por_dia': resumo_tempo,
        'por_mes': resumo_mensal,
        'por_desc': resumo_desc,
        'por_loja_mes_codigo': resumo_loja_mes_codigo
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
    st.set_page_config(page_title="Análise de Despesas", layout="wide")
    st.title("💰 Análise de Despesas por Loja (SEM VEICULO)")
    
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
        descricoes_disponiveis = obter_centros_custo_disponiveis(engine)
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
        "Selecionar Centros de Custo",
        options=descricoes_disponiveis,
        default=[],
        help="Deixe vazio para mostrar todos os centros de custo"
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
    
    # Consulta automática
    with st.spinner("Carregando dados de despesas..."):
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
        
        total_geral = dados['original']['VALOR'].sum()
        media_geral = dados['original']['VALOR'].mean()
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
        
        # Dados Detalhados com filtro de descrição
        st.header("📋 Dados Detalhados")
        
        # Filtro de descrição
        filtro_descricao = st.text_input(
            "🔍 Filtrar por Descrição",
            value="",
            placeholder="Digite parte da descrição",
            help="Busca por partes da descrição - não precisa ser exata"
        )
        
        # Aplicar filtro de descrição
        df_filtrado = dados['original'].copy()
        if filtro_descricao:
            df_filtrado = df_filtrado[
                df_filtrado['DESCRICAO'].str.contains(filtro_descricao, case=False, na=False)
            ]
        
        # Mostrar informações do filtro
        if filtro_descricao:
            st.info(f"📊 Mostrando {len(df_filtrado)} registros filtrados por descrição: '{filtro_descricao}'")
        
        st.dataframe(df_filtrado.head(100), use_container_width=True)
        
        # Análise Visual Principal
        st.header("📊 Análise Visual Principal")
        fig_principal = gerar_grafico_custos(dados, tipo_grafico, tipo_analise)
        st.plotly_chart(fig_principal, use_container_width=True)
        
        # Gráficos complementares
        st.header("📊 Análises Complementares")
        
        # Gráfico de barras: Mês x Loja com valores totais
        st.subheader("Despesas por Mês x Loja")
        
        df_mes_loja = dados['original'].groupby(['MES_ANO', 'LOJA'])['VALOR'].sum().reset_index()
        df_mes_loja['MES_ANO'] = df_mes_loja['MES_ANO'].astype(str)
        
        mediana_mes_loja = df_mes_loja['VALOR'].median()
        
        fig_mes_loja = px.bar(df_mes_loja, 
                             x='LOJA', 
                             y='VALOR',
                             color='MES_ANO',
                             title='Despesas - Distribuição Mensal por Loja',
                             labels={'VALOR': 'Valor Total (R$)', 'LOJA': 'Loja'},
                             barmode='group')
        
        fig_mes_loja.add_hline(y=mediana_mes_loja, 
                              line_dash="dash", 
                              line_color="red",
                              annotation_text=f"Mediana: R$ {mediana_mes_loja:,.2f}")
        
        st.plotly_chart(fig_mes_loja, use_container_width=True)
        
        # Resumos Detalhados
        st.header("📋 Resumos Detalhados")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Por Loja", "Por Centro de Custo", "Detalhado", "Loja-Mês-Código"])
        
        with tab1:
            st.dataframe(dados['por_loja'], use_container_width=True)
        
        with tab2:
            st.dataframe(dados['por_desc'], use_container_width=True)
        
        with tab3:
            st.dataframe(dados['agrupado'].head(20), use_container_width=True)
        
        with tab4:
            st.subheader("Despesas por Loja, Mês e Código")
            
            filtro_codigo_resumo = st.text_input(
                "🔍 Filtrar por Código no Resumo",
                value="",
                placeholder="Digite o código",
                key="filtro_codigo_resumo"
            )
            
            df_resumo_filtrado = dados['por_loja_mes_codigo'].copy()
            if filtro_codigo_resumo:
                df_resumo_filtrado = df_resumo_filtrado[
                    df_resumo_filtrado['CODIGO'].astype(str).str.contains(filtro_codigo_resumo, case=False, na=False)
                ]
                st.info(f"📊 Mostrando {len(df_resumo_filtrado)} registros filtrados por código: '{filtro_codigo_resumo}'")
            
            st.dataframe(df_resumo_filtrado, use_container_width=True)
        
        # Análises Específicas
        st.header("📊 Análises Específicas")
        
        # Heatmap de despesas por loja e data
        st.subheader("Heatmap de Despesas por Loja e Data")
        df_heatmap = dados['original'].groupby(['LOJA', 'DATA_FORMATADA'])['VALOR'].sum().reset_index()
        fig_heatmap = px.density_heatmap(df_heatmap, x='DATA_FORMATADA', y='LOJA', z='VALOR',
                                        title='Heatmap de Despesas por Loja e Data',
                                        labels={'VALOR': 'Despesa Total (R$)'})
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Média de despesas por loja
        st.subheader("Total de Despesas por Loja")
        soma_por_loja = dados['original'].groupby('LOJA')['VALOR'].sum()
        mediana_despesa = soma_por_loja.median()
        
        soma_loja_df = soma_por_loja.reset_index()
        soma_loja_df.columns = ['LOJA', 'DESPESA_TOTAL']
        
        fig_media = px.bar(soma_loja_df, x='LOJA', y='DESPESA_TOTAL',
                            title=f'Despesa Total por Loja (Mediana: R$ {mediana_despesa:,.2f})',
                            labels={'DESPESA_TOTAL': 'Despesa Total (R$)'})
        
        fig_media.add_hline(y=mediana_despesa, line_dash="dash", line_color="red",
                            annotation_text=f"Mediana: R$ {mediana_despesa:,.2f}")
        
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
            st.info(f"💰 **Centro de Custo top**: {desc_maior['DESCRICAO'][:20]}...\nR$ {desc_maior['TOTAL']:,.2f}")
        
        # Download
        st.header("💾 Download dos Dados")
        buffer = io.BytesIO()
        dados['original'].to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="📥 Baixar dados em Excel",
            data=buffer,
            file_name=f"despesas_{data_inicio}_{data_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()