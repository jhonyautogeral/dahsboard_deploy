# from navigation import make_sidebar
# import streamlit as st
# make_sidebar()

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
from datetime import datetime, timedelta
import calendar

# Configurar a página do Streamlit
# st.set_page_config(page_title="Entrega e suas métricas", layout="wide")

# Lista global de dias da semana
dias_semana = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']

# Função para criar conexão com o banco de dados
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

# Função genérica para realizar consultas ao banco de dados
def executar_query(engine, query):
    return pd.read_sql(query, engine)

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

# Função para obter os últimos três anos
def obter_ultimos_anos():
    ano_atual = datetime.now().year
    return [ano_atual - i for i in range(3)]

# Função para obter os meses do ano
def obter_meses():
    return list(calendar.month_name)[1:]

# Função para obter semanas de um mês de um ano
def obter_semanas(ano, mes):
    return len(calendar.monthcalendar(ano, mes))

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
               e.ROTA_HORARIO_REALIZADO
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

# Função para processar e criar o mapa de calor
def gerar_mapa_calor(df, titulo, dias_validos, data_inicio, data_fim):
    df['DIA_DA_SEMANA'] = df['CADASTRO'].dt.dayofweek.map(lambda x: dias_semana[x])
    df['HORA'] = df['CADASTRO'].dt.hour
    df['DIA'] = df['CADASTRO'].dt.date

    # Remover outliers em MINUTOS_ENTREGA e KMS
    limite_minutos_entrega = df['MINUTOS_ENTREGA'].quantile(0.99)
    limite_kms = df['KMS'].quantile(0.99)
    df = df[(df['MINUTOS_ENTREGA'] <= limite_minutos_entrega) & (df['KMS'] <= limite_kms)].copy()

    # Filtrar apenas entregas realizadas (ROTA_STATUS == "ENTREGUE")
    df = df[df['ROTA_STATUS'] == 'ENTREGUE'].copy()

    # Categorizar os dias da semana para manter a ordem correta
    df['DIA_DA_SEMANA'] = pd.Categorical(df['DIA_DA_SEMANA'], categories=dias_semana, ordered=True)

    # Filtrar apenas os dias dentro do intervalo selecionado
    df = df[(df['DIA'] >= data_inicio.date()) & (df['DIA'] <= data_fim.date())].copy()

    # Agrupa diretamente para calcular a mediana da quantidade de entregas
    df_agrupado = (
        df.groupby(['HORA', 'DIA_DA_SEMANA'], observed=False)['expedicao']  # Agrupar por hora e dia da semana
        .count()  # Contar diretamente o número de entregas
        .groupby(level=['HORA', 'DIA_DA_SEMANA'],observed=False)
        .median()  # Calcular a mediana no agrupamento
        .fillna(0)
        .reset_index()
        # .reset_index(name='MEDIANA_QUANTIDADE_ENTREGAS')  # Nomear coluna de saída
        .sort_values(by=['HORA', 'DIA_DA_SEMANA'])
    )

    heatmap_data = df_agrupado.pivot(index='HORA', columns='DIA_DA_SEMANA', values='expedicao')

    # Garantir colunas para todos os dias válidos
    for dia in dias_semana:
        if dia not in heatmap_data.columns:
            heatmap_data[dia] = 0

    heatmap_data = heatmap_data[dias_validos]  # Reordenar para os dias válidos

    plt.figure(figsize=(10, 6))
    sns.heatmap(heatmap_data, annot=True, fmt='.0f', cmap='Blues', cbar=True)
    plt.title(titulo)
    plt.xlabel("Dia da Semana")
    plt.ylabel("Hora")
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    st.pyplot(plt)

