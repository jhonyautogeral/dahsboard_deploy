import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine

class CobliAPI:
    def __init__(self):
        self.api_key = "QCu90NE.ab270a00-a3d6-406c-92fc-d24c10605a50"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "cobli-api-key": self.api_key
        }
    
    def get_motor_data(self, start_date, end_date):
        url = "https://api.cobli.co/public/v1/idle-engine/vehicle"
        payload = {
            "report_type": "PERIODICAL",
            "idle_engine_threshold_in_minutes": 3,
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "America/Sao_Paulo"
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json() if response.status_code == 200 else []
    
    def get_vehicles_list(self):
        url = "https://api.cobli.co/public/v1/vehicles?limit=2000&page=1"
        headers_get = {
            "accept": "application/json",
            "cobli-api-key": self.api_key
        }
        
        response = requests.get(url, headers=headers_get)
        return response.json().get('data', []) if response.status_code == 200 else []

def minutes_to_hms(minutes):
    if not minutes:
        return "00:00:00"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    secs = int((minutes % 1) * 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"

def hms_to_minutes(hms_str):
    """Converte HH:MM:SS para minutos"""
    if not hms_str or hms_str == "00:00:00":
        return 0
    parts = hms_str.split(':')
    return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60

def format_percentage(value):
    return f"{value * 100:.2f}%" if value else "0.00%"

# Função para criar conexão com o banco de dados
def criar_conexao():
    config = st.secrets["connections"]["mysql"]
    url = f"{config['dialect']}://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    return create_engine(url)

def get_entregadores_data():
    """Busca dados dos entregadores do banco"""
    try:
        engine = criar_conexao()
        query = """
        SELECT 
            E.LOJA_PRINCIPAL,
            E.DESCRICAO,
            E.ENTREGADOR_TIPO,
            E.COBL_CODE,
            E.COBL_ID
        FROM entregador E
        WHERE E.ATIVO = 1 
        AND E.COBL_ID IS NOT NULL 
        AND E.COBL_ID != ''
        """
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco: {e}")
        return pd.DataFrame()

def main():
    st.title("📊 Dashboard Cobli - Análise de Frota")
    st.markdown("---")
    
    # Sidebar para filtros
    st.sidebar.header("⚙️ Configurações")
    
    # Seleção de datas
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Data Inicial",
            value=datetime.now() - timedelta(days=15)
        )
    with col2:
        end_date = st.date_input(
            "Data Final",
            value=datetime.now()
        )
    
    # Botão para buscar dados
    if st.sidebar.button("🔍 Buscar Dados", type="primary"):
        # Formatar datas
        start_str = f"{start_date.strftime('%Y-%m-%d')}T00:00:00-03:00"
        end_str = f"{end_date.strftime('%Y-%m-%d')}T23:59:59-03:00"
        
        # Inicializar API
        api = CobliAPI()
        
        with st.spinner("Buscando dados da API..."):
            motor_data = api.get_motor_data(start_str, end_str)
            vehicles_data = api.get_vehicles_list()
        
        if not motor_data:
            st.error("Nenhum dado encontrado para o período selecionado.")
            return
        
        # Buscar dados dos entregadores do banco
        entregadores_df = get_entregadores_data()
        
        if entregadores_df.empty:
            st.warning("Não foi possível carregar dados dos entregadores do banco.")
            return
        
        # Processar dados
        motor_df = pd.DataFrame([{
            'motor_id': item['vehicle']['id'],
            'license_plate': item['vehicle']['license_plate'],
            'grupo_nome': item['vehicle']['group']['name'],
            'marca': item['vehicle']['brand'],
            'modelo': item['vehicle']['model'],
            'tempo_ocioso_min': item['total_idle_in_minutes'],
            'tempo_ocioso': minutes_to_hms(item['total_idle_in_minutes']),
            'percentual_ocioso': item['percentage_idle'],
            'percentual_uso_motor': item['percentage_engine_usage'],
            'consumo_combustivel': f"{item['fuel_consumption']:.2f}L",
            'custo_combustivel': f"R$ {item['fuel_costs']:.2f}",
            'total_paradas': item['total_stop_count']
        } for item in motor_data])
        
        vehicles_df = pd.DataFrame([{
            'lista_id': vehicle['id'],
            'last_driver_name': vehicle['last_driver_name'],
            'license_plate_lista': vehicle['license_plate'],
            'grupo_nome_lista': vehicle['groups'][0]['name'] if vehicle['groups'] else 'Sem grupo'
        } for vehicle in vehicles_data])
        
        # Fazer join
        merged_df = motor_df.merge(
            vehicles_df, 
            left_on='motor_id', 
            right_on='lista_id', 
            how='inner'
        )
        
        # Join com dados dos entregadores
        merged_df = merged_df.merge(
            entregadores_df,
            left_on='last_driver_name',
            right_on='DESCRICAO',
            how='left'
        )
        
        # Métricas resumo no início
        st.subheader("📈 Resumo Geral")
                
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Veículos Ativos", len(merged_df))
        
        
        # Tabelas de ranking
        st.markdown("### 🏆 Rankings")
        
        # Dados para os rankings
        ranking_motoristas = merged_df.groupby(['DESCRICAO', 'LOJA_PRINCIPAL']).agg({
            'tempo_ocioso_min': 'sum'
        }).reset_index()
        ranking_motoristas['Tempo Ocioso'] = ranking_motoristas['tempo_ocioso_min'].apply(minutes_to_hms)
        ranking_motoristas = ranking_motoristas.rename(columns={
            'DESCRICAO': 'Motorista',
            'LOJA_PRINCIPAL': 'Loja'
        })
        
        # Dados para ranking por loja
        ranking_lojas = merged_df.groupby('LOJA_PRINCIPAL').agg({
            'tempo_ocioso_min': 'sum'
        }).reset_index()
        ranking_lojas['Tempo Ocioso'] = ranking_lojas['tempo_ocioso_min'].apply(minutes_to_hms)
        ranking_lojas = ranking_lojas.rename(columns={'LOJA_PRINCIPAL': 'Loja'})
        
        # Layout em 2 colunas
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Top 5 Motoristas + Tempo Ocioso")
            top5_mais = ranking_motoristas.nlargest(5, 'tempo_ocioso_min')[['Motorista', 'Tempo Ocioso', 'Loja']]
            st.dataframe(top5_mais, hide_index=True, use_container_width=True)
            
            st.markdown("#### Lojas + Tempo Ocioso")
            lojas_mais = ranking_lojas.nlargest(5, 'tempo_ocioso_min')[['Loja', 'Tempo Ocioso']]
            st.dataframe(lojas_mais, hide_index=True, use_container_width=True)
        
        with col2:
            st.markdown("#### Top 5 Motoristas - Tempo Ocioso")
            top5_menos = ranking_motoristas.nsmallest(5, 'tempo_ocioso_min')[['Motorista', 'Tempo Ocioso', 'Loja']]
            st.dataframe(top5_menos, hide_index=True, use_container_width=True)
            
            st.markdown("#### Lojas - Tempo Ocioso")
            lojas_menos = ranking_lojas.nsmallest(5, 'tempo_ocioso_min')[['Loja', 'Tempo Ocioso']]
            st.dataframe(lojas_menos, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        
        # Tabela individual
        st.subheader("📋 Dados Individuais por Veículo")
        individual_df = merged_df[[
            'grupo_nome', 'license_plate', 'DESCRICAO', 'LOJA_PRINCIPAL', 'modelo',
            'tempo_ocioso', 'percentual_ocioso', 'percentual_uso_motor',
            'consumo_combustivel', 'custo_combustivel', 'total_paradas'
        ]].rename(columns={
            'grupo_nome': 'Grupo',
            'license_plate': 'Placa',
            'DESCRICAO': 'Motorista',
            'LOJA_PRINCIPAL': 'Loja',
            'modelo': 'Modelo',
            'tempo_ocioso': 'Tempo Ocioso',
            'percentual_ocioso': '% Ocioso',
            'percentual_uso_motor': '% Uso Motor',
            'consumo_combustivel': 'Consumo (L)',
            'custo_combustivel': 'Custo Combustível',
            'total_paradas': 'Total Paradas'
        })
        
        # Filtrar apenas registros com motorista válido (com COBL_ID)
        individual_df = individual_df[individual_df['Motorista'].notna()]
        
        # Ordenar por grupo
        individual_df['grupo_num'] = individual_df['Grupo'].str.extract(r'(\d+)').fillna(0).astype(int)
        individual_df = individual_df.sort_values(['grupo_num', 'Placa']).drop('grupo_num', axis=1)
        
        st.dataframe(individual_df, use_container_width=True)
        
        # Tabela agrupada
        st.subheader("📊 Dados Agrupados por Grupo e Motorista")
        
        # Filtrar apenas registros com motorista válido para agrupamento
        merged_valid = merged_df[merged_df['DESCRICAO'].notna()]
        
        # Agrupar dados
        grouped_data = []
        for (grupo, motorista, loja), group in merged_valid.groupby(['grupo_nome', 'DESCRICAO', 'LOJA_PRINCIPAL']):
            total_tempo_min = group['tempo_ocioso_min'].sum()
            avg_percentual_ocioso = group['percentual_ocioso'].mean()
            avg_percentual_uso = group['percentual_uso_motor'].mean()
            total_veiculos = len(group)
            
            grouped_data.append({
                'Grupo': grupo,
                'Motorista': motorista,
                'Loja': loja,
                'Tempo Total Ocioso': minutes_to_hms(total_tempo_min),
                '% Ocioso Médio': format_percentage(avg_percentual_ocioso),
                '% Uso Motor Médio': format_percentage(avg_percentual_uso),
                'Qtd Veículos': total_veiculos
            })
        
        grouped_df = pd.DataFrame(grouped_data)
        
        # Ordenar por grupo
        grouped_df['grupo_num'] = grouped_df['Grupo'].str.extract(r'(\d+)').fillna(0).astype(int)
        grouped_df = grouped_df.sort_values(['grupo_num', 'Motorista']).drop('grupo_num', axis=1)
        
        st.dataframe(grouped_df, use_container_width=True)

if __name__ == "__main__":
    main()