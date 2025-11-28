# Endpoints de Autorização - Participantes

## 📋 Visão Geral

Este documento descreve a implementação dos endpoints de autorização para participantes, garantindo que cada usuário possa acessar **apenas seu próprio ingresso**.

## 🔐 Fluxo de Autorização

```
1. Login → Cria sessão com participante_id
2. Acesso ao endpoint → Decorator verifica sessão
3. Verificação de autorização → Compara numero_ingresso
4. Acesso concedido/negado
```

## 📍 Endpoints Implementados

### 1. POST `/api/participante/login`
**Descrição**: Autentica participante e cria sessão

**Request**:
```json
{
  "numero_ingresso": "EVTAB12CD34",
  "senha": "senha123"
}
```

**Response (200)**:
```json
{
  "message": "Login bem-sucedido",
  "participante": {
    "nome": "João Silva",
    "email": "joao@example.com",
    "numero_ingresso": "EVTAB12CD34",
    "resgatado": false,
    "data_resgate": null,
    "ativo": true
  },
  "session_created": true
}
```

**Response (401)**:
```json
{
  "error": "Número de ingresso ou senha inválidos"
}
```

---

### 2. POST `/api/participante/logout`
**Descrição**: Encerra sessão do participante

**Headers**: Cookie de sessão

**Response (200)**:
```json
{
  "message": "Logout realizado com sucesso",
  "logged_out": true
}
```

---

### 3. GET `/api/participante/ingresso/<numero_ingresso>` ✨
**Descrição**: Busca ingresso com verificação de autorização

**Proteção**: `@participante_required`

**Autorização**: Participante só pode acessar seu próprio ingresso

**Headers**: Cookie de sessão

**Response (200)** - Autorizado:
```json
{
  "ingresso": {
    "nome": "João Silva",
    "email": "joao@example.com",
    "numero_ingresso": "EVTAB12CD34",
    "resgatado": false,
    "data_resgate": null,
    "ativo": true
  },
  "authorized": true
}
```

**Response (403)** - Acesso negado:
```json
{
  "error": "Acesso negado. Você só pode visualizar seu próprio ingresso.",
  "forbidden": true
}
```

**Response (401)** - Não autenticado:
```json
{
  "error": "Não autorizado. Faça login para acessar este recurso.",
  "auth_required": true
}
```

**Response (404)** - Ingresso não encontrado:
```json
{
  "error": "Ingresso não encontrado"
}
```

---

### 4. GET `/api/participante/meu-ingresso` 💡
**Descrição**: Busca ingresso do participante autenticado automaticamente

**Proteção**: `@participante_required`

**Vantagem**: Não precisa passar numero_ingresso na URL

**Headers**: Cookie de sessão

**Response (200)**:
```json
{
  "ingresso": {
    "nome": "João Silva",
    "email": "joao@example.com",
    "numero_ingresso": "EVTAB12CD34",
    "resgatado": false,
    "data_resgate": null,
    "ativo": true
  },
  "authorized": true
}
```

**Response (401)**:
```json
{
  "error": "Não autorizado. Faça login para acessar este recurso.",
  "auth_required": true
}
```

---

## 🛡️ Decorator `@participante_required`

### Funcionalidade
```python
@participante_required
def rota_protegida(participante_atual):
    # participante_atual é injetado automaticamente
    return jsonify(participante_atual.to_dict())
```

### Verificações Realizadas

1. **Sessão ativa**: Verifica se `participante_id` existe na sessão
2. **Participante válido**: Busca participante no banco de dados
3. **Participante ativo**: Verifica se `ativo = True`
4. **Injeção de contexto**: Passa `participante_atual` para a função

### Códigos de Resposta

| Código | Situação | Ação |
|--------|----------|------|
| 401 | Sem sessão | Retorna erro, frontend redireciona para login |
| 401 | Sessão inválida | Limpa sessão, retorna erro |
| 200 | Autorizado | Executa função protegida |

---

## 🔍 Verificação de Autorização

### Implementação no Endpoint `/ingresso/<numero_ingresso>`

```python
# VERIFICAÇÃO DE AUTORIZAÇÃO:
# Participante só pode acessar seu próprio ingresso
if participante_atual.numero_ingresso != numero_ingresso:
    print(f"[WARN] Acesso negado: {participante_atual.numero_ingresso} tentou acessar {numero_ingresso}")
    return jsonify({
        'error': 'Acesso negado. Você só pode visualizar seu próprio ingresso.',
        'forbidden': True
    }), 403
```

### Cenários de Teste

| Cenário | Resultado |
|---------|-----------|
| Usuário A acessa seu ingresso | ✅ 200 OK |
| Usuário A tenta acessar ingresso de B | ❌ 403 Forbidden |
| Usuário sem login tenta acessar | ❌ 401 Unauthorized |
| Ingresso não existe | ❌ 404 Not Found |

