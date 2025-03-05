import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import calendar
from datetime import datetime, timedelta
from sqlalchemy import create_engine

pd.set_option('future.no_silent_downcasting', True)
# -----------------------
# Proteção de acesso
# -----------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()
# -----------------------
# 1. Conexão com Banco
# -----------------------
def criar_conexao():
    """Cria e retorna a conexão com o banco de dados."""
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@" \
          f"{config['host']}:{config['port']}/{config['database']}"
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

def gerar_query_dados(inicio_str: str, fim_str: str) -> str:
    return f"""
        SELECT a.expedicao, r.ROMANEIO, a.LOJA, a.CADASTRO,
               d.DESCRICAO AS Entregador,
               a.KM_RETORNO - a.KM_SAIDA AS KMS,
               a.ROTA_METROS,
               a.HORA_SAIDA, a.HORA_RETORNO,
               r.TERMINO_SEPARACAO,
               TIMESTAMPDIFF(MINUTE, r.CADASTRO, r.TERMINO_SEPARACAO) AS MINUTOS_DE_SEPARACAO,
               IF(24*60*60 >= (IF(a.HORA_SAIDA < a.HORA_RETORNO,
                                  TIMEDIFF(a.HORA_RETORNO, a.HORA_SAIDA),
                                  TIMEDIFF(a.HORA_SAIDA, a.HORA_RETORNO))),
                  IF(a.HORA_SAIDA < a.HORA_RETORNO,
                     TIMEDIFF(a.HORA_RETORNO, a.HORA_SAIDA),
                     TIMEDIFF(a.HORA_SAIDA, a.HORA_RETORNO)),
                  '23:59:59') AS TEMPO_MARCACAO,
               IF(a.ROTA_TEMPO > 24*60*60, '23:59:59', SEC_TO_TIME(a.ROTA_TEMPO)) AS TEMPO_ROTEAMENTO,
               a.ROTA_TEMPO,
               ((TIME_TO_SEC(a.HORA_RETORNO) - TIME_TO_SEC(a.HORA_SAIDA)) / a.ROTA_TEMPO) AS DIFERENCA_TEMPO,
               r.CADASTRO AS HORA_ROMANEIO,
               TIMEDIFF(e.ROTA_HORARIO_REALIZADO, r.CADASTRO) AS TEMPO_ENTREGA,
               TIMESTAMPDIFF(MINUTE, r.CADASTRO, e.ROTA_HORARIO_REALIZADO) AS MINUTOS_ENTREGA,
               e.ROTA_STATUS,
               e.ROTA_HORARIO_PREVISTO,
               e.ROTA_HORARIO_REALIZADO,
               TIMESTAMPDIFF(MINUTE, a.HORA_SAIDA, e.ROTA_HORARIO_REALIZADO) AS MINUTOS_ENTREGA_REALIZADA
        FROM expedicao_itens e
        JOIN expedicao a ON e.EXPEDICAO_CODIGO = a.EXPEDICAO AND e.EXPEDICAO_LOJA = a.LOJA
        JOIN cadastros_veiculos b ON a.cada_veic_id = b.cada_veic_id
        JOIN produto_veiculo c ON b.veiculo_codigo = c.codigo
        JOIN entregador d ON a.ENTREGADOR_CODIGO = d.CODIGO
        LEFT JOIN romaneios_dbf r ON e.VENDA_TIPO = 'ROMANEIO'
             AND e.CODIGO_VENDA = r.ROMANEIO AND e.LOJA_VENDA = r.LOJA
        WHERE a.ROTA_METROS IS NOT NULL
          AND a.LOJA IN (1,2,3,4,5,6,7,8,9,10,11,12,13)
          AND r.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}';
    """

def process_data(df: pd.DataFrame, meses_validos: list) -> pd.DataFrame:
    df["CADASTRO"] = pd.to_datetime(df["CADASTRO"])
    df["MES"] = df["CADASTRO"].dt.strftime('%Y-%m')
    return df[df["MES"].isin(meses_validos)]

def aggregate_data(df: pd.DataFrame) -> pd.DataFrame:

    # Agrega os dados agrupando por MES e LOJA. Calcula:
    #   - TOTAL_ENTREGAS: total de entregas (count de MINUTOS_ENTREGA)
    #   - Entrega_40: quantidade de entregas com MINUTOS_ENTREGA <= 40
    #   - PORCENTAGEM_ENTREGA_40: (Entrega_40/TOTAL_ENTREGAS)*100
    #   - PORCENTAGEM_TOTAL_ENTREGAS: percentual de TOTAL_ENTREGAS da loja em relação ao total do mês

    filtro = df[df["ROTA_STATUS"] == "ENTREGUE"].copy()
    agrupado = filtro.groupby(["MES", "LOJA"]).agg(
        TOTAL_ENTREGAS=("MINUTOS_ENTREGA", "count"),
        Entrega_40=("MINUTOS_ENTREGA", lambda x: (x <= 40).sum())
    ).reset_index()
    
    agrupado["PORCENTAGEM_ENTREGA_40"] = (agrupado["Entrega_40"] / agrupado["TOTAL_ENTREGAS"]) * 100
    
    # Calcula o total de entregas por mês e, em seguida, o percentual de cada loja
    agrupado["TOTAL_DELIVERIES_MES"] = agrupado.groupby("MES")["TOTAL_ENTREGAS"].transform("sum")
    agrupado["PORCENTAGEM_TOTAL_ENTREGAS"] = (agrupado["TOTAL_ENTREGAS"] / agrupado["TOTAL_DELIVERIES_MES"]) * 100

    agrupado["LOJA"] = agrupado["LOJA"].astype(int)
    agrupado["LOJA_NOME"] = agrupado["LOJA"].map(LOJA_DICT)
    return agrupado

