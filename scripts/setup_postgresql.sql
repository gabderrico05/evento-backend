-- ==========================================
-- Setup PostgreSQL com Permissões Restritas
-- ==========================================
-- 
-- Este script configura um banco de dados PostgreSQL seguro
-- com dois usuários:
-- 1. evento_admin - Permissões completas (apenas para migrations)
-- 2. evento_app_user - Permissões RESTRITAS (SELECT, INSERT, UPDATE)
--
-- IMPORTANTE: Execute este script como superusuário (postgres)
-- ==========================================

-- 1. CRIAR BANCO DE DADOS
CREATE DATABASE evento_db
    WITH 
    ENCODING = 'UTF8'
    LC_COLLATE = 'pt_BR.UTF-8'
    LC_CTYPE = 'pt_BR.UTF-8'
    TEMPLATE = template0;

-- Comentário
COMMENT ON DATABASE evento_db IS 'Banco de dados do sistema de eventos';

-- 2. CRIAR USUÁRIO ADMIN (para migrations e setup)
CREATE USER evento_admin WITH 
    PASSWORD 'Ev3nt0@Adm1n#2024$SecurePass!'
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

-- Conceder todas as permissões no banco ao admin
GRANT ALL PRIVILEGES ON DATABASE evento_db TO evento_admin;

-- Conectar ao banco de dados
\c evento_db

-- Conceder permissões no schema público ao admin
GRANT ALL PRIVILEGES ON SCHEMA public TO evento_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO evento_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO evento_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO evento_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO evento_admin;

-- 3. CRIAR USUÁRIO DA APLICAÇÃO (permissões restritas)
CREATE USER evento_app_user WITH 
    PASSWORD 'evento_secure_password_2024'
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

-- Conceder permissões básicas
GRANT CONNECT ON DATABASE evento_db TO evento_app_user;
GRANT USAGE ON SCHEMA public TO evento_app_user;

-- ==========================================
-- IMPORTANTE: Execute os comandos abaixo APÓS criar as tabelas
-- Use evento_admin para rodar a aplicação e criar as tabelas
-- Depois execute:
-- ==========================================

/*
-- 4. CONCEDER PERMISSÕES RESTRITAS NAS TABELAS
-- Execute APÓS criar as tabelas com evento_admin

GRANT SELECT, INSERT, UPDATE ON participante TO evento_app_user;
GRANT SELECT, INSERT, UPDATE ON "user" TO evento_app_user;

-- Permitir uso de sequences (IDs auto-incrementados)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO evento_app_user;

-- Para futuras tabelas criadas pelo admin
ALTER DEFAULT PRIVILEGES FOR ROLE evento_admin IN SCHEMA public 
    GRANT SELECT, INSERT, UPDATE ON TABLES TO evento_app_user;

ALTER DEFAULT PRIVILEGES FOR ROLE evento_admin IN SCHEMA public 
    GRANT USAGE, SELECT ON SEQUENCES TO evento_app_user;

-- 5. VERIFICAR PERMISSÕES
\dp participante
\dp "user"

-- Ver permissões do usuário
\du evento_app_user

-- 6. TESTAR CONEXÃO
-- Sair e reconectar como evento_app_user
\q
psql -U evento_app_user -d evento_db

-- Testar SELECT (deve funcionar)
SELECT * FROM participante LIMIT 1;

-- Testar INSERT (deve funcionar)
-- Testar UPDATE (deve funcionar)
-- Testar DELETE (deve FALHAR - permission denied)
-- Testar DROP (deve FALHAR - must be owner)
*/

-- ==========================================
-- COMANDOS ÚTEIS
-- ==========================================

-- Ver todas as tabelas
-- \dt

-- Ver permissões de uma tabela
-- \dp nome_tabela

-- Ver usuários
-- \du

-- Ver conexões ativas
-- SELECT * FROM pg_stat_activity WHERE datname = 'evento_db';

-- Rotacionar senha
-- ALTER USER evento_app_user WITH PASSWORD 'nova-senha-aqui';

-- Backup
-- pg_dump -U evento_admin evento_db > backup.sql

-- Restore
-- psql -U evento_admin evento_db < backup.sql
