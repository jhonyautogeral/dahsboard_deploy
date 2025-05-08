
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


# st.set_page_config(page_title="Entrega e suas métricas", layout="wide", page_icon="📊")

# Lista global de dias da semana
dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']

# Função para criar conexão com o banco de dados
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

# Função genérica para realizar consultas ao banco de dados
def executar_query(engine, query):
    try:
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Erro ao executar a query: {e}")
        return pd.DataFrame()


# Função para consultar dados de lojas no banco de dados
def consultar_lojas(engine):
    query = "SELECT codigo, nome FROM autogeral.lojas ORDER BY codigo"
    return executar_query(engine, query)

# Função para validar as datas
def validar_datas(inicio, termino):
    if inicio > termino:
        st.error("A data de início deve ser anterior ou igual à data de término.")
        return False
    return True

# Função para obter os utimos três anos
def obter_ultimos_anos():
    ano_atual = datetime.now().year
    return [ano_atual - i for i in range(3)]

# Função para obter os meses do ano
def obter_meses():
    return list(calendar.month_name)[1:]

# Função para obter semanas de um mês de um ano
def obter_semanas(ano, mes):
    return len(calendar.monthcalendar(ano, mes))

def categorias():
    # Dicionário de opções com nomes legíveis e valores correspondentes às colunas
    categorias_opcoes = {
        'Tempo separação em minutos': 'MINUTOS_DE_SEPARACAO',
        'Quantidade de romaneios gerado por hora': 'ROMANEIO',
        'Entrega completa. Gerado romaneio até entrega': 'MINUTOS_ENTREGA',
        'Saida da loja até entrega, tempo em minutos': 'MINUTOS_ENTREGA_REALIZADA'
    }
    return categorias_opcoes

# Função para gerar a query de dados
def gerar_query_dados(inicio, fim, loja):
    return f"""
        SELECT a.expedicao, r.ROMANEIO, a.LOJA, a.CADASTRO,
               d.DESCRICAO AS 'Entregador',
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
               TIMESTAMPDIFF(MINUTE, a.HORA_SAIDA, e.ROTA_HORARIO_REALIZADO) MINUTOS_ENTREGA_REALIZADA
        FROM expedicao_itens e
        JOIN expedicao a ON e.EXPEDICAO_CODIGO = a.EXPEDICAO AND e.EXPEDICAO_LOJA = a.LOJA
        JOIN cadastros_veiculos b ON a.cada_veic_id = b.cada_veic_id
        JOIN produto_veiculo c ON b.veiculo_codigo = c.codigo
        JOIN entregador d ON a.ENTREGADOR_CODIGO = d.CODIGO
        LEFT JOIN romaneios_dbf r ON e.VENDA_TIPO = 'ROMANEIO' AND e.CODIGO_VENDA = r.ROMANEIO AND e.LOJA_VENDA = r.LOJA
        WHERE a.ROTA_METROS IS NOT NULL
          AND a.LOJA = {loja}
          AND r.CADASTRO BETWEEN '{inicio}' AND '{fim}';
    """
 # Função para gerar o mapa de calor e grafico de barras