def pivot_data(agrupado: pd.DataFrame, meses_validos: list) -> pd.DataFrame:

    # Cria a tabela pivô para PORCENTAGEM_ENTREGA_40 com
    # index = LOJA_NOME e columns = MES.

    pivot = agrupado.pivot(
        index="LOJA_NOME",
        columns="MES",
        values="PORCENTAGEM_ENTREGA_40"
    )
    pivot = pivot.reindex(columns=meses_validos)
    return pivot.fillna(0).round(2)

def pivot_total_data(agrupado: pd.DataFrame, meses_validos: list) -> pd.DataFrame:
 
    # Cria a tabela pivô para PORCENTAGEM_TOTAL_ENTREGAS com
    # index = LOJA_NOME e columns = MES.

    pivot = agrupado.pivot(
        index="LOJA_NOME",
        columns="MES",
        values="PORCENTAGEM_TOTAL_ENTREGAS"
    )
    pivot = pivot.reindex(columns=meses_validos)
    return pivot.fillna(0).round(2)

# -----------------------
# Funções de Plotagem
# -----------------------
def plot_grafico(df_plot: pd.DataFrame, titulo: str, y_label: str):
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

    fig = plot_grafico(df_block, titulo, y_label)
    st.pyplot(fig)
    
    st.write(f"**{titulo} - Tabela**")
    df_tabela = df_block.T.applymap(lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x)
    st.dataframe(df_tabela)

def plot_and_display(df_pivot: pd.DataFrame, meses_validos: list, titulo_base: str, y_label: str):
    n_meses = len(meses_validos)
    if n_meses == 0:
        st.write("Não há meses no intervalo selecionado.")
        return
    
    if n_meses <= 6:
        exibir_bloco(df_pivot, f"{titulo_base} ({n_meses} meses)", y_label)
    else:
        primeiro_bloco = df_pivot[meses_validos[:6]]
        segundo_bloco = df_pivot[meses_validos[6:]]
        
        exibir_bloco(primeiro_bloco, f"{titulo_base} (Primeiros 6 meses)", y_label)
        exibir_bloco(segundo_bloco, f"{titulo_base} (Meses 7 a {n_meses})", y_label)

# -----------------------
# 3. Função Principal
# -----------------------
def main():
    st.set_page_config(page_title="Indicadores de Entregas", layout="wide")
    
    engine = criar_conexao()
    
    st.sidebar.write("## Selecione os parâmetros")
    if st.sidebar.button("Voltar"):
        st.experimental_set_query_params(page="page1.py")
        st.experimental_rerun()
    
    # Seletor de ano (últimos 5 anos)
    ano_atual = datetime.now().year
    anos_disponiveis = list(range(ano_atual, ano_atual-5, -1))
    ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos_disponiveis, index=0)
    
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
    
    numeros_meses = [meses_opcoes.index(m) + 1 for m in meses_escolhidos]
    mes_min = min(numeros_meses)
    mes_max = max(numeros_meses)
    
    inicio = datetime(ano_selecionado, mes_min, 1, 0, 0, 0)
    ultimo_dia = calendar.monthrange(ano_selecionado, mes_max)[1]
    fim = datetime(ano_selecionado, mes_max, ultimo_dia, 23, 59, 59)
    
    inicio_str = inicio.strftime("%Y-%m-%d %H:%M:%S")
    fim_str = fim.strftime("%Y-%m-%d %H:%M:%S")
    query = gerar_query_dados(inicio_str, fim_str)
    df_raw = executar_query(engine, query)
    
    if df_raw.empty:
        st.error("Nenhum dado retornado da consulta.")
        return
    
    # Cria a lista de meses no formato 'YYYY-MM' para cada mês selecionado
    meses_validos = [f"{ano_selecionado}-{m:02d}" for m in sorted(numeros_meses)]
    
    df_process = process_data(df_raw, meses_validos)
    df_agg = aggregate_data(df_process)
    
    # Cria os pivôs para cada indicador
    df_pivot_entrega40 = pivot_data(df_agg, meses_validos)
    df_pivot_total = pivot_total_data(df_agg, meses_validos)
    
    st.title("Indicadores de Entregas")
    
    st.header("1. Porcentagem de Entregas em até 40 minutos")
    plot_and_display(df_pivot_entrega40, meses_validos,
                     "Entregas em menos de 40 minutos", "Porcentagem de entregas ≤ 40 min")
    
    st.header("2. Porcentagem do Total de Entregas por Loja")
    plot_and_display(df_pivot_total, meses_validos,
                     "Contribuição de cada loja no total de entregas", "Porcentagem do total de entregas")

if __name__ == "__main__":
    main()
