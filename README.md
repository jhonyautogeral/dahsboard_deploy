# Projeto de Dashboards com Streamlit 🚀

Este projeto utiliza **Python + Streamlit** para visualização de dados operacionais da Auto Geral.

Projeto funcional em deploy link: https://github.com/jhonyautogeral/dahsboard_deploy

## ✅ Funcionalidades

- Autenticação via Azure (MSAL)
- Conexão com MySQL
- Dashboards multipágina
- Gráficos interativos
- Suporte a Docker
- Sistema de controle de acesso por cargo
- APIs integradas (Cobli)

## 📊 Dashboards Disponíveis

### 💰 Análises Financeiras e Custos

#### **Centro de Custos** (`centro_custo.py`)
- Análise de custos por categoria (FROTA, RASTREADOR, MOTOBOY, etc.)
- Filtros por ano, data personalizada e custo total por lojas
- Visualizações com gráficos e tabelas detalhadas
- Métricas principais e insights automáticos

#### **Custos de Entrega** (`custo_entrega.py`)
- Análise de custo por entrega (TODAS, CLIENTES, ROTA)
- Cálculo de eficiência logística
- Comparativo entre tipos de entrega
- Filtros por período e configurações flexíveis

#### **Análise de Custos Totais** (`custos.py`)
- Custos detalhados por loja, descrição e atividade
- Filtros por data, loja e tipo de custo
- Visualizações com gráficos de barras, linhas e pizza
- Análise por veículo e placas
- Download de dados em Excel

#### **Custo de Combustível da Frota** (`abastecimento_veic.py`)
- Custos detalhados por veículo
- Análise por ano, mês e semana
- Comparativo mensal e anual com variações percentuais
- Gráficos de tendência e tabelas pivot

### 🚚 Gestão de Entregas e Logística

#### **Indicadores de Entregas** (`entrega_em_40.py`)
- Entregas em até 40 minutos vs mais de 40 minutos
- Análise por ano, mês e data personalizada
- Porcentagem de entregas por loja
- Tabelas e gráficos de performance

#### **Entrega Logística 40** (`entrega_logistica_40.py`)
- Análise de performance logística detalhada
- Eficiência dos entregadores
- Tempo de entrega e separação
- Entregas ≤ 7km (meta 40min) e > 40km
- Mapas de calor por hora e dia da semana

#### **Tipos de Entrega** (`tipos_entrega.py`)
- Quantidade de entregas por tipo (TOTAL, CLIENTES, ROTA)
- Análise comparativa com venda casada
- Gráficos dinâmicos por loja
- Dashboard interativo com filtros

#### **Entregas e Rotas** (`entrega_e_rota.py`)
- Análise de entregas e métricas de rota
- Índices de entrega por placa e loja
- Comparativo mensal de performance
- Dados de transferência e venda casada

### 📈 Análises de Vendas

#### **Vendas com Curva ABC/XYZ** (`modo_venda_itens_curva.py`)
- Análise de vendas por modo (PRONTA_ENTREGA, CASADA, FUTURA)
- Curva ABC dos produtos
- Gráficos de área e barras empilhadas
- Análise por ano, mês e período personalizado
- Percentuais de distribuição

#### **Vendas sem Curva** (`modo_vendas_sem_curva.py`)
- Análise simplificada de vendas por modo
- Visualizações por período
- Gráficos comparativos e tendências
- Dados otimizados para performance

#### **Produtos Cruzados Fraga** (`produto_cruzado_fraga.py`)
- Análise de cobertura de código Fraga
- Produtos disponíveis vs total cadastrado
- Métricas por curva ABC
- Gráficos de distribuição e cobertura
- Insights automáticos

### 🗺️ Visualizações e Mapas de Calor

#### **Mapas de Calor** (`mapa_calor.py`)
- Hub principal para mapas de calor
- Acesso às análises por horas e meses

#### **Mapa de Calor por Horas** (`mapa_calor_horas.py`)
- Tempo de separação por hora/dia
- Quantidade de romaneios por período
- Tempo total de entrega
- Análise por ano, mês e semana
- Filtros por categoria de análise

#### **Mapa de Calor por Meses** (`mapa_calor_por_meses.py`)
- Análise sazonal por mês do ano
- Distribuição de atividades por dia da semana
- Tendências anuais de operação

### 🚗 Monitoramento de Frota

#### **Veículos Cobli** (`veiculos_cobli.py`)
- Monitoramento em tempo real via API Cobli
- Dispositivos por loja
- Informações de combustível e consumo
- Localização e status dos veículos
- Filtros por loja e placa

#### **Abastecimento por Veículo** (`abastecimento_veic.py`)
- Controle detalhado de abastecimento
- Análise por veículo e período
- Custos e consumo de combustível
- Relatórios de eficiência

