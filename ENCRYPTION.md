# Criptografia de Dados Sensíveis - AES-256-GCM

## Visão Geral

O sistema implementa criptografia **AES-256-GCM** para proteger dados confidenciais em repouso no banco de dados. Esta abordagem garante:

- **Confidencialidade**: Dados não podem ser lidos sem a chave de criptografia
- **Integridade**: Proteção contra adulteração (AEAD - Authenticated Encryption with Associated Data)
- **Segurança**: AES-256 é considerado seguro contra ataques de força bruta por décadas

## Arquitetura de Segurança

### Separação de Responsabilidades

```
┌─────────────────────────────────────────────────────┐
│                  CAMADA DE APLICAÇÃO                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  SECRET_KEY          →  Sessões, CSRF, JWT         │
│  (Flask)                                            │
│                                                     │
│  ENCRYPTION_KEY      →  Dados sensíveis em repouso │
│  (AES-256-GCM)          (cartões, CPF, etc.)       │
│                                                     │
│  Password Hashing    →  Senhas de usuários         │
│  (Argon2/Werkzeug)      (one-way hash)             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Diferenças entre SECRET_KEY e ENCRYPTION_KEY

| Aspecto | SECRET_KEY | ENCRYPTION_KEY |
|---------|------------|----------------|
| **Propósito** | Assinar sessões, tokens JWT, CSRF | Criptografar dados sensíveis em repouso |
| **Algoritmo** | HMAC-SHA256 (assinatura) | AES-256-GCM (criptografia) |
| **Reversível** | Não (apenas validação) | Sim (precisa descriptografar) |
| **Uso** | Flask internamente | Campos específicos do banco |
| **Rotação** | Invalida sessões ativas | Requer re-criptografia de dados |

## Módulo de Criptografia

### EncryptionManager

Localização: `src/utils/encryption.py`

```python
from src.utils.encryption import encrypt_field, decrypt_field, mask_sensitive_data

# Criptografar
encrypted = encrypt_field("4111111111111111")  # Número de cartão

# Descriptografar
decrypted = decrypt_field(encrypted)

# Mascarar para exibição
masked = mask_sensitive_data("4111111111111111", visible_chars=4)
# Resultado: ************1111
```

### Características Técnicas

1. **AES-256-GCM**
   - Modo de operação: GCM (Galois/Counter Mode)
   - Tamanho da chave: 256 bits (32 bytes)
   - Nonce: 96 bits (12 bytes) - único para cada operação
   - Tag de autenticação: 128 bits (detecta adulteração)

2. **Derivação de Chave**
   - Algoritmo: PBKDF2-HMAC-SHA256
   - Iterações: 480.000 (recomendação OWASP 2024)
   - Salt: Fixo por ambiente (`evento_app_encryption_salt_v1`)
   - Input: ENCRYPTION_KEY do arquivo `.env`
   - Output: Chave de 256 bits para AES

3. **Formato de Armazenamento**
   ```
   Base64( Nonce[12 bytes] + Ciphertext + Tag[16 bytes] )
   ```

## Modelo de Pagamento

### Campos Criptografados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `numero_cartao_encrypted` | Text | Número completo do cartão |
| `cvv_encrypted` | Text | Código de segurança (CVV) |
| `titular_encrypted` | Text | Nome do titular do cartão |
| `cpf_titular_encrypted` | Text | CPF do titular |

### Campos em Texto Claro

| Campo | Tipo | Justificativa |
|-------|------|---------------|
| `validade_mes` | Integer | Não suficientemente sensível |
| `validade_ano` | Integer | Necessário para filtros/validações |
| `metodo_pagamento` | String | Informação operacional |
| `status` | String | Auditoria e processamento |
| `valor` | Float | Relatórios financeiros |

### Exemplo de Uso

```python
from src.models.pagamento import Pagamento
from src.models.db import db

# Criar pagamento com dados criptografados
pagamento = Pagamento(
    participante_id=1,
    valor=150.00,
    metodo_pagamento='credito',
    numero_cartao='4111111111111111',
    cvv='123',
    validade_mes=12,
    validade_ano=2025,
    titular='João Silva',
    cpf_titular='12345678901'
)

