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
dias_semana = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado']

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
 # Função para gerar o mapa de calor
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
        # Convertendo a coluna 'CADASTRO' para datetime
        df['CADASTRO'] = pd.to_datetime(df['CADASTRO'], errors='coerce')
        
        # Remover linhas com datas inválidas
        df = df.dropna(subset=['CADASTRO'])
        
        # Preprocessamento comum
        df['DIA_DA_SEMANA'] = df['CADASTRO'].dt.dayofweek.map(lambda x: dias_semana[x])
        df['HORA'] = df['CADASTRO'].dt.hour
        df['DIA'] = df['CADASTRO'].dt.date

        # Filtrar dados pelo intervalo de datas e status
        df = df[(df['ROTA_STATUS'] == 'ENTREGUE') & 
                (df['DIA'] >= data_inicio.date()) & 
                (df['DIA'] <= data_fim.date())]

        # Validação dos dias válidos
        dias_disponiveis = [dia for dia in dias_validos if dia in df['DIA_DA_SEMANA'].unique()]
        if not dias_disponiveis:
            st.warning("Nenhum dos dias válidos está disponível nos dados.")
            return
        
        # Processar dados com base na categoria
        if categoria_selecionada == 'MINUTOS_ENTREGA':
            # Filtrar entregas válidas
            df['ENTREGAS_40'] = df['MINUTOS_ENTREGA'] <= 40

            # Calcular a mediana de 'MINUTOS_ENTREGA'
            agrupado_total = df.groupby(['HORA', 'DIA_DA_SEMANA'])['MINUTOS_ENTREGA'].median().unstack(fill_value=0)
            agrupado_total = agrupado_total[dias_disponiveis]

            # Remover valores discrepantes com base no IQR
            Q1 = agrupado_total.quantile(0.25)  # Primeiro quartil
            Q3 = agrupado_total.quantile(0.75)  # Terceiro quartil
            IQR = Q3 - Q1                       # Intervalo interquartil

            limite_inferior = Q1 - 1.5 * IQR
            limite_superior = Q3 + 1.5 * IQR

            agrupado_total = agrupado_total.clip(lower=limite_inferior, upper=limite_superior, axis=1)

            # Calcular a mediana para entregas <= 40 minutos
            agrupado_40 = df[df['ENTREGAS_40']].groupby(['HORA', 'DIA_DA_SEMANA'])['MINUTOS_ENTREGA'].count().unstack(fill_value=0)
            agrupado_40 = agrupado_40[dias_disponiveis]

            # Gerar mapa de calor para ambas as métricas
            for titulo, dados in zip(['Total de Entregas mediana, e filtro de remoção de valores discrepantes', 'Quantidade Entregas em até 40 minutos por cada hora'], [agrupado_total, agrupado_40]):
                plt.figure(figsize=(10, 6))
                sns.heatmap(dados, annot=True, fmt='.0f', cmap='Blues', cbar=True)
                plt.title(f"{titulo}")
                plt.xlabel("Dia da Semana")
                plt.ylabel("Hora")
                plt.xticks(rotation=45)
                plt.yticks(rotation=0)
                st.pyplot(plt)
                plt.clf()

        elif categoria_selecionada == 'ROMANEIO':
            # Criar uma coluna com a contagem de valores não nulos por hora e dia da semana
            df['CONTAGEM_ROMANEIO'] = df.groupby(['HORA', 'DIA_DA_SEMANA'])['ROMANEIO'].transform('count')

            # Agrupar os dados e calcular a mediana
            df_agrupado = df.groupby(['HORA', 'DIA_DA_SEMANA'])['CONTAGEM_ROMANEIO'].median().unstack(fill_value=0)
            df_agrupado = df_agrupado[dias_disponiveis]

            # Criar o mapa de calor
            plt.figure(figsize=(10, 6))
            sns.heatmap(df_agrupado, annot=True, fmt='.0f', cmap='Blues', cbar=True)
            plt.title(f"{titulo} - Mediana de Contagem de Romaneios")
            plt.xlabel("Dia da Semana")
            plt.ylabel("Hora")
            plt.xticks(rotation=45)
            plt.yticks(rotation=0)
            st.pyplot(plt)
            plt.clf()  

        elif categoria_selecionada in ['MINUTOS_DE_SEPARACAO', 'MINUTOS_ENTREGA_REALIZADA']:
            df_agrupado = df.groupby(['HORA', 'DIA_DA_SEMANA'])[categoria_selecionada].median().unstack(fill_value=0)
            df_agrupado = df_agrupado[dias_disponiveis]

            plt.figure(figsize=(10, 6))
            sns.heatmap(df_agrupado, annot=True, fmt='.1f', cmap='Blues', cbar=True)
            plt.title(f"{titulo}")
            plt.xlabel("Dia da Semana")
            plt.ylabel("Hora")
            st.pyplot(plt)
            plt.clf()

    except KeyError as e:
        st.error(f"Erro ao processar os dados: {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")

