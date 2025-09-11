# Dashboard Auto Geral 🚀

Sistema de dashboards operacionais para análise de dados da Auto Geral, desenvolvido em **Python + Streamlit**.

## 🚀 Início Rápido

### Opção 1: Docker (Recomendado)
```bash
# 1. Clone o repositório
git clone https://github.com/jhonyautogeral/dahsboard_deploy.git
cd dahsboard_deploy

# 2. Cria pasta pasta proxy_server/
mkdir proxy_server

# 3. Execute
curl -o proxy_server/cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.10.1/cloud-sql-proxy.linux.amd64

# 4. Coloque o arquivo 'erpj-br-sql.json' na pasta proxy_server/

# 5. Execute
chmod +x proxy_server/cloud-sql-proxy

# 6. Execute o setup completo
docker compose up --build -d

# 7. Para acessar os logs 
docker logs streamlit_dashboard

# para acessar url
https://frequently-complete-cowbird.ngrok-free.app/
 
```

## ✅ Principais Funcionalidades

- **Autenticação**: Login via Azure AD com controle de acesso por cargo
- **Análises Financeiras**: Centro de custos, combustível, entregas
- **Gestão de Frota**: Monitoramento Cobli, abastecimento
- **Vendas e Logística**: Performance de entregas, tipos de venda
- **Visualizações**: Mapas de calor, gráficos interativos
- **APIs Integradas**: Cobli, sistemas internos

## ⚙️ Configuração

### Arquivo de Secrets
Crie `.streamlit/secrets.toml` com:
```toml
[connections.mysql]
dialect = "mysql+pymysql"
username = "seu_usuario"
password = "sua_senha"
host = "seu_host"
port = 3306
database = "autogeral"

[oauth]
client_id = "azure_client_id"
client_secret = "azure_client_secret" 
tenant_id = "azure_tenant_id"

[cobli]
key = "cobli_api_key"
```

### Variáveis de Ambiente
- `NGROK_AUTHTOKEN`: Token do ngrok (apenas Docker)
- `REDIRECT_URI`: URL de redirect OAuth (configurado automaticamente)

## 📊 Dashboards Principais

### 💰 Análises Financeiras
- **Centro de Custos**: Análise por categoria (FROTA, RASTREADOR, MOTOBOY)
- **Custos de Entrega**: Eficiência logística por tipo de entrega
- **Combustível**: Controle detalhado por veículo e período

### 🚚 Gestão de Entregas  
- **Performance 40min**: Entregas dentro da meta de tempo
- **Tipos de Entrega**: Comparativo TOTAL, CLIENTES, ROTA
- **Mapas de Calor**: Análise temporal por horas e meses

### 📈 Vendas e Produtos
- **Curva ABC**: Análise de vendas por modo e produto
- **Produtos Cruzados**: Cobertura código Fraga

### 🚗 Monitoramento Frota
- **Cobli**: Rastreamento em tempo real
- **Abastecimento**: Controle de combustível por veículo

## 🛠️ Tecnologias

- **Frontend**: Streamlit
- **Backend**: Python 3.12
- **Database**: MySQL
- **Auth**: Azure AD (MSAL)
- **Visualização**: Plotly, Matplotlib
- **Deploy**: Docker + ngrok

## 📁 Estrutura do Projeto
```
├── app.py              # Aplicação principal
├── navigation.py       # Controle de acesso
├── core/
│   ├── auth.py        # Autenticação Azure
│   └── db.py          # Conexão banco
├── pages/             # Dashboards
└── proxy_server/      # Docker setup
```

## 🆘 Solução de Problemas

**Erro de conexão com banco:**
- Verifique `secrets.toml` 
- Confirme acesso à rede do MySQL

**Erro de autenticação:**
- Valide client_id e tenant_id no Azure
- Confirme REDIRECT_URI

**Docker não inicia:**
- Verifique se `erpj-br-sql.json` está em `proxy_server/`
- Confirme NGROK_AUTHTOKEN configurado

## 📞 Suporte
Equipe de TI - Auto Geral