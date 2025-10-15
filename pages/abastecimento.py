import streamlit as st
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
from datetime import datetime

def criar_conexao():
    """Cria conexão com MySQL"""
    config = st.secrets["connections"]["mysql"]
    url = (f"{config['dialect']}://{config['username']}:{config['password']}@"
           f"{config['host']}:{config['port']}/{config['database']}")
    return create_engine(url)

# Configuração da página
st.set_page_config(page_title="Relatório de Abastecimentos", layout="wide")
st.title("📊 Relatório de Abastecimentos")

if st.sidebar.button("Voltar"):
        st.switch_page("app.py")

# Sidebar
st.sidebar.header("Filtros")
opcao = st.sidebar.selectbox(
    "Selecione o tipo de relatório:",
    ["SOMA POR LOJA, MES E VEICULO", "SOMA POR LOJA E MES", "SOMA TOTAL TODAS LOJAS"]
)

# Conexão
engine = criar_conexao()

# Cores para gráficos
cores = ['#1a237e', '#283593', '#3949ab', '#5c6bc0', '#7986cb', 
         '#9fa8da', '#c5cae9', '#b39ddb', '#9575cd', '#7e57c2',
         '#673ab7', '#5e35b1', '#512da8', '#4527a0']

# ============== OPÇÃO 1: SOMA POR LOJA, MES E VEICULO ==============
if opcao == "SOMA POR LOJA, MES E VEICULO":
    col1, col2 = st.sidebar.columns(2)
    data_inicio = col1.date_input("Data Início", datetime(2025, 9, 1))
    data_fim = col2.date_input("Data Fim", datetime(2025, 9, 30))
    
    # Buscar lojas disponíveis
    lojas_query = "SELECT DISTINCT LOJA FROM cadastros_veiculos_abastecimentos ORDER BY LOJA"
    lojas_df = pd.read_sql(lojas_query, engine)
    lojas_lista = ["Todas"] + lojas_df['LOJA'].tolist()
    
    loja_selecionada = st.sidebar.selectbox("Selecione a Loja", lojas_lista)
    
    # Construir query
    if loja_selecionada == "Todas":
        filtro_loja = ""
    else:
        filtro_loja = f"AND K.LOJA = {loja_selecionada}"
    
    query = f"""
    SELECT
        K.LOJA,
        V.PLACA,
        SUM(K.COMBUSTIVEL_1_LITROS) AS COMBUSTIVEL_LITROS,
        SUM(K.VALOR_TOTAL) AS VALOR_COMBUSTIVEL,
        SUM(K.KM) AS SOMA_KM_MES,
        K.CADA_VEIC_ID,
        DATE_FORMAT(K.CADASTRO, '%%m/%%Y') AS CADASTRO
    FROM cadastros_veiculos_abastecimentos K
    JOIN cadastros_veiculos V ON K.CADA_VEIC_ID = V.CADA_VEIC_ID
    WHERE K.CADASTRO BETWEEN '{data_inicio} 00:00:00' AND '{data_fim} 23:59:59'
        {filtro_loja}
    GROUP BY K.CADA_VEIC_ID, DATE_FORMAT(K.CADASTRO, '%%m/%%Y'), K.LOJA, V.PLACA
    ORDER BY K.LOJA, CADASTRO
    """
    
    df = pd.read_sql(query, engine)
    
    # Filtros acima da tabela
    col_filtro1, col_filtro2 = st.columns(2)
    
    with col_filtro1:
        lojas_disponiveis = ["Todas"] + sorted(df['LOJA'].unique().tolist())
        filtro_loja_tabela = st.selectbox("Filtrar por Loja:", lojas_disponiveis, key="filtro_loja_tabela")
    
    with col_filtro2:
        placas_disponiveis = ["Todas"] + sorted(df['PLACA'].unique().tolist())
        filtro_placa = st.selectbox("Filtrar por Placa:", placas_disponiveis, key="filtro_placa")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if filtro_loja_tabela != "Todas":
        df_filtrado = df_filtrado[df_filtrado['LOJA'] == filtro_loja_tabela]
    
    if filtro_placa != "Todas":
        df_filtrado = df_filtrado[df_filtrado['PLACA'] == filtro_placa]
    
    # Agrupar por mês
    meses = df_filtrado['CADASTRO'].unique()
    
    for mes in meses:
        st.subheader(f"📅 Mês: {mes}")
        df_mes = df_filtrado[df_filtrado['CADASTRO'] == mes]
        st.dataframe(df_mes, use_container_width=True)
        st.divider()

