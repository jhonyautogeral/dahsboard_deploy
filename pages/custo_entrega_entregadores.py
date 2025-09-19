import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

def criar_conexao():
    """Cria conexão com MySQL"""
    config = st.secrets["connections"]["mysql"]
    url = (f"{config['dialect']}://{config['username']}:{config['password']}@"
           f"{config['host']}:{config['port']}/{config['database']}")
    return create_engine(url)

def gerar_dataframes_custos(data_inicio='2025-03-01', data_fim='2025-06-06'):
    """
    Função consolidada para gerar os 3 dataframes e calcular custo por entrega
    """
    
    engine_autogeral = criar_conexao()
    
    # Parâmetros para as queries
    params = {
        'data_inicio': data_inicio,
        'data_fim': data_fim
    }
    
    try:
        # QUERY 1: Custos dos Entregadores
        query_custos = """
        SELECT
            C.LOJA, 
            C.PAGO_EM, 
            C.VALOR
        FROM
            contas_pagar C
        WHERE C.CENTRO_CUSTO_CODIGO = 14
        and C.FORNECEDOR_RAZAO_SOCIAL = 'AUTO GERAL AUTOPECAS LTDA (ENTREGADORES)'
        AND C.PAGO_EM BETWEEN :data_inicio AND :data_fim;
        """
        
        df_custos_raw = pd.read_sql(text(query_custos), engine_autogeral, params=params)
        df_custo_entregadores = df_custos_raw.groupby(['LOJA', 'PAGO_EM'])['VALOR'].sum().round(2).reset_index()
        df_custo_entregadores = df_custo_entregadores.rename(columns={'VALOR': 'custo_entregadores'})
        df_custo_entregadores['PERIODO'] = pd.to_datetime(df_custo_entregadores['PAGO_EM']).dt.to_period('M')
        
        # QUERY 2: Custos de Frota
        query_rate = """
        select
            distinct
            cvu.LOJA as LOJA,
            c.COMP_CODI as COMPRA,
            c.CADA_ATIV_ID as CADASTRO_VEICULO,
            cv.PLACA,
            c.cada_ativ_id as CADA_ATIV_ID,
            c.VALR_RATE as VALOR_UNITARIO_CUSTO,
            (c.VALR_RATE / a.VALOR_TOTAL_NOTA) as PERC,
            c.DSCR as DESCRICAO,
            a.CADASTRO,
            a.VALOR_TOTAL_NOTA
        from
            comp_rate_ativ c
        left join compras_dbf a on
            c.COMP_CODI = a.COMPRA
            and c.COMP_LOJA = a.LOJA
        left join cadastros_ativos ca on
            c.CADA_ATIV_ID = ca.CADA_ATIV_ID
        left join cadastros_veiculos cv on
            ca.CADA_VEIC_ID = cv.CADA_VEIC_ID
        left join cadastros_veiculos_ultilizacao cvu on
            ca.CADA_VEIC_ID = cvu.CADA_VEIC_ID
        where
            a.CADASTRO between :data_inicio and :data_fim
        order by
            a.CADASTRO,
            c.COMP_LOJA;
        """
        
        df_rate_raw = pd.read_sql(text(query_rate), engine_autogeral, params=params)
        df_rate_raw['CADASTRO'] = pd.to_datetime(df_rate_raw['CADASTRO'])
        
        df_frota = df_rate_raw[df_rate_raw['DESCRICAO'].str.contains('FROTA', case=False, na=False)]
        
        df_rate = df_frota.groupby([
            'LOJA',
            pd.Grouper(key='CADASTRO', freq='ME'),
            'DESCRICAO'
        ])['VALOR_UNITARIO_CUSTO'].sum().round(2).reset_index()
        
        df_rate = df_rate.rename(columns={'VALOR_UNITARIO_CUSTO': 'VALOR_CUSTO_LOJA'})
        df_rate['PERIODO'] = df_rate['CADASTRO'].dt.to_period('M')
        
        # QUERY 3: Quantidade de Romaneios
        query_romaneios = """
        SELECT 
            a.LOJA,
            a.CADASTRO,
            r.ROMANEIO 
        FROM 
            expedicao_itens e
        JOIN expedicao a ON 
            e.EXPEDICAO_CODIGO = a.EXPEDICAO
            AND e.EXPEDICAO_LOJA = a.LOJA
        JOIN entregador d ON 
            a.ENTREGADOR_CODIGO = d.CODIGO
        LEFT JOIN romaneios_dbf r ON 
            e.VENDA_TIPO = 'ROMANEIO'
            AND e.CODIGO_VENDA = r.ROMANEIO
            AND e.LOJA_VENDA = r.LOJA
        WHERE 
            a.ROTA_METROS IS NOT NULL
            AND e.ROTA_STATUS = 'ENTREGUE'
            AND r.CADASTRO BETWEEN :data_inicio AND :data_fim
        ORDER BY 
            a.LOJA 
        """
        
        df_romaneios_raw = pd.read_sql(text(query_romaneios), engine_autogeral, params=params)
        df_romaneios_raw['CADASTRO'] = pd.to_datetime(df_romaneios_raw['CADASTRO'])
        df_romaneios_raw['PERIODO'] = df_romaneios_raw['CADASTRO'].dt.to_period('M')
        
        df_ROMANEIO = df_romaneios_raw.groupby(['LOJA', 'PERIODO']).size().reset_index(name='total_romaneios')
        
        engine_autogeral.dispose()
        return df_custo_entregadores, df_rate, df_ROMANEIO
        
    except Exception as e:
        st.error(f"Erro ao executar queries: {e}")
        engine_autogeral.dispose()
        return None, None, None

