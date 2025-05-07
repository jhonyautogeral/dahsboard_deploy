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

def calcula_custo_pedagio(str_inicio,str_fim):
    query = f"""
            SELECT 
                LOJA_VEICULO,
                DATA_ULTILIZADA,
                SUM(CUSTO) AS CUSTO_TOTAL
            FROM (
                -- Origem: Veloe
                SELECT 
                    cv.LOJA AS LOJA_VEICULO, 
                    ve.data_utilizacao AS DATA_ULTILIZACAO
                    ve.valor_cobrado AS CUSTO
                FROM cadastros_veiculos_ultilizacao cv
                LEFT JOIN veloe_extrato ve ON cv.PLACA = ve.placa
                WHERE ve.data_utilizacao BETWEEN '{str_inicio}' AND '{str_fim}'
                UNION ALL
                -- Origem: Despesas
                SELECT 
                    D.LOJA AS LOJA_VEICULO,
                    D.VENCIMENTO AS DATA_ULTILIZADA,
                    D.VALOR AS CUSTO
                FROM despesas D 
                LEFT JOIN centros_custo CC ON D.CENTRO_CUSTO_CODIGO = CC.CODIGO 
                WHERE D.VENCIMENTO BETWEEN '{str_inicio}' AND '{str_fim}'
                AND CC.DESCRICAO = 'PEDAGIO'
            ) AS subquery
            GROUP BY LOJA_VEICULO, DATA_ULTILIZADA
            ORDER BY LOJA_VEICULO, DATA_ULTILIZADA;
    """
    df = pd.read_sql(query, criar_conexao())
    # converter Emissao para datetime e extrair o ano e mês
    df['DATA_ULTILIZACAO'] = pd.to_datetime(df['DATA_ULTILIZACAO']).dt.to_period('M')

    

    return df

# tabela = calcula_custo_pedagio(criar_conexao())
# display(tabela)