# ============== OPÇÃO 2: SOMA POR LOJA E MES ==============
elif opcao == "SOMA POR LOJA E MES":
    col1, col2 = st.sidebar.columns(2)
    data_inicio = col1.date_input("Data Início", datetime(2025, 1, 1))
    data_fim = col2.date_input("Data Fim", datetime(2025, 9, 30))
    
    # Buscar lojas disponíveis
    lojas_query = "SELECT DISTINCT LOJA FROM cadastros_veiculos_abastecimentos ORDER BY LOJA"
    lojas_df = pd.read_sql(lojas_query, engine)
    lojas_lista = ["Todas"] + lojas_df['LOJA'].tolist()
    
    loja_selecionada = st.sidebar.selectbox("Selecione a Loja", lojas_lista)
    
    # Construir query
    if loja_selecionada == "Todas":
        filtro_loja = ""
    else:
        filtro_loja = f"AND K.LOJA = {loja_selecionada}"
    
    query = f"""
    SELECT
        K.LOJA,
        SUM(K.VALOR_TOTAL) AS SOMA_ABASTECIMENTOS,
        SUM(K.KM) AS SOMA_KMS,
        DATE_FORMAT(K.CADASTRO, '%%m/%%Y') AS CADASTRO
    FROM cadastros_veiculos_abastecimentos K
    WHERE K.CADASTRO BETWEEN '{data_inicio} 00:00:00' AND '{data_fim} 23:59:59'
        {filtro_loja}
    GROUP BY K.LOJA, DATE_FORMAT(K.CADASTRO, '%%m/%%Y')
    ORDER BY K.LOJA, CADASTRO
    """
    
    df = pd.read_sql(query, engine)
    
    # Gráfico de barras
    fig = go.Figure()
    for i, loja in enumerate(df['LOJA'].unique()):
        df_loja = df[df['LOJA'] == loja]
        fig.add_trace(go.Bar(
            x=df_loja['CADASTRO'],
            y=df_loja['SOMA_ABASTECIMENTOS'],
            name=f'Loja {loja}',
            text=df_loja['SOMA_ABASTECIMENTOS'].apply(lambda x: f'R${x:,.2f}'),
            textposition='inside',
            marker_color=cores[i % len(cores)]
        ))
    
    fig.update_layout(
        title='Comparação de Abastecimentos por Mês',
        xaxis_title='Mês',
        yaxis_title='Valor Total (R$)',
        barmode='group',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True)