db.session.add(pagamento)
db.session.commit()

# Dados são criptografados automaticamente
print(pagamento.numero_cartao_encrypted)
# Saída: "r3K9j2...base64..." (criptografado)

# Descriptografar (apenas para processamento interno)
numero_real = pagamento.get_numero_cartao()
print(numero_real)
# Saída: "4111111111111111"

# Exibir para usuário (mascarado)
print(pagamento.get_numero_cartao_mascarado())
# Saída: "************1111"

# Serializar para API (NUNCA inclui dados sensíveis)
dados_api = pagamento.to_dict()
# Resultado: {'numero_cartao_mascarado': '************1111', ...}

# Processamento interno (descriptografar)
dados_processamento = pagamento.to_dict(include_sensitive=True)
# Resultado: {'_numero_cartao': '4111111111111111', ...}
```

## Configuração da Chave de Criptografia

### 1. Gerar Chave Forte

```bash
# Gerar chave de 256 bits (64 caracteres hexadecimais)
python -c "import secrets; print(secrets.token_hex(32))"
```

Ou use o método do módulo:

```python
from src.utils.encryption import EncryptionManager
print(EncryptionManager.generate_encryption_key())
```

### 2. Configurar no .env

```bash
# .env (NUNCA versionar!)
ENCRYPTION_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

### 3. Validação

O sistema valida automaticamente:
- ✅ ENCRYPTION_KEY deve estar configurada
- ✅ Deve ter pelo menos 32 caracteres
- ✅ Será derivada em chave de 256 bits via PBKDF2

## Segurança em Produção

### ⚠️ Checklist de Segurança

- [ ] **ENCRYPTION_KEY única e forte** (64+ caracteres aleatórios)
- [ ] **Não versionar** .env (verificar .gitignore)
- [ ] **Backup da chave** em local seguro separado
- [ ] **Diferentes chaves** para dev/staging/produção
- [ ] **Rotação de chaves** planejada (ver abaixo)
- [ ] **Acesso restrito** à ENCRYPTION_KEY (apenas admins)
- [ ] **Logs não expõem** dados descriptografados
- [ ] **CVV nunca armazenado** após processamento inicial

### Rotação de Chaves

Em caso de comprometimento ou política de rotação:

1. **Gerar nova chave**
   ```python
   nova_chave = EncryptionManager.generate_encryption_key()
   ```

2. **Re-criptografar dados existentes**
   ```python
   # Script de migração
   from src.models.pagamento import Pagamento
   from src.utils.encryption import EncryptionManager
   
   old_manager = EncryptionManager(old_encryption_key)
   new_manager = EncryptionManager(new_encryption_key)
   
   pagamentos = Pagamento.query.all()
   for p in pagamentos:
       if p.numero_cartao_encrypted:
           # Descriptografar com chave antiga
           numero = old_manager.decrypt(p.numero_cartao_encrypted)
           # Re-criptografar com chave nova
           p.numero_cartao_encrypted = new_manager.encrypt(numero)
       # Repetir para outros campos...
   
   db.session.commit()
   ```

3. **Atualizar ENCRYPTION_KEY no .env**

4. **Reiniciar aplicação**

### Backup e Disaster Recovery

**CRÍTICO**: Se perder a ENCRYPTION_KEY, **TODOS os dados criptografados serão irrecuperáveis**.

1. **Armazenar cópia segura da chave**:
   - Cofre de senhas corporativo (1Password, LastPass, Azure Key Vault)
   - Documento criptografado offline
   - Hardware Security Module (HSM) em ambientes críticos

2. **Documentar procedimentos de recuperação**:
   ```bash
   # Localização da chave de backup
   # Pessoa de contato
   # Processo de restauração
   ```

3. **Testar recuperação** periodicamente

## Validação e Testes

### Validar Cartão (Algoritmo de Luhn)

```python
pagamento = Pagamento(...)
pagamento.set_numero_cartao('4111111111111111')

if pagamento.validar_cartao():
    print("Cartão válido")
else:
    print("Cartão inválido")
```

### Tratamento de Erros

