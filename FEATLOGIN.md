# Backend - Fluxo de Login e Resgate de Ingresso

Este backend em Flask fornece endpoints para cadastro (resgate de ingresso) e login de participantes. O fluxo antigo que utilizava **código de evento** foi removido e substituído por **senha pessoal** do participante.

## ✅ Visão Geral do Novo Fluxo
1. Usuário acessa a tela inicial e clica em "Entrar / Resgatar".
2. Vai primeiro para a tela de **Login** (email + senha).
3. Se já possui cadastro: faz login e vê seus dados / ingresso.
4. Se não possui: clica em "Não possui login?" → vai para a tela de **Resgate (Cadastro)**.
5. Após resgatar, já pode visualizar o ingresso.

## 🗄 Modelo `Participante`
Campos principais (tabela `participante`):
| Campo | Tipo | Descrição |
|-------|------|----------|
| id | int (PK) | Identificador |
| nome | string | Nome completo |
| email | string | Email (único por ingresso ativo) |
| cpf | string | CPF validado (único) |
| telefone | string | Telefone (10 ou 11 dígitos) |
| senha_hash | string | Hash seguro da senha (Werkzeug) |
| numero_ingresso | string | Código único gerado (prefixo EVT) |
| data_resgate | datetime | Data/hora do cadastro |
| ativo | boolean | Ingresso válido |

> O campo `codigo_evento` foi removido completamente.

## 🔐 Endpoints
Base: `/api`

### 1. Resgatar / Cadastro
`POST /api/resgatar-ingresso`

Body JSON:
```json
{
  "nome": "João Silva",
  "email": "joao@example.com",
  "cpf": "123.456.789-09",
  "telefone": "(11) 98888-7777",
  "senha": "minhaSenhaSegura"
}
```
Respostas:
- 201 (sucesso) → retorna objeto do participante (sem senha)
- 400 → erro de validação (mensagem em `error`)

### 2. Login
`POST /api/login`

Body:
```json
{ "email": "joao@example.com", "senha": "minhaSenhaSegura" }
```
Respostas:
- 200 → participante (mesmo formato do cadastro)
- 401 → `{ "error": "Credenciais inválidas" }`
- 400 → `{ "error": "Email e senha são obrigatórios" }`

### 3. Listar Participantes (uso interno/teste)
`GET /api/participantes`

### 4. Buscar Participante por ID
`GET /api/participante/<id>`

## 🔄 Estrutura das Respostas (Participante)
```json
{
  "id": 1,
  "nome": "João Silva",
  "email": "joao@example.com",
  "cpf": "12345678909",
  "cpfFormatado": "123.456.789-09",
  "telefone": "(11) 98888-7777",
  "numeroIngresso": "EVTAB12CD34",
  "dataResgate": "2025-10-08T14:22:11.330194",
  "ativo": true
}
```

## 🧪 Exemplos de Código (Front-End)
### Cadastro
```js
async function cadastrar(dados) {
  const resp = await fetch('/api/resgatar-ingresso', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dados)
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || 'Erro ao resgatar');
  return data;
}
```

### Login
```js
async function login(email, senha) {
  const resp = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, senha })
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || 'Falha no login');
  return data;
}
```

### Sessão Local
```js
function salvarParticipante(p) { localStorage.setItem('participante', JSON.stringify(p)); }
function obterParticipante() { return JSON.parse(localStorage.getItem('participante') || 'null'); }
function logout() { localStorage.removeItem('participante'); }
```

## 🧠 Fluxo do Front (Sugestão)
1. Ao carregar app:
   - Se `participante` no localStorage → redirecionar para página "Meu Ingresso".
   - Caso contrário → mostrar tela de Login.
2. Tela Login:
   - Form (email, senha)
   - Se sucesso → salvar participante + ir para "Meu Ingresso".
   - Link: "Não possui login?" → tela de Cadastro.
3. Tela Cadastro:
   - Envia para `/api/resgatar-ingresso`
   - Se sucesso → salvar + ir para "Meu Ingresso".
4. Tela Meu Ingresso:
   - Exibe dados retornados.
   - Botão Sair → `logout()`.

## 🧾 Validações Realizadas no Backend
| Campo | Regra |
|-------|------|
| nome | >= 2 caracteres |
| email | formato regex simples |
| cpf | algoritmo oficial + 11 dígitos |
| telefone | 10 ou 11 dígitos (apenas números) |
| senha | apenas obrigatório (regras extras podem ser no front) |

## 🔐 Segurança Atual
- Senhas armazenadas como hash via `werkzeug.security.generate_password_hash`.
- Sem tokens/JWT ainda (pode ser adicionado depois).

### Melhorias Futuras (Opcional)
- JWT / sessão server-side
- Recuperação de senha
- Limite de tentativas de login
- Validação de força de senha

## 🗃 Migração do Banco
Como a estrutura mudou (remoção de `codigo_evento` e adição de `senha_hash`), apague o banco SQLite antes de rodar de novo em ambiente local:
```powershell
Remove-Item -Path .\src\database\app.db
```
Ao iniciar a aplicação Flask, o `db.create_all()` recriará o arquivo com o novo schema.

## ▶️ Rodando o Backend
### Instalar dependências
```powershell
pip install -r requirements.txt
```
### Executar
```powershell
python .\src\main.py
```
A API ficará em: `http://localhost:5000/api`

## ✅ Checklist para o Front
- [ ] Tela Login
- [ ] Tela Cadastro (Resgate)
- [ ] Armazenar sessão local
- [ ] Exibir ingresso
- [ ] Tratar mensagens de erro
- [ ] Implementar logout
- [ ] Redirecionamentos condicionais

## ❓ Erros Possíveis
| Mensagem | Significado |
|----------|------------|
| Campo X é obrigatório | Front não enviou ou vazio |
| CPF inválido | Falha na validação do algoritmo |
| Email inválido | Regex falhou |
| CPF já possui ingresso resgatado | Usuário já cadastrado |
| Email já possui ingresso resgatado | Usuário já cadastrado |
| Credenciais inválidas | Email ou senha incorretos |
| Erro interno do servidor | Exceção inesperada |

---
Se precisar acrescentar JWT ou controle de sessão mais forte, posso estender este arquivo.
