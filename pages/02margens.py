import streamlit as st
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página
    
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from datetime import datetime
import calendar

# Configuração da página (descomente se necessário)
# st.set_page_config(page_title="Entrega e suas métricas", layout="wide", page_icon="📊")

# Lista global de dias da semana em português (segunda a sábado)
dias_semana = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado']
# Caso deseje incluir domingo, adicione-o à lista, por exemplo:
# dias_semana = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']

def criar_conexao():
    """
    Cria e retorna uma conexão com o banco de dados MySQL utilizando as credenciais definidas em st.secrets.
    """
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

def executar_query(engine, query):
    """
    Executa a query SQL e retorna um DataFrame com os resultados.
    Em caso de erro, exibe a mensagem e retorna um DataFrame vazio.
    """
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Erro ao executar a query: {e}")
        return pd.DataFrame()

def consultar_lojas(engine):
    """Consulta e retorna os dados das lojas."""
    query = "SELECT codigo, nome FROM autogeral.lojas ORDER BY codigo"
    return executar_query(engine, query)

def validar_datas(inicio, termino):
    """Valida se a data de início é anterior ou igual à data de término."""
    if inicio > termino:
        st.error("A data de início deve ser anterior ou igual à data de término.")
        return False
    return True

def obter_ultimos_anos():
    """Retorna uma lista com os últimos três anos, incluindo o ano atual."""
    ano_atual = datetime.now().year
    return [ano_atual - i for i in range(3)]

def obter_meses():
    """Retorna a lista de nomes dos meses conforme o calendário."""
    # Atenção: Dependendo da localidade, os nomes dos meses podem vir em inglês.
    return list(calendar.month_name)[1:]

def obter_semanas(ano, mes):
    """Retorna o número de semanas de um mês específico de um ano."""
    return len(calendar.monthcalendar(ano, mes))

def categorias():
    """
    Retorna um dicionário com as categorias disponíveis para análise.
    As chaves são os nomes legíveis e os valores são os identificadores usados para filtrar os dados.
    """
    categorias_opcoes = {
        'Linha Leve': 'LEVE',
        'Linha Pesada': 'PESADO',
        'Operação Venda': 'Venda',
        'Operação Devolução do cliente': 'Devolução'
    }
    return categorias_opcoes

def gerar_query_dados(inicio, fim, loja):
    """
    Gera e retorna uma query SQL para extrair dados de vendas entre as datas especificadas e para a loja selecionada.
    
    Parâmetros:
        inicio (str): Data de início no formato 'YYYY-MM-DD'.
        fim (str): Data de término no formato 'YYYY-MM-DD'.
        loja (int ou str): Código da loja.
    """
    query = f"""
        SELECT V.TIPO, V.CODIGO, V.LOJA AS LOJA_REQUERENTE,
               O.DESCRICAO_SIMPLIFICADA AS OPERACAO,
               E.GIRO, E.QUANTIDADE_MINIMA, E.CURVA,
               V.EMISSAO, V.SITUACAO, VD.DESCRICAO AS VENDEDOR,
               P.CODIGO_X, P.CODIGO_SEQUENCIA, P.DESCRICAO,
               VI.QUANTIDADE,
               VI.VALOR_UNIDADE, VI.CUSTO_UNIDADE, (VI.VALOR_UNIDADE - VI.CUSTO_UNIDADE) AS MARGEM,
               L.DESCRICAO AS LINHA
        FROM vendas V 
             LEFT JOIN vendedores_dbf VD ON V.VENDEDOR_CODIGO = VD.CODIGO
             JOIN movimentos_operacoes O ON V.OPERACAO_CODIGO = O.CODIGO
             LEFT JOIN vendas_itens VI ON V.TIPO = VI.TIPO AND V.CODIGO = VI.CODIGO AND V.LOJA = VI.LOJA
             LEFT JOIN produtos_dbf P ON VI.PRODUTO_CODIGO = P.CODIGO
             LEFT JOIN produto_estoque E ON P.CODIGO = E.PRODUTO_CODIGO AND E.LOJA = V.LOJA
             LEFT JOIN produto_linha L ON P.LINHA_CODIGO = L.CODIGO
        WHERE V.OPERACAO_CODIGO IN (1,2,3,8,9)
          AND V.SITUACAO = 'NORMAL'
          AND V.LOJA = {loja}
          AND V.EMISSAO BETWEEN '{inicio}' AND '{fim}';
    """
    return query

