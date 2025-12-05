#!/bin/bash
# Exemplo de integração com script de deploy
# Este script mostra como usar a auditoria de dependências antes do deploy

set -e  # Exit on error

echo "========================================="
echo "PRÉ-DEPLOY: Auditoria de Segurança"
echo "========================================="

# Executar auditoria completa
python scripts/pre_deploy_audit.py --fail-on high

# Se chegou aqui, auditoria passou
echo ""
echo "========================================="
echo "✓ Auditoria aprovada! Iniciando deploy..."
echo "========================================="

# ... comandos de deploy ...
# gunicorn -c gunicorn_config.py src.main:app
