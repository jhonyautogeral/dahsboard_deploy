#!/bin/bash

# Inicie o proxy Cloud SQL em background
/proxy_server/cloud-sql-proxy  --credentials-file=/proxy_server/erpj-br-sql.json  erpj-br:southamerica-east1:erpj-sql  --port=3309 &
  
# Inicie o ngrok
ngrok http 9000 > /dev/null &
sleep 5

# Obtenha a URL do ngrok
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url')

# URL de configuração do Azure
azure=https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/d435d888-7afa-436b-9673-cb26d6e7e233/isMSAApp~/false

echo "Antes de acessar a aplicação no navegador:"
echo "1. Vá na Azure em: $azure"
echo "2. Atualize o link de verificação com o seguinte link: $NGROK_URL"
echo "3. Após atualizar, acesse a aplicação no navegador: $NGROK_URL"

# Define a URL de redirecionamento para autenticação
export REDIRECT_URI="$NGROK_URL"

# Inicie o Streamlit
streamlit run app.py --server.port=9000 --server.address=0.0.0.0
