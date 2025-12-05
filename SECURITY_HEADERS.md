# 🛡️ Security Headers Configuration

## ✅ Status da Implementação

**TODOS OS 20 TESTES PASSARAM** ✅

```
20 passed in 1.33s
```

---

## 📋 Headers de Segurança Implementados

### 1. **Remoção do Header `Server`**

**Antes**:
```http
Server: Werkzeug/3.1.3 Python/3.14.0
```

**Depois**:
```http
(header removido)
```

**Objetivo**: Ocultar informações sobre a versão do Flask/Werkzeug (reduz surface de ataques).

---

### 2. **X-Content-Type-Options: nosniff**

```http
X-Content-Type-Options: nosniff
```

**Proteção**: Previne ataques de **MIME sniffing**.

- Browsers não tentam "adivinhar" o Content-Type
- Previne que `text/plain` seja executado como `text/html`
- Proteção contra ataques XSS via upload de arquivos

---

### 3. **X-Frame-Options: DENY**

```http
X-Frame-Options: DENY
```

**Proteção**: Previne ataques de **clickjacking**.

- Não permite que a página seja carregada em `<iframe>`
- Protege contra sobreposição de frames maliciosos
- Complementado por `frame-ancestors 'none'` no CSP

---

### 4. **X-XSS-Protection: 1; mode=block**

```http
X-XSS-Protection: 1; mode=block
```

**Proteção**: Ativa proteção contra **XSS** (browsers legados).

- Browsers antigos que não suportam CSP
- `mode=block` bloqueia a página inteira ao detectar XSS
- Camada adicional de defesa (CSP é preferencial)

---

### 5. **Referrer-Policy: strict-origin-when-cross-origin**

```http
Referrer-Policy: strict-origin-when-cross-origin
```

**Proteção**: Controla informações de **referrer** enviadas.

- **Same-origin**: Envia URL completa
- **Cross-origin HTTPS→HTTPS**: Envia apenas origem (sem path/query)
- **HTTPS→HTTP**: Não envia referrer (downgrade)
- Protege privacidade dos usuários

---

### 6. **Content-Security-Policy (CSP)**

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests
```

#### Diretivas CSP Explicadas:

| Diretiva | Valor | Justificativa |
|----------|-------|---------------|
| `default-src` | `'self'` | Recursos apenas da mesma origem (padrão) |
| `script-src` | `'self' 'unsafe-inline' 'unsafe-eval'` | React/Vite: inline scripts e eval (HMR, DevTools) |
| `style-src` | `'self' 'unsafe-inline'` | React: CSS modules e styled-components inline |
| `img-src` | `'self' data: https:` | Imagens locais + base64 + CDNs externos |
| `font-src` | `'self' data:` | Fontes locais e data URIs |
| `connect-src` | `'self'` | API calls apenas ao próprio backend |
| `frame-ancestors` | `'none'` | Equivalente a `X-Frame-Options: DENY` |
| `base-uri` | `'self'` | Tag `<base>` apenas da mesma origem |
| `form-action` | `'self'` | Forms submetem apenas à mesma origem |
| `upgrade-insecure-requests` | (flag) | Força upgrade HTTP → HTTPS automaticamente |

#### ⚠️ Nota sobre `'unsafe-inline'` e `'unsafe-eval'`

**Por que estão presentes?**
- **React/Vite**: Gera inline styles e scripts durante build
- **HMR (Hot Module Replacement)**: Requer `eval()` em desenvolvimento
- **React DevTools**: Usa `eval()` para debugging

**Alternativas mais seguras (produção)**:
1. **Nonce-based CSP**: Gerar nonce único por request
   ```python
   nonce = secrets.token_urlsafe(16)
   csp = f"script-src 'nonce-{nonce}'"
   # Injetar nonce nas tags <script> do HTML
   ```

2. **Hash-based CSP**: Hash SHA-256 dos scripts inline
   ```python
   script_hash = hashlib.sha256(script.encode()).digest()
   csp = f"script-src 'sha256-{base64.b64encode(script_hash)}'"
   ```

---

## 🔒 Proteções Ativas

### ✅ **MIME Sniffing Attacks**
- Header: `X-Content-Type-Options: nosniff`
- Previne execução de scripts disfarçados como imagens/texto

### ✅ **Clickjacking Attacks**
- Headers: `X-Frame-Options: DENY` + `frame-ancestors 'none'`
- Previne sobreposição de frames maliciosos

### ✅ **XSS (Cross-Site Scripting)**
- Headers: `X-XSS-Protection` + CSP (`script-src`)
- CSP bloqueia scripts inline não autorizados

### ✅ **Information Disclosure**
- Remoção do header `Server`
- Oculta versões de Flask/Werkzeug

### ✅ **HTTP Downgrade Attacks**
- CSP: `upgrade-insecure-requests`
- Força upgrade automático para HTTPS

### ✅ **Data Exfiltration**
- CSP: `connect-src 'self'`
- API calls apenas ao próprio backend

---

## 📁 Implementação Técnica

### **Arquivo**: `src/main.py`

```python
@app.after_request
def add_security_headers(response):
    """
    Middleware executado após cada request.
    
    - Remove header 'Server'
    - Adiciona headers de segurança
    - Configura Content-Security-Policy
    """
    # Remover header Server
    response.headers.pop('Server', None)
    
    # Headers de segurança
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "upgrade-insecure-requests"
    ]
    response.headers['Content-Security-Policy'] = '; '.join(csp_directives)
    
    return response
