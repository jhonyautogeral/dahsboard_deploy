# cobli_api.py

import requests
import pandas as pd
import io
import datetime
from sqlalchemy import create_engine
import warnings
import streamlit as st

# Corrige warnings do openpyxl
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl.styles.stylesheet")

# Constantes de configuração da API COBLI
CHAVE_API = st.secrets["cobli"]["key"]
URL_BASE = "https://api.cobli.co/herbie-1.1/costs/report"
FUSO_HORARIO = "America/Sao_Paulo"

def buscar_dados_por_periodo(data_inicio: datetime.datetime, data_fim: datetime.datetime, fuso=FUSO_HORARIO) -> pd.DataFrame:
    """
    Obtém os dados da API para um período específico.
    """
    try:
        inicio_ms = int(data_inicio.timestamp() * 1000)
        fim_ms = int(data_fim.timestamp() * 1000)
        url = f"{URL_BASE}?begin={inicio_ms}&end={fim_ms}&tz={fuso}"
        cabecalhos = {
            "accept": "text/csv",
            "cobli-api-key": CHAVE_API
        }
        resposta = requests.get(url, headers=cabecalhos)
        resposta.raise_for_status()
    except requests.RequestException as erro:
        st.error(f"Erro ao buscar dados na API COBLI: {erro}")
        return pd.DataFrame()
    
    try:
        arquivo = io.BytesIO(resposta.content)
        df = pd.read_excel(arquivo, engine="openpyxl")
        return df
    except Exception as erro:
        st.error(f"Erro ao ler o arquivo Excel da API COBLI: {erro}")
        return pd.DataFrame()

def obter_intervalos_mensais(inicio_periodo: datetime.datetime, fim_periodo: datetime.datetime) -> list:
    """
    Gera uma lista de tuplas (data_inicio, data_fim) para cada mês dentro do período informado.
    """
    intervalos = []
    atual = inicio_periodo
    while atual <= fim_periodo:
        data_inicio = atual.replace(day=1)
        # Calcula o primeiro dia do mês seguinte
        if atual.month == 12:
            proximo_mes = atual.replace(year=atual.year + 1, month=1, day=1)
        else:
            proximo_mes = atual.replace(month=atual.month + 1, day=1)
        data_fim = proximo_mes - datetime.timedelta(seconds=1)
        if data_fim > fim_periodo:
            data_fim = fim_periodo
        intervalos.append((data_inicio, data_fim))
        atual = proximo_mes
    return intervalos

def processar_dados(df: pd.DataFrame, inicio_periodo: datetime.datetime, fim_periodo: datetime.datetime) -> pd.DataFrame:
    """
    Processa o DataFrame:
    - Verifica se o primeiro registro contém mensagem de aviso e o descarta se necessário.
    - Filtra os registros para o período informado.
    - Converte a coluna 'Dia' para datetime e gera a coluna 'Mes'.
    - Agrupa por 'Mes' e 'Placa'.
    - Chama a função de concatenação com os dados do banco.
    """
    if df.empty:
        return df

    colunas_necessarias = ['Dia', 'Placa']
    if not all(col in df.columns for col in colunas_necessarias):
        st.error("Colunas necessárias não encontradas no DataFrame da API COBLI.")
        return pd.DataFrame()

    if isinstance(df.iloc[0]['Dia'], str) and "Não há gastos" in df.iloc[0]['Dia']:
        df = df.iloc[1:].copy()
    
    df['Dia'] = pd.to_datetime(df['Dia'], errors='coerce')
    df = df.dropna(subset=['Dia'])
    
    # Filtra os registros dentro do período definido
    df = df[(df['Dia'] >= inicio_periodo) & (df['Dia'] <= fim_periodo)]
    
    # Converte a data para período mensal (formato 'YYYY-MM')
    df['Mes'] = df['Dia'].dt.to_period('M')
    df_agrupado = df.groupby(['Mes', 'Placa']).size().reset_index(name='QUANTIDADE')
    df_agrupado = df_agrupado.rename(columns={'Mes': 'DATA'})
    
    return concatenar_dados_com_banco(df_agrupado)

