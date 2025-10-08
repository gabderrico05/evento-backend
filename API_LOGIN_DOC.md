# Sistema de Login - Documentação da API

## Visão Geral

O sistema de login foi implementado com autenticação JWT (JSON Web Token) e inclui funcionalidades completas de registro, login, gerenciamento de usuários e proteção de rotas.

## Dependências Adicionadas

- `PyJWT==2.8.0` - Para geração e validação de tokens JWT
- `bcrypt==4.0.1` - Para hash seguro de senhas

## Endpoints da API

### Autenticação (`/api/auth`)

#### 1. Registro de Usuário
```
POST /api/auth/register
Content-Type: application/json

{
    "username": "usuario123",
    "email": "usuario@exemplo.com", 
    "password": "minhasenha123"
}
```

**Resposta de Sucesso (201):**
```json
{
    "message": "Usuário criado com sucesso",
    "user": {
        "id": 1,
        "username": "usuario123",
        "email": "usuario@exemplo.com",
        "created_at": "2025-10-07T10:30:00",
        "is_active": true
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 2. Login
```
POST /api/auth/login
Content-Type: application/json

{
    "login": "usuario123",  // pode ser username ou email
    "password": "minhasenha123"
}
```

**Resposta de Sucesso (200):**
```json
{
    "message": "Login realizado com sucesso",
    "user": {
        "id": 1,
        "username": "usuario123",
        "email": "usuario@exemplo.com",
        "created_at": "2025-10-07T10:30:00",
        "is_active": true
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 3. Informações do Usuário Atual
```
GET /api/auth/me
Authorization: Bearer {token}
```

**Resposta de Sucesso (200):**
```json
{
    "user": {
        "id": 1,
        "username": "usuario123",
        "email": "usuario@exemplo.com",
        "created_at": "2025-10-07T10:30:00",
        "is_active": true
    }
}
```

#### 4. Alterar Senha
```
POST /api/auth/change-password
Authorization: Bearer {token}
Content-Type: application/json

{
    "current_password": "senhaatual",
    "new_password": "novasenha123"
}
```

#### 5. Logout
```
POST /api/auth/logout
Authorization: Bearer {token}
```

### Usuários (`/api/users`) - Rotas Protegidas

Todas as rotas de usuários agora requerem autenticação.

#### 1. Listar Usuários
```
GET /api/users
Authorization: Bearer {token}
```

#### 2. Buscar Usuário por ID
```
GET /api/users/{id}
Authorization: Bearer {token}
```

#### 3. Atualizar Usuário
```
PUT /api/users/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
    "username": "novousername",
    "email": "novoemail@exemplo.com"
}
```
*Nota: Usuários só podem atualizar seus próprios dados*

#### 4. Deletar Usuário
```
DELETE /api/users/{id}
Authorization: Bearer {token}
```
*Nota: Usuários só podem deletar sua própria conta*

## Autenticação

### Como Usar o Token

1. Após login ou registro, você receberá um token JWT
2. Inclua o token no header de todas as requisições protegidas:
   ```
   Authorization: Bearer {seu_token_aqui}
   ```

### Expiração do Token

- Tokens expiram em 24 horas
- Após expiração, é necessário fazer login novamente

## Validações Implementadas

### Registro:
- Username: mínimo 3 caracteres, único
- Email: formato válido, único
- Senha: mínimo 6 caracteres

### Login:
- Aceita username ou email
- Verifica se conta está ativa
- Verifica senha com hash seguro

### Segurança:
- Senhas são hasheadas com bcrypt
- Tokens JWT assinados com chave secreta
- Proteção contra ataques de força bruta básica

## Exemplo de Uso (JavaScript)

```javascript
// Registro
const registerResponse = await fetch('/api/auth/register', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        username: 'meuusuario',
        email: 'meu@email.com',
        password: 'minhasenha123'
    })
});

const registerData = await registerResponse.json();
const token = registerData.token;

// Usar token em requisições protegidas
const protectedResponse = await fetch('/api/auth/me', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
```

## Códigos de Erro Comuns

- `400` - Dados inválidos ou ausentes
- `401` - Token inválido, expirado ou ausente
- `403` - Ação não permitida (ex: tentar alterar dados de outro usuário)
- `404` - Recurso não encontrado
- `409` - Conflito (ex: username/email já em uso)
- `500` - Erro interno do servidor

## Estrutura do Banco de Dados

O modelo `User` foi atualizado com os seguintes campos:

```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # NOVO
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # NOVO
    is_active = db.Column(db.Boolean, default=True)  # NOVO
```

## Arquivos Modificados/Criados

1. **Novos arquivos:**
   - `src/auth.py` - Gerenciador de autenticação e decoradores
   - `src/routes/auth.py` - Rotas de autenticação
   - `API_LOGIN_DOC.md` - Esta documentação

2. **Arquivos modificados:**
   - `requirements.txt` - Adicionadas dependências JWT e bcrypt
   - `src/models/user.py` - Modelo atualizado com autenticação
   - `src/routes/user.py` - Rotas protegidas por autenticação
   - `src/main.py` - Registro das novas rotas

O sistema de login está completo e pronto para uso!