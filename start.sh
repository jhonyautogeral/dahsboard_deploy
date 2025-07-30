#!/bin/bash

# Inicie o proxy Cloud SQL em background
/proxy_server/cloud-sql-proxy  --credentials-file=/proxy_server/erpj-br-sql.json  erpj-br:southamerica-east1:erpj-sql  --port=3309 &
  
# URL estática do ngrok
NGROK_URL="https://frequently-complete-cowbird.ngrok-free.app"

# Inicie o ngrok com domínio estático
ngrok http 9000 --domain=frequently-complete-cowbird.ngrok-free.app > /dev/null &
sleep 5

# URL de configuração do Azure
azure=https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/d435d888-7afa-436b-9673-cb26d6e7e233/isMSAApp~/false

echo "==================================================================================="
echo "✅ Aplicação configurada com URL estática do ngrok!"
echo "==================================================================================="
echo "🔗 URL da aplicação: $NGROK_URL"
echo "🔧 Azure config: $azure"
echo "==================================================================================="
echo "A URL de redirecionamento já está configurada como: $NGROK_URL"
echo "Você pode acessar diretamente a aplicação no navegador!"
echo "==================================================================================="

# Define a URL de redirecionamento para autenticação
export REDIRECT_URI="$NGROK_URL"

# Inicie o Streamlit
streamlit run app.py --server.port=9000 --server.address=0.0.0.0