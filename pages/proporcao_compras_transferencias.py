import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from sqlalchemy import create_engine
from datetime import date

def conectar_banco():
    """Cria conexão com MySQL"""
    config = st.secrets["connections"]["mysql"]
    url = (f"{config['dialect']}://{config['username']}:{config['password']}@"
           f"{config['host']}:{config['port']}/{config['database']}")
    return create_engine(url)

def buscar_dados_compras(engine, data_inicio, data_fim):
    """Busca dados de compras do banco"""
    query = f'''SELECT LOJA as Loja,
                       OPERACAO_DESCRICAO as Operacao,
                       MONTH(CADASTRO) as Mes,
                       COUNT(1) as Notas,
                       SUM(VALOR_TOTAL_NOTA) as Valor
                FROM compras_dbf
                WHERE cadastro BETWEEN '{data_inicio} 00:00:00' AND '{data_fim} 23:59:59'
                GROUP BY LOJA, OPERACAO_DESCRICAO, MONTH(CADASTRO)'''
    
    return pd.read_sql(query, con=engine)

def filtrar_mercadorias(df):
    """Filtra apenas operações de mercadoria, excluindo consumo e comodato"""
    # Renomear operações específicas
    df.loc[df['Operacao'].str.contains('AQUISICAO DE MERCADORIAS DENTRO DO ESTADO PARA COMERCIALIZAC', 
                                       case=False, na=False), 'Operacao'] = 'COMPRA MERCADORIAS'
    df.loc[df['Operacao'].str.contains('TRANSFERENCIA DE MERCADORIA\\(ENTRADA\\) - ESTADUAL', 
                                       case=False, na=False, regex=True), 'Operacao'] = 'TRANSFERENCIA MERCADORIA'
    
    return df[
        (df['Operacao'].str.contains('MERCADORIA', case=False, na=False)) &
        (~df['Operacao'].str.contains('CONSUMO|COMODATO', case=False, na=False)) &
        (df['Loja'] != 1)
    ]

def criar_tabela_pivot(df):
    """Cria tabela pivot com dados por mês"""
    df_pivot = df.pivot_table(
        index=['Loja', 'Operacao'], 
        columns='Mes', 
        values='Valor', 
        fill_value=0
    ).reset_index()
    
    # Converter nomes das colunas para string para evitar tipos mistos
    df_pivot.columns = [str(col) for col in df_pivot.columns]
    
    # Adicionar coluna Total
    colunas_mes = [col for col in df_pivot.columns if col.isdigit()]
    df_pivot['Total'] = df_pivot[colunas_mes].sum(axis=1)
    df_pivot['Total %'] = (df_pivot['Total'] / df_pivot['Total'].sum() * 100).round(2)
    
    return df_pivot

def agrupar_dados(df):
    """Agrupa dados por loja/operação e por operação"""
    # Por Loja e Operação
    df_loja = df.groupby(['Loja', 'Operacao']).agg({
        'Notas': 'sum',
        'Valor': 'sum'
    }).reset_index().rename(columns={'Valor': 'Total'})
    
    df_loja['Total %'] = (df_loja['Total'] / df_loja.groupby('Loja')['Total'].transform('sum') * 100).round(2)
    
    # Por Operação
    df_operacao = df_loja.groupby('Operacao').agg({
        'Notas': 'sum',
        'Total': 'sum'
    }).reset_index()
    
    df_operacao['Total %'] = (df_operacao['Total'] / df_operacao['Total'].sum() * 100).round(2)
    
    return df_loja, df_operacao

