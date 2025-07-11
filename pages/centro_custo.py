import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import calendar
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine

# Configuração do pandas para evitar downcasting silencioso
pd.set_option('future.no_silent_downcasting', True)
# if st.button("⬅️ Voltar para página inicial"):
#     st.switch_page("app.py")
# -----------------------
# Proteção de acesso
# -----------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

# -----------------------
# 1. Conexão com Banco de Dados
# -----------------------
def criar_conexao():
    """Cria e retorna a conexão com o banco de dados MySQL."""
    config = st.secrets["connections"]["mysql"]
    url = (f"{config['dialect']}://{config['username']}:{config['password']}@"
           f"{config['host']}:{config['port']}/{config['database']}")
    return create_engine(url)

def executar_query(engine, query):
    """Executa a query no banco de dados e retorna um DataFrame."""
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Erro ao executar a query: {e}")
        return pd.DataFrame()

# -----------------------
# 2. Funções Auxiliares
# -----------------------
def obter_meses():
    """Retorna a lista dos meses em português."""
    return [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]

# Dicionário para mapear código de lojas para seus nomes
LOJA_DICT = {
    1: 'CD',
    2: 'SALTO',
    3: 'SOROCABA',
    4: 'CAETANO',
    5: 'INDAIATUBA',
    6: 'PORTO FELIZ',
    7: 'ÉDEN',
    8: 'JACARE',
    9: 'TATUI',
    10: 'BOITUVA',
    11: 'PIEDADE',
    12: 'OTAVIANO',
    13: 'CERQUILHO'
}

def custos():
    """
    Retorna um dicionário com as opções de custo disponíveis para consulta.
    Chave e valor são idênticos, possibilitando iteração.
    """
    custos_opcoes = {
        'CUSTO FROTA_REPAROS/CONSERTOS': 'CUSTO FROTA_REPAROS/CONSERTOS',
        'CUSTO FROTA LAVAGEM': 'CUSTO FROTA LAVAGEM',
        'CUSTO FROTA LICENCIAMENTO': 'CUSTO FROTA LICENCIAMENTO',
        'CUSTO FROTA IPVA': 'CUSTO FROTA IPVA',
        'CUSTO FROTA MULTAS DE TRANSITO': 'CUSTO FROTA MULTAS DE TRANSITO',
        'CUSTO PEDAGIO': 'CUSTO PEDAGIO',
        'CUSTO RASTREADOR': 'CUSTO RASTREADOR',
        'CUSTO MOTOBOY TERCEIRIZADO': 'CUSTO MOTOBOY TERCEIRIZADO',
        'CUSTO COMBUSTIVEL': 'CUSTO COMBUSTIVEL',
    }
    return custos_opcoes

def process_data(df: pd.DataFrame, meses_validos: list) -> pd.DataFrame:
    """
    Processa o DataFrame:
      - Converte DATA_REFERENCIA para datetime.
      - Cria a coluna 'MES' formatada como 'YYYY-MM'.
      - Filtra os dados apenas para os meses válidos.
    """
    df = df.copy()
    
    # Converte DATA_REFERENCIA para datetime, tratando erros
    if isinstance(df["DATA_REFERENCIA"].dtype, pd.PeriodDtype):
        df["DATA_REFERENCIA"] = df["DATA_REFERENCIA"].dt.to_timestamp()
    else:
        df["DATA_REFERENCIA"] = pd.to_datetime(df["DATA_REFERENCIA"], errors="coerce")
    
    df["MES"] = df["DATA_REFERENCIA"].dt.strftime('%Y-%m')
    return df[df["MES"].isin(meses_validos)]

def pivot_data(df: pd.DataFrame, meses_validos: list) -> pd.DataFrame:
    """
    Cria uma tabela pivô com os totais mensais por loja.
    Espera que o DataFrame possua as colunas 'LOJA_NOME' e 'TOTAL'.
    """
    pivot = df.pivot(
        index="LOJA_NOME",
        columns="MES",
        values="TOTAL"
    )
    # Reordena as colunas conforme os meses válidos e preenche valores nulos com 0
    pivot = pivot.reindex(columns=meses_validos)
    return pivot.fillna(0).round(2)

