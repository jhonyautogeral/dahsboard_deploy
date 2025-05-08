#!/bin/sh

# Inicie o ngrok
ngrok http 9000 > /dev/null &

# Aguarde o ngrok inicializar
sleep 5

# Obtenha a URL do ngrok
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url')

azure=https://portal.azure.com/?ocid=AIDcmmzmnb0182_SEM__k_Cj0KCQjwrPHABhCIARIsAFW2XBPTVqkIFJH6ZuPT-uX8vOdsExIMwKooq2QoJ13JneZzSlai0-N0iFoaAj90EALw_wcB_k_&icid=free-search#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Authentication/appId/d435d888-7afa-436b-9673-cb26d6e7e233/isMSAApp~/false
# Exiba a URL no console
echo "Antes de acessar a aplicação no navegador:"
echo "1. Vá na Azure em: $azure"
echo "2. Atualize o link de verificação com o seguinte link: $NGROK_URL"
echo "3. Após atualizar, acesse a aplicação no navegador: $NGROK_URL"

# Configure a variável de ambiente para o Streamlit
export REDIRECT_URI="$NGROK_URL"

# Inicie o Streamlit
streamlit run app.py --server.port=9000 --server.address=0.0.0.0
