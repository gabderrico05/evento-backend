# Configuração Segura do Banco de Dados

## 📋 Visão Geral

Este documento descreve a configuração segura do banco de dados para a aplicação Flask, implementando o **Princípio do Menor Privilégio** (Least Privilege Principle).

## 🔐 Princípios de Segurança

### Permissões Restritas

O usuário da aplicação possui **APENAS**:
- ✅ `SELECT` - Leitura de dados
- ✅ `INSERT` - Inserção de novos registros
- ✅ `UPDATE` - Atualização de registros existentes

**SEM permissões de**:
- ❌ `DROP` - Exclusão de tabelas
- ❌ `DELETE` - Exclusão de registros
- ❌ `CREATE` - Criação de tabelas
- ❌ `ALTER` - Modificação de estrutura
- ❌ `GRANT` - Concessão de permissões
- ❌ Acesso a outras tabelas/schemas

## 🗄️ Opções de Banco de Dados

### 1. SQLite (Desenvolvimento) ⚠️

**Uso**: Apenas para desenvolvimento local e testes

**Características**:
- Arquivo local (`src/database/app.db`)
- Não possui controle granular de permissões
- Fácil configuração
- **NÃO recomendado para produção**

**Configuração**:
```env
DATABASE_TYPE=sqlite
SQLITE_DB_PATH=src/database/app.db
```

---

### 2. PostgreSQL (Produção) ✅ RECOMENDADO

**Uso**: Produção e ambientes críticos

**Vantagens**:
- Controle granular de permissões
- Alta performance e escalabilidade
- Suporte a transações ACID
- Auditoria avançada

#### Setup PostgreSQL

**1. Criar banco de dados e usuários**:

```sql
-- Conectar como superusuário (postgres)
sudo -u postgres psql

-- 1. Criar banco de dados
CREATE DATABASE evento_db;

-- 2. Criar usuário ADMIN (apenas para migrations/setup)
CREATE USER evento_admin WITH PASSWORD 'admin-password-here';
GRANT ALL PRIVILEGES ON DATABASE evento_db TO evento_admin;

-- 3. Conectar ao banco
\c evento_db

-- 4. Conceder permissões no schema público
GRANT ALL PRIVILEGES ON SCHEMA public TO evento_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO evento_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO evento_admin;

-- 5. Criar usuário da APLICAÇÃO (permissões restritas)
CREATE USER evento_app_user WITH PASSWORD 'app-password-here';

-- 6. Conceder permissões RESTRITAS
-- Apenas SELECT, INSERT, UPDATE nas tabelas específicas
GRANT CONNECT ON DATABASE evento_db TO evento_app_user;
GRANT USAGE ON SCHEMA public TO evento_app_user;

-- IMPORTANTE: Execute após criar as tabelas com evento_admin
-- GRANT SELECT, INSERT, UPDATE ON participante TO evento_app_user;
-- GRANT SELECT, INSERT, UPDATE ON "user" TO evento_app_user;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO evento_app_user;
```

**2. Criar tabelas (usar evento_admin)**:

```bash
# Configurar .env para usar evento_admin
DATABASE_TYPE=postgresql
DB_USER=evento_admin
DB_PASSWORD=admin-password-here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=evento_db

# Executar aplicação para criar tabelas
python src/main.py
```

**3. Conceder permissões nas tabelas criadas**:

```sql
-- Conectar como postgres
sudo -u postgres psql -d evento_db

-- Conceder permissões nas tabelas
GRANT SELECT, INSERT, UPDATE ON participante TO evento_app_user;
GRANT SELECT, INSERT, UPDATE ON "user" TO evento_app_user;

-- Permitir uso de sequences (para IDs auto-incrementados)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO evento_app_user;

-- Verificar permissões
\dp participante
\dp "user"
```

**4. Configurar aplicação para usar evento_app_user**:

```env
DATABASE_TYPE=postgresql
DB_USER=evento_app_user
DB_PASSWORD=app-password-here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=evento_db
```

#### Verificação de Segurança PostgreSQL

