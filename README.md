
# Projeto de Dashboards com Streamlit 🚀

Este projeto utiliza **Python + Streamlit** para visualização de dados operacionais da Auto Geral.

## ✅ Funcionalidades

- Autenticação via Azure (MSAL)
- Conexão com MySQL
- Dashboards multipágina
- Gráficos interativos
- Suporte a Docker

## ▶️ Como rodar localmente (Você deve ter o poetry instalado em sua maquina)

```bash
poetry install
streamlit run app.py
```

## 🐳 Como rodar com Docker

```bash
docker compose up --build -d
```

```bash
docker logs
```

### ✅ Rodar docker logs (id) do container e Acessar o link do site gerado atualmente com ngrok


## 🌐 Variáveis de Ambiente

- `REDIRECT_URI`: URL de redirecionamento para OAuth
- Secrets: Configurar `secrets.toml` com client_id, tenant_id, etc.

## 📁 Estrutura

```
core/
├── auth.py         # Autenticação Azure
├── db.py           # Conexão com banco
pages/              # Dashboards por tema
```
