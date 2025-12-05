# Auditoria de Dependências - Guia Completo

Este documento explica como usar o sistema de auditoria de segurança para verificar vulnerabilidades conhecidas em todas as dependências do projeto antes do deploy.

## 📋 Visão Geral

O sistema de auditoria verifica vulnerabilidades em:
- **Backend (Python)**: Usando `pip-audit`
- **Frontend (Node.js/React)**: Usando `npm audit`

## 🛠️ Ferramentas

### pip-audit (Python)
Ferramenta oficial da PyPA para auditar dependências Python contra o banco de dados PyPI Advisory Database.

### npm audit (Node.js)
Ferramenta nativa do npm para verificar vulnerabilidades no registro npm.

## 📁 Scripts Disponíveis

### 1. `scripts/audit_python.py`
Auditoria específica do backend Python.

**Uso**:
```bash
python scripts/audit_python.py [opções]
```

**Opções**:
- `--json`: Gera relatório em formato JSON
- `--fix`: Tenta corrigir vulnerabilidades automaticamente
- `--severity LEVEL`: Filtra por severidade mínima (low, medium, high, critical)
- `--fail-on LEVEL`: Define quando falhar (any, high, critical)

**Exemplos**:
```bash
# Auditoria básica
python scripts/audit_python.py

# Auditoria com correção automática
python scripts/audit_python.py --fix

# Falhar apenas em vulnerabilidades críticas
python scripts/audit_python.py --fail-on critical

# Gerar relatório JSON
python scripts/audit_python.py --json
```

---

### 2. `scripts/audit_nodejs.js`
Auditoria específica do frontend Node.js/React.

**Uso**:
```bash
node scripts/audit_nodejs.js [opções]
```

**Opções**:
- `--json`: Gera relatório em formato JSON
- `--fix`: Tenta corrigir vulnerabilidades automaticamente
- `--production`: Audita apenas dependências de produção
- `--severity LEVEL`: Filtra por severidade mínima
- `--fail-on LEVEL`: Define quando falhar (any, high, critical)

**Exemplos**:
```bash
# Auditoria básica
node scripts/audit_nodejs.js

# Auditoria com correção automática
node scripts/audit_nodejs.js --fix

# Apenas dependências de produção
node scripts/audit_nodejs.js --production

# Falhar apenas em vulnerabilidades altas ou críticas
node scripts/audit_nodejs.js --fail-on high
```

---

### 3. `scripts/pre_deploy_audit.py` ⭐ **RECOMENDADO**
Script unificado que executa ambas as auditorias.

**Uso**:
```bash
python scripts/pre_deploy_audit.py [opções]
```

**Opções**:
- `--fix`: Tenta corrigir vulnerabilidades em ambos os projetos
- `--fail-on LEVEL`: Define quando bloquear deploy (any, high, critical)
- `--skip-python`: Pula auditoria Python
- `--skip-nodejs`: Pula auditoria Node.js
- `--report-only`: Apenas gera relatório sem bloquear deploy

**Exemplos**:
```bash
# Auditoria completa (Python + Node.js)
python scripts/pre_deploy_audit.py

# Auditoria com correção automática
python scripts/pre_deploy_audit.py --fix

# Bloquear deploy apenas em vulnerabilidades críticas
python scripts/pre_deploy_audit.py --fail-on critical

# Apenas relatório (não bloqueia deploy)
python scripts/pre_deploy_audit.py --report-only

# Auditar apenas backend
python scripts/pre_deploy_audit.py --skip-nodejs
```

---

## 🚀 Integração com CI/CD

### GitHub Actions
Adicione ao `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main, production]

jobs:
  security-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          cd ../evento-site && npm ci
      
      - name: Run Security Audit
        run: python scripts/pre_deploy_audit.py --fail-on high
      
      - name: Upload Audit Reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: audit-reports
          path: audit_reports/

  deploy:
    needs: security-audit
    runs-on: ubuntu-latest
    steps:
      # ... passos de deploy ...
```

---

### GitLab CI
Adicione ao `.gitlab-ci.yml`:

```yaml
stages:
  - audit
  - deploy

security_audit:
  stage: audit
  image: python:3.10
  before_script:
    - apt-get update && apt-get install -y nodejs npm
    - pip install -r requirements.txt
    - cd ../evento-site && npm ci && cd -
  script:
    - python scripts/pre_deploy_audit.py --fail-on high
  artifacts:
    paths:
      - audit_reports/
    expire_in: 30 days
  only:
    - main
    - production

deploy_production:
  stage: deploy
  dependencies:
    - security_audit
  script:
    - # ... comandos de deploy ...
  only:
    - production
```

---

