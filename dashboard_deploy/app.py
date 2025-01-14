from msal import ConfidentialClientApplication
import streamlit as st
from time import sleep
# from navigation import make_sidebar
# make_sidebar()

import os

# Microsoft OAuth Configurations
CLIENT_ID = st.secrets["oauth"]["client_id"]
CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
TENANT_ID = st.secrets["oauth"]["tenant_id"]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://default-url.ngrok-free.app/")
SCOPES = ["User.Read"]

st.title("Painéis de gestão da Auto Geral")

def fetch_user_data(auth_response):
    app = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
    return app.acquire_token_by_authorization_code(code=auth_response, scopes=SCOPES, redirect_uri=REDIRECT_URI)

def login_page():
    st.write("Faça login com sua conta da Auto Geral.")
    if not st.session_state.get("user"):
        app = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
        auth_url = app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)
        st.markdown(f"Faça login clicando [aqui]({auth_url})")

        if "code" in st.query_params:
            auth_response = st.query_params.get("code", [None])[0]
            if auth_response:
                user_data = fetch_user_data(auth_response)
                if user_data:
                    st.session_state["user"] = {
                        "name": user_data.get("id_token_claims", {}).get("name", "Usuário"),
                        "email": user_data.get("id_token_claims", {}).get("preferred_username", "Email não encontrado")
                    }
                    st.session_state["logged_in"] = True
                    st.success(f"Bem-vindo, {st.session_state['user']['name']}!")
                    sleep(1)
                    st.switch_page("pages/page1.py")
                    st.rerun()
                else:
                    st.error("Falha na autenticação. Tente novamente.")

def main():
    if not st.session_state.get("user"):
        login_page()
    else:
        st.success("Você já está logado!")
        sleep(1)
        st.switch_page("pages/page1.py")
        st.rerun()
if __name__ == "__main__":
    main()
