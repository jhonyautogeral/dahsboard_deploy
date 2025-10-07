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

def gerar_dataframes_custos(data_inicio='2025-03-01 00:00:00', data_fim='2025-06-06 23:59:59'):
    """
    Função consolidada para gerar os 3 dataframes e calcular custo por entrega
    """
    
    engine_autogeral = criar_conexao()
    
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
        df_custos_raw['VALOR'] = pd.to_numeric(df_custos_raw['VALOR'], errors='coerce')
        
        df_custo_entregadores = df_custos_raw.groupby(['LOJA', 'PAGO_EM'])['VALOR'].sum().round(2).reset_index()
        df_custo_entregadores = df_custo_entregadores.rename(columns={'VALOR': 'custo_entregadores'})
        df_custo_entregadores['PERIODO'] = pd.to_datetime(df_custo_entregadores['PAGO_EM'], format='%Y-%m-%d %H:%M:%S').dt.to_period('M')
        
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
        df_rate_raw['CADASTRO'] = pd.to_datetime(df_rate_raw['CADASTRO'], format='%Y-%m-%d %H:%M:%S')
        df_rate_raw['VALOR_UNITARIO_CUSTO'] = pd.to_numeric(df_rate_raw['VALOR_UNITARIO_CUSTO'], errors='coerce')
        df_rate_raw['VALOR_TOTAL_NOTA'] = pd.to_numeric(df_rate_raw['VALOR_TOTAL_NOTA'], errors='coerce')
        
        df_frota = df_rate_raw[df_rate_raw['DESCRICAO'].str.contains('FROTA', case=False, na=False)]
        
        df_rate = df_frota.groupby([
            'LOJA',
            pd.Grouper(key='CADASTRO', freq='ME'),
            'DESCRICAO'
        ])['VALOR_UNITARIO_CUSTO'].sum().round(2).reset_index()
        
        df_rate = df_rate.rename(columns={'VALOR_UNITARIO_CUSTO': 'VALOR_CUSTO_LOJA'})
        df_rate['PERIODO'] = df_rate['CADASTRO'].dt.to_period('M')
        
        # QUERY 3: Quantidade de EXPEDICAO 
        query_romaneios = """
        SELECT
            E.LOJA,
            DATE_FORMAT(E.CADASTRO, '%m/%Y') AS PERIODO,
            COUNT(E.EXPEDICAO) AS EXPEDICAO_CODIGO,
            SUM(COALESCE(EI.ITEMS_EXPEDICAO, 0)) AS "ITENS DA EXPEDICAO"
        FROM expedicao E
        LEFT JOIN (
            SELECT 
                EXPEDICAO_CODIGO,
                EXPEDICAO_LOJA,
                SUM(ITEM) AS ITEMS_EXPEDICAO
            FROM expedicao_itens
            WHERE
                ROTA_METROS IS NOT NULL
                AND VENDA_TIPO = 'ROMANEIO'
                AND COMPRADOR_NOME NOT LIKE ('AUTO GERAL AUTOPECAS LTDA%')
                AND CADASTRO BETWEEN :data_inicio and :data_fim
            GROUP BY EXPEDICAO_CODIGO, EXPEDICAO_LOJA
        ) EI 
            ON EI.EXPEDICAO_CODIGO = E.EXPEDICAO
            AND EI.EXPEDICAO_LOJA = E.LOJA
        WHERE
            E.CADASTRO BETWEEN :data_inicio and :data_fim
        GROUP BY
            E.LOJA,
            DATE_FORMAT(E.CADASTRO, '%m/%Y')
        ORDER BY
            E.LOJA;
        """

        df_romaneios_raw = pd.read_sql(text(query_romaneios), engine_autogeral, params=params)

        # Converter PERIODO para period
        df_romaneios_raw['PERIODO'] = pd.to_datetime(df_romaneios_raw['PERIODO'], format='%m/%Y').dt.to_period('M')

        # Apenas renomear 
        df_ROMANEIO = df_romaneios_raw.rename(columns={'EXPEDICAO_CODIGO': 'total_expedicoes'})
        
        # QUERY 4: Detalhes dos Centro de Custo
        query_comp_rate = """
            SELECT DISTINCT
                cvu.LOJA AS LOJA,
                c.COMP_CODI AS COMPRA,
                c.COMP_LOJA,
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
            WHERE a.CADASTRO BETWEEN :data_inicio AND :data_fim
            ORDER BY a.CADASTRO, c.COMP_LOJA
        """
        
        df_comp_rate_ativ = pd.read_sql(text(query_comp_rate), engine_autogeral, params=params)
        
        engine_autogeral.dispose()
        return df_custo_entregadores, df_rate, df_ROMANEIO, df_comp_rate_ativ
        
    except Exception as e:
        st.error(f"Erro ao executar queries: {e}")
        engine_autogeral.dispose()
        return None, None, None, None

