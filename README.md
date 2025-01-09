# dahsboard_deploy

### Para criar a imagem no docker: esse comando deve ser executado na mesma pasta aonde está a pasta 'dockerfile'

docker build -t deploy_dashboards_streamlit:v10 .

### Para executar o container e rodar a aplicação:

docker run -p 9000:9000 deploy_dashboards_streamlit:v10

## Para acessar a aplicação na web:

### se Tiver subido no docker de teste 252
### Entao acesse web com:
    10.50.1.252:9000

### se Tiver subido no docker na maquina local
### Entao acesse web com:
    localhost:9000