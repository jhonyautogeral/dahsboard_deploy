import streamlit as st
from navigation import make_sidebar

def check_auth():
    """Verifica se usuário está autenticado"""
    if not st.session_state.get("logged_in"):
        st.switch_page("app.py")
        return False
    return True

def setup_page():
    """Configura página com sidebar e autenticação"""
    if check_auth():
        make_sidebar()
        return True
    return False