## 🔐 Sistema de Autenticação

### **Autenticação Azure** (`auth.py`)
- Integração com Microsoft Azure AD
- Login via OAuth 2.0
- Controle de sessão

### **Controle de Acesso** (`navigation.py`)
- Sistema de permissões por cargo
- Acesso diferenciado por funcionalidade
- Cargos suportados:
  - Gestor, Encarregado, VENDAS
  - Estagiário de TI, Sócio
  - Desenvolvedora de Software
  - Contas_pagar, Compras

## 🔗 APIs e Integrações

### **API Cobli** (`api_custo_cobli.py`)
- Integração com sistema de rastreamento
- Dados de custos por período
- Processamento automático de dados

### **APIs de Custos**
- **Combustível** (`api_custo_combustivel.py`)
- **Manutenção de Frota** (`api_custo_manutencao_frota.py`)
- **Motoboy Terceirizado** (`api_custo_motoboy_tercerizado.py`)
- **Pedágio** (`api_custo_pedagio.py`)

## ▶️ Como rodar localmente

### Pré-requisitos
- Python 3.12
- Poetry instalado
- Acesso ao banco MySQL
- Configuração das secrets do Streamlit

### Instalação
```bash
poetry install
streamlit run app.py
```

### Configuração
Crie o arquivo `.streamlit/secrets.toml`:
```toml
[connections.mysql]
dialect = "mysql+pymysql"
username = "seu_usuario"
password = "sua_senha"
host = "localhost"
port = 3306
database = "autogeral"

[oauth]
client_id = "seu_client_id"
client_secret = "seu_client_secret"
tenant_id = "seu_tenant_id"

[cobli]
key = "sua_chave_cobli"
```

## 🐳 Como rodar com Docker

```bash
docker compose up --build -d
```

### Verificar logs
```bash
docker logs <container_id>
```

### ✅ Acessar aplicação
O link do site será gerado automaticamente (atualmente com ngrok)

## 🌐 Variáveis de Ambiente

- `REDIRECT_URI`: URL de redirecionamento para OAuth
- Secrets: Configurar `secrets.toml` com client_id, tenant_id, etc.

## 📁 Estrutura do Projeto

```
├── app.py                          # Aplicação principal e autenticação
├── navigation.py                   # Sistema de navegação e controle de acesso
├── core/
│   ├── auth.py                    # Autenticação Azure
│   └── db.py                      # Conexão com banco
├── pages/                         # Dashboards por funcionalidade
│   ├── page1.py                   # Dashboard principal
│   ├── centro_custo.py            # Centro de custos
│   ├── custo_entrega.py           # Análise custo por entrega
│   ├── custos.py                  # Custos totais
│   ├── abastecimento_veic.py      # Combustível da frota
│   ├── entrega_em_40.py           # Indicadores de entrega
│   ├── entrega_logistica_40.py    # Performance logística
│   ├── tipos_entrega.py           # Tipos de entrega
│   ├── entrega_e_rota.py          # Entregas e rotas
│   ├── modo_venda_itens_curva.py  # Vendas com curva ABC
│   ├── modo_vendas_sem_curva.py   # Vendas simplificadas
│   ├── produto_cruzado_fraga.py   # Produtos cruzados
│   ├── mapa_calor.py              # Hub mapas de calor
│   ├── mapa_calor_horas.py        # Mapas por hora
│   ├── mapa_calor_por_meses.py    # Mapas por mês
│   ├── veiculos_cobli.py          # Monitoramento Cobli
│   └── api_*.py                   # APIs de integração
```

## 🛠️ Tecnologias Utilizadas

- **Frontend**: Streamlit
- **Backend**: Python
- **Banco de Dados**: MySQL
- **Autenticação**: Microsoft Azure AD (MSAL)
- **Visualização**: Plotly, Matplotlib, Seaborn
- **APIs**: Cobli, APIs internas
- **Deploy**: Docker, Ngrok

## 📈 Recursos Avançados

- **Cache inteligente** para otimização de performance
- **Filtros dinâmicos** em todas as análises
- **Export de dados** em Excel
- **Gráficos interativos** com Plotly
- **Mapas de calor** para análise temporal
- **Métricas em tempo real**
- **Sistema de insights automáticos**

## 🔧 Manutenção e Desenvolvimento

Para adicionar novas funcionalidades:
1. Criar arquivo na pasta `pages/`
2. Adicionar permissões em `navigation.py`
3. Atualizar `page1.py` com nova funcionalidade
4. Testar autenticação e acesso

## 📞 Suporte

Para suporte técnico, entre em contato com a equipe de TI da Auto Geral.