from core.auth import get_msal_app
from core.db import get_user_cargo
import streamlit as st
from time import sleep
import os

class AuthConfig:
    """Configurações de autenticação"""
    def __init__(self):
        self.CLIENT_ID = st.secrets["oauth"]["client_id"]
        self.CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
        self.TENANT_ID = st.secrets["oauth"]["tenant_id"]
        self.AUTHORITY = f"https://login.microsoftonline.com/{self.TENANT_ID}"
        self.REDIRECT_URI = os.getenv("REDIRECT_URI", "https://default-url.ngrok-free.app/")
        self.SCOPES = ["User.Read"]

class AuthManager:
    """Gerencia autenticação e login"""
    
    def __init__(self):
        self.config = AuthConfig()
    
    def fetch_user_data(self, auth_code: str) -> dict:
        """Busca dados do usuário com código de autorização"""
        app = get_msal_app()
        return app.acquire_token_by_authorization_code(
            code=auth_code, 
            scopes=self.config.SCOPES, 
            redirect_uri=self.config.REDIRECT_URI
        )
    
    def display_login(self):
        """Exibe botão de login OAuth"""
        st.write("### Faça login com sua conta da Auto Geral.")
        
        app = get_msal_app()
        auth_url = app.get_authorization_request_url(
            self.config.SCOPES, 
            redirect_uri=self.config.REDIRECT_URI
        )
        
        if st.button("Fazer Login"):
            st.markdown(
                f'<meta http-equiv="refresh" content="0;url={auth_url}">', 
                unsafe_allow_html=True
            )
    
    def user_details_form(self) -> dict:
        """Formulário para informações adicionais do usuário"""
        st.write("Por favor, complete as informações adicionais:")
        
        with st.form("user_details_form", clear_on_submit=True):
            user_email = st.text_input("Digite seu e-mail da Auto Geral")
            submitted = st.form_submit_button("Enviar")
        
        if submitted:
            user_info = get_user_cargo(user_email)
            if not user_info:
                st.error("Usuário não encontrado ou sem permissões.")
                return {}
            return user_info
        return {}
    
    def login_flow(self):
        """Fluxo completo de login"""
        query_params = st.query_params
        
        if "code" in query_params:
            auth_code = query_params["code"][0]
            token_response = self.fetch_user_data(auth_code)
            
            # Armazena informações básicas
            id_token_claims = token_response.get("id_token_claims", {})
            st.session_state["user"] = {
                "name": id_token_claims.get("name", "Usuário"),
                "email": id_token_claims.get("preferred_username", "Email não encontrado"),
                "access_token": token_response.get("access_token")
            }
            
            # Solicita informações adicionais
            additional_info = self.user_details_form()
            if additional_info:
                st.session_state["user_info"] = {
                    **st.session_state["user"],
                    "cargo": additional_info["cargo"],
                    "name": additional_info["name"]
                }
                st.session_state["logged_in"] = True
                st.success(f"Bem-vindo, {additional_info['name']}! Cargo: {additional_info['cargo']}")
                sleep(1)
                st.switch_page("pages/page1.py")
        else:
            self.display_login()

class App:
    """Classe principal da aplicação"""
    
    def __init__(self):
        self.auth_manager = AuthManager()
    
    def run(self):
        """Executa a aplicação"""
        st.title("Painéis de gestão da Auto Geral")
        
        if not st.session_state.get("logged_in"):
            self.auth_manager.login_flow()
        else:
            st.success("Você já está logado!")
            st.switch_page("pages/page1.py")

if __name__ == "__main__":
    app = App()
    app.run()