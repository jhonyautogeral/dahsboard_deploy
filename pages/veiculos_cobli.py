import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Dashboard Cobli", layout="wide")
st.title("🚗 Dashboard de Monitoramento Cobli")

# Proteção de acesso
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("Você não está logado. Redirecionando para a página de login...")
    st.switch_page("app.py")
    st.stop()

# Configuração da API
API_KEY = "QCu90NE.ab270a00-a3d6-406c-92fc-d24c10605a50"
HEADERS = {
    "accept": "application/json",
    "cobli-api-key": API_KEY
}

@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_api_data(endpoint):
    """Função para fazer requisições à API"""
    url = f"https://api.cobli.co/public/v1/{endpoint}?limit=2000&page=1"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()['data']
        else:
            st.error(f"Erro na API {endpoint}: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Erro na requisição {endpoint}: {e}")
        return []

@st.cache_data(ttl=300)
def get_device_details(device_id):
    """Busca detalhes específicos do dispositivo"""
    url = f"https://api.cobli.co/herbie-1.1/dash/device/{device_id}"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def extract_store_number(store_name):
    """Extrai o número da loja do nome"""
    try:
        if isinstance(store_name, str) and '-' in store_name:
            number_part = store_name.split('-')[0].strip()
            return int(number_part) if number_part.isdigit() else 999
        return 999
    except:
        return 999

def create_filters(df, key_suffix=""):
    """Cria filtros de loja e placa"""
    col1, col2 = st.columns(2)
    
    with col1:
        lojas = ['Todas'] + sorted(df['Loja'].unique().tolist())
        filtro_loja = st.selectbox(f"🏪 Filtrar por Loja:", lojas, key=f"loja_{key_suffix}")
    
    with col2:
        placas = ['Todas'] + sorted([p for p in df['Placa'].unique() if p != 'N/A'])
        filtro_placa = st.selectbox(f"🚙 Filtrar por Placa:", placas, key=f"placa_{key_suffix}")
    
    return filtro_loja, filtro_placa

def apply_filters(df, filtro_loja, filtro_placa):
    """Aplica os filtros no dataframe"""
    df_filtered = df.copy()
    
    if filtro_loja != 'Todas':
        df_filtered = df_filtered[df_filtered['Loja'] == filtro_loja]
    
    if filtro_placa != 'Todas':
        df_filtered = df_filtered[df_filtered['Placa'] == filtro_placa]
    
    return df_filtered

# Carregamento dos dados
with st.spinner('Carregando dados da API...'):
    devices = get_api_data("devices")
    groups = get_api_data("groups")
    vehicles = get_api_data("vehicles")

if not vehicles:
    st.error("Não foi possível carregar os dados. Verifique a API.")
    st.stop()

# TABELA 1: DISPOSITIVOS POR LOJA
st.header("📱 Dispositivos por Loja")
st.write("Listagem completa de todos os veículos com seus respectivos dispositivos e informações básicas.")

device_table = []
for vehicle in vehicles:
    if vehicle.get('groups'):
        group_name = vehicle['groups'][0]['name']
        device_data = {
            'Loja': group_name,
            'Device ID': vehicle.get('device_id', 'N/A'),
            'Placa': vehicle.get('license_plate', 'N/A'),
            'Marca': vehicle.get('brand', 'N/A'),
            'Modelo': vehicle.get('model', 'N/A'),
            'Ano': vehicle.get('year', 'N/A'),
            'Motorista': vehicle.get('last_driver_name', 'Sem motorista'),
            'Cobli ID': vehicle.get('id', 'N/A'),
            'Ativo': 'Sim' if vehicle.get('device_id') else 'Não'
        }
        device_table.append(device_data)

df_devices = pd.DataFrame(device_table)
df_devices['_sort_key'] = df_devices['Loja'].apply(extract_store_number)
df_devices = df_devices.sort_values('_sort_key').drop('_sort_key', axis=1)

# Filtros para tabela de dispositivos
filtro_loja_1, filtro_placa_1 = create_filters(df_devices, "devices")
df_devices_filtered = apply_filters(df_devices, filtro_loja_1, filtro_placa_1)

st.dataframe(df_devices_filtered, use_container_width=True)
st.write(f"📊 Mostrando {len(df_devices_filtered)} de {len(df_devices)} veículos")

# TABELA 2: RESUMO POR LOJA
st.header("📈 Resumo por Loja")
st.write("Consolidado com quantidade total de veículos, veículos ativos e amostra de placas por loja.")

summary_table = df_devices.groupby('Loja').agg({
    'Device ID': 'count',
    'Placa': lambda x: ', '.join(x.head(3)) + ('...' if len(x) > 3 else ''),
    'Ativo': lambda x: sum(1 for v in x if v == 'Sim')
}).rename(columns={
    'Device ID': 'Total Veículos',
    'Placa': 'Placas (Amostra)',
    'Ativo': 'Ativos'
})
summary_table['_sort_key'] = summary_table.index.map(extract_store_number)
summary_table = summary_table.sort_values('_sort_key').drop('_sort_key', axis=1)

# Filtro apenas por loja para resumo
lojas_resumo = ['Todas'] + sorted(summary_table.index.tolist())
filtro_loja_resumo = st.selectbox("🏪 Filtrar por Loja:", lojas_resumo, key="resumo")

