# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
```bash
# Install dependencies with Poetry
poetry install

# Run the application locally
streamlit run app.py

# Alternative: Run with Poetry
poetry run streamlit run app.py
```

### Docker Development
```bash
# Build and run with Docker Compose
docker compose up --build -d

# View container logs
docker logs <container_id>

# The application will be available at the ngrok URL displayed in logs
```

### Dependencies Management
- **Package Manager**: Poetry (pyproject.toml) with fallback to pip (requirements.txt)
- **Python Version**: 3.12
- **Key Dependencies**: Streamlit, Pandas, MySQL connectors, MSAL for Azure auth, Plotly/Matplotlib for visualization

## Architecture Overview

### Core Structure
This is a **Streamlit-based dashboard application** for Auto Geral's operational analytics with the following key architectural components:

#### Authentication & Authorization System
- **Azure AD Integration**: Uses MSAL (Microsoft Authentication Library) for OAuth 2.0 authentication
- **Role-based Access Control**: Implemented in `navigation.py` with granular permissions per dashboard
- **User Roles**: Gestor, Encarregado, VENDAS, Estagiário de TI, Sócio, Desenvolvedora de Software, Contas_pagar, Compras
- **Database Integration**: User verification against MySQL `acessos_dbf` table

#### Core Modules
- **`app.py`**: Main application entry point, handles authentication flow and initial routing
- **`navigation.py`**: Central navigation system with role-based page access control
- **`core/auth.py`**: MSAL authentication configuration and token management
- **`core/db.py`**: Database connection management (singleton pattern) and user lookup functions

#### Dashboard Pages Architecture
All dashboard pages located in `/pages/` directory follow a consistent pattern:
- Import `navigation.py` for sidebar rendering
- Use `core/db.py` for database connections
- Implement caching with Streamlit's `@st.cache_data`
- Follow role-based access restrictions defined in `navigation.py`

#### Key Dashboard Categories
1. **Financial Analysis**: Centro de custos, análise de custos de entrega, combustível
2. **Logistics & Delivery**: Entregas em 40min, tipos de entrega, rotas
3. **Sales Analysis**: Vendas com/sem curva ABC, produtos cruzados
4. **Fleet Management**: Veículos Cobli, abastecimento
5. **Heat Maps**: Temporal analysis por horas/meses

### Database Integration
- **Primary Database**: MySQL via SQLAlchemy with PyMySQL driver
- **Connection Pattern**: Singleton DatabaseManager in `core/db.py`
- **Cloud SQL Proxy**: Used in Docker deployment for Google Cloud SQL connection

### Deployment Architecture
- **Local**: Direct Streamlit execution
- **Docker**: Multi-service container with Cloud SQL Proxy and ngrok tunneling
- **Production URL**: Static ngrok domain for consistent Azure AD redirect URI
- **Port Configuration**: Streamlit runs on port 9000, ngrok exposes via HTTPS

## Configuration Requirements

### Streamlit Secrets (`.streamlit/secrets.toml`)
```toml
[connections.mysql]
dialect = "mysql+pymysql"
username = "database_username"
password = "database_password"
host = "database_host"
port = 3306
database = "autogeral"

[oauth]
client_id = "azure_client_id"
client_secret = "azure_client_secret"
tenant_id = "azure_tenant_id"

[cobli]
key = "cobli_api_key"
```

### Environment Variables
- `REDIRECT_URI`: Azure AD redirect URI (set automatically in Docker via start.sh)
- `NGROK_AUTHTOKEN`: Required for ngrok tunneling in Docker deployment

## Key Development Patterns

### Database Queries
```python
from core.db import DatabaseManager

# Use the singleton pattern
df = DatabaseManager.execute_query("SELECT * FROM table")
```

### Page Access Control
```python
from navigation import make_sidebar

# Every page should call this for consistent navigation
make_sidebar()
```

### Caching Pattern
```python
@st.cache_data
def load_data():
    return DatabaseManager.execute_query(query)
```

## Important Notes

- **Azure AD Configuration**: Redirect URI must match the ngrok domain in `start.sh`
- **Database Security**: All user authentication goes through `get_user_cargo()` function
- **Role Management**: Page access permissions are centrally managed in `navigation.py`
- **API Integrations**: Cobli API integration for real-time vehicle tracking
- **Deployment**: Uses static ngrok domain for consistent production URLs