def format_br_currency(value):
    """Formata valor para padrão brasileiro R$"""
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def format_number_br(value):
    """Formata número para padrão brasileiro com ponto e vírgula"""
    if isinstance(value, (int, float)):
        if value != int(value):
            return f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            return f"{int(value):,}".replace(',', '.')
    return str(value)

def consolidar_custos_entrega(df_custo_entregadores, df_rate, df_ROMANEIO, data_inicio=None, data_fim=None):
    """Consolida os 3 dataframes e calcula custo por entrega"""
    
    df_rate_grouped = df_rate.groupby(['LOJA', 'PERIODO'])['VALOR_CUSTO_LOJA'].sum().reset_index()
    df_custos_grouped = df_custo_entregadores.groupby(['LOJA', 'PERIODO'])['custo_entregadores'].sum().reset_index()
    
    df_merged = pd.merge(df_custos_grouped, df_ROMANEIO, on=['LOJA', 'PERIODO'], how='outer')
    df_consolidado = pd.merge(df_merged, df_rate_grouped, on=['LOJA', 'PERIODO'], how='outer')
    
    df_consolidado = df_consolidado.fillna(0)
    
    # Filtrar por período
    if data_inicio and data_fim:
        periodo_inicio = pd.Period(data_inicio, freq='M')
        periodo_fim = pd.Period(data_fim, freq='M')
        df_consolidado = df_consolidado[
            (df_consolidado['PERIODO'] >= periodo_inicio) & 
            (df_consolidado['PERIODO'] <= periodo_fim)
        ]
    
    df_consolidado['custo_total'] = (df_consolidado['custo_entregadores'] + 
                                   df_consolidado['VALOR_CUSTO_LOJA']).round(2)
    
    df_consolidado['custo_por_entrega'] = df_consolidado.apply(
        lambda row: round(row['custo_total'] / row['total_expedicoes'], 2) 
        if row['total_expedicoes'] > 0 else row['custo_total'], axis=1
    )
    
    df_consolidado['PERIODO_STR'] = df_consolidado['PERIODO'].astype(str)
    
    return df_consolidado

def filtrar_por_lojas(df, lojas_selecionadas):
    """Filtra dataframe pelas lojas selecionadas"""
    if 'Todas' in lojas_selecionadas or not lojas_selecionadas:
        return df
    return df[df['LOJA'].isin(lojas_selecionadas)]

