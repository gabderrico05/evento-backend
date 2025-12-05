# Configuração de Ambientes

Este documento explica como configurar diferentes ambientes (desenvolvimento, produção, testes) na aplicação Flask.

## 📋 Visão Geral

O sistema utiliza **diferentes configurações por ambiente**:
- **Development**: SQLite local, debug ativado, logs verbosos
- **Production**: PostgreSQL/MySQL remoto, debug desativado, HTTPS obrigatório
- **Testing**: SQLite em memória, testes automatizados

## 🔧 Estrutura de Configuração

### Arquivo: `src/config.py`

Contém 3 classes de configuração:

1. **`Config`** - Configuração base (compartilhada)
2. **`DevelopmentConfig`** - Desenvolvimento local
3. **`ProductionConfig`** - Produção (validações extras)
4. **`TestingConfig`** - Testes automatizados

### Arquivo: `.env`

Variáveis de ambiente específicas de cada instalação. **NUNCA** versione este arquivo!

## 🚀 Como Usar

### 1. Desenvolvimento Local (SQLite)

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env
FLASK_ENV=development
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=src/database/app.db
SECRET_KEY=dev-secret-key-change-in-production
```

```bash
# Executar aplicação
python src/main.py
```

**Características**:
- ✅ Debug ativado (`DEBUG=True`)
- ✅ SQLite local (sem configuração de servidor)
- ✅ Logs detalhados no console
- ✅ Recarregamento automático ao modificar código
- ⚠️ Não usar em produção!

---

### 2. Produção (PostgreSQL)

```bash
# Editar .env para produção
FLASK_ENV=production
DATABASE_TYPE=postgresql

# Configurações do banco
DB_USER=evento_app_user
DB_PASSWORD=SuaSenhaSegura123!
DB_HOST=seu-servidor-db.com
DB_PORT=5432
DB_NAME=evento_db
DB_SSL_MODE=require

# Secret Key ÚNICA (gere uma nova!)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Encryption Key ÚNICA (gere uma nova!)
ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Session (produção)
SESSION_COOKIE_SECURE=True
```

```bash
# Executar com Gunicorn
gunicorn -c gunicorn_config.py src.main:app
```

**Características**:
- ✅ Debug desativado (`DEBUG=False`)
- ✅ PostgreSQL remoto com SSL
- ✅ HTTPS obrigatório (`SESSION_COOKIE_SECURE=True`)
- ✅ Validações de segurança automáticas
- ✅ Logs em arquivo (`app.log`)
- ⚠️ Requer SECRET_KEY única (valida na inicialização)
- ⚠️ Requer PostgreSQL/MySQL (bloqueia SQLite)

---

### 3. Produção Alternativa (MySQL)

```bash
# Editar .env
FLASK_ENV=production
DATABASE_TYPE=mysql

DB_USER=evento_app_user
DB_PASSWORD=SuaSenhaSegura123!
DB_HOST=seu-servidor-mysql.com
DB_PORT=3306
DB_NAME=evento_db
DB_SSL_CA=/path/to/ca-cert.pem
```

---

### 4. Testes Automatizados

```bash
# Editar .env (ou usar pytest com env vars)
FLASK_ENV=testing

# Executar testes
pytest
```

**Características**:
- ✅ SQLite em memória (rápido)
- ✅ Banco zerado a cada teste
- ✅ CSRF desabilitado (facilita testes)

---

## 🔐 Validações de Segurança (Produção)

A classe `ProductionConfig` valida automaticamente:

### ❌ Bloqueia inicialização se:
- `SECRET_KEY` não foi alterada (ainda é a padrão)
- `DATABASE_TYPE` é SQLite (não suportado em produção)
- `DB_PASSWORD` não está configurada

```python
# Exemplo de erro ao tentar usar SQLite em produção:
ValueError: ⚠️  SQLite não pode ser usado em produção! Use PostgreSQL ou MySQL.
```

---

## 📊 Bancos de Dados Suportados

| Banco       | Ambiente      | Driver         | Configuração                              |
|-------------|---------------|----------------|-------------------------------------------|
| SQLite      | Development   | Built-in       | `DATABASE_TYPE=sqlite`                    |
| PostgreSQL  | Production    | psycopg2       | `DATABASE_TYPE=postgresql` + credenciais  |
| MySQL       | Production    | pymysql        | `DATABASE_TYPE=mysql` + credenciais       |

### Instalar Drivers:

```bash
# PostgreSQL (já incluído no requirements.txt)
pip install psycopg2-binary

# MySQL (se necessário)
pip install pymysql
```

---

## 🔑 Gerando Chaves Seguras

### Secret Key (Flask Session):
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Exemplo: a3f7b2c9e8d4f6a1b5c3e7d9f2a4b8c6e1f3a5b7c9d2e4f6a8b1c3d5e7f9a2b4
```

