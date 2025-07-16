# Use a imagem base do Python
FROM python:3.12-slim

# Instale dependências do sistema operacional
RUN apt-get update && apt-get install -y \
    wget \
    gcc \
    libmariadb-dev \
    libssl-dev \
    pkg-config \
    libnss3-tools \
    unzip \
    curl \
    jq \
    net-tools \
    procps \
    mysql-client \
    telnet \
    ping \
    vim \
    nano \
    bash \
    && apt-get clean

# Instale o ngrok
RUN wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip \
    && unzip ngrok-v3-stable-linux-amd64.zip \
    && mv ngrok /usr/local/bin/ \
    && rm ngrok-v3-stable-linux-amd64.zip

# Instale o cloud-sql-proxy para Linux
RUN wget -q https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O /usr/local/bin/cloud_sql_proxy \
    && chmod +x /usr/local/bin/cloud_sql_proxy

# Adicionar variáveis de ambiente
ENV NGROK_AUTHTOKEN=2sdnuIh9i59xefKut8c7j7Hhgby_3bWNDGP16fKCtXND1zQpx

# Configure o authtoken do ngrok dinamicamente
RUN ngrok config add-authtoken $NGROK_AUTHTOKEN

# Configure o diretório de trabalho e copie o projeto
WORKDIR /app
COPY . .

# Instale as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Exponha a porta do Streamlit
EXPOSE 9000

# Configure o script de inicialização
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Comando de inicialização: inicie o Streamlit e o ngrok
CMD ["/start.sh"]
