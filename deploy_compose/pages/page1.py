import streamlit as st
from navigation import make_sidebar
make_sidebar()

# st.set_page_config(page_title="Entrega e suas métricas", layout="wide")

st.write("### Bem-vindo ao dashboard de métricas da Auto Geral.")
# Caminho para o arquivo da imagem
image_path = "pages/logo_autogral.jpg"


# Exibindo a imagem
st.image(image_path, caption="", width=300)