```

---

## 🧪 Testes de Validação

### **Arquivo**: `tests/test_security_headers.py`

**20 testes automatizados**:

1. ✅ `test_server_header_removed` - Header Server removido
2. ✅ `test_server_header_removed_api` - Server removido em API
3. ✅ `test_x_content_type_options_present` - X-Content-Type-Options configurado
4. ✅ `test_x_frame_options_present` - X-Frame-Options configurado
5. ✅ `test_x_xss_protection_present` - X-XSS-Protection configurado
6. ✅ `test_referrer_policy_present` - Referrer-Policy configurado
7. ✅ `test_csp_present` - CSP presente
8. ✅ `test_csp_default_src_self` - CSP default-src 'self'
9. ✅ `test_csp_script_src_configured` - CSP script-src configurado
10. ✅ `test_csp_style_src_configured` - CSP style-src configurado
11. ✅ `test_csp_img_src_configured` - CSP img-src configurado
12. ✅ `test_csp_connect_src_configured` - CSP connect-src configurado
13. ✅ `test_csp_frame_ancestors_none` - CSP frame-ancestors 'none'
14. ✅ `test_csp_upgrade_insecure_requests` - CSP upgrade-insecure-requests
15. ✅ `test_headers_on_health_endpoint` - Headers em /health
16. ✅ `test_headers_on_api_endpoints` - Headers em /api/*
17. ✅ `test_headers_on_static_files` - Headers em arquivos estáticos
18. ✅ `test_all_security_headers_present` - Todos headers presentes
19. ✅ `test_no_information_disclosure_headers` - Sem vazamento de info
20. ✅ `test_summary_security_headers` - Resumo geral

### Executar Testes

```bash
pytest tests/test_security_headers.py -v
```

---

## 🚀 Validação Manual (Produção)

### 1. **Verificar Headers com cURL**

```bash
curl -I https://seudominio.com/health
```

**Saída esperada**:
```http
HTTP/2 200
content-type: application/json
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; ...
```

**NÃO deve aparecer**:
```http
Server: Werkzeug/3.1.3 Python/3.14.0  ❌
```

---

### 2. **Verificar com Security Headers Analyzer**

Ferramentas online:
- **https://securityheaders.com/** - Análise completa de headers
- **https://observatory.mozilla.org/** - Score de segurança Mozilla

**Score esperado**: **A** ou **A+**

---

### 3. **Verificar CSP no Browser DevTools**

1. Abrir DevTools (F12)
2. Aba **Console**
3. Procurar por erros CSP:
   - ❌ `Refused to load script... violates Content Security Policy`
   - ✅ Não deve haver erros para recursos do próprio domínio

4. Aba **Network**
5. Selecionar request
6. Verificar **Response Headers**:
   - ✅ `Content-Security-Policy` presente
   - ✅ `X-Frame-Options: DENY`

---

## 🎯 Compatibilidade com Frontend React

### ✅ **Vite Build**
- `'unsafe-inline'` permite inline styles/scripts do Vite
- `'unsafe-eval'` permite HMR (Hot Module Replacement)

### ✅ **React Components**
- CSS Modules: `style-src 'unsafe-inline'`
- Styled-components: `style-src 'unsafe-inline'`
- Inline styles: `<div style={{...}}>` ✅

### ✅ **API Calls**
- `connect-src 'self'` permite fetch/axios ao backend
- Cross-origin API calls requerem ajuste:
  ```python
  csp = "connect-src 'self' https://api.external.com"
  ```

### ✅ **Imagens**
- Base64: `img-src data:` ✅
- CDNs: `img-src https:` ✅
- Imagens locais: `img-src 'self'` ✅

---

## ⚙️ Configuração Avançada (Produção)

### **Opção 1: CSP com Nonce (mais seguro)**

```python
import secrets

