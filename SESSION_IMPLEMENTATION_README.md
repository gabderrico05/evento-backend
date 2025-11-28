# 🔐 Sistema de Gerenciamento de Sessão - Implementação Completa

## 📋 Resumo da Implementação

Sistema completo de gerenciamento de sessão para Flask com:

✅ **Tempo de inatividade**: 15 minutos  
✅ **Tempo máximo de vida**: 60 minutos  
✅ **Re-login obrigatório** após expiração  
✅ **Cookies seguros** (HTTPOnly, SameSite)  
✅ **Integração com JWT** e autenticação MFA  
✅ **Proteção contra XSS e CSRF**  

## 📁 Arquivos Modificados/Criados

### Backend (Flask)

#### Modificados
- ✅ `requirements.txt` - Adicionada dependência `Flask-Session==0.8.0`
- ✅ `src/main.py` - Configurações de sessão e middleware de gerenciamento
- ✅ `src/routes/user.py` - Rotas de login, logout e gerenciamento de sessão

#### Criados
- ✅ `SESSION_MANAGEMENT.md` - Documentação completa do sistema
- ✅ `SESSION_FRONTEND_GUIDE.md` - Guia de integração React
- ✅ `tests/test_session_management.py` - Suite de testes

### Frontend (React)

#### Criados
- ✅ `evento-site/src/components/ParticipanteDados.jsx` - Componente com proteção XSS
- ✅ `evento-site/src/components/ExemploParticipante.jsx` - Exemplo de uso
- ✅ `evento-site/PARTICIPANTE_DADOS_XSS_PROTECTION.md` - Documentação XSS

## 🚀 Instalação

### Backend

```bash
cd evento-backend

# Instalar dependências
pip install -r requirements.txt

# Executar servidor
python src/main.py
```

### Testes

```bash
# Instalar dependências de teste
pip install pytest pytest-flask

# Executar testes
pytest tests/test_session_management.py -v
```

## 🔧 Configurações Principais

### main.py

```python
# Tempo de inatividade: 15 minutos
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

# Tempo máximo de vida: 60 minutos
app.config['SESSION_MAX_LIFETIME'] = timedelta(minutes=60)

# Segurança de cookies
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Anti-XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' # Anti-CSRF
app.config['SESSION_COOKIE_SECURE'] = True    # HTTPS only (produção)
```

### Middleware de Gerenciamento

O middleware `@app.before_request` executa antes de cada requisição e:

1. ✅ Ignora rotas públicas (login, registro)
2. ✅ Verifica se sessão existe
3. ✅ Valida tempo máximo de vida (60 min)
4. ✅ Valida tempo de inatividade (15 min)
5. ✅ Atualiza `last_activity` automaticamente
6. ✅ Limpa sessão se expirada

## 📡 Endpoints Implementados

### 🔐 Autenticação

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/login` | POST | Login (primeira etapa) |
| `/api/login/mfa` | POST | Login com MFA (segunda etapa) |
| `/api/logout` | POST | Encerrar sessão |

### 📊 Gerenciamento de Sessão

| Endpoint | Método | Autenticação | Descrição |
|----------|--------|--------------|-----------|
| `/api/session/status` | GET | ❌ Não | Verificar status da sessão |
| `/api/session/refresh` | POST | ✅ Sim | Renovar sessão (atualizar atividade) |

### Exemplos de Uso

#### Login
```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "usuario", "password": "senha"}' \
  -c cookies.txt
```

#### Verificar Status
```bash
curl -X GET http://localhost:5000/api/session/status \
  -b cookies.txt
```

#### Renovar Sessão
```bash
curl -X POST http://localhost:5000/api/session/refresh \
  -H "Authorization: Bearer <token>" \
  -b cookies.txt
```

#### Logout
```bash
curl -X POST http://localhost:5000/api/logout \
  -b cookies.txt
