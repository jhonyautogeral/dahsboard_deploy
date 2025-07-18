# Projeto de Dashboards com Streamlit 🚀

Este projeto utiliza **Python + Streamlit** para visualização de dados operacionais da Auto Geral.

Projeto funcional em deploy link: https://github.com/jhonyautogeral/dahsboard_deploy

## ✅ Funcionalidades

- Autenticação via Azure (MSAL)
- Conexão com MySQL
- Dashboards multipágina
- Gráficos interativos
- Suporte a Docker

## 📊 Dashboards Disponíveis

### 💰 Página CUSTOS
- Soma total de custos por loja
- Filtros por Data e Loja
- Custos incluídos:
  - FROTA/ABASTECIMENTO
  - FROTA/MANUTENCAO
  - FROTA/COBLI
  - FROTA/PEDAGIO
  - FROTA/MULTA

### 🚗 Custos de Abastecimento
- Custos detalhados por veículo
- Análise individual de cada unidade da frota

### 📦 CUSTO DE ENTREGA
- Soma de todos os custos dividido pela quantidade de entregas
- Análise de eficiência logística

### 📈 Vendas
- **Vendas Itens e Curva**: Análise com curva ABC/XYZ
- **Vendas Itens sem Curva**: Dados brutos de vendas

### 🚚 Entrega Logística
- Eficiência do entregador
- Tempo de entrega
- Tempo de separação
- Entregas ≤ 7km
- Entregas > 40km

### ⏱️ Indicadores de Entrega
- Entregas em até 40 minutos
- Entregas com mais de 40 minutos
- Análise de performance temporal

### ⛽ CUSTO COMBUSTÍVEL FROTA
- Gráfico e tabela com custo de combustível por loja
- **Nota**: Dados não vêm da tabela 'COM_RATEIOS' - precisa ser avaliado

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
├── custos.py       # Página de custos gerais
├── abastecimento.py # Custos por veículo
├── custo_entrega.py # Custo por entrega
├── vendas.py       # Vendas com/sem curva
├── logistica.py    # Entrega logística
├── indicadores.py  # Indicadores de entrega
└── combustivel.py  # Custo combustível
```
