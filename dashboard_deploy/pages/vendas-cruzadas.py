import streamlit as st

title = 'Índice de venda cruzada'
st.set_page_config(page_title=title, layout="wide")
st.title(title)
st.sidebar.title(title)

st.text('Qual os vendedores com maiores números de itens nos pedidos?')
st.text('Vende óleo sem filtro?')
st.text('Vende filtro sem óleo, só um filto ou vende filtro de cabine, óleo e ar(motor)?')
st.text('Vendeu turbina sozinha?')
st.text('Vende amortecedor sem kit?')
st.text('Vende kit de amortecedor sem amortecedor?')