def get_cost_data(engine, inicio_str: str, fim_str: str, custo_selecionado: str) -> pd.DataFrame:
    """
    Recupera os dados de custo via API para o período e custo selecionados.
    Retorna um DataFrame com as colunas padronizadas: DATA_REFERENCIA, MES, LOJA, VALOR.
    """
    # CUSTO RASTREADOR
    if custo_selecionado.upper() == "CUSTO RASTREADOR":
        from pages.api_custo_cobli import cobli_api
        df = cobli_api(inicio_str, fim_str)
        if not df.empty:
            if isinstance(df["DATA_REFERENCIA"].dtype, pd.PeriodDtype):
                df["DATA_REFERENCIA"] = df["DATA_REFERENCIA"].dt.to_timestamp()
            else:
                df["DATA_REFERENCIA"] = pd.to_datetime(df["DATA_REFERENCIA"], errors="coerce")
            df["MES"] = df["DATA_REFERENCIA"].dt.strftime("%Y-%m")
            return df[["DATA_REFERENCIA", "MES", "LOJA", "VALOR"]]
        return pd.DataFrame()
    
    # CUSTO FROTA_REPAROS/CONSERTOS
    elif custo_selecionado.upper() == "CUSTO FROTA_REPAROS/CONSERTOS":
        from pages.api_custo_manutencao_frota import custo_frota_loja
        df = custo_frota_loja(inicio_str, fim_str)
        if not df.empty:
            df["VALOR"] = df["VALOR_TOTAL"]
            df["DATA_REFERENCIA"] = df["EMISSAO"].astype(str).apply(lambda x: f"{x}-01")
            df["DATA_REFERENCIA"] = pd.to_datetime(df["DATA_REFERENCIA"], errors="coerce")
            df["LOJA"] = df["LOJA"].astype(int)
            df["MES"] = df["DATA_REFERENCIA"].dt.strftime("%Y-%m")
            return df[["DATA_REFERENCIA", "MES", "LOJA", "VALOR"]]
        return pd.DataFrame()
    
    # CUSTO MOTOBOY TERCEIRIZADO
    elif custo_selecionado.upper() == "CUSTO MOTOBOY TERCEIRIZADO":
        from pages.api_custo_motoboy_tercerizado import calc_custo_motobiy_tercerizado
        df = calc_custo_motobiy_tercerizado(inicio_str, fim_str)
        if not df.empty:
            df["VALOR"] = df["VALOR_TOTAL"]
            df["DATA_REFERENCIA"] = df["EMISSAO"].astype(str).apply(lambda x: f"{x}-01")
            df["DATA_REFERENCIA"] = pd.to_datetime(df["DATA_REFERENCIA"], errors="coerce")
            df["LOJA"] = df["LOJA"].astype(int)
            df["MES"] = df["DATA_REFERENCIA"].dt.strftime("%Y-%m")
            return df[["DATA_REFERENCIA", "MES", "LOJA", "VALOR"]]
        return pd.DataFrame()
    # CUSTO Combustivel
    elif custo_selecionado.upper() == "CUSTO COMBUSTIVEL":
        from pages.api_custo_combustivel import preparar_dados
        df = preparar_dados(inicio_str, fim_str)
        if not df.empty:
            df["VALOR"] = df["VALOR_TOTAL"]
            df["DATA_REFERENCIA"] = df["CADASTRO"].astype(str).apply(lambda x: f"{x}-01")
            df["DATA_REFERENCIA"] = pd.to_datetime(df["DATA_REFERENCIA"], errors="coerce")
            df["LOJA"] = df["LOJA"].astype(int)
            df["MES"] = df["DATA_REFERENCIA"].dt.strftime("%Y-%m")
            return df[["DATA_REFERENCIA", "MES", "LOJA", "VALOR"]]
        return pd.DataFrame()
    # CUSTO PEDAGIO
    elif custo_selecionado.upper() == "CUSTO PEDAGIO":
        from pages.api_custo_pedagio import calcula_custo_pedagio
        df = calcula_custo_pedagio(inicio_str, fim_str)
        if not df.empty:
            df["VALOR"] = df["CUSTO_TOTAL"]
            df["DATA_REFERENCIA"] = df["DATA_UTILIZACAO"].astype(str).apply(lambda x: f"{x}-01")

            df["LOJA"] = df["LOJA_VEICULO"].astype(int)
            df["MES"] = df["DATA_REFERENCIA"].dt.strftime("%Y-%m")
            return df[["DATA_REFERENCIA", "MES", "LOJA", "VALOR"]]
        return pd.DataFrame()
    
    # Caso não seja capturado nenhum caso, retorna DataFrame vazio
    else:
        return pd.DataFrame()

