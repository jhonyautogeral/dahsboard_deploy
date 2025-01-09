import streamlit as st

title = 'Painel de vendas por vendedor'
st.set_page_config(page_title=title)
st.title(title)
st.sidebar.title(title)

st.text('Meta mensal')
st.text('Vendas totais')
st.text('Vendas na loja física')
st.text('Vendas que faltaram para bater a meta')

st.text('Orçamentos relizados')
st.text('Orçamentos fechados')

st.text('Itens vendidos')
st.text('Itens devolvidos')

st.text('Não entregas (clientes ausente ou pedentede pagamento)')
