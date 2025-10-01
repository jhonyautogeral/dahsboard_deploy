import streamlit as st

st.set_page_config(page_title="Mapa de calor de Entregas")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

if st.sidebar.button("Voltar", key="btn_voltar"):
    st.switch_page("app.py")

st.write("## MAPAS DE CALOR")

tab1, tab2 = st.tabs(["Mapa de calor por horas", "Mapa de calor por meses"])

with tab1:
    try:
        from pages.mapa_calor_horas import main as mapa_calor_horas_main
        mapa_calor_horas_main()
    except ModuleNotFoundError:
        st.error("Erro ao carregar 'Mapa de calor por horas'.")

with tab2:
    try:
        from pages.mapa_calor_por_meses import main as mapa_calor_por_meses_main
        mapa_calor_por_meses_main()
    except ModuleNotFoundError:
        st.error("Erro ao carregar 'Mapa de calor por meses'.")