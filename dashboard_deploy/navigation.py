
# ------------------------------

import streamlit as st
from time import sleep
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.source_util import get_pages


def get_current_page_name():
    ctx = get_script_run_ctx()
    if not ctx:
        return "app"  # Fallback para página inicial
    pages = get_pages("")
    return pages.get(ctx.page_script_hash, {}).get("page_name", "app")

def make_sidebar():
    with st.sidebar:
        st.title("Painéis de Gestão da Auto Geral")

        # Mudar para False o usuario estiver logado
        # Deixei em True para não precisar logar toda vez que reiniciar o servidor
        if st.session_state.get("logged_in", False):
            st.page_link("pages/page1.py", label="DASHBOARD E METRICAS DA AUTO GERAL")
            st.page_link("pages/mapa_calor.py", label="Mapa de Calor")
            # st.page_link("pages/mapa_calor_horas.py", label="mapa de calor por horas")
            # st.page_link("pages/mapa_calor_por_meses.py", label="mapa de calor por meses")
            st.page_link("pages/totais_entrega.py", label="Totais Entrega, Grafico de barra")
            st.page_link("pages/custo_frota.py")
            st.page_link("pages/entrega_completa.py")
            st.page_link("pages/estacionamento_custo_frota.py")
            st.page_link("pages/manutencao_custo_frota.py")
            st.page_link("pages/comercial-grupo-produto.py")
            st.page_link("pages/compras-pit-stop.py")
            st.page_link("pages/financeiro-boletos-emitidos-por-loja-mes.py")
            st.page_link("pages/financeiro-pix-recebios.py")
            st.page_link("pages/fiscal-apuracao-icms.py")
            st.page_link("pages/fiscal-compras-recalcular.py")
            st.page_link("pages/fiscal-notas-pendentes-lancamento.py")
            st.page_link("pages/fraga-cruzamento.py")
            st.page_link("pages/logistica-indice-venda-casada.py")
            st.page_link("pages/vendas-cancelamentos-romaneios.py")
            st.page_link("pages/vendas-cruzadas.py")
            st.page_link("pages/vendas-faturamento-por-emissao.py")
            st.page_link("pages/vendas-indice-atendimento.py")
            st.page_link("pages/vendas-prospeccao.py")
            st.page_link("pages/vendas-vendedor.py")

            if st.button("Sair"):
                logout()
        elif get_current_page_name() != "app":
            st.switch_page("app.py")  # Redirecionar para página inicial

def logout():
    st.session_state["logged_in"] = False
    st.session_state["user"] = None
    st.info("Até breve!")
    sleep(1)
    st.switch_page("app.py")