def gerar_analise(df, titulo, data_inicio, data_fim, categoria_selecionada):
    """
    Gera análises e visualizações (gráfico de barras e mapa de calor) com base nos dados fornecidos.
    
    Parâmetros:
        df (DataFrame): Dados a serem analisados.
        titulo (str): Título da análise.
        data_inicio (datetime): Data inicial para o filtro.
        data_fim (datetime): Data final para o filtro.
        categoria_selecionada (str): Identificador da categoria para filtro.
    """
    try:
        # Verificar colunas necessárias
        colunas_necessarias = ['EMISSAO', 'LINHA', 'OPERACAO', 'MARGEM']
        for coluna in colunas_necessarias:
            if coluna not in df.columns:
                st.error(f"Coluna ausente no DataFrame: {coluna}")
                return

        # Preprocessamento dos dados
        df['EMISSAO'] = pd.to_datetime(df['EMISSAO'])
        df = df[(df['EMISSAO'] >= data_inicio) & (df['EMISSAO'] <= data_fim)]
        
        # Converter a data para mês (nome) e definir a ordem correta dos meses
        df['MES'] = df['EMISSAO'].dt.month_name()
        meses_ordenados = obter_meses()  # Observe que os nomes podem vir em inglês; ajuste se necessário
        df['MES'] = pd.Categorical(df['MES'], categories=meses_ordenados, ordered=True)
        
        # Converter o dia da semana para nomes em português usando mapeamento
        mapping_dias = {
            "Monday": "segunda",
            "Tuesday": "terça",
            "Wednesday": "quarta",
            "Thursday": "quinta",
            "Friday": "sexta",
            "Saturday": "sábado",
            "Sunday": "domingo"
        }
        df['DIA_SEMANA'] = df['EMISSAO'].dt.day_name().map(mapping_dias)

        # Aplicar filtro conforme a categoria selecionada
        if categoria_selecionada == "LEVE":
            df = df[df['LINHA'] == 'LEVE']
        elif categoria_selecionada == "PESADO":
            df = df[df['LINHA'] == 'PESADO']
        elif categoria_selecionada == "Venda":
            df = df[df['OPERACAO'] == 'Venda']
        elif categoria_selecionada == "Devolução":
            df = df[df['OPERACAO'] == 'Devolução do cliente']

        # Verificar se há dados após os filtros
        if df.empty:
            st.warning("Nenhum dado disponível após aplicar os filtros.")
            return

        # Agrupar e calcular a média da margem por mês
        margem_por_mes = df.groupby('MES', observed=True)['MARGEM'].mean().reset_index()

        # Agrupar por mês e dia da semana para criar o mapa de calor
        margem_por_dia_semana = (
            df.groupby(['MES', 'DIA_SEMANA'], observed=False)['MARGEM']
              .mean()
              .unstack()
              .reindex(columns=dias_semana)  # Correção: utiliza a lista global de dias
        )

        # Visualizações
        st.header(f"{titulo} - {categoria_selecionada if categoria_selecionada else 'Geral'}")

        # Gráfico de barras: Média de Margens por Mês
        st.subheader("Média de Margens por Mês")
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(data=margem_por_mes, x='MES', y='MARGEM', ax=ax)
        ax.set_ylabel("Média da Margem")
        ax.set_xlabel("Mês")
        ax.set_title("Média da Margem por Mês")
        st.pyplot(fig)

        # Mapa de calor: Margem Média por Dia da Semana
        st.subheader("Mapa de Calor: Margem Média por Dia da Semana")
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(margem_por_dia_semana, annot=True, fmt=".2f", cmap="Blues", ax=ax)
        ax.set_ylabel("Mês")
        ax.set_xlabel("Dia da Semana")
        ax.set_title("Mapa de Calor das Margens")
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Ocorreu um erro durante a análise: {e}")

def main():
    # Criar conexão com o banco de dados
    engine = criar_conexao()

    # Consultar dados das lojas
    df_lojas = consultar_lojas(engine)
    if df_lojas.empty:
        st.error("Nenhuma loja encontrada no banco de dados.")
        return
    loja_dict = dict(zip(df_lojas['codigo'], df_lojas['nome']))
    
    st.sidebar.write("## Mapa de calor por meses")
    
    # Seleção da loja
    loja_selecionada = st.sidebar.selectbox(
        "Selecione a loja", 
        options=list(loja_dict.keys()), 
        format_func=lambda x: loja_dict[x], 
        key="mnavm_loja"
    )

    # Navegação por barra
    navegacao = st.sidebar.radio("Navegação", options=["Ano"], key="mnavm_navegacao")

    if navegacao == "Ano":
        # Seleção da categoria
        categorias_opcoes = categorias()
        categoria_legivel = st.sidebar.selectbox(
            "Selecione a categoria",
            options=list(categorias_opcoes.keys()),
            key="mnavm1_categoria"
        )
        # Recupera o valor correspondente para filtro
        categoria_selecionada = categorias_opcoes[categoria_legivel]

        # Seleção do ano
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="mnavm_ano")

        data_inicio_ano = datetime(ano_selecionado, 1, 1)
        data_fim_ano = datetime(ano_selecionado, 12, 31)

        st.write(f"### Mapa de calor para Categoria: {categoria_legivel}")

        # Gerar e executar a query de dados (formatando as datas como 'YYYY-MM-DD')
        query = gerar_query_dados(
            data_inicio_ano.strftime('%Y-%m-%d'), 
            data_fim_ano.strftime('%Y-%m-%d'), 
            loja_selecionada
        )
        df = executar_query(engine, query)
        if not df.empty:
            gerar_analise(df, f"Mapa de calor - Ano {ano_selecionado}", data_inicio_ano, data_fim_ano, categoria_selecionada)
        else:
            st.warning("Nenhum dado encontrado para o ano selecionado.")

if __name__ == "__main__":
    main()