### Azure DevOps
Adicione ao `azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main
      - production

pool:
  vmImage: 'ubuntu-latest'

stages:
- stage: SecurityAudit
  displayName: 'Security Audit'
  jobs:
  - job: AuditDependencies
    steps:
    - task: UsePythonVersion@0
      inputs:
        versionSpec: '3.10'
    
    - task: NodeTool@0
      inputs:
        versionSpec: '18.x'
    
    - script: |
        pip install -r requirements.txt
        cd ../evento-site && npm ci && cd -
      displayName: 'Install Dependencies'
    
    - script: python scripts/pre_deploy_audit.py --fail-on high
      displayName: 'Run Security Audit'
    
    - task: PublishBuildArtifacts@1
      condition: always()
      inputs:
        pathToPublish: 'audit_reports'
        artifactName: 'security-audit-reports'

- stage: Deploy
  dependsOn: SecurityAudit
  jobs:
  - job: DeployApp
    steps:
    # ... passos de deploy ...
```

---

## 📊 Relatórios Gerados

Os scripts geram relatórios JSON no diretório `audit_reports/`:

### `python_audit.json`
```json
{
  "timestamp": "2024-01-15T10:30:00.000000",
  "tool": "pip-audit",
  "project": "evento-backend",
  "audit_data": {
    "vulnerabilities": [
      {
        "package": "werkzeug",
        "version": "2.3.0",
        "vulnerability_id": "PYSEC-2024-123",
        "severity": "high",
        "description": "...",
        "fixed_version": "2.3.7"
      }
    ]
  }
}
```

### `nodejs_audit.json`
```json
{
  "timestamp": "2024-01-15T10:31:00.000000",
  "tool": "npm audit",
  "project": "evento-site",
  "severity_stats": {
    "critical": 0,
    "high": 2,
    "moderate": 5,
    "low": 3,
    "info": 1,
    "total": 11
  },
  "audit_data": { ... }
}
```

### `consolidated_audit.json`
```json
{
  "timestamp": "2024-01-15T10:32:00.000000",
  "project": "evento (backend + frontend)",
  "summary": {
    "python": {
      "status": "passed",
      "exit_code": 0,
      "has_vulnerabilities": false
    },
    "nodejs": {
      "status": "failed",
      "exit_code": 1,
      "has_vulnerabilities": true
    }
  },
  "reports": { ... }
}
```

---

## 🔧 Configuração

### Instalação de Dependências

**Backend (Python)**:
```bash
pip install pip-audit
# ou
pip install -r requirements.txt
```

**Frontend (Node.js)**:
```bash
# npm audit já vem com npm (nada a instalar)
```

---

## 📝 Políticas de Severidade

### Níveis de Severidade

| Severidade | Descrição | Ação Recomendada |
|-----------|-----------|------------------|
| **Critical** | Vulnerabilidades críticas que permitem execução remota de código ou comprometimento total do sistema | Bloquear deploy imediatamente |
| **High** | Vulnerabilidades graves que podem comprometer a segurança | Bloquear deploy e corrigir ASAP |
| **Moderate** | Vulnerabilidades médias com impacto limitado | Revisar e planejar correção |
| **Low** | Vulnerabilidades menores com impacto mínimo | Monitorar e corrigir quando possível |
| **Info** | Informações sobre atualizações disponíveis | Opcional |

### Políticas de Deploy

#### Política Restritiva (`--fail-on any`)
```bash
python scripts/pre_deploy_audit.py --fail-on any
```
- **Uso**: Ambientes de produção críticos
- **Comportamento**: Bloqueia deploy se **qualquer** vulnerabilidade for encontrada
- **Vantagem**: Máxima segurança
- **Desvantagem**: Pode bloquear deploys frequentemente

#### Política Balanceada (`--fail-on high`) ⭐ **RECOMENDADO**
```bash
python scripts/pre_deploy_audit.py --fail-on high
```
- **Uso**: Produção padrão
- **Comportamento**: Bloqueia apenas vulnerabilidades **high** e **critical**
- **Vantagem**: Equilíbrio entre segurança e agilidade
- **Desvantagem**: Vulnerabilidades moderate/low são permitidas

#### Política Permissiva (`--fail-on critical`)
```bash
python scripts/pre_deploy_audit.py --fail-on critical
```
- **Uso**: Desenvolvimento, staging
- **Comportamento**: Bloqueia apenas vulnerabilidades **critical**
- **Vantagem**: Máxima agilidade
- **Desvantagem**: Vulnerabilidades high são permitidas

---

## 🛡️ Correção de Vulnerabilidades

### Correção Automática

