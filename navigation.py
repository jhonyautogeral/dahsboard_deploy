import streamlit as st
from time import sleep
from app import AuthManager
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.source_util import get_pages

class AccessControl:
    """Controla acesso às páginas por cargo"""
    
    PERMISSIONS = {
        "centro_custo.py": ["Gestor", "Encarregado", "VENDAS", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
        "custo_entrega.py": ["Gestor", "Encarregado", "VENDAS", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
        "custos.py": ["Gestor", "Encarregado", "VENDAS", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
        "modo_venda_itens_curva.py": ["Gestor", "Encarregado", "VENDAS", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
        "modo_vendas_sem_curva.py": ["Gestor", "Encarregado", "VENDAS", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
        "mapa_calor.py": ["Gestor", "Encarregado", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
        "entrega_em_40.py": ["Gestor", "Encarregado", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
        "abastecimento_veic.py": ["Gestor", "Contas_pagar", "Compras", "Estagiário de TI", "Sócio"],
        "entrega_logistica.py": ["Gestor", "Contas_pagar", "Compras", "Estagiário de TI", "Sócio"]
    }
    
    PAGES = [
        {"file": "page1.py", "label": "DASHBOARD E MÉTRICAS DA AUTO GERAL", "permitir": None},
        {"file": "centro_custo.py", "label": "Centro de custo", "permitir": PERMISSIONS.get("centro_custo.py")},
        {"file": "custo_entrega.py", "label": "Custo de entrega", "permitir": PERMISSIONS.get("custo_entrega.py")},
        {"file": "custos.py", "label": "Custos", "permitir": PERMISSIONS.get("custos.py")},
        {"file": "mapa_calor.py", "label": "Mapa de Calor", "permitir": PERMISSIONS.get("mapa_calor.py")},
        {"file": "modo_venda_itens_curva.py", "label": "Vendas intens e curva", "permitir": PERMISSIONS.get("modo_venda_itens_curva.py")},
        {"file": "modo_vendas_sem_curva.py", "label": "Vendas sem curva", "permitir": PERMISSIONS.get("modo_vendas_sem_curva.py")},
        {"file": "entrega_em_40.py", "label": "Indicadores de Entregas", "permitir": PERMISSIONS.get("entrega_em_40.py")},
        {"file": "abastecimento_veic.py", "label": "Custo combustivel frota", "permitir": PERMISSIONS.get("abastecimento_veic.py")},
        {"file": "entrega_logistica.py", "label": "Entrega Logística", "permitir": PERMISSIONS.get("entrega_logistica.py")},

    ]
    
    @classmethod
    def has_access(cls, page_file: str, user_role: str) -> bool:
        """Verifica se usuário tem acesso à página"""
        permissions = cls.PERMISSIONS.get(page_file)
        return permissions is None or user_role in permissions

class Navigation:
    """Gerencia navegação e sidebar"""
    
    def __init__(self):
        self.auth_manager = AuthManager()
        self.access_control = AccessControl()
    
    def get_current_page_name(self) -> str:
        """Retorna nome da página atual"""
        ctx = get_script_run_ctx()
        if not ctx:
            return "app"
        pages = get_pages("")
        return pages.get(ctx.page_script_hash, {}).get("page_name", "app")
    
    def logout(self):
        """Executa logout do usuário"""
        st.session_state["logged_in"] = False
        st.session_state["user_info"] = None
        st.info("Até breve!")
        sleep(1)
        st.switch_page("app.py")
    
    def render_user_info(self, user_info: dict):
        """Renderiza informações do usuário"""
        cargo_usuario = user_info["cargo"]
        nome_usuario = user_info["name"]
        
        st.write(f"**Cargo:** {cargo_usuario}")
        st.write(f"**Usuario:** {nome_usuario}")
        st.markdown("### Acessos Disponíveis:")
        
        # Exibe páginas permitidas
        for pagina in self.access_control.PAGES:
            if pagina["permitir"] is None or cargo_usuario in pagina["permitir"]:
                st.page_link(f"pages/{pagina['file']}", label=pagina["label"])
    
    def make_sidebar(self):
        """Cria sidebar com navegação"""
        with st.sidebar:
            st.title("Painéis de Gestão da Auto Geral")
            
            if not st.session_state.get("logged_in"):
                self.auth_manager.login_flow()
                return
            
            user_info = st.session_state.get("user_info", {})
            
            if user_info and user_info.get("cargo") and user_info.get("name"):
                self.render_user_info(user_info)
                
                if st.button("Sair"):
                    self.logout()
            
            elif st.session_state.get("logged_in", False):
                st.error("Seu perfil não possui cargo definido. Entre em contato com o suporte.")
                if st.button("Sair"):
                    self.logout()
            
            else:
                # Redireciona para login se não estiver na página inicial
                if self.get_current_page_name() != "app":
                    st.switch_page("app.py")

# Função global para manter compatibilidade
def make_sidebar():
    """Função global para compatibilidade com código existente"""
    navigation = Navigation()
    navigation.make_sidebar()