def gerar_mapa_calor(df, titulo, dias_validos, data_inicio, data_fim, categoria_selecionada):
    """
    Gera um mapa de calor para uma categoria selecionada.
    
    Args:
        df (DataFrame): Dados para análise.
        titulo (str): Título do gráfico.
        dias_validos (list): Dias da semana válidos.
        data_inicio (datetime): Data inicial do intervalo.
        data_fim (datetime): Data final do intervalo.
        categoria_selecionada (str): Categoria selecionada.
    
    Returns:
        None
    """
    # Validação da categoria selecionada
    categorias_validas = ['ROMANEIO', 'MINUTOS_DE_SEPARACAO', 'MINUTOS_ENTREGA_REALIZADA', 'MINUTOS_ENTREGA']
    if categoria_selecionada not in categorias_validas:
        st.error(f"Categoria inválida: {categoria_selecionada}")
        return
    
    try:
        # Preprocessamento comum
        
        # Convertendo a coluna 'CADASTRO' para datetime
        df['CADASTRO'] = pd.to_datetime(df['CADASTRO'])
        df['DIA_DA_SEMANA'] = df['CADASTRO'].dt.dayofweek.map(lambda x: dias_semana[x])
        df['MES'] = df['CADASTRO'].dt.month
        df['MES'] = df['MES'].map({1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4:'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'})
        df['MES'] = pd.Categorical(df['MES'], categories=['Janeiro','Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho','Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'], ordered=True)
        df = df.sort_values('MES')
        df['DIA'] = df['CADASTRO'].dt.date

        # Filtrar apenas entregas realizadas e intervalo de data
        df = df[(df['ROTA_STATUS'] == 'ENTREGUE') & 
                (df['DIA'] >= data_inicio.date()) & 
                (df['DIA'] <= data_fim.date())]

        # Filtrar dados para a categoria
        if categoria_selecionada in ['ROMANEIO', 'MINUTOS_DE_SEPARACAO', 'MINUTOS_ENTREGA_REALIZADA']:
            df['CATEGORIA'] = df[categoria_selecionada]
            df_filtrado = df[df['CATEGORIA'].notnull()]

            # Agrupar e calcular medianas
            df_agrupado = (
                df_filtrado.groupby(['MES', 'DIA_DA_SEMANA'], observed=False)[categoria_selecionada]
                .median()
                .reset_index(name='MEDIANA')
            )

        elif categoria_selecionada == 'MINUTOS_ENTREGA':
            # df = df[(df['MES'] >= 8) & (df['HORA'] <= 18)]
            df['ENTREGAS_40'] = df[categoria_selecionada] <= 40

            df_agrupado = (
                df[df['ENTREGAS_40']]
                .groupby(['MES', 'DIA_DA_SEMANA'], observed=False)
                .size()
                .reset_index(name='QUANTIDADE_ENTREGAS')
            )

        # Criar tabela para o mapa de calor
        tabela = df_agrupado.pivot(index='MES', columns='DIA_DA_SEMANA', values=df_agrupado.columns[-1])
        tabela = tabela.fillna(0)

        # Garantir dias válidos
        for dia in dias_semana:
            if dia not in tabela.columns:
                tabela[dia] = 0

        tabela = tabela[dias_validos]

        # Gerar o mapa de calor
        plt.figure(figsize=(10, 6))
        x = sns.heatmap(tabela, annot=True, fmt='.0f', cmap='Blues', cbar=True)
        plt.title(titulo)

        x.xaxis.set_label_position('top')  # define a posição do rótulo para o topo
        x.xaxis.tick_top()                  # move as marcações do eixo X para o topo
        x.set_xlabel("Dia da Semana", labelpad=10)
        # plt.xlabel("Dia da Semana")
        plt.ylabel("Mês")
        plt.xticks(rotation=0)
        plt.yticks(rotation=0)
        st.pyplot(plt)
    
    except KeyError as e:
        st.error(f"Erro ao processar os dados: Coluna ausente {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")


def main():
    # Criar conexão com o banco de dados
    engine = criar_conexao()

    # Consultar dados das lojas
    df_lojas = consultar_lojas(engine)
    loja_dict = dict(zip(df_lojas['codigo'], df_lojas['nome']))
    
    st.sidebar.write("## Mapa de calor por meses")
    # Seleção de loja
    loja_selecionada = st.sidebar.selectbox("Selecione a loja", options=loja_dict.keys(), format_func=lambda x: loja_dict[x], key="mnavm_loja")

    # Navegação por barra
    navegacao = st.sidebar.radio("Navegação", options=["Ano"], key="mnavm_navegacao")

    if navegacao == "Ano":
        # Apenas exibe os widgets para "Ano"
        categorias_opcoes = categorias()
        # Seleção da categoria
        categoria_legivel = st.sidebar.selectbox(
            "Selecione a categoria",
            options=list(categorias_opcoes.keys()),  # Exibe os nomes legíveis no selectbox
            key="mnavm1_categoria"
        )
        # Recupera o valor correspondente à coluna no DataFrame
        categoria_selecionada = categorias_opcoes[categoria_legivel]

        # selecionar o ano
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="mnavm_ano")

        data_inicio_ano = datetime(ano_selecionado, 1, 1)
        data_fim_ano = datetime(ano_selecionado, 12, 31)

        # Mostrar o nome da categoria selecionada
        categoria_legivel = [k for k, v in categorias().items() if v == categoria_selecionada][0]
        st.write(f"### Mapa de calor para Categoria: {categoria_legivel}")

        # st.write("### Mediana Tempo em minutos Geração do romaneio até entrega")
        query = gerar_query_dados(data_inicio_ano, data_fim_ano, loja_selecionada)
        df = executar_query(engine, query)
        if not df.empty:
            gerar_mapa_calor(df, f"Mapa de calor - Ano {ano_selecionado}", dias_semana, data_inicio_ano, data_fim_ano, categoria_selecionada)
        else:
            st.warning("Nenhum dado encontrado para o ano selecionado.")

if __name__ == "__main__":
    main()