### Encryption Key (AES-256):
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Exemplo: 9e4f2a7c5b8d1e6f3a9b2c7d4e8f1a6b3c9d5e2f7a1b4c8d6e3f9a2b7c5d1e8
```

**IMPORTANTE**: Gere chaves ÚNICAS para cada ambiente! NUNCA compartilhe entre desenvolvimento e produção!

---

## 📂 Estrutura de Arquivos

```
evento-backend/
├── .env.example           # Template de configuração (versionado)
├── .env                   # Configuração real (NUNCA versionar!)
├── .gitignore             # .env deve estar listado aqui
├── src/
│   ├── config.py          # Classes de configuração
│   ├── main.py            # Carrega config com get_config()
│   └── database/
│       └── app.db         # SQLite (apenas desenvolvimento)
└── requirements.txt       # Inclui python-dotenv
```

---

## 🔄 Alternando Entre Ambientes

### Opção 1: Modificar `.env`
```bash
# Desenvolvimento
FLASK_ENV=development

# Produção
FLASK_ENV=production
```

### Opção 2: Variável de ambiente temporária
```bash
# Linux/Mac
FLASK_ENV=production python src/main.py

# Windows (PowerShell)
$env:FLASK_ENV="production"; python src/main.py
```

### Opção 3: Múltiplos arquivos `.env`
```bash
# Criar arquivos específicos
.env.development
.env.production

# Carregar o correto
ln -s .env.production .env  # Linux/Mac
```

---

## 🛡️ Melhores Práticas

### ✅ FAZER:
- Usar SQLite apenas em desenvolvimento
- Gerar SECRET_KEY e ENCRYPTION_KEY únicas para produção
- Ativar SSL/TLS para banco de dados em produção
- Versionar `.env.example` com valores de exemplo
- Adicionar `.env` ao `.gitignore`
- Usar PostgreSQL em produção (recomendado)
- Ativar `SESSION_COOKIE_SECURE=True` em produção (HTTPS)

### ❌ NÃO FAZER:
- Versionar arquivo `.env` com credenciais reais
- Usar SQLite em produção
- Compartilhar SECRET_KEY entre ambientes
- Usar SECRET_KEY padrão em produção
- Expor DB_PASSWORD em logs ou código
- Desativar debug em desenvolvimento

---

## 🔍 Verificação de Configuração

Ao iniciar a aplicação, o sistema exibe:

```
[CONFIG] Database: postgresql
[CONFIG] User: evento_app_user
[CONFIG] Environment: production
[CONFIG] Debug: False
```

Se houver problemas:
```
[WARNING] ⚠️  SQLite em produção NÃO é recomendado!
[WARNING] ⚠️  Use PostgreSQL ou MySQL para produção
```

---

## 📝 Exemplo Completo

### Desenvolvimento:
```env
FLASK_ENV=development
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=src/database/app.db
SECRET_KEY=dev-secret-key
ENCRYPTION_KEY=dev-encryption-key
SESSION_COOKIE_SECURE=False
```

### Produção:
```env
FLASK_ENV=production
DATABASE_TYPE=postgresql
DB_USER=evento_app_user
DB_PASSWORD=Pr0d#S3cur3P@ssw0rd!
DB_HOST=db.exemplo.com
DB_PORT=5432
DB_NAME=evento_db
DB_SSL_MODE=require
SECRET_KEY=a3f7b2c9e8d4f6a1b5c3e7d9f2a4b8c6e1f3a5b7c9d2e4f6a8b1c3d5e7f9a2b4
ENCRYPTION_KEY=9e4f2a7c5b8d1e6f3a9b2c7d4e8f1a6b3c9d5e2f7a1b4c8d6e3f9a2b7c5d1e8
SESSION_COOKIE_SECURE=True
```

---

## 🐛 Troubleshooting

### Erro: "Working outside of application context"
**Causa**: App não foi inicializado corretamente  
**Solução**: Verificar se `get_config()` está sendo chamado em `main.py`

### Erro: "DB_PASSWORD não configurada"
**Causa**: Variável de ambiente não foi definida  
**Solução**: Adicionar `DB_PASSWORD=...` no arquivo `.env`

### Erro: "SQLite não pode ser usado em produção"
**Causa**: `FLASK_ENV=production` com `DATABASE_TYPE=sqlite`  
**Solução**: Alterar para PostgreSQL ou MySQL

### Banco de dados não conecta
**Causa**: Credenciais incorretas ou host inacessível  
**Solução**: Verificar DB_HOST, DB_PORT, DB_USER, DB_PASSWORD

---

## 📚 Referências

- [Flask Configuration](https://flask.palletsprojects.com/en/latest/config/)
- [python-dotenv Documentation](https://pypi.org/project/python-dotenv/)
- [PostgreSQL Connection Strings](https://www.postgresql.org/docs/current/libpq-connect.html)
- [MySQL Connection Strings](https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html)
