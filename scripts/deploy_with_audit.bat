@echo off
REM Exemplo de integração com script de deploy (Windows)
REM Este script mostra como usar a auditoria de dependências antes do deploy

echo =========================================
echo PRE-DEPLOY: Auditoria de Seguranca
echo =========================================

REM Executar auditoria completa
python scripts/pre_deploy_audit.py --fail-on high

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo =========================================
    echo X AUDITORIA FALHOU! Deploy bloqueado.
    echo =========================================
    exit /b 1
)

REM Se chegou aqui, auditoria passou
echo.
echo =========================================
echo OK Auditoria aprovada! Iniciando deploy...
echo =========================================

REM ... comandos de deploy ...
REM gunicorn -c gunicorn_config.py src.main:app
