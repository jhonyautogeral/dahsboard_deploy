# dahsboard_deploy

### Para criar a imagem no docker: esse comando deve ser executado na mesma pasta aonde está a pasta 'dockerfile'

docker build -t deploy_dashboards_streamlit:v10 .

### Para executar o container e rodar a aplicação:

docker run -p 9000:9000 deploy_dashboards_streamlit:v10

## Para acessar a aplicação na web:

Siga os passoa que irá surgir na tela e depois acesse o link da aplicação