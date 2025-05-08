from core.auth import get_msal_app, fetch_user_data
# removido para modularização
import streamlit as st
from time import sleep
from core.db import get_user_cargo
import os

# Configurações do Microsoft OAuth
CLIENT_ID = st.secrets["oauth"]["client_id"]
CLIENT_SECRET = st.secrets["oauth"]["client_secret"]
TENANT_ID = st.secrets["oauth"]["tenant_id"]
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://default-url.ngrok-free.app/")
SCOPES = ["User.Read"]

st.title("Painéis de gestão da Auto Geral")


# # função movida para core/auth.py
# def get_msal_app_old() -> ConfidentialClientApplication:
#     """Instancia e retorna o objeto MSAL para autenticação."""
#     return ConfidentialClientApplication(
#         CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
#     )


def fetch_user_data(auth_code: str) -> dict:
    """
    Busca os dados do usuário utilizando o código de autorização.
    Retorna o dicionário com a resposta do token.
    """
    app = get_msal_app()
    token_response = app.acquire_token_by_authorization_code(
        code=auth_code, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    return token_response


def display_login():
    """Exibe um botão para que o usuário inicie o fluxo OAuth."""
    st.write("### Faça login com sua conta da Auto Geral.")
    
    app = get_msal_app()
    auth_url = app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)

    if st.button("Fazer Login"):
        # st.write("Redirecionando para a página de autenticação...")
        st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)

def user_details_form() -> dict:
    """
    Exibe um formulário para coletar informações adicionais do usuário.
    Retorna um dicionário com os dados informados ou um dicionário vazio se houver erro.
    """
    st.write("Por favor, complete as informações adicionais:")
    with st.form("user_details_form", clear_on_submit=True):
        user_email = st.text_input("Digite seu e-mail da Auto Geral")
        submitted = st.form_submit_button("Enviar")

    if submitted:
        # Consulta o banco de dados para obter o cargo do usuário
        user_info = get_user_cargo(user_email)
        if not user_info:
            st.error("Usuário não encontrado ou sem permissões.")
            return {}
        return user_info
    return {}


def login_flow():
    """
    Gerencia o fluxo completo de login:
      - Verifica se há código de autorização na URL.
      - Tenta obter o token de acesso e os dados do usuário.
      - Exibe o formulário para informações adicionais e valida os dados.
      - Se tudo estiver correto, atualiza a sessão e redireciona para a página principal.
    """
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params["code"][0]
        token_response = fetch_user_data(auth_code)
        # if "access_token" not in token_response:
        #     st.error("Falha na autenticação. Tente novamente.")
        #     return

        # Armazena informações básicas obtidas do token
        id_token_claims = token_response.get("id_token_claims", {})
        st.session_state["user"] = {
            "name": id_token_claims.get("name", "Usuário"),
            "email": id_token_claims.get("preferred_username", "Email não encontrado"),
            "access_token": token_response.get("access_token")
        }

        # Solicita informações adicionais do usuário
        additional_info = user_details_form()
        if additional_info:
            # Atualiza a sessão com as informações completas do usuário
            st.session_state["user_info"] = {
                **st.session_state["user"],
                "cargo": additional_info["cargo"],
                "name": additional_info["name"]
            }
            st.session_state["logged_in"] = True
            st.success(
                f"Bem-vindo, {additional_info['name']}! cargo: {additional_info['cargo']}."
            )
            sleep(1)
            st.switch_page("pages/page1.py")
        # Caso o formulário não tenha sido submetido corretamente, a página permanecerá para nova tentativa.
    else:
        display_login()


def main():
    if not st.session_state.get("logged_in"):
        login_flow()
    else:
        st.success("Você já está logado!")
        st.switch_page("pages/page1.py")

if __name__ == "__main__":
    main()