```sql
-- Conectar como evento_app_user
psql -U evento_app_user -d evento_db

-- Testar SELECT (deve funcionar)
SELECT * FROM participante LIMIT 1;

-- Testar INSERT (deve funcionar)
INSERT INTO participante (nome, email, numero_ingresso, senha_hash, ativo) 
VALUES ('Test', 'test@example.com', 'TESTINGRESSO', 'hash', true);

-- Testar UPDATE (deve funcionar)
UPDATE participante SET nome = 'Test Updated' WHERE email = 'test@example.com';

-- Testar DELETE (deve FALHAR)
DELETE FROM participante WHERE email = 'test@example.com';
-- Erro esperado: ERROR: permission denied for table participante

-- Testar DROP (deve FALHAR)
DROP TABLE participante;
-- Erro esperado: ERROR: must be owner of table participante

-- Testar CREATE (deve FALHAR)
CREATE TABLE test_table (id INT);
-- Erro esperado: ERROR: permission denied for schema public
```

---

### 3. MySQL (Produção Alternativa)

**Uso**: Produção (alternativa ao PostgreSQL)

#### Setup MySQL

**1. Criar banco de dados e usuários**:

```sql
-- Conectar como root
mysql -u root -p

-- 1. Criar banco de dados
CREATE DATABASE evento_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. Criar usuário ADMIN (para migrations)
CREATE USER 'evento_admin'@'localhost' IDENTIFIED BY 'admin-password-here';
GRANT ALL PRIVILEGES ON evento_db.* TO 'evento_admin'@'localhost';
FLUSH PRIVILEGES;

-- 3. Criar usuário da APLICAÇÃO (permissões restritas)
CREATE USER 'evento_app_user'@'localhost' IDENTIFIED BY 'app-password-here';

-- 4. Conceder permissões RESTRITAS
GRANT SELECT, INSERT, UPDATE ON evento_db.participante TO 'evento_app_user'@'localhost';
GRANT SELECT, INSERT, UPDATE ON evento_db.user TO 'evento_app_user'@'localhost';
FLUSH PRIVILEGES;

-- 5. Verificar permissões
SHOW GRANTS FOR 'evento_app_user'@'localhost';
```

**2. Configurar .env**:

```env
DATABASE_TYPE=mysql
DB_USER=evento_app_user
DB_PASSWORD=app-password-here
DB_HOST=localhost
DB_PORT=3306
DB_NAME=evento_db
```

#### Verificação de Segurança MySQL

```sql
-- Conectar como evento_app_user
mysql -u evento_app_user -p evento_db

-- Testar SELECT (deve funcionar)
SELECT * FROM participante LIMIT 1;

-- Testar INSERT (deve funcionar)
INSERT INTO participante (nome, email, numero_ingresso, senha_hash, ativo) 
VALUES ('Test', 'test@example.com', 'TESTINGRESSO', 'hash', 1);

-- Testar UPDATE (deve funcionar)
UPDATE participante SET nome = 'Test Updated' WHERE email = 'test@example.com';

-- Testar DELETE (deve FALHAR)
DELETE FROM participante WHERE email = 'test@example.com';
-- Erro esperado: ERROR 1142 (42000): DELETE command denied

-- Testar DROP (deve FALHAR)
DROP TABLE participante;
-- Erro esperado: ERROR 1142 (42000): DROP command denied
```

---

## 🔧 Configuração da Aplicação

### Arquivo .env

```env
# Copiar de .env.example
cp .env.example .env

# Editar com suas credenciais
nano .env
```

### Instalar dependências adicionais

```bash
# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install pymysql cryptography

# Carregar variáveis de ambiente
pip install python-dotenv
```

### Código de Configuração (main.py)

```python
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar URI do banco de dados
DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')

if DATABASE_TYPE == 'postgresql':
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME')
    
    DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    
elif DATABASE_TYPE == 'mysql':
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME')
    
    DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    
else:  # sqlite (padrão)
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'src/database/app.db')
    DATABASE_URI = f'sqlite:///{SQLITE_DB_PATH}'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
```