def main():
    # Criar conexão com o banco de dados
    engine = criar_conexao()

    # Consultar dados das lojas
    df_lojas = consultar_lojas(engine)
    loja_dict = dict(zip(df_lojas['codigo'], df_lojas['nome']))

    st.sidebar.write("## Mapa de calor por horas")
    # Seleção de loja
    loja_selecionada = st.sidebar.selectbox("Selecione a loja", options=loja_dict.keys(), format_func=lambda x: loja_dict[x], key="mnavh_loja")

    # Navegação por barra
    navegacao = st.sidebar.radio("Navegação", options=["Ano", "Mês", "Semana"], key="mnavh_navegacao")

    if navegacao == "Ano":
        # Apenas exibe os widgets para "Ano"
        categorias_opcoes = categorias()
        # Seleção da categoria
        categoria_legivel = st.sidebar.selectbox(
            "Selecione a categoria",
            options=list(categorias_opcoes.keys()),  # Exibe os nomes legíveis no selectbox
            key="mnavh1_categoria"
        )
        # Recupera o valor correspondente à coluna no DataFrame
        categoria_selecionada = categorias_opcoes[categoria_legivel]

        # selecionar o ano
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="mnavh_ano")

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

    elif navegacao == "Mês":
        # Apenas exibe os widgets para "Mês"
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="mnavh_mes_ano")
        meses = obter_meses()
        mes_selecionado = st.sidebar.selectbox("Selecione o mês", options=meses, key="mnavh_mes_mes")

        # Dicionário de opções com nomes legíveis e valores correspondentes às colunas
        categorias_opcoes = categorias()

        # Seleção da categoria
        categoria_legivel = st.sidebar.selectbox(
            "Selecione a categoria",
            options=list(categorias_opcoes.keys()),  # Exibe os nomes legíveis no selectbox
            key="mnavh1_categoria"
        )

        # Recupera o valor correspondente à coluna no DataFrame
        categoria_selecionada = categorias_opcoes[categoria_legivel]

        mes_index = meses.index(mes_selecionado) + 1
        data_inicio_mes = datetime(ano_selecionado, mes_index, 1)
        _, ultimo_dia = calendar.monthrange(ano_selecionado, mes_index)
        data_fim_mes = datetime(ano_selecionado, mes_index, ultimo_dia)

        dias_validos = dias_semana

        # Mostrar o nome da categoria selecionada
        categoria_legivel = [k for k, v in categorias().items() if v == categoria_selecionada][0]
        st.write(f"### Mapa de calor para Categoria: {categoria_legivel}")

        st.write(f"Mapa de calor para {mes_selecionado}/{ano_selecionado}")
        # st.write("### Mediana Tempo em minutos Geração do romaneio até entrega")
        query = gerar_query_dados(data_inicio_mes, data_fim_mes, loja_selecionada)
        df = executar_query(engine, query)
        if not df.empty:
            gerar_mapa_calor(df, f"Mapa de calor - {mes_selecionado}/{ano_selecionado}", dias_validos, data_inicio_mes, data_fim_mes, categoria_selecionada)
        else:
            st.warning("Nenhum dado encontrado para o mês selecionado.")
    
    elif navegacao == "Semana":
        anos = obter_ultimos_anos()
        ano_selecionado = st.sidebar.selectbox("Selecione o ano", options=anos, key="Qnav3_ano")
        meses = obter_meses()
        mes_selecionado = st.sidebar.selectbox("Selecione o mês", options=meses, key="Qnav3_mes")

                # Dicionário de opções com nomes legíveis e valores correspondentes às colunas
        categorias_opcoes = categorias()

        # Seleção da categoria
        categoria_legivel = st.sidebar.selectbox(
            "Selecione a categoria",
            options=list(categorias_opcoes.keys()),  # Exibe os nomes legíveis no selectbox
            key="mnavh1_categoria"
        )

        # Recupera o valor correspondente à coluna no DataFrame
        categoria_selecionada = categorias_opcoes[categoria_legivel]

        mes_index = meses.index(mes_selecionado) + 1
        semanas = obter_semanas(ano_selecionado, mes_index)
        semana_selecionada = st.selectbox("Selecione a semana", options=range(1, semanas + 1), key="Qnav3_semana")

        calendario_mes = calendar.monthcalendar(ano_selecionado, mes_index)
        semana = calendario_mes[semana_selecionada - 1]

        dias_validos = [
            dias_semana[i] 
            for i in range(len(semana)) 
            if i < len(dias_semana) and semana[i] != 0
        ]

        primeiro_dia_semana = [d for d in semana if d != 0][0]
        ultimo_dia_semana = [d for d in semana if d != 0][-1]

        data_inicio_semana = datetime(ano_selecionado, mes_index, primeiro_dia_semana)
        data_fim_semana = datetime(ano_selecionado, mes_index, ultimo_dia_semana)

        # Mostrar o nome da categoria selecionada
        categoria_legivel = [k for k, v in categorias().items() if v == categoria_selecionada][0]
        st.write(f"### Mapa de calor para Categoria: {categoria_legivel}")

        st.write(f"Mapa de calor para a semana {semana_selecionada} de {mes_selecionado}/{ano_selecionado}")

        query = gerar_query_dados(data_inicio_semana, data_fim_semana, loja_selecionada)
        df = executar_query(engine, query)
        if not df.empty:
            gerar_mapa_calor(df, f"Mapa de calor - Semana {semana_selecionada} - {mes_selecionado}/{ano_selecionado}", dias_validos, data_inicio_semana, data_fim_semana, categoria_selecionada)
        else:
            st.warning("Nenhum dado encontrado para a semana selecionada.")
if __name__ == "__main__":
    main()