def format_br_currency(value):
    """Formata valor para padrão brasileiro R$"""
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def consolidar_custos_entrega(df_custo_entregadores, df_rate, df_ROMANEIO):
    """Consolida os 3 dataframes e calcula custo por entrega"""
    
    df_rate_grouped = df_rate.groupby(['LOJA', 'PERIODO'])['VALOR_CUSTO_LOJA'].sum().reset_index()
    df_custos_grouped = df_custo_entregadores.groupby(['LOJA', 'PERIODO'])['custo_entregadores'].sum().reset_index()
    
    df_merged = pd.merge(df_custos_grouped, df_ROMANEIO, on=['LOJA', 'PERIODO'], how='outer')
    df_consolidado = pd.merge(df_merged, df_rate_grouped, on=['LOJA', 'PERIODO'], how='outer')
    
    df_consolidado = df_consolidado.fillna(0)
    
    df_consolidado['custo_total'] = (df_consolidado['custo_entregadores'] + 
                                   df_consolidado['VALOR_CUSTO_LOJA']).round(2)
    
    df_consolidado['custo_por_entrega'] = df_consolidado.apply(
        lambda row: round(row['custo_total'] / row['total_romaneios'], 2) 
        if row['total_romaneios'] > 0 else row['custo_total'], axis=1
    )
    
    # Converter periodo para string para melhor visualização
    df_consolidado['PERIODO_STR'] = df_consolidado['PERIODO'].astype(str)
    
    return df_consolidado

