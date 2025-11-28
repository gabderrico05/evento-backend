# Sistema de Autenticação com MFA (Multi-Factor Authentication)

## Visão Geral

Este sistema implementa autenticação de dois fatores (2FA) usando TOTP (Time-based One-Time Password) para contas sensíveis. O fluxo de autenticação garante que usuários com contas sensíveis precisem fornecer:
1. **Senha** (primeiro fator)
2. **Código TOTP** (segundo fator) gerado por um app autenticador

## Tecnologias Utilizadas

- **Argon2**: Hash seguro de senhas
- **PyOTP**: Geração e validação de códigos TOTP
- **PyJWT**: Tokens JWT para autenticação
- **QRCode**: Geração de QR codes para configuração fácil

## Instalação

```bash
pip install -r requirements.txt
```

## Fluxo de Autenticação

### 1. Registro de Usuário

**Endpoint**: `POST /api/register`

```json
{
  "username": "usuario",
  "email": "usuario@exemplo.com",
  "password": "senha123",
  "is_sensitive_account": true
}
```

**Resposta**:
```json
{
  "message": "Usuário registrado com sucesso",
  "user": {
    "id": 1,
    "username": "usuario",
    "email": "usuario@exemplo.com"
  }
}
```

### 2. Configuração do MFA (Primeira Vez)

#### 2.1. Setup Inicial
**Endpoint**: `POST /api/mfa/setup`

**Headers**: 
```
Authorization: Bearer <token>
```

**Resposta**:
```json
{
  "message": "MFA configurado. Escaneie o QR code com seu app autenticador.",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "secret": "JBSWY3DPEHPK3PXP",
  "totp_uri": "otpauth://totp/EventoApp:usuario@exemplo.com?secret=JBSWY3DPEHPK3PXP&issuer=EventoApp"
}
```

**Instruções**:
1. Instale um app autenticador (Google Authenticator, Authy, Microsoft Authenticator)
2. Escaneie o QR code retornado
3. Ou insira manualmente o `secret` no app

#### 2.2. Habilitar MFA
**Endpoint**: `POST /api/mfa/enable`

**Headers**: 
```
Authorization: Bearer <token>
```

**Body**:
```json
{
  "totp_code": "123456"
}
```

**Resposta**:
```json
{
  "message": "MFA habilitado com sucesso",
  "user": {
    "id": 1,
    "username": "usuario",
    "email": "usuario@exemplo.com",
    "mfa_enabled": true,
    "is_sensitive_account": true
  }
}
```

### 3. Login com MFA

#### 3.1. Primeira Etapa (Senha)
**Endpoint**: `POST /api/login`

**Body**:
```json
{
  "username": "usuario",
  "password": "senha123"
}
```

**Resposta para conta sensível com MFA**:
```json
{
  "message": "Primeira etapa concluída",
  "requires_mfa": true,
  "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Resposta para conta sem MFA**:
```json
{
  "message": "Login realizado com sucesso",
  "requires_mfa": false,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "usuario",
    "email": "usuario@exemplo.com",
    "mfa_enabled": false,
    "is_sensitive_account": false
  }
}
```

#### 3.2. Segunda Etapa (MFA)
**Endpoint**: `POST /api/login/mfa`

**Body**:
```json
{
  "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "totp_code": "123456"
}
```

**Resposta**:
```json
{
  "message": "Login com MFA realizado com sucesso",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "usuario",
    "email": "usuario@exemplo.com",
    "mfa_enabled": true,
    "is_sensitive_account": true
  }
}
```

### 4. Gerenciamento de MFA

#### Verificar Status
**Endpoint**: `GET /api/mfa/status`

**Headers**: 
```
Authorization: Bearer <token>
```

**Resposta**:
```json
{
  "mfa_enabled": true,
  "is_sensitive_account": true,
  "requires_mfa": true
}
```

#### Desabilitar MFA
**Endpoint**: `POST /api/mfa/disable`

**Headers**: 
```
Authorization: Bearer <token>
```

**Body**:
```json
{
  "password": "senha123",
  "totp_code": "123456"
}
```

**Resposta**:
```json
{
  "message": "MFA desabilitado com sucesso",
  "user": {
    "id": 1,
    "username": "usuario",
    "email": "usuario@exemplo.com",
    "mfa_enabled": false,
    "is_sensitive_account": true
  }
}
```

## Uso em Rotas Protegidas

Para proteger rotas que requerem autenticação, use o decorator `@token_required`:

```python
from src.routes.user import token_required

