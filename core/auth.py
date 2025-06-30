from msal import ConfidentialClientApplication
import streamlit as st
import os

class MSALConfig:
    """Configuração centralizada do MSAL"""
    def __init__(self):
        self.CLIENT_ID = st.secrets["oauth"]["client_id"]
        self.CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
        self.TENANT_ID = st.secrets["oauth"]["tenant_id"]
        self.AUTHORITY = f"https://login.microsoftonline.com/{self.TENANT_ID}"
        self.REDIRECT_URI = os.getenv("REDIRECT_URI", "https://default-url.ngrok-free.app/")
        self.SCOPES = ["User.Read"]

# Singleton para configuração
_config = None

def get_config():
    """Retorna instância única da configuração"""
    global _config
    if _config is None:
        _config = MSALConfig()
    return _config

def get_msal_app() -> ConfidentialClientApplication:
    """Retorna instância do MSAL App"""
    config = get_config()
    return ConfidentialClientApplication(
        config.CLIENT_ID, 
        authority=config.AUTHORITY, 
        client_credential=config.CLIENT_SECRET
    )

def fetch_user_data(auth_code: str) -> dict:
    """Busca dados do usuário com código de autorização"""
    config = get_config()
    app = get_msal_app()
    return app.acquire_token_by_authorization_code(
        auth_code, 
        scopes=config.SCOPES, 
        redirect_uri=config.REDIRECT_URI
    )