---

## 📊 Logs de Segurança

### Login bem-sucedido
```
[INFO] Login bem-sucedido: EVTAB12CD34 - João Silva
```

### Logout
```
[INFO] Logout: EVTAB12CD34
```

### Acesso autorizado
```
[INFO] Acesso autorizado ao ingresso: EVTAB12CD34 - João Silva
```

### Tentativa de acesso não autorizado
```
[WARN] Acesso negado: EVTAB12CD34 tentou acessar EVTXY98ZW76
```

---

## 🔐 Gestão de Sessão

### Configuração (main.py)
```python
# Tempo de inatividade: 15 minutos
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

# Tempo máximo de vida: 60 minutos
app.config['SESSION_MAX_LIFETIME'] = timedelta(minutes=60)

# Cookies seguros
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

### Dados Armazenados na Sessão
```python
session['participante_id'] = participante.id
session['participante_numero_ingresso'] = participante.numero_ingresso
session['participante_nome'] = participante.nome
session.permanent = True
```

---

## 🧪 Testes de Autorização

### Teste 1: Login e Acesso Autorizado
```python
# 1. Login
response = client.post('/api/participante/login', json={
    'numero_ingresso': 'EVTAB12CD34',
    'senha': 'senha123'
})
assert response.status_code == 200

# 2. Acessar próprio ingresso
response = client.get('/api/participante/ingresso/EVTAB12CD34')
assert response.status_code == 200
assert response.json['authorized'] == True
```

### Teste 2: Tentativa de Acesso Não Autorizado
```python
# 1. Login como usuário A
client.post('/api/participante/login', json={
    'numero_ingresso': 'EVTAB12CD34',
    'senha': 'senha123'
})

# 2. Tentar acessar ingresso de B
response = client.get('/api/participante/ingresso/EVTXY98ZW76')
assert response.status_code == 403
assert 'Acesso negado' in response.json['error']
```

### Teste 3: Acesso sem Login
```python
# Tentar acessar sem sessão
response = client.get('/api/participante/ingresso/EVTAB12CD34')
assert response.status_code == 401
assert response.json['auth_required'] == True
```

---

## 📱 Integração Frontend

### Fluxo de Autenticação
```javascript
// 1. Login
const loginResponse = await fetch('/api/participante/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include', // IMPORTANTE: Envia cookies
  body: JSON.stringify({
    numero_ingresso: 'EVTAB12CD34',
    senha: 'senha123'
  })
});

// 2. Acessar ingresso (opção 1 - com numero_ingresso)
const ingressoResponse = await fetch('/api/participante/ingresso/EVTAB12CD34', {
  credentials: 'include' // Envia cookie de sessão
});

// 3. Acessar ingresso (opção 2 - automática)
const meuIngressoResponse = await fetch('/api/participante/meu-ingresso', {
  credentials: 'include'
});

// 4. Logout
await fetch('/api/participante/logout', {
  method: 'POST',
  credentials: 'include'
});
```

### Tratamento de Erros
```javascript
const response = await fetch('/api/participante/ingresso/EVTAB12CD34', {
  credentials: 'include'
});

if (response.status === 401) {
  // Redirecionar para login
  window.location.href = '/login';
} else if (response.status === 403) {
  // Mostrar mensagem de acesso negado
  alert('Você só pode visualizar seu próprio ingresso');
} else if (response.ok) {
  const data = await response.json();
  console.log(data.ingresso);
}
```

---

## ✅ Checklist de Segurança

- [x] Decorator `@participante_required` implementado
- [x] Verificação de autorização (numero_ingresso match)
- [x] Logs de acesso (autorizados e negados)
- [x] Sessão segura (HTTPOnly, SameSite)
- [x] IDs internos não expostos em URLs
- [x] Mensagens de erro apropriadas (401, 403, 404)
- [x] Endpoint `/meu-ingresso` para conveniência
- [x] Logout implementado
- [x] LGPD compliance (dados mínimos na sessão)

---

## 🚀 Próximos Passos

1. **Frontend**: Implementar componente de login
2. **Frontend**: Integrar `credentials: 'include'` nas requisições
3. **Frontend**: Criar página de visualização do ingresso
4. **Testes**: Implementar suite completa de testes de autorização
5. **Monitoramento**: Adicionar métricas de tentativas de acesso não autorizado

---

## 📚 Referências

- [SESSION_MANAGEMENT.md](./SESSION_MANAGEMENT.md) - Gestão de sessões
- [SECURITY_PUBLIC_IDS.md](./SECURITY_PUBLIC_IDS.md) - IDs públicos
- [FEATLOGIN.md](./FEATLOGIN.md) - Feature de login
- [Flask Sessions](https://flask.palletsprojects.com/en/3.0.x/quickstart/#sessions)
