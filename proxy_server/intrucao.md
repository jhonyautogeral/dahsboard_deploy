# Para rodar no linux e acessar a proxy de banco 

## Primeiro instale com
```
curl -o proxy_server/cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.10.1/cloud-sql-proxy.linux.amd64
```

### Depois execute:

```
chmod +x proxy_server/cloud-sql-proxy
```

### E então rode :

```
sudo docker compose up --build -d
```