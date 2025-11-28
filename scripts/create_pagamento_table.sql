"""
Script para criar a tabela de pagamentos no banco de dados PostgreSQL.

Este script adiciona a tabela 'pagamento' com campos criptografados para
armazenar dados sensíveis de cartões de crédito usando AES-256-GCM.

ATENÇÃO: Execute este script SOMENTE se a tabela ainda não existir.
         Use migrações (Alembic) para mudanças em produção.
"""

-- Criar tabela de pagamentos
CREATE TABLE IF NOT EXISTS pagamento (
    id SERIAL PRIMARY KEY,
    participante_id INTEGER NOT NULL,
    
    -- Dados operacionais
    valor FLOAT NOT NULL,
    metodo_pagamento VARCHAR(20) NOT NULL CHECK (metodo_pagamento IN ('credito', 'debito', 'pix', 'boleto')),
    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'aprovado', 'recusado', 'cancelado')),
    data_pagamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Dados criptografados (AES-256-GCM em base64)
    numero_cartao_encrypted TEXT,
    cvv_encrypted TEXT,
    titular_encrypted TEXT,
    cpf_titular_encrypted TEXT,
    
    -- Validade (não sensível suficiente para criptografar)
    validade_mes INTEGER CHECK (validade_mes >= 1 AND validade_mes <= 12),
    validade_ano INTEGER CHECK (validade_ano >= 2024),
    
    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    CONSTRAINT fk_participante 
        FOREIGN KEY (participante_id) 
        REFERENCES participante(id) 
        ON DELETE CASCADE
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_pagamento_participante ON pagamento(participante_id);
CREATE INDEX IF NOT EXISTS idx_pagamento_status ON pagamento(status);
CREATE INDEX IF NOT EXISTS idx_pagamento_data ON pagamento(data_pagamento);
CREATE INDEX IF NOT EXISTS idx_pagamento_metodo ON pagamento(metodo_pagamento);

-- Trigger para atualizar timestamp automaticamente
CREATE OR REPLACE FUNCTION update_pagamento_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_pagamento_timestamp
    BEFORE UPDATE ON pagamento
    FOR EACH ROW
    EXECUTE FUNCTION update_pagamento_timestamp();

-- Permissões para usuário da aplicação
GRANT SELECT, INSERT, UPDATE ON pagamento TO evento_app_user;
GRANT USAGE, SELECT ON SEQUENCE pagamento_id_seq TO evento_app_user;

-- Comentários para documentação
COMMENT ON TABLE pagamento IS 'Armazena dados de pagamentos com criptografia AES-256-GCM';
COMMENT ON COLUMN pagamento.numero_cartao_encrypted IS 'Número do cartão criptografado (AES-256-GCM)';
COMMENT ON COLUMN pagamento.cvv_encrypted IS 'CVV criptografado - DEVE ser deletado após processamento (PCI-DSS)';
COMMENT ON COLUMN pagamento.titular_encrypted IS 'Nome do titular criptografado';
COMMENT ON COLUMN pagamento.cpf_titular_encrypted IS 'CPF do titular criptografado';

-- Verificar se a tabela foi criada
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM 
    information_schema.columns
WHERE 
    table_name = 'pagamento'
ORDER BY 
    ordinal_position;
