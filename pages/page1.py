import streamlit as st
from navigation import make_sidebar
from common_utils import check_auth
import os

# """Verifica autenticação - usar no início de cada página"""
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando...")
    st.switch_page("app.py")
    st.stop()


# Configurar página
st.set_page_config(page_title="Dashboard Auto Geral", layout="wide")

# Criar sidebar
make_sidebar()

# Conteúdo principal
col1, col2 = st.columns([2, 1])

with col1:
    st.title("Dashboard Auto Geral")
    st.markdown("""
    ### Bem-vindo ao sistema de métricas da Auto Geral
    
    **Principais funcionalidades disponíveis:**
    
    **📊 Análises Financeiras e Custos:**
    - Centro de Custos por categoria
    - Custos de Entrega e análise de eficiência
    - Análise de Custos Totais por loja
    - Custo de Combustível da Frota
    
    **🚚 Gestão de Entregas e Logística:**
    - Indicadores de Entregas (≤40min e >40min)
    - Entrega Logística com análise de performance
    - Quantidade de Entregas por Tipo
    - Análise de Entregas e Rotas
    
    **📈 Análises de Vendas:**
    - Vendas com Curva ABC/XYZ
    - Vendas sem análise de curva
    - Produtos Cruzados (Código Fraga)
    
    **🗺️ Visualizações e Mapas:**
    - Mapas de Calor por horas
    - Mapas de Calor por meses
    
    **🚗 Monitoramento de Frota:**
    - Monitoramento de Veículos Cobli
    - Abastecimento por Veículo
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