if filtro_loja_resumo != 'Todas':
    summary_filtered = summary_table[summary_table.index == filtro_loja_resumo]
else:
    summary_filtered = summary_table

st.dataframe(summary_filtered, use_container_width=True)

# TABELA 3: COMBUSTÍVEL E CONSUMO
st.header("⛽ Combustível e Consumo")
st.write("Informações sobre tipo de combustível, consumo por KM e preços dos veículos.")

fuel_table = []
for vehicle in vehicles:
    if vehicle.get('groups') and vehicle.get('fuel'):
        fuel_info = vehicle['fuel']
        fuel_data = {
            'Loja': vehicle['groups'][0]['name'],
            'Placa': vehicle.get('license_plate', 'N/A'),
            'Marca': vehicle.get('brand', 'N/A'),
            'Modelo': vehicle.get('model', 'N/A'),
            'Tipo Combustível': fuel_info.get('type', 'N/A'),
            'Consumo por KM': fuel_info.get('consumption_per_km', 'N/A'),
            'Preço': fuel_info.get('price', 'N/A'),
            'Tamanho': vehicle.get('size', 'N/A')
        }
        fuel_table.append(fuel_data)

if fuel_table:
    df_fuel = pd.DataFrame(fuel_table)
    df_fuel['_sort_key'] = df_fuel['Loja'].apply(extract_store_number)
    df_fuel = df_fuel.sort_values('_sort_key').drop('_sort_key', axis=1)
    
    # Filtros para tabela de combustível
    filtro_loja_2, filtro_placa_2 = create_filters(df_fuel, "fuel")
    df_fuel_filtered = apply_filters(df_fuel, filtro_loja_2, filtro_placa_2)
    
    st.dataframe(df_fuel_filtered, use_container_width=True)
    st.write(f"📊 Mostrando {len(df_fuel_filtered)} de {len(df_fuel)} veículos com dados de combustível")
else:
    st.warning("Nenhum dado de combustível encontrado.")

# TABELA 4: MONITORAMENTO DE LOCALIZAÇÃO
st.header("📍 Monitoramento de Localização")
st.write("Últimas posições conhecidas dos dispositivos com informações de velocidade e status.")

with st.spinner('Carregando dados de localização...'):
    location_table = []
    
    # Busca detalhes de localização para alguns dispositivos
    for i, vehicle in enumerate(vehicles[:80]):  # Limita a 10 para performance
        if vehicle.get('device_id'):
            device_details = get_device_details(vehicle['device_id'])
            
            if device_details.get('last_location'):
                loc = device_details['last_location']
                location_data = {
                    'Loja': vehicle['groups'][0]['name'] if vehicle.get('groups') else 'N/A',
                    'Placa': vehicle.get('license_plate', 'N/A'),
                    'Device ID': vehicle.get('device_id'),
                    'Latitude': loc.get('latitude', 'N/A'),
                    'Longitude': loc.get('longitude', 'N/A'),
                    'Velocidade': f"{loc.get('speed', 0)} km/h",
                    'Ignição': '🟢 Ligada' if loc.get('ignition_on') else '🔴 Desligada',
                    'Conectado': '✅ Sim' if loc.get('is_plugged') else '❌ Não',
                    'Última Atualização': datetime.fromtimestamp(loc.get('time', 0)).strftime('%d/%m/%Y %H:%M')
                }
                location_table.append(location_data)

if location_table:
    df_location = pd.DataFrame(location_table)
    df_location['_sort_key'] = df_location['Loja'].apply(extract_store_number)
    df_location = df_location.sort_values('_sort_key').drop('_sort_key', axis=1)
    
    # Filtros para tabela de localização
    filtro_loja_3, filtro_placa_3 = create_filters(df_location, "location")
    df_location_filtered = apply_filters(df_location, filtro_loja_3, filtro_placa_3)
    
    st.dataframe(df_location_filtered, use_container_width=True)
    st.write(f"📊 Mostrando {len(df_location_filtered)} de {len(df_location)} dispositivos com localização")
else:
    st.warning("Nenhum dado de localização encontrado.")

# ESTATÍSTICAS GERAIS
st.header("📊 Estatísticas Gerais")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total de Veículos",
        value=len(vehicles)
    )

with col2:
    st.metric(
        label="Total de Lojas", 
        value=len(groups)
    )

with col3:
    veiculos_com_motorista = sum(1 for v in vehicles if v.get('last_driver_name'))
    st.metric(
        label="Com Motorista",
        value=veiculos_com_motorista
    )

with col4:
    veiculos_sem_motorista = sum(1 for v in vehicles if not v.get('last_driver_name'))
    st.metric(
        label="Sem Motorista",
        value=veiculos_sem_motorista
    )

# Consumo médio por tipo de combustível
if fuel_table:
    st.subheader("⛽ Consumo Médio por Tipo de Combustível")
    fuel_stats = df_fuel.groupby('Tipo Combustível')['Consumo por KM'].apply(
        lambda x: pd.to_numeric(x, errors='coerce').mean()
    ).round(2)
    
    for fuel_type, avg_consumption in fuel_stats.items():
        if pd.notna(avg_consumption):
            st.write(f"**{fuel_type}**: {avg_consumption} L/km")

st.success("✅ Dashboard carregado com sucesso!")