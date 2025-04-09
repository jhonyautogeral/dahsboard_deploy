import streamlit as st
# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()  # Interrompe a execução para evitar continuar carregando esta página


# from navigation import make_sidebar  
# # Chamada para criar a barra lateral (se aplicável)
# make_sidebar()

st.set_page_config(page_title="Mapa de calor de Entregas")

# Título e imagem da página
st.write("## MAPAS DE CALOR.")
# Subpáginas como abas
tab1, tab2 = st.tabs(["Mapa de calor por horas ", "Mapa de calor por meses"])

with tab1:
    # Importando e chamando o conteúdo da página
    try:
        from pages.mapa_calor_horas import main as mapa_calor_horas_main
        mapa_calor_horas_main()  # Certifique-se de que a função 'main()' exista na página.
    except ModuleNotFoundError:
        st.error("A página 'Mapa de calor por horas'. Talvez erro na conexão com o banco de dados.")

with tab2:
    # Importando e chamando o conteúdo da página
    try:
        from pages.mapa_calor_por_meses import main as mapa_calor_por_meses_main
        mapa_calor_por_meses_main()  # Certifique-se de que a função 'main()' exista na página.
    except ModuleNotFoundError:
        st.error("A página 'Mapa de calor por meses'. Talvez erro na conexão com o banco de dados.")

