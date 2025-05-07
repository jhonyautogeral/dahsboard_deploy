import pandas as pd
from sqlalchemy import create_engine
import streamlit as st
def criar_conexao():
    """
    Cria e retorna uma conexão com o banco de dados MySQL.
    """
    config = st.secrets["connections"]["mysql"]
    url = (f"{config['dialect']}://{config['username']}:{config['password']}@"
           f"{config['host']}:{config['port']}/{config['database']}")
    return create_engine(url)

def consulta_custo_cobustivel(str_inicio,str_fim,engine):
    """
    Consulta os custos de combustíveis entre duas datas.
    """
    query = f"""
    SELECT K.CADASTRO, K.LOJA, V.PLACA, K.CADASTRO_LOJA, C.NOME AS POSTO, K.COMBUSTIVEL_1_LITROS,
        K.VALOR_TOTAL, K.KM, CV.TIPO, K.CADA_VEIC_ID
    FROM 
        cadastros_veiculos_abastecimentos K JOIN cadastros_veiculos V ON K.CADA_VEIC_ID=V.CADA_VEIC_ID
        LEFT JOIN cadastros_veiculos CV ON V.CADA_VEIC_ID = CV.CADA_VEIC_ID
        LEFT JOIN cadastros C ON K.CADASTRO_CODIGO=C.CODIGO AND K.CADASTRO_LOJA=C.LOJA
    WHERE 
        K.CADASTRO BETWEEN '{str_inicio}' AND '{str_fim}'
        AND K.CADASTRO_LOJA IN (1,2,3,4,5,6,7,8,9,10,11,12,13)
    ORDER BY K.CADASTRO, K.LOJA;
    """
    return pd.read_sql_query(query, engine)

def preparar_dados(str_inicio,str_fim,):
    """
    Prepara os dados para análise, incluindo conversão de tipos e agregação.
    """
    df = consulta_custo_cobustivel(str_inicio,str_fim,criar_conexao())
    # Converter a coluna CADASTRO para datetime
    df['CADASTRO'] = pd.to_datetime(df['CADASTRO'], errors='coerce').dt.to_period('M')

    # Limpar coluna PLACA removendo espaços em branco e caracteres especiais
    df['PLACA'] = df['PLACA'].str.replace(r'\s+', '', regex=True).str.replace(r'[^A-Za-z0-9]', '', regex=True)
    
    # # Agrupar por CADASTRO, loja, placa, TIPO e somar COMBUSTIVEL_1_LITROS, VALOR_TOTAL e KM
    # df = df.groupby(['CADASTRO','PLACA','LOJA','TIPO']).agg({'VALOR_TOTAL': 'sum' }).reset_index()
    df_custo_somado = df.groupby(['LOJA', 'CADASTRO'], as_index=False)['VALOR_TOTAL'].sum()

    # Retornar um dataframe com os dados preparados
    # df = df.rename(columns={'CADASTRO': 'DATA', 'COMBUSTIVEL_1_LITROS': 'LITROS', 'VALOR_TOTAL': 'VALOR', 'KM': 'KM'})

    return df_custo_somado
