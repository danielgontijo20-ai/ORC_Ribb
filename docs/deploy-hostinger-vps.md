# Deploy ORC_Ribb Web na VPS Hostinger (Ubuntu)

## 1) Conectar na VPS
```bash
ssh root@SEU_IP_DA_VPS
```

## 2) Pacotes base
```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git nginx
```

## 3) Clonar o projeto
```bash
mkdir -p /var/www
cd /var/www
git clone https://github.com/danielgontijo20-ai/ORC_Ribb.git
cd ORC_Ribb
git checkout cursor/web-fastapi-auth-3237
```

## 4) Ambiente Python
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.db.migrate
```

## 5) Variáveis de ambiente (importante)
```bash
nano /etc/orc-ribb.env
```
Conteúdo:
```env
ORC_SECRET_KEY=coloque-uma-chave-longa-e-aleatoria
ORC_ENV=production
```

## 6) Serviço systemd
```bash
nano /etc/systemd/system/orc-ribb.service
```
```ini
[Unit]
Description=ORC_Ribb Web
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/ORC_Ribb
EnvironmentFile=/etc/orc-ribb.env
ExecStart=/var/www/ORC_Ribb/.venv/bin/uvicorn web.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload
systemctl enable --now orc-ribb
systemctl status orc-ribb
```

## 7) Nginx + domínio
No painel Hostinger DNS, aponte:
- Tipo A: `orc` → IP da VPS

Nginx:
```bash
nano /etc/nginx/sites-available/orc-ribb
```
```nginx
server {
    listen 80;
    server_name orc.seudominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
```bash
ln -s /etc/nginx/sites-available/orc-ribb /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

SSL (Let's Encrypt):
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d orc.seudominio.com
```

## 8) Login inicial
- URL: `https://orc.seudominio.com/login`
- E-mail: `admin@ribbontech.com`
- Senha: `admin123`  
**Troque a senha assim que entrar em produção.**

## 9) Atualizar o sistema
```bash
cd /var/www/ORC_Ribb
git pull origin cursor/web-fastapi-auth-3237
source .venv/bin/activate
pip install -r requirements.txt
python -m src.db.migrate
systemctl restart orc-ribb
```

## Observações
- A Versão 01 (Streamlit) continua disponível via tag `versao01`.
- A fase 1 web já tem login, menu, históricos, cadastros (consulta), aprovar e PDF.
- Novo orçamento completo na web é a fase 2.