**Python**:
```bash
python scripts/audit_python.py --fix
```
O pip-audit tentará atualizar pacotes para versões corrigidas.

**Node.js**:
```bash
node scripts/audit_nodejs.js --fix
# ou diretamente
npm audit fix
```

**Ambos**:
```bash
python scripts/pre_deploy_audit.py --fix
```

### Correção Manual

1. **Identificar vulnerabilidade**:
```bash
python scripts/pre_deploy_audit.py --json
```

2. **Verificar correção disponível** no relatório JSON

3. **Atualizar dependência** manualmente:

   **Python** (`requirements.txt`):
   ```diff
   - werkzeug==2.3.0
   + werkzeug==2.3.7
   ```

   **Node.js** (`package.json`):
   ```diff
   - "express": "4.17.1"
   + "express": "4.18.2"
   ```

4. **Reinstalar**:
   ```bash
   pip install -r requirements.txt
   # ou
   npm install
   ```

5. **Verificar novamente**:
   ```bash
   python scripts/pre_deploy_audit.py
   ```

---

## 🎯 Melhores Práticas

### 1. Execute Antes de Cada Deploy
Sempre execute a auditoria antes de fazer deploy para produção:
```bash
python scripts/pre_deploy_audit.py --fail-on high
```

### 2. Integre ao CI/CD
Configure o pipeline para executar automaticamente:
- ✅ Bloqueia merges/deploys com vulnerabilidades
- ✅ Gera relatórios armazenados como artefatos
- ✅ Notifica equipe sobre problemas

### 3. Revise Relatórios Regularmente
Agende auditorias semanais mesmo sem deploy:
```bash
# Cron job (Linux/Mac)
0 9 * * 1 cd /path/to/projeto && python scripts/pre_deploy_audit.py --report-only
```

### 4. Mantenha Dependências Atualizadas
```bash
# Python
pip list --outdated

# Node.js
npm outdated
```

### 5. Use Políticas Apropriadas
- **Produção**: `--fail-on high` (mínimo)
- **Staging**: `--fail-on critical`
- **Desenvolvimento**: `--report-only`

### 6. Documente Exceções
Se precisar pular uma vulnerabilidade temporariamente, documente:

```python
# .auditignore (exemplo)
{
  "vulnerabilities": [
    {
      "id": "PYSEC-2024-123",
      "package": "werkzeug",
      "reason": "Aguardando correção upstream - workaround aplicado",
      "expires": "2024-02-01",
      "approved_by": "security-team@exemplo.com"
    }
  ]
}
```

---

## 🔍 Troubleshooting

### Erro: "pip-audit not found"
**Solução**:
```bash
pip install pip-audit
```

### Erro: "npm not found"
**Solução**:
- Instale Node.js: https://nodejs.org/
- Ou use Docker: `docker run -it node:18 /bin/bash`

### Falsos Positivos
Vulnerabilidades reportadas incorretamente:

1. Verifique se é falso positivo no banco de dados oficial
2. Reporte o falso positivo:
   - Python: https://github.com/pypa/advisory-database
   - Node.js: https://github.com/advisories

3. Temporariamente: Use `--report-only` e monitore

### Performance Lenta
Auditoria demorando muito:

**Python**:
```bash
# Cache local
pip-audit --cache-dir ~/.cache/pip-audit
```

**Node.js**:
```bash
# Apenas produção (mais rápido)
node scripts/audit_nodejs.js --production
```

---

## 📚 Recursos Adicionais

- **pip-audit**: https://github.com/pypa/pip-audit
- **npm audit**: https://docs.npmjs.com/cli/v9/commands/npm-audit
- **PyPI Advisory Database**: https://github.com/pypa/advisory-database
- **npm Security**: https://docs.npmjs.com/about-security-audits
- **OWASP Dependency Check**: https://owasp.org/www-project-dependency-check/

---

## 🆘 Suporte

Em caso de dúvidas ou problemas:

1. Verifique a documentação acima
2. Execute com `--help`:
   ```bash
   python scripts/audit_python.py --help
   node scripts/audit_nodejs.js --help
   python scripts/pre_deploy_audit.py --help
   ```
3. Consulte os logs em `audit_reports/`
4. Entre em contato com a equipe de segurança

---

## 📅 Changelog

### v1.0.0 (2024-01-15)
- ✅ Script de auditoria Python (`audit_python.py`)
- ✅ Script de auditoria Node.js (`audit_nodejs.js`)
- ✅ Script unificado pré-deploy (`pre_deploy_audit.py`)
- ✅ Geração de relatórios JSON
- ✅ Políticas de severidade configuráveis
- ✅ Correção automática de vulnerabilidades
- ✅ Documentação completa
