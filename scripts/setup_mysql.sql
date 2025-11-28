-- ==========================================
-- Setup MySQL com Permissões Restritas
-- ==========================================
-- 
-- Este script configura um banco de dados MySQL seguro
-- com dois usuários:
-- 1. evento_admin - Permissões completas (apenas para migrations)
-- 2. evento_app_user - Permissões RESTRITAS (SELECT, INSERT, UPDATE)
--
-- IMPORTANTE: Execute este script como root
-- mysql -u root -p < setup_mysql.sql
-- ==========================================

-- 1. CRIAR BANCO DE DADOS
CREATE DATABASE IF NOT EXISTS evento_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

-- 2. CRIAR USUÁRIO ADMIN (para migrations e setup)
CREATE USER IF NOT EXISTS 'evento_admin'@'localhost' 
    IDENTIFIED BY 'CHANGE-THIS-ADMIN-PASSWORD';  -- ⚠️  MUDAR SENHA

-- Conceder todas as permissões ao admin
GRANT ALL PRIVILEGES ON evento_db.* TO 'evento_admin'@'localhost';

-- 3. CRIAR USUÁRIO DA APLICAÇÃO (permissões restritas)
CREATE USER IF NOT EXISTS 'evento_app_user'@'localhost' 
    IDENTIFIED BY 'CHANGE-THIS-APP-PASSWORD';  -- ⚠️  MUDAR SENHA

-- ==========================================
-- IMPORTANTE: Execute os comandos abaixo APÓS criar as tabelas
-- Use evento_admin para rodar a aplicação e criar as tabelas
-- Depois execute:
-- ==========================================

/*
-- 4. CONCEDER PERMISSÕES RESTRITAS NAS TABELAS
-- Execute APÓS criar as tabelas com evento_admin

GRANT SELECT, INSERT, UPDATE ON evento_db.participante TO 'evento_app_user'@'localhost';
GRANT SELECT, INSERT, UPDATE ON evento_db.user TO 'evento_app_user'@'localhost';

-- Aplicar permissões
FLUSH PRIVILEGES;

-- 5. VERIFICAR PERMISSÕES
SHOW GRANTS FOR 'evento_app_user'@'localhost';

-- 6. TESTAR CONEXÃO
-- Sair e reconectar como evento_app_user
-- mysql -u evento_app_user -p evento_db

-- Testar SELECT (deve funcionar)
-- SELECT * FROM participante LIMIT 1;

-- Testar INSERT (deve funcionar)
-- Testar UPDATE (deve funcionar)
-- Testar DELETE (deve FALHAR - DELETE command denied)
-- Testar DROP (deve FALHAR - DROP command denied)
*/

-- ==========================================
-- COMANDOS ÚTEIS
-- ==========================================

-- Ver todas as tabelas
-- USE evento_db;
-- SHOW TABLES;

-- Ver estrutura de uma tabela
-- DESCRIBE participante;

-- Ver permissões de um usuário
-- SHOW GRANTS FOR 'evento_app_user'@'localhost';

-- Ver conexões ativas
-- SHOW PROCESSLIST;

-- Rotacionar senha
-- ALTER USER 'evento_app_user'@'localhost' IDENTIFIED BY 'nova-senha-aqui';
-- FLUSH PRIVILEGES;

-- Backup
-- mysqldump -u evento_admin -p evento_db > backup.sql

-- Restore
-- mysql -u evento_admin -p evento_db < backup.sql

-- Remover usuário (se necessário)
-- DROP USER 'evento_app_user'@'localhost';

-- Revogar permissões (se necessário)
-- REVOKE ALL PRIVILEGES ON evento_db.* FROM 'evento_app_user'@'localhost';
-- FLUSH PRIVILEGES;
