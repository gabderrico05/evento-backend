# Guia de Deploy em Produção - Flask com HTTPS

Este guia descreve como fazer deploy da aplicação Flask em produção com HTTPS obrigatório.

## Stack de Produção

```
Internet (HTTPS)
    ↓
Nginx/Apache (Proxy Reverso + SSL Termination)
    ↓
Gunicorn (WSGI Server)
    ↓
Flask App
    ↓
PostgreSQL
```

## Pré-requisitos

- Servidor Ubuntu/Debian (recomendado)
- Domínio configurado apontando para o servidor
- Python 3.8+
- PostgreSQL instalado
- Acesso root/sudo

---

## 1. Preparação do Servidor

### 1.1 Atualizar sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalar dependências

```bash
# Python e ferramentas
sudo apt install -y python3 python3-pip python3-venv

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Nginx (escolher um: Nginx OU Apache)
sudo apt install -y nginx

# OU Apache
# sudo apt install -y apache2 libapache2-mod-wsgi-py3
```

### 1.3 Criar usuário para aplicação

```bash
sudo useradd -m -s /bin/bash www-data
```

---

## 2. Configuração da Aplicação

### 2.1 Criar diretórios

```bash
sudo mkdir -p /var/www/evento-app/{backend,frontend,logs}
sudo chown -R www-data:www-data /var/www/evento-app
```

### 2.2 Clonar/copiar código

```bash
cd /var/www/evento-app/backend
sudo -u www-data git clone <seu-repo> .
# OU copiar arquivos manualmente
```

### 2.3 Criar ambiente virtual e instalar dependências

```bash
cd /var/www/evento-app/backend
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install --upgrade pip
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### 2.4 Configurar variáveis de ambiente

```bash
sudo -u www-data cp .env.example .env
sudo -u www-data nano .env
```

Configurar `.env` para produção:

```bash
# Flask
SECRET_KEY=<gerar_chave_segura_64_caracteres>
FLASK_ENV=production

# Encryption
ENCRYPTION_KEY=<gerar_chave_segura_64_caracteres>

# Database - PostgreSQL
DATABASE_TYPE=postgresql
DB_USER=evento_app_user
DB_PASSWORD=<senha_segura>
DB_HOST=localhost
DB_PORT=5432
DB_NAME=evento_db
DB_SSL_MODE=prefer

# Session
SESSION_TYPE=filesystem
SESSION_PERMANENT=False
SESSION_USE_SIGNER=True
SESSION_FILE_DIR=/var/www/evento-app/backend/.flask_session
```

**Gerar chaves seguras:**

```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_hex(32))"
```

### 2.5 Criar diretórios de logs e sessions

```bash
sudo -u www-data mkdir -p /var/www/evento-app/backend/logs
sudo -u www-data mkdir -p /var/www/evento-app/backend/.flask_session
```

---

## 3. Configuração do PostgreSQL

```bash
# Executar script de setup
sudo -u postgres psql -f scripts/setup_postgresql.sql

# Ou manualmente:
sudo -u postgres createdb evento_db
sudo -u postgres psql -c "CREATE USER evento_app_user WITH PASSWORD 'senha_segura';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE evento_db TO evento_app_user;"
```

---

## 4. Obter Certificado SSL (Let's Encrypt)

### 4.1 Instalar Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
# OU para Apache:
# sudo apt install -y certbot python3-certbot-apache
```

### 4.2 Obter certificado

**Para Nginx:**

```bash
sudo certbot --nginx -d seu-dominio.com -d www.seu-dominio.com
```

**Para Apache:**

```bash
sudo certbot --apache -d seu-dominio.com -d www.seu-dominio.com
```

### 4.3 Renovação automática

```bash
# Testar renovação
sudo certbot renew --dry-run

# Certbot configura cron automaticamente, mas verificar:
sudo systemctl status certbot.timer
```

---

## 5. Configuração do Nginx

### 5.1 Copiar configuração

```bash
sudo cp nginx.conf /etc/nginx/sites-available/evento-app
```

### 5.2 Editar configuração

```bash
sudo nano /etc/nginx/sites-available/evento-app
```

