import streamlit as st
from time import sleep
from app import login_flow
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.source_util import get_pages

# Dicionário de controle de acesso: arquivo -> lista de cargos permitidos
ACCESS_CONTROL = {
    "modo_vendas.py": ["Gestor","Encarregado","VENDAS", "Estagiário de TI","Sócio", "Desenvolvedora de Software"],
    "mapa_calor.py": ["Gestor","Encarregado", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
    "totais_entrega.py": ["Gestor","Encarregado", "Estagiário de TI", "Sócio", "Desenvolvedora de Software"],
    # "entrega_completa.py": ["Gestor","Encarregado", "Estagiário de TI", "Sócio"],
    # "custo-frota.py": ["Gestor","Contas_pagar", "Estagiário de TI", "Sócio"],
    "02margens.py": ["Gestor","VENDAS", "Contas_pagar", "Compras", "Sócio", "Estagiário de TI"],
    "manutencao_custo_frota.py": ["Gestor","Contas_pagar", "Compras", "Estagiário de TI", "Sócio"],
    "abastecimento_veic.py": ["Gestor","Contas_pagar", "Compras", "Estagiário de TI", "Sócio"]
}

PAGES = [
    {"file": "page1.py", "label": "DASHBOARD E MÉTRICAS DA AUTO GERAL", "permitir": None},  # Acesso livre
    {"file": "mapa_calor.py", "label": "Mapa de Calor", "permitir": ACCESS_CONTROL.get("mapa_calor.py")},
    {"file": "02margens.py", "label": "02Magens", "permitir": ACCESS_CONTROL.get("02margens.py")},
    {"file": "modo_vendas.py", "label": "Modo Vendas", "permitir": ACCESS_CONTROL.get("modo_vendas.py")},
    {"file": "entrega_em_40.py", "label": "Indicadores de Entregas", "permitir": ACCESS_CONTROL.get("entrega_em_40.py")},
    # {"file": "entrega_completa.py", "label": "Entrega Completa", "permitir": ACCESS_CONTROL.get("entrega_completa.py")},
    # {"file": "custo-frota.py", "label": "Custo da Frota", "permitir": ACCESS_CONTROL.get("custo-frota.py")},
    {"file": "abastecimento_veic.py", "label": "Custo combustivel frota", "permitir": ACCESS_CONTROL.get("abastecimento_veic.py")},
    {"file": "manutencao_custo_frota.py", "label": "Manutenção Custo Frota", "permitir": ACCESS_CONTROL.get("manutencao_custo_frota.py")},
]

def get_current_page_name():
    ctx = get_script_run_ctx()
    if not ctx:
        return "app"  # Fallback para página inicial
    pages = get_pages("")
    return pages.get(ctx.page_script_hash, {}).get("page_name", "app")

def make_sidebar():
    with st.sidebar:
        st.title("Painéis de Gestão da Auto Geral")
        # chamar função login_flow em app para seber qual cargo o usuário pertence com email da Auto Geral
        if not st.session_state.get("logged_in"):
            login_flow()
        # Agora utilizamos "user_info" (armazenado após o login) para obter os dados do usuário
        user_info = st.session_state.get("user_info",{})
        
        if user_info and user_info.get("cargo") and user_info.get("name"):
            cargo_usuario = user_info["cargo"]
            nome_usuario = user_info["name"]
            st.write(f"**Cargo:** {cargo_usuario}")
            st.write(f"**Usuario:** {nome_usuario}")
            st.markdown("### Acessos Disponíveis:")
            
            # Exibe apenas as páginas permitidas de acordo com o cargo do usuário
            for pagina in PAGES:
                if pagina["permitir"]:
                    if cargo_usuario in pagina["permitir"]:
                        st.page_link(f"pages/{pagina['file']}", label=pagina["label"])
                else:
                    # Se não houver regra definida, libera acesso
                    st.page_link(f"pages/{pagina['file']}", label=pagina["label"])
            
            if st.button("Sair"):
                logout()
        elif st.session_state.get("logged_in", False):
            # Usuário está logado, mas não possui cargo definido
            st.error("Seu perfil não possui cargo definido. Entre em contato com o suporte.")
            if st.button("Sair"):
                logout()
        else:
            # Usuário não logado: redireciona para a página de login, se não estiver nela
            if get_current_page_name() != "app":
                st.switch_page("app.py")  # Redireciona para a página inicial

def logout():
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None
    st.info("Até breve!")
    sleep(1)
    st.switch_page("app.py")
