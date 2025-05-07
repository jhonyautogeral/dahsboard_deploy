import pandas as pd
from sqlalchemy import create_engine
import streamlit as st

def criar_conexao():
    try:
        config = st.secrets["connections"]["mysql"]
        url = f"{config['dialect']}://{config['username']}:{config['password']}@" \
              f"{config['host']}:{config['port']}/{config['database']}"
        return create_engine(url)
    except Exception as e:
        st.error(f"Erro ao criar conexão com o banco de dados: {e}")
        return None

def query_motoboy_tercerizado(inicio_str,fim_str):
    query = f"""
    SELECT C.LOJA, C.EMISSAO,C.OPERACAO_DESCRICAO, CC.DESCRICAO AS CENTRO_CUSTO, 
	C.VALOR_TOTAL_NOTA
    FROM compras_dbf AS C LEFT JOIN centros_custo CC ON C.CENTRO_CUSTO_CODIGO=CC.CODIGO
    WHERE C.LOJA IN (1,2,3,4,5,6,7,8,9,10,11,12,13)
	AND CC.DESCRICAO LIKE ('DESPESAS COM ENTREGAS (MOTOBOY TERCEIRIZADO)')
	AND C.CADASTRO BETWEEN '{inicio_str}' AND '{fim_str}';
    """
    return query

def calc_custo_motobiy_tercerizado(inicio_str,fim_str):

    try:
        engine = criar_conexao()
        if engine is None:
            st.warning("Erro ao estabelecer conexão com banco de dados!.")
            return pd.DataFrame()
        query = query_motoboy_tercerizado(inicio_str, fim_str)
        df = pd.read_sql(query, engine)
        if df.empty:
            st.warning("Nenhum dado encontrado para o intervalo de datas fornecido.")
            return df
        df['EMISSAO'] = pd.to_datetime(df['EMISSAO']).dt.to_period('M')

        df.rename(columns={'VALOR_TOTAL_NOTA': 'VALOR_TOTAL'}, inplace=True)

        df_custo_somado = df.groupby(['LOJA', 'EMISSAO'], as_index=False)['VALOR_TOTAL'].sum()
        # converter duas casas decimais
        # df_custo_somado['VALOR_TOTAL'] = df_custo_somado['VALOR_TOTAL'].round(2)
            
        return df_custo_somado
    except Exception as e:
        st.error(f"Erro ao processar custos motoboy tercerizado: {e}")
        return pd.DataFrame()
    
# engine = criar_conexao()
# df_resultado = calc_custo_motobiy_tercerizado('2024-01-01', '2024-12-31')
# print(df_resultado)