@app.route('/api/protected', methods=['GET'])
@token_required
def protected_route(current_user):
    return jsonify({
        'message': f'Olá, {current_user.username}!',
        'user': current_user.to_dict(include_mfa_status=True)
    })
```

## Segurança

### Características de Segurança Implementadas:

1. **Hash de Senha com Argon2**: Algoritmo moderno e resistente a ataques
2. **TOTP com janela de validação**: Aceita códigos com ±30 segundos de tolerância
3. **Tokens JWT com expiração**: Tokens expiram em 24 horas
4. **Token temporário**: Válido por apenas 5 minutos durante o processo de MFA
5. **Verificação em duas etapas**: Para desabilitar MFA, requer senha + código TOTP
6. **Rehashing automático**: Atualiza hash se parâmetros do Argon2 mudarem

### Contas Sensíveis:

- Contas marcadas como `is_sensitive_account=true` **DEVEM** usar MFA
- Após habilitar MFA, não é possível fazer login sem fornecer o código TOTP
- O sistema requer ambos os fatores mesmo que o MFA seja habilitado posteriormente

## Apps Autenticadores Recomendados

- **Google Authenticator** (iOS/Android)
- **Microsoft Authenticator** (iOS/Android)
- **Authy** (iOS/Android/Desktop)
- **1Password** (Multiplataforma)
- **Bitwarden** (Multiplataforma)

## Exemplos de Código Frontend

### Login Completo com MFA (JavaScript)

```javascript
async function login(username, password) {
  // Primeira etapa - senha
  const response1 = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  
  const data1 = await response1.json();
  
  if (data1.requires_mfa) {
    // Solicitar código TOTP ao usuário
    const totpCode = prompt('Digite o código do seu autenticador:');
    
    // Segunda etapa - MFA
    const response2 = await fetch('/api/login/mfa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        temp_token: data1.temp_token,
        totp_code: totpCode
      })
    });
    
    const data2 = await response2.json();
    
    // Salvar token final
    localStorage.setItem('token', data2.token);
    return data2;
  } else {
    // Login sem MFA
    localStorage.setItem('token', data1.token);
    return data1;
  }
}
```

### Configurar MFA (JavaScript)

```javascript
async function setupMFA(token) {
  // 1. Setup inicial
  const response1 = await fetch('/api/mfa/setup', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const data1 = await response1.json();
  
  // 2. Mostrar QR code ao usuário
  const img = document.createElement('img');
  img.src = data1.qr_code;
  document.body.appendChild(img);
  
  // 3. Solicitar código de verificação
  const totpCode = prompt('Escaneie o QR code e digite o código:');
  
  // 4. Habilitar MFA
  const response2 = await fetch('/api/mfa/enable', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ totp_code: totpCode })
  });
  
  const data2 = await response2.json();
  return data2;
}
```

## Troubleshooting

### Código TOTP não aceito
- Verifique se o relógio do dispositivo está sincronizado
- TOTP depende de timestamps precisos
- Use NTP para sincronizar o relógio

### Token expirado
- Tokens JWT expiram em 24 horas
- Token temporário (MFA) expira em 5 minutos
- Refaça o login se o token expirar

### MFA não funciona após setup
- Certifique-se de chamar `/api/mfa/enable` após `/api/mfa/setup`
- Verifique se o código TOTP está correto durante a habilitação

## Testes

### Testar sem MFA:
```bash
# Registro
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"teste","email":"teste@exemplo.com","password":"senha123"}'

# Login
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"teste","password":"senha123"}'
```

### Testar com MFA:
```bash
# Registro (conta sensível)
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@exemplo.com","password":"senha123","is_sensitive_account":true}'

# Login - obtém token
TOKEN=$(curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"senha123"}' | jq -r '.token')

# Setup MFA
curl -X POST http://localhost:5000/api/mfa/setup \
  -H "Authorization: Bearer $TOKEN"

# Habilitar MFA (substitua 123456 pelo código do app)
curl -X POST http://localhost:5000/api/mfa/enable \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"totp_code":"123456"}'

# Login com MFA
TEMP_TOKEN=$(curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"senha123"}' | jq -r '.temp_token')

curl -X POST http://localhost:5000/api/login/mfa \
  -H "Content-Type: application/json" \
  -d "{\"temp_token\":\"$TEMP_TOKEN\",\"totp_code\":\"123456\"}"
```