def criar_grafico_loja_operacao(df):
    """Cria gráfico de barras para dados por Loja e Operação"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    lojas = sorted(df['Loja'].unique())
    operacoes = df['Operacao'].unique()
    
    x = range(len(lojas))
    largura = 0.8 / len(operacoes)
    cores = ['#B8860B', '#191970']
    
    for i, operacao in enumerate(operacoes):
        valores = []
        for loja in lojas:
            valor = df[(df['Loja'] == loja) & (df['Operacao'] == operacao)]['Total'].sum()
            valores.append(valor)
        
        posicoes = [pos + largura * i for pos in x]
        cor = cores[i % len(cores)]
        bars = ax.bar(posicoes, valores, largura, label=operacao, color=cor)
        
        # Adicionar valores nas barras
        for bar, valor in zip(bars, valores):
            if valor > 0:
                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + max(valores)*0.01,
                       f'{valor:,.0f}', ha='center', va='bottom', fontsize=8)
    
    # Configurações do gráfico
    ax.set_xlabel('Loja')
    ax.set_ylabel('Total')
    ax.set_title('Total por Loja e Operação')
    ax.set_xticks([pos + largura * (len(operacoes)-1)/2 for pos in x])
    ax.set_xticklabels(lojas)
    
    media = df['Total'].mean()
    ax.axhline(y=media, color='red', linestyle='--', alpha=0.8, label=f'Média: {media:,.0f}')
    
    ax.legend()
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
    plt.tight_layout()
    
    return fig

def criar_grafico_operacao(df):
    """Cria gráfico de barras para dados por Operação"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    operacoes = df['Operacao'].tolist()
    valores = df['Total'].tolist()
    cores = ['#B8860B', '#191970']
    
    bars = ax.bar(operacoes, valores, color=[cores[i % len(cores)] for i in range(len(operacoes))], alpha=0.8)
    
    # Adicionar valores nas barras
    for bar, valor in zip(bars, valores):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + max(valores)*0.01,
               f'{valor:,.0f}', ha='center', va='bottom', fontsize=9)
    
    # Linha da média
    media = df['Total'].mean()
    ax.axhline(y=media, color='red', linestyle='--', alpha=0.8, label=f'Média: {media:,.0f}')
    
    ax.set_ylabel('Total')
    ax.set_title('Total por Operação')
    ax.set_xticks([])
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
    ax.legend()
    plt.tight_layout()
    
    return fig

# Interface Streamlit
st.title('Proporção de Compras e Transferencias')

with st.sidebar:
    st.header('Filtros')
    
    data_inicio = st.date_input(
        'Data de Início',
        value=date.today().replace(day=1),
        help='Selecione a data inicial do período'
    )
    
    data_fim = st.date_input(
        'Data Final',
        value=date.today(),
        help='Selecione a data final do período'
    )
    
    aplicar_filtro = st.button('Aplicar Filtros', type='primary')

st.markdown('---')

# Validação das datas
if data_inicio > data_fim:
    st.error('A data de início não pode ser maior que a data final!')
else:
    if aplicar_filtro or 'df_pivot' not in st.session_state:
        with st.spinner('Carregando dados...'):
            try:
                engine = conectar_banco()
                df_compras = buscar_dados_compras(engine, data_inicio, data_fim)
                
                if df_compras.empty:
                    st.warning('Nenhum dado encontrado para o período selecionado.')
                else:
                    df_filtrado = filtrar_mercadorias(df_compras)
                    df_pivot = criar_tabela_pivot(df_filtrado)
                    df_loja, df_operacao = agrupar_dados(df_filtrado)
                    
                    # Armazenar no session_state
                    st.session_state.df_pivot = df_pivot
                    st.session_state.df_loja = df_loja
                    st.session_state.df_operacao = df_operacao
                    
                    st.success(f'Dados carregados! Período: {data_inicio} a {data_fim}')
                    
            except Exception as e:
                st.error(f'Erro ao carregar dados: {str(e)}')

    # Exibir dados
    if all(key in st.session_state for key in ['df_pivot', 'df_loja', 'df_operacao']):
        
        st.header('Dados por Loja, Operação e Mês')
        st.dataframe(st.session_state.df_pivot, width='stretch')

        fig1 = criar_grafico_loja_operacao(st.session_state.df_loja)
        st.pyplot(fig1)

        st.markdown('---')

        st.header('Dados agrupados por Operação')
        st.dataframe(st.session_state.df_operacao, width='stretch')

        fig2 = criar_grafico_operacao(st.session_state.df_operacao)
        st.pyplot(fig2)