**Alterar:**
- `seu-dominio.com` → seu domínio real
- Caminhos dos certificados SSL (se não usar Let's Encrypt)

### 5.3 Gerar parâmetros Diffie-Hellman

```bash
sudo openssl dhparam -out /etc/nginx/dhparam.pem 2048
```

### 5.4 Ativar site

```bash
sudo ln -s /etc/nginx/sites-available/evento-app /etc/nginx/sites-enabled/
sudo nginx -t  # Testar configuração
sudo systemctl restart nginx
```

---

## 6. Configuração do Apache (Alternativa ao Nginx)

### 6.1 Ativar módulos necessários

```bash
sudo a2enmod ssl rewrite proxy proxy_http headers
```

### 6.2 Copiar configuração

```bash
sudo cp apache.conf /etc/apache2/sites-available/evento-app.conf
```

### 6.3 Editar configuração

```bash
sudo nano /etc/apache2/sites-available/evento-app.conf
```

**Alterar:**
- `seu-dominio.com` → seu domínio real

### 6.4 Ativar site

```bash
sudo a2ensite evento-app.conf
sudo apache2ctl configtest  # Testar configuração
sudo systemctl restart apache2
```

---

## 7. Configuração do Gunicorn (Systemd)

### 7.1 Copiar service file

```bash
sudo cp evento-app.service /etc/systemd/system/
```

### 7.2 Editar service file (se necessário)

```bash
sudo nano /etc/systemd/system/evento-app.service
```

### 7.3 Ativar e iniciar serviço

```bash
sudo systemctl daemon-reload
sudo systemctl enable evento-app
sudo systemctl start evento-app
```

### 7.4 Verificar status

```bash
sudo systemctl status evento-app

# Ver logs
sudo journalctl -u evento-app -f
```

---

## 8. Firewall

### 8.1 Configurar UFW

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
sudo ufw status
```

---

## 9. Validação

### 9.1 Testar HTTPS

```bash
curl -I https://seu-dominio.com
```

**Deve retornar:**
- `HTTP/2 200` ou `HTTP/1.1 200`
- Headers de segurança (HSTS, X-Frame-Options, etc.)

### 9.2 Testar redirecionamento HTTP → HTTPS

```bash
curl -I http://seu-dominio.com
```

**Deve retornar:**
- `HTTP/1.1 301 Moved Permanently`
- `Location: https://seu-dominio.com/`

### 9.3 Verificar TLS

```bash
# Verificar protocolos TLS
nmap --script ssl-enum-ciphers -p 443 seu-dominio.com

# OU usar testssl.sh
git clone https://github.com/drwetter/testssl.sh.git
cd testssl.sh
./testssl.sh https://seu-dominio.com
```

### 9.4 Teste online

- **SSL Labs:** https://www.ssllabs.com/ssltest/
- **Security Headers:** https://securityheaders.com/

**Meta:** Nota A+ no SSL Labs

---

## 10. Monitoramento

### 10.1 Logs da aplicação

```bash
# Logs do Gunicorn
tail -f /var/www/evento-app/backend/logs/gunicorn_error.log
tail -f /var/www/evento-app/backend/logs/gunicorn_access.log

# Logs da aplicação Flask
tail -f /var/www/evento-app/backend/app.log

# Logs do Nginx
tail -f /var/log/nginx/evento-app-error.log
tail -f /var/log/nginx/evento-app-access.log

# Logs do systemd
sudo journalctl -u evento-app -f
```

### 10.2 Health check

```bash
curl https://seu-dominio.com/health
```

---

## 11. Backup e Manutenção

### 11.1 Backup do banco de dados

```bash
# Criar script de backup
sudo -u postgres pg_dump evento_db > backup_$(date +%Y%m%d).sql

# Automatizar com cron (diário às 2h)
sudo crontab -e
# Adicionar:
# 0 2 * * * /usr/bin/pg_dump evento_db > /backups/evento_db_$(date +\%Y\%m\%d).sql
```

### 11.2 Atualizar aplicação

```bash
cd /var/www/evento-app/backend
sudo -u www-data git pull
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo systemctl restart evento-app
```

### 11.3 Renovar certificado SSL

```bash
# Testar renovação
sudo certbot renew --dry-run

# Forçar renovação (se necessário)
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

---

## 12. Troubleshooting

### Erro: "502 Bad Gateway"

```bash
# Verificar se Gunicorn está rodando
sudo systemctl status evento-app

# Verificar logs
sudo journalctl -u evento-app -n 50
```

### Erro: "Connection refused"

```bash
# Verificar se Gunicorn está escutando na porta correta
sudo netstat -tlnp | grep 8000

# Verificar firewall
sudo ufw status
```

### Erro: "SSL certificate problem"

```bash
# Verificar certificado
sudo certbot certificates

# Renovar certificado
sudo certbot renew
```

### Gunicorn não inicia

```bash
# Verificar permissões
ls -la /var/www/evento-app/backend

# Verificar se venv está correto
/var/www/evento-app/backend/venv/bin/python --version

# Rodar manualmente para debug
cd /var/www/evento-app/backend
sudo -u www-data venv/bin/gunicorn -c gunicorn_config.py src.main:app
```

---

## 13. Checklist Final

- [ ] PostgreSQL configurado e rodando
- [ ] Aplicação Flask instalada em `/var/www/evento-app/backend`
- [ ] `.env` configurado com chaves seguras
- [ ] Gunicorn rodando via systemd
- [ ] Nginx/Apache configurado com SSL
- [ ] Certificado SSL válido (Let's Encrypt)
- [ ] HTTP redireciona para HTTPS (301)
- [ ] TLS 1.2+ apenas
- [ ] Headers de segurança configurados
- [ ] Firewall configurado (UFW)
- [ ] Health check funcionando
- [ ] Logs acessíveis
- [ ] Backup automatizado do banco
- [ ] SSL Labs: Nota A+
- [ ] Security Headers: Nota A+

---

## 14. Contatos e Suporte

**Documentação:**
- Flask: https://flask.palletsprojects.com/
- Gunicorn: https://gunicorn.org/
- Nginx: https://nginx.org/en/docs/
- Let's Encrypt: https://letsencrypt.org/docs/

**Segurança:**
- OWASP: https://owasp.org/
- Mozilla SSL Configuration: https://ssl-config.mozilla.org/

---

**Última atualização:** 2024
**Versão:** 1.0