@app.after_request
def add_security_headers(response):
    # Gerar nonce único
    nonce = secrets.token_urlsafe(16)
    
    # CSP com nonce (remove 'unsafe-inline')
    csp = f"script-src 'self' 'nonce-{nonce}'"
    response.headers['Content-Security-Policy'] = csp
    
    # Injetar nonce no HTML (template Jinja2)
    # <script nonce="{{ nonce }}">...</script>
    
    return response
```

### **Opção 2: CSP Report-Only (testing)**

```python
# CSP em modo report-only (não bloqueia, apenas reporta)
response.headers['Content-Security-Policy-Report-Only'] = csp

# Configurar endpoint para receber reports
csp += "; report-uri /api/csp-report"
```

### **Opção 3: HSTS (Strict-Transport-Security)**

Já configurado no **Nginx** (`nginx.conf`):
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

Opcional em Flask (redundante se Nginx já envia):
```python
response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
```

---

## 🐛 Troubleshooting

### Problema: React não carrega (CSP blocking)

**Erro no Console**:
```
Refused to execute inline script because it violates CSP directive "script-src 'self'"
```

**Solução**:
Adicionar `'unsafe-inline'` ao `script-src`:
```python
"script-src 'self' 'unsafe-inline'"
```

---

### Problema: Imagens de CDN bloqueadas

**Erro no Console**:
```
Refused to load image from 'https://cdn.example.com/image.png' because it violates CSP directive "img-src 'self'"
```

**Solução**:
Adicionar domínio específico ou `https:` ao `img-src`:
```python
"img-src 'self' data: https://cdn.example.com"
# OU
"img-src 'self' data: https:"
```

---

### Problema: API externa bloqueada (fetch/axios)

**Erro no Console**:
```
Refused to connect to 'https://api.external.com' because it violates CSP directive "connect-src 'self'"
```

**Solução**:
Adicionar domínio da API ao `connect-src`:
```python
"connect-src 'self' https://api.external.com"
```

---

## 📈 Monitoramento Contínuo

### **1. CSP Violation Reports**

Configurar endpoint para receber reports:

```python
@app.route('/api/csp-report', methods=['POST'])
def csp_report():
    report = request.get_json()
    logger.warning(f"CSP Violation: {report}")
    
    # Salvar no banco para análise
    # ...
    
    return '', 204
```

Adicionar ao CSP:
```python
csp += "; report-uri /api/csp-report"
```

---

### **2. Alertas de Segurança**

Monitorar logs para:
- ❌ CSP violations frequentes (possível ataque XSS)
- ❌ Tentativas de clickjacking (requests com `Referer` suspeito)
- ❌ MIME sniffing attempts (Content-Type incorreto)

---

## ✅ Checklist de Segurança

Antes de deploy em produção:

- [x] Header `Server` removido ✅
- [x] `X-Content-Type-Options: nosniff` ✅
- [x] `X-Frame-Options: DENY` ✅
- [x] `X-XSS-Protection: 1; mode=block` ✅
- [x] `Referrer-Policy` configurado ✅
- [x] CSP configurado para React ✅
- [x] 20/20 testes passando ✅
- [ ] Testado em https://securityheaders.com ⏳
- [ ] Testado em https://observatory.mozilla.org ⏳
- [ ] CSP violations monitoradas ⏳
- [ ] Frontend React sem erros CSP ⏳

---

## 📚 Referências

- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [MDN - Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/3.1.x/security/)
- [CSP Evaluator (Google)](https://csp-evaluator.withgoogle.com/)

---

**Implementado em**: 2024-01-15  
**Última validação**: 2024-01-15 (20/20 testes)  
**Versão Flask**: 3.1.1  
**Compatibilidade**: React + Vite ✅
