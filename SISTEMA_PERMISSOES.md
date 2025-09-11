# Sistema de Controle de Acesso - Dashboard Auto Geral

Este documento explica como funciona o sistema de autenticacao e autorizacao do dashboard, incluindo como gerenciar permissoes de usuarios.

## 📋 Visao Geral

O sistema utiliza **Azure AD** para autenticacao e um **banco MySQL** para autorizacao baseada em cargos. Cada usuario deve ter seu email cadastrado na tabela `acessos_dbf` com um cargo especifico para acessar os dashboards.

## 🔐 Fluxo de Autenticacao

1. **Login Azure AD**: Usuario faz login com conta Microsoft
2. **Validacao no banco**: Sistema busca o email na tabela `acessos_dbf`
3. **Verificacao de cargo**: Confirma se o cargo esta definido
4. **Controle de acesso**: Libera apenas dashboards permitidos para o cargo

## 👥 Cargos Disponiveis

### Hierarquia de Cargos (do maior para menor acesso):

1. **Socio** - Acesso total
2. **Gestor** - Acesso amplo a analises gerenciais  
3. **Desenvolvedora de Software** - Acesso tecnico completo
4. **Estagiario de TI** - Acesso tecnico completo
5. **Gerente de Vendas** - Foco em vendas e entregas
6. **Encarregado** - Acesso operacional
7. **VENDAS** - Foco em analises de vendas
8. **Contas_pagar** - Foco em custos financeiros
9. **Compras** - Foco em custos e abastecimento

## 🎯 Mapeamento de Permissoes por Dashboard

### 📊 Dashboards com Acesso Amplo
**Cargos:** Gestor, Encarregado, VENDAS, Estagiario de TI, Socio, Desenvolvedora de Software, Gerente de Vendas

- **Monitora Veiculos Cobli** (`veiculos_cobli.py`)
- **Custo de entrega** (`custo_entrega.py`)
- **Custos** (`custos.py`)
- **Vendas intens e curva** (`modo_venda_itens_curva.py`)
- **Vendas sem curva** (`modo_vendas_sem_curva.py`)
- **Centro de custo** (`centro_custo.py`)

## 🆕 Como Adicionar Novos Dashboards

### 1. Criar Arquivo da Pagina
Adicione o arquivo `.py` na pasta `pages/`

### 2. Definir Permissoes
No arquivo `navigation.py`, adicione as permissoes:

```python
# Na classe AccessControl, adicione:
PERMISSIONS = {
    # ... existing permissions ...
    "novo_dashboard.py": ["Gestor", "Socio", "Estagiario de TI"],
}
```

### 3. Adicionar a Lista de Paginas
```python
# Na classe AccessControl, adicione:
PAGES = [
    # ... existing pages ...
    {"file": "novo_dashboard.py", "label": "Nome do Dashboard", "permitir": PERMISSIONS.get("novo_dashboard.py")},
]
```

## 🚨 Troubleshooting

### Problema: "Seu perfil nao possui cargo definido"

**Causa:** Email do usuario nao esta cadastrado ou cargo esta vazio

**Solucao:**
1. Verificar se email existe na tabela:
```sql
SELECT * FROM acessos_dbf WHERE E_MAIL = 'email@usuario.com';
```

### Problema: Dashboard nao aparece na navegacao

**Verificacoes:**
1. Arquivo existe em `pages/`?
2. Permissoes definidas em `AccessControl.PERMISSIONS`?
3. Pagina adicionada em `AccessControl.PAGES`?
4. Cargo do usuario esta na lista de permissoes?

### Problema: Erro de conexao com banco

**Verificacoes:**
1. Arquivo `secrets.toml` configurado?
2. Credenciais do MySQL corretas?
3. Tabela `acessos_dbf` existe?

## 🔧 Arquivos do Sistema

- **`navigation.py`**: Controle de acesso e navegacao
- **`core/db.py`**: Conexao com banco e busca de usuarios
- **`app.py`**: Autenticacao Azure AD
- **`.streamlit/secrets.toml`**: Configuracoes de conexao

## 📞 Suporte

Para duvidas sobre o sistema de permissoes, entre em contato com a equipe de TI da Auto Geral.