# ============== OPÇÃO 3: SOMA TOTAL TODAS LOJAS ==============
else:
    ano_atual = datetime.now().year
    anos = [ano_atual - 2, ano_atual - 1, ano_atual]
    
    query = f"""
    SELECT
        SUM(K.VALOR_TOTAL) AS SOMA_ABASTECIMENTOS,
        SUM(K.KM) AS SOMA_KMS,
        MONTH(K.CADASTRO) AS MES_NUM,
        YEAR(K.CADASTRO) AS ANO
    FROM cadastros_veiculos_abastecimentos K
    WHERE YEAR(K.CADASTRO) IN ({','.join(map(str, anos))})
    GROUP BY YEAR(K.CADASTRO), MONTH(K.CADASTRO)
    ORDER BY YEAR(K.CADASTRO), MONTH(K.CADASTRO)
    """
    
    df = pd.read_sql(query, engine)
    
    # Nomes dos meses
    meses_nomes = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
                   7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
    
    # Pivot para organizar dados
    df_pivot = df.pivot(index='MES_NUM', columns='ANO', values='SOMA_ABASTECIMENTOS').fillna(0)
    df_pivot_km = df.pivot(index='MES_NUM', columns='ANO', values='SOMA_KMS').fillna(0)
    
    # Gráfico de barras
    fig = go.Figure()
    cores_anos = ['#5c9bd5', '#4472c4', '#ed7d31']
    
    for i, ano in enumerate(anos):
        if ano in df_pivot.columns:
            valores = df_pivot[ano]
            meses_labels = [meses_nomes[m] for m in df_pivot.index]
            
            fig.add_trace(go.Bar(
                x=meses_labels,
                y=valores,
                name=str(ano),
                text=valores.apply(lambda x: f'{x:,.0f}' if x > 0 else '0.00'),
                textposition='inside',
                marker_color=cores_anos[i]
            ))
    
    fig.update_layout(
        xaxis_title='Mês',
        yaxis_title='Valor Total',
        barmode='group',
        height=500,
        showlegend=True,
        legend=dict(title='variable', orientation='v', x=1.02, y=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Criar tabela formatada
    st.subheader("📊 Tabela Comparativa por Ano")
    
    # Preparar dados da tabela
    tabela_data = {'ANO': []}
    for mes_num in range(1, 13):
        tabela_data[meses_nomes[mes_num]] = []
    tabela_data['Total Ano'] = []
    tabela_data['YTD'] = []
    
    # Preencher dados para cada ano
    for ano in anos:
        tabela_data['ANO'].append(ano)
        total_ano = 0
        mes_atual = datetime.now().month if ano == ano_atual else 12
        
        for mes_num in range(1, 13):
            if ano in df_pivot.columns and mes_num in df_pivot.index:
                valor = df_pivot.loc[mes_num, ano]
                tabela_data[meses_nomes[mes_num]].append(f'{valor:,.2f}')
                if mes_num <= mes_atual:
                    total_ano += valor
            else:
                tabela_data[meses_nomes[mes_num]].append('0.00')
        
        tabela_data['Total Ano'].append(f'{total_ano:,.2f}')
        tabela_data['YTD'].append(f'{total_ano:,.2f}')
    
    # Calcular variações
    if len(anos) >= 2:
        tabela_data['ANO'].append(f'Var% {anos[1]}x{anos[0]}')
        for mes_num in range(1, 13):
            col_name = meses_nomes[mes_num]
            val_2023 = float(tabela_data[col_name][0].replace(',', ''))
            val_2024 = float(tabela_data[col_name][1].replace(',', ''))
            var = ((val_2024 - val_2023) / val_2023 * 100) if val_2023 > 0 else 0
            tabela_data[col_name].append(f'{var:.2f}')
        
        total_2023 = float(tabela_data['Total Ano'][0].replace(',', ''))
        total_2024 = float(tabela_data['Total Ano'][1].replace(',', ''))
        var_total = ((total_2024 - total_2023) / total_2023 * 100) if total_2023 > 0 else 0
        tabela_data['Total Ano'].append(f'{var_total:.2f}')
        tabela_data['YTD'].append(f'{var_total:.2f}')
    
    if len(anos) >= 3:
        tabela_data['ANO'].append(f'Var% {anos[2]}x{anos[1]}')
        for mes_num in range(1, 13):
            col_name = meses_nomes[mes_num]
            val_2024 = float(tabela_data[col_name][1].replace(',', ''))
            val_2025 = float(tabela_data[col_name][2].replace(',', ''))
            var = ((val_2025 - val_2024) / val_2024 * 100) if val_2024 > 0 else 0
            tabela_data[col_name].append(f'{var:.2f}')
        
        total_2024 = float(tabela_data['Total Ano'][1].replace(',', ''))
        total_2025 = float(tabela_data['Total Ano'][2].replace(',', ''))
        var_total = ((total_2025 - total_2024) / total_2024 * 100) if total_2024 > 0 else 0
        tabela_data['Total Ano'].append(f'{var_total:.2f}')
        tabela_data['YTD'].append(f'{var_total:.2f}')
    
    df_tabela = pd.DataFrame(tabela_data)
    st.dataframe(df_tabela, use_container_width=True)