def concatenar_dados_com_banco(df_agrupado: pd.DataFrame) -> pd.DataFrame:
    """
    Concatena os dados processados com os dados do banco de dados.
    Realiza o join entre as placas obtidas via API e as placas cadastradas no banco.
    Em seguida, agrupa por loja e data e calcula o custo total multiplicando a quantidade por 69,90.
    """
    def criar_conexao():
        """Cria e retorna a conexão com o banco de dados."""
        config = st.secrets["connections"]["mysql"]
        url = f"{config['dialect']}://{config['username']}:{config['password']}@" \
            f"{config['host']}:{config['port']}/{config['database']}"
        return create_engine(url)

    query = "SELECT cv.LOJA, cv.PLACA FROM cadastros_veiculos_ultilizacao cv;"
    try:
        engine = criar_conexao()
        df_banco = pd.read_sql_query(query, engine)
    except Exception as e:
        st.error(f"Erro ao conectar ao banco na função COBLI: {e}")
        return pd.DataFrame()

    df_final = pd.merge(df_agrupado, df_banco, how="inner", left_on="Placa", right_on="PLACA")
    df_final = df_final.drop(columns=['PLACA'])
    df_final = df_final.groupby(['LOJA', 'DATA']).size().reset_index(name='QUANTIDADE')

    # a partir de 2024-08, o custo por rastreagor cobli é de 73,05, antes disso era 69,90
    data_corte = pd.Period('2024-08')
    df_final['QUANTIDADE'] = df_final.apply(
        lambda row: row['QUANTIDADE'] * 73.05 if row['DATA'] >= data_corte else row['QUANTIDADE'] * 69.90, 
        axis=1
    )
    
    df_final['QUANTIDADE'] = df_final['QUANTIDADE'].round(2)
    df_final = df_final.sort_values(by=['LOJA', 'DATA'])
    return df_final

def cobli_api(inicio_str: str, fim_str: str) -> pd.DataFrame:
    """
    Integra com a API COBLI, buscando os dados por intervalos mensais,
    processa-os e retorna um DataFrame final.
    
    Args:
        inicio_str (str): Data de início no formato "YYYY-MM-DD HH:MM:SS"
        fim_str (str): Data de fim no formato "YYYY-MM-DD HH:MM:SS"
        
    Returns:
        pd.DataFrame: DataFrame final processado com os dados da API COBLI.
    """
    # Converter as strings para objetos datetime
    inicio_periodo = datetime.datetime.strptime(inicio_str, "%Y-%m-%d %H:%M:%S")
    fim_periodo = datetime.datetime.strptime(fim_str, "%Y-%m-%d %H:%M:%S")
    
    intervalos = obter_intervalos_mensais(inicio_periodo, fim_periodo)
    df_final = pd.DataFrame()
    
    status_container = st.empty()
    for data_inicio, data_fim in intervalos:
        status_container.text(f"Buscando dados de {data_inicio.date()} até {data_fim.date()} na API COBLI...")
        df_mensal = buscar_dados_por_periodo(data_inicio, data_fim)
        df_final = pd.concat([df_final, df_mensal], ignore_index=True)
    status_container = st.empty()
    st.write("Dados concatenados da API COBLI:", df_final.shape)
    df_processado = processar_dados(df_final, inicio_periodo, fim_periodo)
    
    # Renomeando as colunas para adequar o DataFrame ao esperado pelo centro_custo
    df_processado = df_processado.rename(columns={'DATA': 'DATA_REFERENCIA', 'QUANTIDADE': 'VALOR'})

    #  Corrigir tipo de DATA_REFERENCIA 
    if pd.api.types.is_period_dtype(df_processado["DATA_REFERENCIA"].dtype):
        df_processado["DATA_REFERENCIA"] = df_processado["DATA_REFERENCIA"].dt.to_timestamp()

    return df_processado

