import re
import pandas as pd
from sqlalchemy import create_engine
import streamlit as st

def criar_conexao():
    """
    Cria uma conexão com o banco de dados MySQL usando configurações do Streamlit Secrets.

    Returns:
        sqlalchemy.engine.base.Engine or None: Objeto de conexão com o banco ou None em caso de erro.
    """
    try:
        config = st.secrets["connections"]["mysql"]
        url = f"{config['dialect']}://{config['username']}:{config['password']}@" \
              f"{config['host']}:{config['port']}/{config['database']}"
        return create_engine(url)
    except Exception as e:
        st.error(f"Erro ao criar conexão com o banco de dados: {e}")
        return None


def listar_placas(engine):
    """
    Consulta placas de veículos do tipo 'MOTO' ou 'CARRO' no banco de dados.

    Args:
        engine (sqlalchemy.engine.base.Engine): Conexão com o banco de dados.

    Returns:
        pandas.DataFrame: DataFrame contendo as placas únicas encontradas.
    """
    query = """
    SELECT cv.PLACA 
    FROM cadastros_veiculos AS cv
    WHERE cv.TIPO IN ('MOTO','CARRO')
    ORDER BY cv.CADASTRO_CODIGO;
    """
    lista_de_placas = pd.read_sql(query, engine)
    placas = lista_de_placas.drop_duplicates()
    return placas


def consulta_nfe_bd(inicio_str, fim_str):
    """
    Gera a query SQL para buscar notas fiscais dentro de um intervalo de datas.

    Args:
        inicio_str (str): Data inicial no formato 'YYYY-MM-DD'.
        fim_str (str): Data final no formato 'YYYY-MM-DD'.

    Returns:
        str: Query SQL para execução.
    """
    return f"""
    SELECT N.LOJA, N.EMISSAO, N.OPERACAO_DESCRICAO, N.VALOR_TOTAL, N.OBS   
    FROM nfes AS N 
    LEFT JOIN vendas V ON (V.TIPO='NFE' AND N.NFE=V.CODIGO AND N.LOJA=V.LOJA)
    WHERE N.EMISSAO BETWEEN '{inicio_str}' AND '{fim_str}'
        AND N.OPERACAO_DESCRICAO LIKE 'LANCAMENTO EFETUADO A TITULO DE BAIXA DE ESTOQUE (CONSUMO)'
        AND N.LOJA IN (1,2,3,4,5,6,7,8,9,10,11,12,13)
        AND N.SITUACAO = 'NORMAL'
    ORDER BY N.LOJA, N.EMISSAO;
    """


def consulta_pedidos_bd(inicio_str, fim_str):
    """
    Gera a query SQL para buscar pedidos vinculados a centro de custo da frota.

    Args:
        inicio_str (str): Data inicial no formato 'YYYY-MM-DD'.
        fim_str (str): Data final no formato 'YYYY-MM-DD'.

    Returns:
        str: Query SQL para execução.
    """
    return f"""
    SELECT 
        P.LOJA, P.EMISSAO, P.OPERACAO_DESCRICAO, P.VALOR_TOTAL, P.OBS, 
        A.DESCRICAO AS CENTRO_CUSTO
    FROM pedidos_dbf AS P
    LEFT JOIN vendas V ON V.TIPO = 'PEDIDO' AND P.PEDIDO = V.CODIGO AND P.LOJA = V.LOJA
    LEFT JOIN cadastros C ON P.CADASTRO_CODIGO = C.CODIGO AND P.CADASTRO_LOJA = C.LOJA
    LEFT JOIN centros_custo A ON P.CENTRO_CUSTO_CODIGO = A.CODIGO
    WHERE 
        P.EMISSAO BETWEEN '{inicio_str}' AND '{fim_str}'
        AND P.OPERACAO_DESCRICAO = 'BAIXA PARA CONSUMO'
        AND A.DESCRICAO = 'FROTA REPAROS/CONSERTOS'
        AND P.LOJA IN (1,2,3,4,5,6,7,8,9,10,11,12,13)
        AND P.SITUACAO = 'NORMAL'
    ORDER BY LOJA, P.EMISSAO;
    """


def calc_pedidos(inicio_str, fim_str):
    """
    Consulta e agrega os valores totais dos pedidos da frota por loja e mês.

    Args:
        inicio_str (str): Data inicial no formato 'YYYY-MM-DD'.
        fim_str (str): Data final no formato 'YYYY-MM-DD'.

    Returns:
        pandas.DataFrame: DataFrame com LOJA, EMISSAO (mensal) e soma dos VALOR_TOTAL.
    """
    try:
        engine = criar_conexao()
        if engine is None:
            return pd.DataFrame()
        query = consulta_pedidos_bd(inicio_str, fim_str)
        df = pd.read_sql(query, engine)
        if df.empty:
            st.warning("Nenhum dado encontrado para o intervalo de datas fornecido.")
            return df
        df['EMISSAO'] = pd.to_datetime(df['EMISSAO']).dt.to_period('M')
        return df.groupby(['LOJA', 'EMISSAO'], as_index=False)['VALOR_TOTAL'].sum()
    except Exception as e:
        st.error(f"Erro ao processar custos da frota: {e}")
        return pd.DataFrame()