# -----------------------
# Funções de Plotagem
# -----------------------
def plot_grafico(df_plot: pd.DataFrame, titulo: str, y_label: str):
    """
    Cria e retorna um gráfico de barras para os dados fornecidos.
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    df_plot.plot(kind='bar', ax=ax, width=0.8)
    ax.set_title(titulo, fontsize=12)
    ax.set_xlabel("Cidades/Loja")
    ax.set_ylabel(y_label)
    ax.legend(title="Mês", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    return fig

def exibir_bloco(df_block: pd.DataFrame, titulo: str, y_label: str):
    """
    Exibe o bloco de gráficos e a tabela formatada.
    """
    fig = plot_grafico(df_block, titulo, y_label)
    st.pyplot(fig)
    
    st.write(f"**{titulo} - Tabela**")
    df_block = df_block.fillna(0).copy()
    # Formata a tabela: aplica formatação numérica para valores
    df_tabela = df_block.T.apply(lambda col: col.map(lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x))
    st.dataframe(df_tabela)

def plot_total_geral_grafico(df_total: pd.DataFrame, titulo: str, y_label: str):
    """
    Cria e retorna um gráfico de barras para o total geral por loja.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    # Extração dos dados
    labels = df_total.index.tolist()
    valores = df_total.iloc[:, 0].tolist()

    # Paleta de cores sólidas (fortes)
    cmap = plt.colormaps['Set1']  # Set1 = forte e vibrante
    cores = [cmap(i % cmap.N) for i in range(len(valores))]

    # grafico
    bars = ax.bar(labels, valores, color=cores)

    # df_total.plot(kind='bar', ax=ax, legend=False, width=0.8)
    ax.set_title(titulo, fontsize=15)
    ax.set_xlabel("Cidades/Loja")
    ax.set_ylabel(y_label)
    ax.tick_params(axis='x', rotation=45)

    # Exibir valores acima das barras
    for bar in bars:
        altura = bar.get_height()
        texto_formatado = f'{altura:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        ax.text(bar.get_x() + bar.get_width() / 2, altura + altura * 0.01,
                texto_formatado, ha='center', va='bottom', fontsize=14)

    plt.tight_layout()
    return fig

def exibir_total_geral(df_total: pd.DataFrame, titulo: str, y_label: str):
    """
    Exibe o gráfico e a tabela do total geral por loja.
    """
    fig = plot_total_geral_grafico(df_total, titulo, y_label)
    st.pyplot(fig)
    st.write(f"**{titulo} - Tabela**")
    # Pivot da tabela para exibir valores por loja
    df_pivot = df_total.T
    df_pivot_filtrado = df_pivot.loc[:, (df_pivot.iloc[0].notnull()) & (df_pivot.iloc[0] > 0)]
    st.dataframe(df_pivot_filtrado.style.format("{:,.2f}"))

def plot_and_display(df_pivot: pd.DataFrame, meses_validos: list, titulo_base: str, y_label: str):
    """
    Exibe os gráficos e a tabela completa conforme o período selecionado.
    
    Em função do período escolhido pelo usuário, a função seleciona a fatia de dados desejada
    e chama 'exibir_bloco' para renderizar o gráfico e a tabela completa (com valores vazios preenchidos
    com zero).
    """
    n_meses = len(meses_validos)
    if n_meses == 0:
        st.write("Não há meses no intervalo selecionado.")
        return
    
    if df_pivot.values.sum() == 0:
        st.write("Não há valores de custo lançados para o centro de custo deste período.")
    else:
        # Permite que o usuário escolha qual fatia do período deseja visualizar
        periodo_exibicao = st.selectbox(
            "Selecione o período a ser exibido:",
            ["Últimos 6 meses", "Primeiros 6 meses", "Mostrar os 12 meses"],
            key="periodo_select"
        )
        
        if periodo_exibicao == "Últimos 6 meses":
            exibir_bloco(df_pivot.iloc[:, -6:], f"{titulo_base} (Últimos 6 meses)", y_label)
        elif periodo_exibicao == "Primeiros 6 meses":
            exibir_bloco(df_pivot.iloc[:, :6], f"{titulo_base} (Primeiros 6 meses)", y_label)
        else:  # Exibe todos os 12 meses
            st.write("### Primeiros 6 meses")
            exibir_bloco(df_pivot.iloc[:, :6], f"{titulo_base} (Primeiros 6 meses)", y_label)
            st.write("### Últimos 6 meses")
            exibir_bloco(df_pivot.iloc[:, -6:], f"{titulo_base} (Últimos 6 meses)", y_label)

