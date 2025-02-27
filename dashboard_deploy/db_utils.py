# db_utils.py
import streamlit as st
from sqlalchemy import create_engine
import pandas as pd

def criar_conexao():
    # Cria e retorna a conexão com o banco de dados utilizando as configurações do st.secrets.
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@" \
          f"{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

# def get_user_cargo(user_email):
#     engine = criar_conexao()
#     query = f"""
#     SELECT ad.LOGIN, ad.CARGO, ad.E_MAIL, ap.ACESSO_CODIGO 
#     FROM acessos_dbf ad
#     LEFT JOIN acessos_perfis ap ON ad.CODIGO = ap.ACESSO_CODIGO
#     WHERE ad.ativo = 1
#       AND ad.CARGO IN ('ENCARREGADO', 'COMPRAS', 'GESTOR', 'Estagiário de TI')
#       AND ad.E_MAIL = '{user_email}';
#     """

def get_user_cargo(user_email):
    engine = criar_conexao()
    query = f"""
    SELECT ad.NOME, ad.CARGO, ad.E_MAIL  
    from  acessos_dbf ad
    where CARGO in ('Encarregado', 'Compras', 'Gestor', 'Sócio','Estagiário de TI','Desenvolvedora de Software')
    and ad.E_MAIL = '{user_email}';
    """
    
    query = pd.read_sql_query(query, con= engine)
    print('Antes do filtro',query)

    user_data = query[query["E_MAIL"] == user_email]
    if not user_data.empty:
        return {
            "name": user_data["NOME"].iloc[0],  
            "email": user_email,
            "cargo": user_data["CARGO"].iloc[0]
        }
    return None