```python
try:
    numero = pagamento.get_numero_cartao()
except ValueError as e:
    # Dados corrompidos ou chave errada
    logger.error(f"Erro ao descriptografar: {e}")
    return {"error": "Erro ao processar pagamento"}, 500
```

## Compliance e Regulamentações

### PCI-DSS (Payment Card Industry)

- ✅ **Req 3.4**: Dados de cartão criptografados em repouso (AES-256)
- ✅ **Req 3.5**: Chaves protegidas e gerenciadas separadamente
- ⚠️ **Req 3.2.1**: CVV não deve ser armazenado após autorização
- ✅ **Req 3.6**: Procedimentos de gestão de chaves documentados

**IMPORTANTE**: O modelo atual armazena CVV criptografado. Em conformidade com PCI-DSS:
- CVV pode ser coletado e usado para autorização
- CVV **DEVE** ser deletado imediatamente após aprovação/rejeição
- Implementar job para limpar `cvv_encrypted` após processamento:

```python
def limpar_cvv_processados():
    """Remove CVV de pagamentos já processados"""
    pagamentos = Pagamento.query.filter(
        Pagamento.status.in_(['aprovado', 'recusado']),
        Pagamento.cvv_encrypted.isnot(None)
    ).all()
    
    for p in pagamentos:
        p.cvv_encrypted = None
    
    db.session.commit()
```

### LGPD (Lei Geral de Proteção de Dados)

- ✅ **Art. 46**: Segurança técnica adequada (criptografia forte)
- ✅ **Art. 48**: Comunicação de incidentes (logs de falhas)
- ✅ **Art. 18**: Direito à portabilidade (método `to_dict()`)
- ✅ **Art. 16**: Direito ao esquecimento (deletar registros)

## Schema do Banco de Dados

```sql
CREATE TABLE pagamento (
    id SERIAL PRIMARY KEY,
    participante_id INTEGER NOT NULL REFERENCES participante(id),
    
    -- Dados operacionais
    valor FLOAT NOT NULL,
    metodo_pagamento VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente',
    data_pagamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Dados criptografados (AES-256-GCM)
    numero_cartao_encrypted TEXT,
    cvv_encrypted TEXT,
    titular_encrypted TEXT,
    cpf_titular_encrypted TEXT,
    
    -- Validade (não sensível)
    validade_mes INTEGER,
    validade_ano INTEGER,
    
    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_pagamento_participante ON pagamento(participante_id);
CREATE INDEX idx_pagamento_status ON pagamento(status);
CREATE INDEX idx_pagamento_data ON pagamento(data_pagamento);
```

## Monitoramento e Auditoria

### Eventos Logados

- ✅ Criptografia de campo (info)
- ✅ Descriptografia de campo (info)
- ✅ Erros de criptografia/descriptografia (error + stack trace)
- ✅ Validação de cartão (info)
- ✅ Mudanças de status de pagamento (info)

### Alertas Recomendados

```python
# Monitorar falhas de descriptografia
# (pode indicar chave errada ou dados corrompidos)
if error_count > threshold:
    send_alert("Múltiplas falhas de descriptografia detectadas")

# Monitorar acessos a dados sensíveis
logger.warning(f"Dados sensíveis acessados por usuário {user_id}")
```

## Migração de Dados Existentes

Se já existem dados sem criptografia:

```python
from src.models.pagamento import Pagamento
from src.models.db import db

# Migração segura
pagamentos = Pagamento.query.all()

for p in pagamentos:
    # Assumindo que dados estão em campos antigos não criptografados
    if hasattr(p, 'numero_cartao_plain'):
        p.set_numero_cartao(p.numero_cartao_plain)
        # Limpar campo antigo
        p.numero_cartao_plain = None
    
    # Repetir para outros campos...

db.session.commit()

# Depois, dropar colunas antigas via migration:
# ALTER TABLE pagamento DROP COLUMN numero_cartao_plain;
```

## Referências

- [NIST Special Publication 800-38D](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf) - AES-GCM
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [PCI DSS v4.0](https://www.pcisecuritystandards.org/)
- [LGPD - Lei 13.709/2018](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)

---

**Última atualização**: 2024
**Versão**: 1.0