```

## 🕐 Comportamento de Expiração

### Cenário 1: Expiração por Inatividade

```
10:00 - Login
10:05 - Última requisição
10:25 - Próxima requisição
❌ ERRO: Sessão expirada (>15 min de inatividade)
```

### Cenário 2: Expiração por Tempo Máximo

```
10:00 - Login
10:55 - Última requisição (usuário ativo)
11:05 - Próxima requisição
❌ ERRO: Sessão expirada (>60 min desde criação)
```

### Cenário 3: Renovação Bem-Sucedida

```
10:00 - Login
10:10 - Requisição (renova last_activity)
10:20 - Requisição (renova last_activity)
10:30 - Requisição (renova last_activity)
✅ Sessão permanece ativa (< 15 min entre requisições)
```

## 🔒 Segurança Implementada

### Cookies Seguros

| Configuração | Proteção |
|-------------|----------|
| `HttpOnly` | Previne acesso via JavaScript (XSS) |
| `SameSite=Lax` | Proteção contra CSRF |
| `Secure` | Apenas HTTPS em produção |

### Validação Dupla

Rotas protegidas verificam:
1. ✅ Sessão válida no servidor
2. ✅ Token JWT válido
3. ✅ `user_id` do token = `user_id` da sessão
4. ✅ Usuário existe no banco

### Limpeza Automática

- ✅ Sessões expiradas são limpas automaticamente
- ✅ Logout limpa todos os dados da sessão
- ✅ Token inválido limpa sessão

## 📊 Estrutura da Sessão

```python
session = {
    'user_id': 1,                              # ID do usuário
    'username': 'usuario123',                  # Nome do usuário
    'session_created_at': '2025-11-26T10:00',  # Timestamp de criação
    'last_activity': '2025-11-26T10:05',       # Última atividade
    'mfa_verified': True,                      # Status MFA
    'permanent': True                          # Usa PERMANENT_SESSION_LIFETIME
}
```

## 🧪 Testes

### Executar Todos os Testes

```bash
pytest tests/test_session_management.py -v
```

### Testes Implementados

- ✅ Criação de sessão no login
- ✅ Status de sessão ativa/inativa
- ✅ Renovação de sessão
- ✅ Expiração por inatividade
- ✅ Expiração por tempo máximo
- ✅ Logout e limpeza de sessão
- ✅ Proteção de rotas
- ✅ Validação de token + sessão
- ✅ Segurança de cookies
- ✅ Sessão temporária MFA

## 🌐 Integração Frontend (React)

### Axios com Cookies

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  withCredentials: true, // IMPORTANTE: Envia cookies
});
```

### Hook de Autenticação

```javascript
import { useAuth } from './hooks/useAuth';

function App() {
  const { login, logout, sessionInfo } = useAuth();
  
  // Verificar sessão periodicamente
  useEffect(() => {
    const interval = setInterval(checkSession, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);
}
```

### Renovação Automática

```javascript
// Renovar sessão a cada 10 minutos
setInterval(async () => {
  await api.post('/session/refresh');
}, 10 * 60 * 1000);
```

Consulte `SESSION_FRONTEND_GUIDE.md` para implementação completa.

## 📚 Documentação

- **`SESSION_MANAGEMENT.md`** - Documentação completa do backend
- **`SESSION_FRONTEND_GUIDE.md`** - Guia de integração React
- **`PARTICIPANTE_DADOS_XSS_PROTECTION.md`** - Proteção XSS no frontend

## 🔐 Proteção XSS (Bônus)

Componente React `ParticipanteDados` implementado com:

- ✅ Escaping automático do React
- ✅ Validação de tipos com PropTypes
- ✅ Sanitização explícita de dados
- ✅ Sem uso de `dangerouslySetInnerHTML`

```jsx
<ParticipanteDados
  nome="João Silva"
  email="joao@example.com"
  numeroIngresso="ABC123456"
/>
```

## ⚙️ Produção

### Variáveis de Ambiente

```bash
export SECRET_KEY="sua-chave-super-segura-aqui"
export SESSION_COOKIE_SECURE="True"
export FLASK_ENV="production"
```

### HTTPS Obrigatório

```python
# Em produção
app.config['SESSION_COOKIE_SECURE'] = True
```

### Redis (Opcional para Escalabilidade)

```bash
pip install Flask-Session redis
```

```python
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
```

## 📈 Próximas Melhorias

- [ ] Implementar rate limiting
- [ ] Adicionar logs de auditoria
- [ ] Implementar refresh token
- [ ] Dashboard de sessões ativas
- [ ] Notificações de login em novo dispositivo
- [ ] "Remember Me" opcional

## 📞 Suporte

Para dúvidas ou problemas:

1. Consulte a documentação em `SESSION_MANAGEMENT.md`
2. Execute os testes: `pytest tests/test_session_management.py -v`
3. Verifique logs do servidor Flask

## ✅ Checklist de Verificação

- ✅ Sessões expiram após 15 minutos de inatividade
- ✅ Sessões expiram após 60 minutos de vida
- ✅ Re-login obrigatório após expiração
- ✅ Cookies com HTTPOnly e SameSite
- ✅ Middleware de gerenciamento funcionando
- ✅ Endpoints de status e renovação
- ✅ Integração com JWT e MFA
- ✅ Testes unitários completos
- ✅ Documentação detalhada
- ✅ Guia de integração frontend

---

**Status**: ✅ Implementação Completa  
**Versão**: 1.0.0  
**Data**: 26 de Novembro de 2025