def limpa_texto(placa):
    """
    Remove caracteres especiais e espaços, deixando apenas letras maiúsculas e números.

    Args:
        placa (str): Texto a ser limpo (geralmente uma placa de veículo).

    Returns:
        str: Texto normalizado contendo apenas letras e números maiúsculos.
    """
    return re.sub(r'[^A-Z0-9]', '', placa.upper())


def extrair_placas(texto, placas_set):
    """
    Extrai placas presentes no texto comparando com um conjunto de placas normalizadas.

    Args:
        texto (str): Texto a ser analisado (ex: coluna OBS).
        placas_set (set): Conjunto de placas já normalizadas.

    Returns:
        list: Lista de placas encontradas no texto.
    """
    if pd.isna(texto):
        return []
    texto_normalizado = limpa_texto(texto)
    return [placa for placa in placas_set if placa in texto_normalizado]


def custo_frota_loja(inicio_str, fim_str):
    """
    Calcula o custo total da frota por loja e mês, com base nas NFEs e pedidos que referenciam placas.

    - Filtra e normaliza placas.
    - Compara com a coluna OBS das NFEs para identificar associação com veículos.
    - Agrega os valores totais por mês e loja.

    Args:
        inicio_str (str): Data inicial no formato 'YYYY-MM-DD'.
        fim_str (str): Data final no formato 'YYYY-MM-DD'.

    Returns:
        pandas.DataFrame: DataFrame com custo total da frota por loja e mês.
    """
    try:
        engine = criar_conexao()
        if engine is None:
            return pd.DataFrame()
        
        # Consulta base NFE
        query = consulta_nfe_bd(inicio_str, fim_str)
        custo_frota = pd.read_sql(query, engine)

        if custo_frota.empty:
            st.warning("Nenhum dado encontrado para o intervalo de datas fornecido.")
            return custo_frota
        
        custo_frota['EMISSAO'] = pd.to_datetime(custo_frota['EMISSAO']).dt.to_period('M')

        # Carrega e normaliza as placas
        placas_df = listar_placas(engine)
        placas_df['placa_normalizada'] = placas_df['PLACA'].apply(limpa_texto)
        placas_set = set(placas_df['placa_normalizada'])

        # Extrai placas das observações
        custo_frota['placas_encontradas'] = custo_frota['OBS'].apply(lambda x: extrair_placas(str(x), placas_set))
        custo_frota['cont_placa'] = custo_frota['placas_encontradas'].apply(len)

        # Explode as placas por linha (1 linha por placa encontrada)
        placas_explodidas = custo_frota.explode('placas_encontradas')

        # Agrupa por LOJA, EMISSAO e placa
        tabela_placas = (
            placas_explodidas.dropna(subset=['placas_encontradas'])
            .groupby(['LOJA', 'EMISSAO', 'placas_encontradas'], as_index=False)
            .agg({'VALOR_TOTAL': 'sum'})
            .rename(columns={'placas_encontradas': 'PLACA'})
        )

        # Junta os pedidos
        tabela_pedidos = calc_pedidos(inicio_str, fim_str)

        # Junta com os dados por placa
        tabela_agrupada = pd.merge(
            tabela_placas, tabela_pedidos, on=['LOJA', 'EMISSAO'], how='outer'
        )

        tabela_agrupada['VALOR_TOTAL_x'] = tabela_agrupada['VALOR_TOTAL_x'].fillna(0)
        tabela_agrupada['VALOR_TOTAL_y'] = tabela_agrupada['VALOR_TOTAL_y'].fillna(0)

        tabela_agrupada['VALOR_TOTAL'] = tabela_agrupada['VALOR_TOTAL_x'] + tabela_agrupada['VALOR_TOTAL_y']

        # Agrupa por loja e mês final
        tabela_agrupada = tabela_agrupada.groupby(['LOJA', 'EMISSAO'], as_index=False)['VALOR_TOTAL'].sum()
        tabela_agrupada['VALOR_TOTAL'] = tabela_agrupada['VALOR_TOTAL'].round(2)
        
        return tabela_agrupada

    except Exception as e:
        st.error(f"Erro ao processar custos da frota: {e}")
        return pd.DataFrame()


# Execução de exemplo
# engine = criar_conexao()
# df_resultado = custo_frota_loja('2025-01-01', '2025-01-15')
# df_resultado
