import streamlit as st
from navigation import make_sidebar
from common_utils import check_auth
import os

# """Verifica autenticação - usar no início de cada página"""
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando...")
    st.switch_page("app.py")
    st.stop()

# Criar sidebar
make_sidebar()

# Configurar página
# st.set_page_config(page_title="Dashboard Auto Geral", layout="wide")

# Conteúdo principal
col1, col2 = st.columns([2, 1])

with col1:
    st.title("Dashboard Auto Geral")
    st.markdown("""
    ### Bem-vindo ao sistema de métricas da Auto Geral
    
    **Principais funcionalidades disponíveis:**
    -  Centro de Custos e Análises Financeiras
    -  Indicadores de Entregas e Rotas
    -  Mapas de Calor e Visualizações
    -  Controle de Margens e Vendas
    -  Gestão de Frota e Combustível
    """)
    
    # Métricas rápidas
    if st.session_state.get("user_info"):
        user = st.session_state["user_info"]
        st.success(f" Olá, **{user.get('name', 'Usuário')}**!")
        st.info(f" Cargo: **{user.get('cargo', 'N/A')}**")

with col2:
    # Logo da empresa
    logo_path = "pages/logo_autogral.jpg"
    if os.path.exists(logo_path):
        st.image(logo_path, width=250)
    else:
        st.info("📸 Logo não encontrada")
    
    # Status do sistema
    st.markdown("###  Status do Sistema")
    st.success("✅ Sistema Online")
    st.info("🔄 Última atualização: Tempo real")

# Rodapé
st.markdown("---")
st.markdown(
    "* Use a barra lateral para navegar entre as funcionalidades disponíveis.*"
)