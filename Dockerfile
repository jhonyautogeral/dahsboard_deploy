FROM python:3.12-slim

# Instala dependências do sistema
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
    iputils-ping \
    default-mysql-client \
    telnet \
    vim \
    nano \
    bash \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Instala ngrok
RUN wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip \
 && unzip ngrok-v3-stable-linux-amd64.zip \
 && mv ngrok /usr/local/bin/ \
 && rm ngrok-v3-stable-linux-amd64.zip

# Configura token do ngrok
ENV NGROK_AUTHTOKEN=2sdnuIh9i59xefKut8c7j7Hhgby_3bWNDGP16fKCtXND1zQpx
RUN ngrok config add-authtoken $NGROK_AUTHTOKEN

# Define diretório de trabalho
WORKDIR /app
COPY . .

# Instala dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Permite execução do script de start
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Exponha porta do Streamlit
EXPOSE 9000

CMD ["/start.sh"]
