import streamlit as st
from sqlalchemy import create_engine
import pandas as pd
from typing import Optional

class DatabaseManager:
    """Gerenciador de conexões com banco de dados"""
    
    _engine = None
    
    @classmethod
    def get_engine(cls):
        """Retorna engine de conexão (singleton)"""
        if cls._engine is None:
            config = st.secrets["connections"]["mysql"]
            url = f"{config['dialect']}://{config['username']}:{config['password']}@" \
                  f"{config['host']}:{config['port']}/{config['database']}"
            cls._engine = create_engine(url, pool_pre_ping=True)
        return cls._engine
    
    @classmethod
    def execute_query(cls, query: str) -> pd.DataFrame:
        """Executa query e retorna DataFrame"""
        try:
            return pd.read_sql_query(query, cls.get_engine())
        except Exception as e:
            st.error(f"Erro na consulta: {e}")
            return pd.DataFrame()

def criar_conexao():
    """Função de compatibilidade - retorna engine"""
    return DatabaseManager.get_engine()
def get_user_cargo(user_email: str) -> Optional[dict]:
    """Busca cargo do usuário por email"""
    engine = DatabaseManager.get_engine()
    
    query = """
    SELECT ad.NOME, ad.CARGO, ad.E_MAIL  
    FROM acessos_dbf ad
    WHERE ad.E_MAIL = %(email)s
    """
    
    try:
        df = pd.read_sql_query(query, engine, params={'email': user_email})
        if not df.empty:
            return {
                "name": df["NOME"].iloc[0],
                "email": user_email,
                "cargo": df["CARGO"].iloc[0]
            }
    except Exception as e:
        st.error(f"Erro ao buscar usuário: {e}")
    
    return None