def main():
    # Criar conexão com o banco de dados
    engine = criar_conexao()

    # Consultar dados das lojas
    df_lojas = consultar_lojas(engine)
    loja_dict = dict(zip(df_lojas['codigo'], df_lojas['nome']))

    # Seleção de loja
    loja_selecionada = st.selectbox("Selecione a loja", options=loja_dict.keys(), format_func=lambda x: loja_dict[x], key="E_H1_nav_loja")

    # Navegação por barra
    navegacao = st.radio("Navegação", options=["Ano", "Mês", "Semana"], key="E_H1_nav_navegacao")

    if navegacao == "Ano":
        anos = obter_ultimos_anos()
        ano_selecionado = st.selectbox("Selecione o ano", options=anos, key="E_H1_nav_ano")

        data_inicio_ano = datetime(ano_selecionado, 1, 1)
        data_fim_ano = datetime(ano_selecionado, 12, 31)

        st.write(f"Mapa de calor para o ano {ano_selecionado}")
        st.write("### Mediana Qtd Expedição por Hora")
        query = gerar_query_dados(data_inicio_ano, data_fim_ano, loja_selecionada)
        df = executar_query(engine, query)
        if not df.empty:
            gerar_mapa_calor(df, f"Mapa de calor - Ano {ano_selecionado}", dias_semana, data_inicio_ano, data_fim_ano)
        else:
            st.warning("Nenhum dado encontrado para o ano selecionado.")

    elif navegacao == "Mês":
        anos = obter_ultimos_anos()
        ano_selecionado = st.selectbox("Selecione o ano", options=anos, key="E_h2_nav_ano")
        meses = obter_meses()
        mes_selecionado = st.selectbox("Selecione o mês", options=meses, key= "E_h2_nav_mes")

        mes_index = meses.index(mes_selecionado) + 1
        data_inicio_mes = datetime(ano_selecionado, mes_index, 1)
        _, ultimo_dia = calendar.monthrange(ano_selecionado, mes_index)
        data_fim_mes = datetime(ano_selecionado, mes_index, ultimo_dia)

        # Incluir todos os dias da semana como válidos para exibição
        dias_validos = dias_semana

        st.write(f"Mapa de calor para {mes_selecionado}/{ano_selecionado}")
        st.write("### Mediana Qtd Expedição por Hora")
        query = gerar_query_dados(data_inicio_mes, data_fim_mes, loja_selecionada)
        df = executar_query(engine, query)
        if not df.empty:
            gerar_mapa_calor(df, f"Mapa de calor - {mes_selecionado}/{ano_selecionado}", dias_validos, data_inicio_mes, data_fim_mes)
        else:
            st.warning("Nenhum dado encontrado para o mês selecionado.")

    elif navegacao == "Semana":
        anos = obter_ultimos_anos()
        ano_selecionado = st.selectbox("Selecione o ano", options=anos, key="E_H3_nav_ano")
        meses = obter_meses()
        mes_selecionado = st.selectbox("Selecione o mês", options=meses, key="E_H3_nav_mes")

        mes_index = meses.index(mes_selecionado) + 1
        semanas = obter_semanas(ano_selecionado, mes_index)
        semana_selecionada = st.selectbox("Selecione a semana", options=range(1, semanas + 1), key="E_H3_nav_semana")

        calendario_mes = calendar.monthcalendar(ano_selecionado, mes_index)
        semana = calendario_mes[semana_selecionada - 1]

        dias_validos = [dias_semana[i] for i in range(len(semana)) if semana[i] != 0]

        primeiro_dia_semana = [d for d in semana if d != 0][0]
        ultimo_dia_semana = [d for d in semana if d != 0][-1]

        data_inicio_semana = datetime(ano_selecionado, mes_index, primeiro_dia_semana)
        data_fim_semana = datetime(ano_selecionado, mes_index, ultimo_dia_semana)

        st.write(f"Mapa de calor para a semana {semana_selecionada} de {mes_selecionado}/{ano_selecionado}")
        st.write("### Mediana Qtd Expedição por Hora")
        query = gerar_query_dados(data_inicio_semana, data_fim_semana, loja_selecionada)
        df = executar_query(engine, query)
        if not df.empty:
            gerar_mapa_calor(df, f"Mapa de calor - Semana {semana_selecionada} - {mes_selecionado}/{ano_selecionado}", dias_validos, data_inicio_semana, data_fim_semana)
        else:
            st.warning("Nenhum dado encontrado para a semana selecionada.")
if __name__ == "__main__":
    main()