def main():
    """Cria o dashboard principal"""
    
    st.set_page_config(page_title="Dashboard Custos por Entrega", layout="wide")
    
    st.title("📊 Dashboard - Custos por Entrega e Tabela Centro de Custo")
    st.markdown("---")
    
    if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
    
    # Sidebar com calendário
    st.sidebar.header("🗓️ Período de Análise")
    st.sidebar.markdown("Selecione o período para análise dos custos:")
    
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
    
    if data_inicio > data_fim:
        st.sidebar.error("❌ Data início deve ser menor que data fim!")
        return
    
    dias_periodo = (data_fim - data_inicio).days + 1
    st.sidebar.success(f"✅ Período: {dias_periodo} dias")
    
    # ====== FILTRO DE LOJAS ======
    st.sidebar.markdown("---")
    st.sidebar.header("🏪 Filtrar por Loja")
    
    # Carregar dados temporariamente para pegar lista de lojas
    if 'df_consolidado' in st.session_state:
        lojas_disponiveis = ['Todas'] + sorted(st.session_state.df_consolidado['LOJA'].unique().tolist())
    else:
        lojas_disponiveis = ['Todas']
    
    lojas_selecionadas = st.sidebar.multiselect(
        "Selecione as lojas:",
        options=lojas_disponiveis,
        default=['Todas'],
        help="Selecione uma ou mais lojas para análise"
    )
    
    atualizar = st.sidebar.button(
        "🔄 Atualizar Dados", 
        type="primary",
        help="Clique para buscar dados do período selecionado"
    )
    
    # Sidebar informações
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Como Calculamos")
    st.sidebar.markdown("""
    **Custo por Entrega:**
                        
    **Custo Entregadores:** Total pago aos entregadores no período. 
                         
    **Custo Frota:** Total rateado por lojas dos custos de frota no período.
                        
    **Total de Expedições:** Total de expedições por loja (Entrega realizada ou não) no período.
                        
    1. **Custo Total** = 
       - Custo Entregadores + 
       - Custo Frota
    
    2. **Custo por Entrega** = 
       - Custo Total ÷ Total de Expedições
    
    **Fontes de Dados:**
    - 💰 Entregadores: contas_pagar
    - 🚚 Frota: comp_rate_ativ (rateio)
    - 📦 Expedições: expedicao_itens
    
    **Agrupamento:** Por loja e mês
    """)
    
    key_periodo = f"{data_inicio}_{data_fim}"
    
    if atualizar or 'ultimo_periodo' not in st.session_state or st.session_state.ultimo_periodo != key_periodo:
        st.session_state.ultimo_periodo = key_periodo
        st.session_state.dados_atualizados = True
    
    # Carregar dados
    if 'df_consolidado' not in st.session_state or st.session_state.get('dados_atualizados', False):
        with st.spinner(f'🔄 Carregando dados do período {data_inicio} até {data_fim}...'):
            df_custo, df_rate, df_romaneio, df_comp_rate_ativ = gerar_dataframes_custos(
                data_inicio=str(data_inicio), 
                data_fim=str(data_fim)
            )
            
            if df_custo is not None:
                # CORREÇÃO: Passar data_inicio e data_fim
                st.session_state.df_consolidado = consolidar_custos_entrega(
                    df_custo, df_rate, df_romaneio,
                    data_inicio=data_inicio,
                    data_fim=data_fim
                )
                st.session_state.df_comp_rate_ativ = df_comp_rate_ativ
                st.session_state.dados_atualizados = False
                st.success(f"Dados carregados com sucesso! Período: {data_inicio} até {data_fim}")
            else:
                st.error("Erro ao carregar dados")
                return
    df = filtrar_por_lojas(st.session_state.df_consolidado, lojas_selecionadas)
    df_comp_rate = filtrar_por_lojas(st.session_state.df_comp_rate_ativ, lojas_selecionadas)

    # Mostrar informações do período na sidebar
    st.sidebar.markdown("---")
    
    if len(df) > 0:
        st.sidebar.info(f"**Total de registros:** {len(df)}")
    else:
        st.sidebar.warning("- Nenhum dado encontrado para o período selecionado")
    
    # KPIs principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_lojas = df['LOJA'].nunique()
        st.metric("Total de Lojas", total_lojas)
    
    with col2:
        total_expedicoes = int(df['total_expedicoes'].sum())
        st.metric("Total Expedições", f"{total_expedicoes:,.0f}".replace(',', '.'))
    
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
    df_tabela['Total Expedições'] = df_tabela['total_expedicoes'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
    
    tabela_final = df_tabela[['LOJA', 'PERIODO_STR', 'Custo Entregadores', 'Custo Frota', 
                             'Total Expedições', 'Custo Total', 'Custo/Entrega']]
    
    tabela_final.columns = ['Loja', 'Período', 'Custo Entregadores', 'Custo Frota', 
                           'Total Expedições', 'Custo Total', 'Custo por Entrega']
    
    st.dataframe(tabela_final, width='stretch', hide_index=True)
    
    # Estatísticas por loja
    st.subheader("📈 Estatísticas por Loja")
    
    stats_loja = df.groupby('LOJA').agg({
        'custo_total': 'sum',
        'total_expedicoes': 'sum',
        'custo_por_entrega': 'mean'
    }).round(2)
    
    stats_loja['custo_total_fmt'] = stats_loja['custo_total'].apply(format_br_currency)
    stats_loja['custo_por_entrega_fmt'] = stats_loja['custo_por_entrega'].apply(format_br_currency)
    stats_loja['total_expedicoes_fmt'] = stats_loja['total_expedicoes'].apply(lambda x: f"{int(x):,}".replace(',', '.'))
    
    stats_final = stats_loja[['custo_total_fmt', 'total_expedicoes_fmt', 'custo_por_entrega_fmt']]
    stats_final.columns = ['Custo Total', 'Total Expedições', 'Custo Médio/Entrega']
    
    st.dataframe(stats_final, width='stretch', hide_index=True)
    
    st.markdown("---")
    
    # SEÇÃO: Detalhes do Centro de Custo - comp_rate_ativ
    st.subheader("- Detalhes dos Centros de Custo - Rateio")
    
    # Filtros em 3 colunas
    col1_filtro, col2_filtro, col3_filtro = st.columns(3)
    
    with col1_filtro:
        lojas_disponiveis = ['Todas'] + sorted(df_comp_rate['LOJA'].dropna().unique().tolist())
        filtro_loja = st.selectbox("Filtrar por Loja:", lojas_disponiveis)
    
    with col2_filtro:
        descricoes_disponiveis = ['Todas'] + sorted(df_comp_rate['DESCRICAO'].dropna().unique().tolist())
        filtro_descricao = st.selectbox("Filtrar por Descrição:", descricoes_disponiveis)
    
    with col3_filtro:
        placas_disponiveis = ['Todas'] + sorted(df_comp_rate['PLACA'].dropna().unique().tolist())
        filtro_placa = st.selectbox("Filtrar por Placa:", placas_disponiveis)
    
    # Aplicar filtros
    df_filtrado = df_comp_rate.copy()
    
    if filtro_loja != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['LOJA'] == filtro_loja]
    
    if filtro_descricao != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['DESCRICAO'] == filtro_descricao]
    
    if filtro_placa != 'Todas':
        df_filtrado = df_filtrado[df_filtrado['PLACA'] == filtro_placa]
    
    # Mostrar tabela filtrada
    if len(df_filtrado) > 0:
        df_exibir = df_filtrado.copy()
        df_exibir['VALOR_UNITARIO_CUSTO'] = df_exibir['VALOR_UNITARIO_CUSTO'].apply(
            lambda x: format_br_currency(x) if pd.notna(x) else 'N/A'
        )
        df_exibir['VALOR_TOTAL_NOTA'] = df_exibir['VALOR_TOTAL_NOTA'].apply(
            lambda x: format_br_currency(x) if pd.notna(x) else 'N/A'
        )
        
        colunas_exibir = {
            'LOJA': 'Loja',
            'COMPRA': 'Compra',
            'COMP_LOJA': 'Loja Compra',
            'CADASTRO_VEICULO': 'ID Veículo',
            'PLACA': 'Placa',
            'VALOR_UNITARIO_CUSTO': 'Valor Unitário',
            'DESCRICAO': 'Descrição',
            'CADASTRO': 'Data Cadastro',
            'VALOR_TOTAL_NOTA': 'Valor Total Nota'
        }
        
        df_exibir = df_exibir.rename(columns=colunas_exibir)
        
        st.dataframe(df_exibir, width='stretch', hide_index=True)
        st.info(f"- Mostrando {len(df_filtrado)} registros")
    else:
        st.warning("- Nenhum registro encontrado com os filtros aplicados")
    
    st.markdown("---")
    
    # Gráficos por Loja
    st.subheader("- Custo dos Entregadores + Custo da Frota - Cada Loja")
    
    lojas_disponiveis = sorted(df['LOJA'].unique())
    lojas_ate_12 = [loja for loja in lojas_disponiveis if loja <= 12]
    
    cores_alternadas = ['#1f4e79', '#87ceeb']
    
    for i in range(0, len(lojas_ate_12), 2):
        cols = st.columns(2)
        
        for j, loja in enumerate(lojas_ate_12[i:i+2]):
            df_loja = df[df['LOJA'] == loja].copy()
            
            if len(df_loja) > 0:
                with cols[j]:
                    cores_barras = [cores_alternadas[idx % 2] for idx in range(len(df_loja))]
                    
                    fig_loja = px.bar(
                        df_loja,
                        x='PERIODO_STR',
                        y='custo_total',
                        title=f"Loja {loja} - Custo Total",
                        text='custo_total'
                    )
                    
                    fig_loja.update_traces(
                        texttemplate=[f'R$ {format_number_br(val)}' for val in df_loja['custo_total']], 
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
                    st.plotly_chart(fig_loja, width='stretch')
            else:
                with cols[j]:
                    st.info(f"Loja {loja}: Sem dados")
    
    # Custo por Entrega por Mês
    st.subheader("- Custo por Entrega por Mês - Cada Loja")
    
    for i in range(0, len(lojas_ate_12), 2):
        cols = st.columns(2)
        
        for j, loja in enumerate(lojas_ate_12[i:i+2]):
            df_loja = df[df['LOJA'] == loja].copy()
            
            if len(df_loja) > 0:
                with cols[j]:
                    cores_barras = [cores_alternadas[idx % 2] for idx in range(len(df_loja))]
                    
                    fig_loja_entrega = px.bar(
                        df_loja,
                        x='PERIODO_STR',
                        y='custo_por_entrega',
                        title=f"Loja {loja} - Custo por Entrega",
                        text='custo_por_entrega'
                    )
                    
                    fig_loja_entrega.update_traces(
                        texttemplate=[f'R$ {format_number_br(val)}' for val in df_loja['custo_por_entrega']], 
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
                    st.plotly_chart(fig_loja_entrega, width='stretch')
            else:
                with cols[j]:
                    st.info(f"Loja {loja}: Sem dados")
    
    # Comparação Entregadores vs Frota
    st.subheader("- Comparação: Custos Entregadores vs Frota")
    
    df_entregadores = df.groupby(['LOJA', 'PERIODO_STR'])['custo_entregadores'].sum().reset_index()
    df_frota = df.groupby(['LOJA', 'PERIODO_STR'])['VALOR_CUSTO_LOJA'].sum().reset_index()
    
    st.subheader("- Custos de Entregadores por Loja e Período")
    
    fig_entregadores = px.bar(
        df_entregadores,
        x='LOJA',
        y='custo_entregadores',
        color='PERIODO_STR',
        title="Custos de Entregadores",
        text='custo_entregadores',
        color_discrete_sequence=[cores_alternadas[i % 2] for i in range(len(df_entregadores['PERIODO_STR'].unique()))]
    )
    
    fig_entregadores.update_traces(
        texttemplate=[f'R$ {format_number_br(val)}' for val in df_entregadores['custo_entregadores']], 
        textposition='outside'
    )
    fig_entregadores.update_layout(
        xaxis_title="Loja",
        yaxis_title="Custo Entregadores (R$)",
        height=400
    )
    st.plotly_chart(fig_entregadores, width='stretch')
    
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
    
    fig_frota.update_traces(
        texttemplate=[f'R$ {format_number_br(val)}' for val in df_frota['VALOR_CUSTO_LOJA']], 
        textposition='outside'
    )
    fig_frota.update_layout(
        xaxis_title="Loja",
        yaxis_title="Custo Frota (R$)",
        height=400
    )
    st.plotly_chart(fig_frota, width='stretch')

if __name__ == "__main__":
    main()