def main():
    """Cria o dashboard principal"""
    
    st.set_page_config(page_title="Dashboard Custos por Entrega", layout="wide")
    
    st.title("📊 Dashboard - Custos por Entrega")
    st.markdown("---")
    if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
    
    # Sidebar com calendário
    st.sidebar.header("🗓️ Período de Análise")
    st.sidebar.markdown("Selecione o período para análise dos custos:")
    
    # Calendários para seleção de datas
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data_inicio = st.date_input(
            "📅 Data Início", 
            value=pd.to_datetime('2025-03-01'),
            help="Selecione a data inicial do período"
        )
    
    with col2:
        data_fim = st.date_input(
            "📅 Data Fim", 
            value=pd.to_datetime('2025-06-06'),
            help="Selecione a data final do período"
        )
    
    # Validação de datas
    if data_inicio > data_fim:
        st.sidebar.error("❌ Data início deve ser menor que data fim!")
        return
    
    # Mostrar período selecionado
    dias_periodo = (data_fim - data_inicio).days + 1
    st.sidebar.success(f"✅ Período: {dias_periodo} dias")
    
    # Botão para atualizar
    atualizar = st.sidebar.button(
        "🔄 Atualizar Dados", 
        type="primary",
        help="Clique para buscar dados do período selecionado"
    )
    
    # Verificar se precisa atualizar dados
    key_periodo = f"{data_inicio}_{data_fim}"
    
    if atualizar or 'ultimo_periodo' not in st.session_state or st.session_state.ultimo_periodo != key_periodo:
        st.session_state.ultimo_periodo = key_periodo
        st.session_state.dados_atualizados = True
    
    # Carregar dados
    if 'df_consolidado' not in st.session_state or st.session_state.get('dados_atualizados', False):
        with st.spinner(f'🔄 Carregando dados do período {data_inicio} até {data_fim}...'):
            df_custo, df_rate, df_romaneio = gerar_dataframes_custos(
                data_inicio=str(data_inicio), 
                data_fim=str(data_fim)
            )
            
            if df_custo is not None:
                st.session_state.df_consolidado = consolidar_custos_entrega(df_custo, df_rate, df_romaneio)
                st.session_state.dados_atualizados = False
                st.success(f"✅ Dados carregados com sucesso! Período: {data_inicio} até {data_fim}")
            else:
                st.error("❌ Erro ao carregar dados")
                return
    
    df = st.session_state.df_consolidado
    
    # Mostrar informações do período na sidebar
    st.sidebar.markdown("---")
    
    if len(df) > 0:
        st.sidebar.info(f"**Total de registros:** {len(df)}")
    else:
        st.sidebar.warning("⚠️ Nenhum dado encontrado para o período selecionado")
    
    # KPIs principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_lojas = df['LOJA'].nunique()
        st.metric("Total de Lojas", total_lojas)
    
    with col2:
        total_romaneios = int(df['total_romaneios'].sum())
        st.metric("Total Romaneios", f"{total_romaneios:,.0f}".replace(',', '.'))
    
    with col3:
        custo_total = df['custo_total'].sum()
        st.metric("Custo Total", format_br_currency(custo_total))
    
    with col4:
        custo_mediano = df['custo_por_entrega'].median()
        st.metric("Custo Mediano/Entrega", format_br_currency(custo_mediano))
    
    st.markdown("---")
    
    # Tabelas primeiro - antes dos gráficos
    st.subheader("📋 Tabela Detalhada")
    
    # Preparar tabela formatada
    df_tabela = df.copy()
    df_tabela['Custo Entregadores'] = df_tabela['custo_entregadores'].apply(format_br_currency)
    df_tabela['Custo Frota'] = df_tabela['VALOR_CUSTO_LOJA'].apply(format_br_currency)
    df_tabela['Custo Total'] = df_tabela['custo_total'].apply(format_br_currency)
    df_tabela['Custo/Entrega'] = df_tabela['custo_por_entrega'].apply(format_br_currency)
    df_tabela['Total Romaneios'] = df_tabela['total_romaneios'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
    
    tabela_final = df_tabela[['LOJA', 'PERIODO_STR', 'Custo Entregadores', 'Custo Frota', 
                             'Total Romaneios', 'Custo Total', 'Custo/Entrega']]
    
    tabela_final.columns = ['Loja', 'Período', 'Custo Entregadores', 'Custo Frota', 
                           'Total Romaneios', 'Custo Total', 'Custo por Entrega']
    
    st.dataframe(tabela_final, use_container_width=True, hide_index=True)
    
    # Estatísticas por loja
    st.subheader("📈 Estatísticas por Loja")
    
    stats_loja = df.groupby('LOJA').agg({
        'custo_total': 'sum',
        'total_romaneios': 'sum',
        'custo_por_entrega': 'mean'
    }).round(2)
    
    stats_loja['custo_total_fmt'] = stats_loja['custo_total'].apply(format_br_currency)
    stats_loja['custo_por_entrega_fmt'] = stats_loja['custo_por_entrega'].apply(format_br_currency)
    stats_loja['total_romaneios_fmt'] = stats_loja['total_romaneios'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
    
    stats_final = stats_loja[['custo_total_fmt', 'total_romaneios_fmt', 'custo_por_entrega_fmt']]
    stats_final.columns = ['Custo Total', 'Total Romaneios', 'Custo Médio/Entrega']
    
    st.dataframe(stats_final, use_container_width=True)
    
    st.markdown("---")
    
    # Filtrar dados - excluir LOJA = 1 dos gráficos principais
    df_sem_loja1 = df[df['LOJA'] != 1].copy()
    df_loja1 = df[df['LOJA'] == 1].copy()
    
    # Gráficos por Loja - Custo Total por Mês (LOJA 1 até 12)
    st.subheader("💰 Custo Total por Mês - Cada Loja")
    
    # Criar gráficos para cada loja de 1 a 12
    lojas_disponiveis = sorted(df['LOJA'].unique())
    lojas_ate_12 = [loja for loja in lojas_disponiveis if loja <= 12]
    
    # Definir cores alternadas - azul escuro e azul claro
    cores_alternadas = ['#1f4e79', '#87ceeb']  # azul escuro e azul claro
    
    # Organizar em linhas de 2 gráficos
    for i in range(0, len(lojas_ate_12), 2):
        cols = st.columns(2)
        
        for j, loja in enumerate(lojas_ate_12[i:i+2]):
            df_loja = df[df['LOJA'] == loja].copy()
            
            if len(df_loja) > 0:
                with cols[j]:
                    # Criar cores para as barras baseado no índice do mês
                    cores_barras = [cores_alternadas[idx % 2] for idx in range(len(df_loja))]
                    
                    fig_loja = px.bar(
                        df_loja,
                        x='PERIODO_STR',
                        y='custo_total',
                        title=f"Loja {loja} - Custo Total",
                        text='custo_total'
                    )
                    
                    # Aplicar cores alternadas nas barras
                    fig_loja.update_traces(
                        texttemplate='R$ %{text:,.0f}', 
                        textposition='outside',
                        marker_color=cores_barras
                    )
                    
                    fig_loja.update_layout(
                        xaxis_title="Mês",
                        yaxis_title="Custo Total (R$)",
                        height=400,
                        showlegend=False,
                        title_font_size=14
                    )
                    st.plotly_chart(fig_loja, use_container_width=True)
            else:
                with cols[j]:
                    st.info(f"Loja {loja}: Sem dados")
    
    # Segundo gráfico - Custo por Entrega por Mês - Cada Loja
    st.subheader("📦 Custo por Entrega por Mês - Cada Loja")
    
    # Organizar em linhas de 2 gráficos
    for i in range(0, len(lojas_ate_12), 2):
        cols = st.columns(2)
        
        for j, loja in enumerate(lojas_ate_12[i:i+2]):
            df_loja = df[df['LOJA'] == loja].copy()
            
            if len(df_loja) > 0:
                with cols[j]:
                    # Criar cores para as barras baseado no índice do mês
                    cores_barras = [cores_alternadas[idx % 2] for idx in range(len(df_loja))]
                    
                    fig_loja_entrega = px.bar(
                        df_loja,
                        x='PERIODO_STR',
                        y='custo_por_entrega',
                        title=f"Loja {loja} - Custo por Entrega",
                        text='custo_por_entrega'
                    )
                    
                    # Aplicar cores alternadas nas barras
                    fig_loja_entrega.update_traces(
                        texttemplate='R$ %{text:,.2f}', 
                        textposition='outside',
                        marker_color=cores_barras
                    )
                    
                    fig_loja_entrega.update_layout(
                        xaxis_title="Mês",
                        yaxis_title="Custo por Entrega (R$)",
                        height=400,
                        showlegend=False,
                        title_font_size=14
                    )
                    st.plotly_chart(fig_loja_entrega, use_container_width=True)
            else:
                with cols[j]:
                    st.info(f"Loja {loja}: Sem dados")
    # Gráficos de comparação entregadores vs frota - separados
    st.subheader("⚖️ Comparação: Custos Entregadores vs Frota")
    
    # Preparar dados para entregadores
    df_entregadores = df.groupby(['LOJA', 'PERIODO_STR'])['custo_entregadores'].sum().reset_index()
    df_frota = df.groupby(['LOJA', 'PERIODO_STR'])['VALOR_CUSTO_LOJA'].sum().reset_index()
    
    # Gráfico de Entregadores
    st.subheader("👥 Custos de Entregadores por Loja e Período")
    
    # Criar cores alternadas para as barras
    cores_entregadores = []
    for loja in sorted(df_entregadores['LOJA'].unique()):
        df_loja_ent = df_entregadores[df_entregadores['LOJA'] == loja]
        cores_loja = [cores_alternadas[idx % 2] for idx in range(len(df_loja_ent))]
        cores_entregadores.extend(cores_loja)
    
    fig_entregadores = px.bar(
        df_entregadores,
        x='LOJA',
        y='custo_entregadores',
        color='PERIODO_STR',
        title="Custos de Entregadores",
        text='custo_entregadores',
        color_discrete_sequence=[cores_alternadas[i % 2] for i in range(len(df_entregadores['PERIODO_STR'].unique()))]
    )
    
    fig_entregadores.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
    fig_entregadores.update_layout(
        xaxis_title="Loja",
        yaxis_title="Custo Entregadores (R$)",
        height=400
    )
    st.plotly_chart(fig_entregadores, use_container_width=True)
    
    # Gráfico de Frota
    st.subheader("🚚 Custos de Frota por Loja e Período")
    
    fig_frota = px.bar(
        df_frota,
        x='LOJA',
        y='VALOR_CUSTO_LOJA',
        color='PERIODO_STR',
        title="Custos de Frota",
        text='VALOR_CUSTO_LOJA',
        color_discrete_sequence=[cores_alternadas[i % 2] for i in range(len(df_frota['PERIODO_STR'].unique()))]
    )
    
    fig_frota.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
    fig_frota.update_layout(
        xaxis_title="Loja",
        yaxis_title="Custo Frota (R$)",
        height=400
    )
    st.plotly_chart(fig_frota, use_container_width=True)

# Executar dashboard
if __name__ == "__main__":
    main()