# -----------------------
# 3. Função Principal
# -----------------------
def main():
    """
    Função principal que configura a página, coleta parâmetros via sidebar,
    processa os dados conforme a navegação e exibe os gráficos e tabelas.
    """
    st.set_page_config(page_title="Indicadores de Custo da auto geral", layout="wide")
    
    engine = criar_conexao()
    
    if st.sidebar.button("Voltar"):
        st.switch_page("app.py")
    st.sidebar.write("## Selecione os parâmetros")
    
    # Define a ordem das lojas com base no código numérico
    ordered_lojas = [LOJA_DICT[k] for k in sorted(LOJA_DICT.keys())]
    
    # Navegação por barra com as opções definidas
    navegacao = st.sidebar.radio("Navegação", options=["Ano", "selecione data", "Custo Total por lojas"], key="bar_navegacao")
    
    if navegacao == "Ano":
        # Seleciona o ano (últimos 5 anos)
        ano_atual = datetime.now().year
        anos_disponiveis = list(range(ano_atual, ano_atual - 5, -1))
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos_disponiveis, index=0)

        # Seleciona o custo conforme as opções definidas na função custos()
        custo_selecionado = st.sidebar.selectbox("Selecione o custo", options=list(custos().keys()), index=0)

        # Seletor de meses (multiselect)
        meses_opcoes = obter_meses()
        meses_escolhidos = st.sidebar.multiselect(
            "Selecione os meses para comparar",
            options=meses_opcoes,
            default=[]
        )
        
        if not meses_escolhidos:
            st.warning("Selecione pelo menos um mês para prosseguir.")
            st.stop()
        
        # Determina o menor e o maior mês selecionado
        numeros_meses = [meses_opcoes.index(m) + 1 for m in meses_escolhidos]
        mes_min = min(numeros_meses)
        mes_max = max(numeros_meses)
        
        inicio = datetime(ano_selecionado, mes_min, 1, 0, 0, 0)
        ultimo_dia = calendar.monthrange(ano_selecionado, mes_max)[1]
        fim = datetime(ano_selecionado, mes_max, ultimo_dia, 23, 59, 59)
        
        inicio_str = inicio.strftime("%Y-%m-%d %H:%M:%S")
        fim_str = fim.strftime("%Y-%m-%d %H:%M:%S")
        df_raw = get_cost_data(engine, inicio_str, fim_str, custo_selecionado)
        
        # Cria a lista de meses válidos no formato 'YYYY-MM'
        meses_validos = [f"{ano_selecionado}-{m:02d}" for m in sorted(numeros_meses)]
    
    elif navegacao == "selecione data":
        # Seleção de datas via calendário
        data_inicio = st.sidebar.date_input("Data de início", value=(date.today() - timedelta(days=180)))
        data_fim = st.sidebar.date_input("Data de fim", value=date.today())

        # Seleciona o custo
        custo_selecionado = st.sidebar.selectbox("Selecione o custo", options=list(custos().keys()), index=0)
                    
        if data_inicio > data_fim:
            st.error("A data de início deve ser anterior à data de fim.")
            st.stop()
        
        inicio_str = data_inicio.strftime("%Y-%m-%d 00:00:00")
        fim_str = data_fim.strftime("%Y-%m-%d 23:59:59")
        df_raw = get_cost_data(engine, inicio_str, fim_str, custo_selecionado)
        
        # Gera a lista de meses válidos para o período selecionado
        meses_validos = []
        current = data_inicio.replace(day=1)
        while current <= data_fim:
            meses_validos.append(current.strftime("%Y-%m"))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    
    elif navegacao == "Custo Total por lojas":
        # Seleção de datas via calendário para total geral por lojas
        data_inicio = st.sidebar.date_input("Data de início", value=(date.today() - timedelta(days=180)))
        data_fim = st.sidebar.date_input("Data de fim", value=date.today())
        if data_inicio > data_fim:
            st.error("A data de início deve ser anterior à data de fim.")
            st.stop()
        inicio_str = data_inicio.strftime("%Y-%m-%d 00:00:00")
        fim_str = data_fim.strftime("%Y-%m-%d 23:59:59")
        
        # Cria a lista de meses válidos para o período selecionado
        meses_validos = []
        current = data_inicio.replace(day=1)
        while current <= data_fim:
            meses_validos.append(current.strftime("%Y-%m"))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        # Obtém o dicionário de custos disponíveis
        custos_opcoes = custos()
        # Dicionário para armazenar os dados somados de cada custo por loja
        dict_custos = {}

        # Loop sobre cada opção de custo
        for custo_nome in custos_opcoes:
            df_raw = get_cost_data(engine, inicio_str, fim_str, custo_nome)
            if df_raw.empty:
                continue
            # Processa os dados para filtrar os meses e padronizar datas
            df_proc = process_data(df_raw, meses_validos)
            # Mapeia o código da loja para o nome e renomeia a coluna de valor para TOTAL
            df_proc["LOJA"] = df_proc["LOJA"].astype(int)
            df_proc["LOJA_NOME"] = df_proc["LOJA"].map(LOJA_DICT)
            df_proc = df_proc.rename(columns={"VALOR": "TOTAL"})
            # Se necessário, agrupa por LOJA_NOME para somar os custos (caso hajam múltiplas linhas)
            df_sum = df_proc.groupby("LOJA_NOME", observed=False)["TOTAL"].sum().reset_index()
            dict_custos[custo_nome] = df_sum

        if not dict_custos:
            st.warning("Nenhum dado encontrado para o período selecionado e os custos disponíveis.")
            return

        # Combina os totais de todos os custos por loja
        df_total = None
        for df_sum in dict_custos.values():
            if df_total is None:
                df_total = df_sum.copy()
            else:
                # Faz a junção dos DataFrames e soma os valores
                df_total = pd.merge(df_total, df_sum, on="LOJA_NOME", how="outer", suffixes=('', '_new'))
                df_total["TOTAL"] = df_total["TOTAL"].fillna(0) + df_total["TOTAL_new"].fillna(0)
                df_total.drop(columns=["TOTAL_new"], inplace=True)

        df_total = df_total.set_index("LOJA_NOME").reindex(ordered_lojas).fillna(0)
        st.write("# Custo Total por Loja")
        st.write("### Os custos somados foram:")
        for custo_nome in dict_custos:
            st.write(f"- {custo_nome}")
        exibir_total_geral(df_total, "Custo Total por Loja", "Valor Total")
        return  # Interrompe o fluxo para não executar o restante do código
    
    # Para as opções "Ano" e "selecione data", processa os dados retornados pela API
    if df_raw.empty:
        st.warning("Nenhum valor cadastrado para o centro de custo selecionado.")
        return

    # Processa os dados e padroniza a coluna de loja e total
    df_process = process_data(df_raw, meses_validos)
    df_process["LOJA"] = df_process["LOJA"].astype(int)
    df_process["LOJA_NOME"] = df_process["LOJA"].map(LOJA_DICT)
    df_agg = df_process.rename(columns={"VALOR": "TOTAL"})
    
    # Cria a tabela pivô para o gráfico mensal (Centro de custo) e reordena as lojas
    df_pivot_entrega40 = pivot_data(df_agg, meses_validos)
    df_pivot_entrega40 = df_pivot_entrega40.reindex(ordered_lojas).fillna(0)
    
    # Calcula o total geral por loja para o período selecionado e reordena conforme a ordem definida
    df_total_geral = df_agg.groupby("LOJA_NOME", observed=False)["TOTAL"].sum().reset_index()
    df_total_geral = df_total_geral.set_index("LOJA_NOME").reindex(ordered_lojas).fillna(0)
    
    st.title("Indicadores Centro de custo")
    
    if df_pivot_entrega40.values.sum() > 0:
        st.header("1. Centro de custo selecionado - total")
        plot_and_display(df_pivot_entrega40, meses_validos, "Centro de custo", "Valor total do custo")
        st.header("2. Total Centro de custo Anual")
        exibir_total_geral(df_total_geral, "Total Anual", "Valor total do custo")
    else:
        st.header("1. Total de custo Anual")
        exibir_total_geral(df_total_geral, "Total Anual", "Valor total do custo")
    
if __name__ == "__main__":
    main()


# Atualiza o codigo 