---

## 📊 Comparação de Segurança

| Recurso | SQLite | PostgreSQL | MySQL |
|---------|--------|------------|-------|
| Permissões granulares | ❌ | ✅ | ✅ |
| Auditoria | ❌ | ✅ | ✅ |
| Usuários separados | ❌ | ✅ | ✅ |
| Produção | ❌ | ✅ | ✅ |
| Facilidade setup | ✅ | ⚠️ | ⚠️ |

---

## 🛡️ Boas Práticas de Segurança

### 1. Separação de Usuários

- **evento_admin**: Usado APENAS para migrations e setup inicial
- **evento_app_user**: Usado pela aplicação em runtime

### 2. Rotação de Senhas

```sql
-- PostgreSQL
ALTER USER evento_app_user WITH PASSWORD 'new-password-here';

-- MySQL
ALTER USER 'evento_app_user'@'localhost' IDENTIFIED BY 'new-password-here';
```

### 3. Monitoramento

```sql
-- PostgreSQL: Ver conexões ativas
SELECT usename, application_name, client_addr, state 
FROM pg_stat_activity 
WHERE datname = 'evento_db';

-- MySQL: Ver conexões ativas
SHOW PROCESSLIST;
```

### 4. Backup Regular

```bash
# PostgreSQL
pg_dump -U evento_admin evento_db > backup_$(date +%Y%m%d).sql

# MySQL
mysqldump -u evento_admin -p evento_db > backup_$(date +%Y%m%d).sql
```

### 5. SSL/TLS em Produção

```python
# PostgreSQL com SSL
DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require'

# MySQL com SSL
DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?ssl_ca=/path/to/ca.pem'
```

---

## 🔍 Auditoria e Logs

### PostgreSQL - Habilitar logging

```sql
-- postgresql.conf
log_statement = 'mod'  # Log INSERT, UPDATE, DELETE
log_connections = on
log_disconnections = on
```

### MySQL - Habilitar audit log

```sql
-- my.cnf
[mysqld]
general_log = 1
general_log_file = /var/log/mysql/general.log
```

---

## 📝 Checklist de Segurança

- [ ] Usuário da aplicação tem APENAS SELECT, INSERT, UPDATE
- [ ] Usuário da aplicação NÃO tem permissões de DROP, DELETE, CREATE
- [ ] Credenciais armazenadas em .env (não versionado)
- [ ] .env incluído no .gitignore
- [ ] Senhas fortes e únicas
- [ ] SSL/TLS habilitado em produção
- [ ] Backup automático configurado
- [ ] Logs de auditoria habilitados
- [ ] Permissões testadas (verificar que DELETE/DROP falham)

---

## 🚨 Troubleshooting

### Erro: "permission denied for table"

**Causa**: Usuário não tem permissões na tabela

**Solução**:
```sql
-- PostgreSQL
GRANT SELECT, INSERT, UPDATE ON nome_tabela TO evento_app_user;

-- MySQL
GRANT SELECT, INSERT, UPDATE ON evento_db.nome_tabela TO 'evento_app_user'@'localhost';
FLUSH PRIVILEGES;
```

### Erro: "relation does not exist"

**Causa**: Tabelas não foram criadas

**Solução**:
1. Usar evento_admin para criar tabelas
2. Conceder permissões ao evento_app_user
3. Trocar para evento_app_user

### Erro: "connection refused"

**Causa**: Banco de dados não está rodando

**Solução**:
```bash
# PostgreSQL
sudo systemctl start postgresql

# MySQL
sudo systemctl start mysql
```

---

## 📚 Referências

- [PostgreSQL Security Best Practices](https://www.postgresql.org/docs/current/sql-grant.html)
- [MySQL Security](https://dev.mysql.com/doc/refman/8.0/en/security.html)
- [OWASP Database Security](https://owasp.org/www-community/vulnerabilities/Unrestricted_Database_Access)
- [Flask-SQLAlchemy Configuration](https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/config/)
