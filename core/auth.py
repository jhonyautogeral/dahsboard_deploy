
from msal import ConfidentialClientApplication
import streamlit as st
import os

# Configurações do Microsoft OAuth
CLIENT_ID = st.secrets["oauth"]["client_id"]
CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
TENANT_ID = st.secrets["oauth"]["tenant_id"]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://default-url.ngrok-free.app/")
SCOPES = ["User.Read"]

def get_msal_app() -> ConfidentialClientApplication:
    return ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )

def fetch_user_data(auth_code: str) -> dict:
    app = get_msal_app()
    return app.acquire_token_by_authorization_code(auth_code, scopes=SCOPES, redirect_uri=REDIRECT_URI)
