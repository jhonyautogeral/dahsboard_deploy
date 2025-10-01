import streamlit as st

# Configuração da página
st.set_page_config(page_title="Mapa de calor de Entregas")

# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

if st.sidebar.button("Voltar"):
    st.switch_page("app.py")

# Título da página
st.write("## MAPAS DE CALOR.")

# Subpáginas como abas
tab1, tab2 = st.tabs(["Mapa de calor por horas", "Mapa de calor por meses"])

with tab1:
    try:
        from pages.mapa_calor_horas import main as mapa_calor_horas_main
        mapa_calor_horas_main()
    except ModuleNotFoundError:
        st.error("Erro ao carregar 'Mapa de calor por horas'. Verifique a conexão com o banco de dados.")

with tab2:
    try:
        from pages.mapa_calor_por_meses import main as mapa_calor_por_meses_main
        mapa_calor_por_meses_main()
    except ModuleNotFoundError:
        st.error("Erro ao carregar 'Mapa de calor por meses'. Verifique a conexão com o banco de dados.")