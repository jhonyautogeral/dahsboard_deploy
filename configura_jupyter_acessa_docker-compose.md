```
scp -r C:\Users\jhonatan.novais\Desktop\fazer_deploy\deploy_compose jonathannovais@10.50.1.252:/home/jonathannovais/Documentos/
```

C:\Users\jhonatan.novais\Desktop\fazer_deploy\dashboard_deploy\dockerfile

docker run -p 9000:9000 deploy_dashboard_ngrok


# 🐳 Deploy de Container Jupyter com Volume Montado

Este guia mostra como subir um container Docker com Jupyter Notebook utilizando imagem `jupyter/pyspark-notebook` ou `jupyter/base-notebook`, montando um volume com permissões adequadas.

---

## 🔄 Remover container existente

```bash
sudo docker rm -f jupyter-deploy-compose
```

---

## 🚀 Rodar o container com volume montado

```bash
sudo docker run --name jupyter-deploy-compose -p 8888:8888 \
  -v /home/jonathannovais/Documentos/deploy_compose:/home/jovyan/work:rw \
  --user root \
  jupyter/pyspark-notebook \
  start-notebook.sh \
    --NotebookApp.ip='0.0.0.0' \
    --NotebookApp.port=8888 \
    --NotebookApp.notebook_dir=/home/jovyan/work \
    --NotebookApp.token='ag'
```

- `--user root`: evita problemas de permissão.
- `:rw`: monta o volume com permissão de leitura e escrita.
- `--NotebookApp.token='ag'`: define token de acesso ao Jupyter.

---

## ❗ Problema comum: pasta aparece vazia no Jupyter

Mesmo que o volume esteja montado corretamente, se a pasta aparecer vazia, isso geralmente ocorre por falta de permissão do usuário **jovyan (UID 1000)** dentro do container.

---

## 🔍 Verificação de permissões dentro do container

Execute os comandos abaixo para investigar:

```bash
sudo docker exec -it jupyter-deploy-compose bash -c "ls -la /home/jovyan"
sudo docker exec -it jupyter-deploy-compose bash -c "ls -la /home/jovyan/work"
```

Se o resultado for algo como:

```
drwx------ 2 root root ...
```

ou

```
ls: cannot open directory ... Permission denied
```

então o `jovyan` não tem acesso à pasta montada.

---

## 🛠️ Solução rápida: rodar tudo como root

```bash
sudo docker rm -f jupyter-deploy-compose

sudo docker run -d \
  --name jupyter-deploy-compose \
  -p 8888:8888 \
  -v /home/jonathannovais/Documentos/deploy_compose:/home/jovyan/work:rw \
  --user root \
  jupyter/base-notebook \
  start-notebook.sh \
    --NotebookApp.ip='0.0.0.0' \
    --NotebookApp.port=8888 \
    --NotebookApp.notebook_dir=/home/jovyan/work \
    --NotebookApp.token=''
```

> ⚠️ Obs: Usar o usuário root não é o ideal para produção, mas resolve rapidamente o problema de permissão para testes locais.

---

## 🔐 Solução definitiva (melhor prática): ajustar permissões no host

Se desejar manter o container rodando com o usuário **jovyan (UID 1000)**, execute no host:

```bash
sudo chown -R 1000:1000 /home/jonathannovais/Documentos/deploy_compose
sudo chmod -R a+rX /home/jonathannovais/Documentos/deploy_compose
```

Depois reinicie o container sem `--user root`:

```bash
sudo docker rm -f jupyter-deploy-compose

sudo docker run -d \
  --name jupyter-deploy-compose \
  -p 8888:8888 \
  -v /home/jonathannovais/Documentos/deploy_compose:/home/jovyan/work \
  jupyter/base-notebook \
  start-notebook.sh \
    --NotebookApp.ip='0.0.0.0' \
    --NotebookApp.port=8888 \
    --NotebookApp.notebook_dir=/home/jovyan/work \
    --NotebookApp.token=''
```

---

## 🛡️ Caso use SELinux (CentOS/RHEL)

Acrescente `:Z` ou `:z` ao volume:

```bash
-v /home/jonathannovais/Documentos/deploy_compose:/home/jovyan/work:Z
```

> Isso ajusta o contexto SELinux para permitir leitura do diretório pelo container.

---

## ✅ Resultado esperado

Se configurado corretamente, os arquivos do diretório local `deploy_compose` devem aparecer na interface web do Jupyter Notebook acessível via `http://<IP>:8888`.
