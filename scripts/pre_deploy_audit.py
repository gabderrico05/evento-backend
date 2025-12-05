#!/usr/bin/env python3
"""
Script Unificado de Auditoria Pré-Deploy

Este script executa todas as verificações de segurança antes do deploy:
1. Auditoria de dependências Python (pip-audit)
2. Auditoria de dependências Node.js/React (npm audit)
3. Geração de relatório consolidado

Uso:
    python scripts/pre_deploy_audit.py [--fix] [--fail-on LEVEL]

Opções:
    --fix           Tenta corrigir vulnerabilidades automaticamente
    --fail-on       Nível mínimo para bloquear deploy (any, high, critical)
    --skip-python   Pula auditoria Python
    --skip-nodejs   Pula auditoria Node.js
    --report-only   Apenas gera relatório sem bloquear deploy

Retorna:
    0 - Deploy aprovado (sem vulnerabilidades ou abaixo do limite)
    1 - Deploy bloqueado (vulnerabilidades encontradas)
    2 - Erro na execução

Exemplo:
    python scripts/pre_deploy_audit.py --fail-on critical
"""

import subprocess
import sys
import json
import os
from datetime import datetime
from pathlib import Path


class Colors:
    """Cores ANSI para terminal"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_header(message):
    """Imprime cabeçalho formatado"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{message.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.RESET}\n")


def print_success(message):
    """Imprime mensagem de sucesso"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message):
    """Imprime mensagem de erro"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message):
    """Imprime mensagem de aviso"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message):
    """Imprime mensagem informativa"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def run_python_audit(fix=False, fail_on='any'):
    """
    Executa auditoria Python
    
    Args:
        fix: Se True, tenta corrigir vulnerabilidades
        fail_on: Nível mínimo para falhar (any, high, critical)
    
    Returns:
        tuple: (exit_code, has_vulnerabilities)
    """
    print_header("AUDITORIA PYTHON (Backend)")
    
    cmd = [sys.executable, 'scripts/audit_python.py', '--json', f'--fail-on={fail_on}']
    
    if fix:
        cmd.append('--fix')
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        
        if result.stderr:
            print(result.stderr)
        
        return result.returncode, result.returncode == 1
    except Exception as e:
        print_error(f"Erro ao executar auditoria Python: {e}")
        return 2, False


def run_nodejs_audit(fix=False, fail_on='any'):
    """
    Executa auditoria Node.js
    
    Args:
        fix: Se True, tenta corrigir vulnerabilidades
        fail_on: Nível mínimo para falhar (any, high, critical)
    
    Returns:
        tuple: (exit_code, has_vulnerabilities)
    """
    print_header("AUDITORIA NODE.JS/REACT (Frontend)")
    
    # Verificar se Node.js está instalado
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("Node.js não instalado. Pulando auditoria Node.js.")
        return 0, False
    
    cmd = ['node', 'scripts/audit_nodejs.js', '--json', f'--fail-on={fail_on}']
    
    if fix:
        cmd.append('--fix')
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        
        if result.stderr:
            print(result.stderr)
        
        return result.returncode, result.returncode == 1
    except Exception as e:
        print_error(f"Erro ao executar auditoria Node.js: {e}")
        return 2, False


def load_audit_reports():
    """
    Carrega relatórios de auditoria gerados
    
    Returns:
        dict: Relatórios consolidados
    """
    reports = {
        'python': None,
        'nodejs': None
    }
    
    # Carregar relatório Python
    python_report_path = Path('audit_reports/python_audit.json')
    if python_report_path.exists():
        with open(python_report_path, 'r', encoding='utf-8') as f:
            reports['python'] = json.load(f)
    
    # Carregar relatório Node.js
    nodejs_report_path = Path('audit_reports/nodejs_audit.json')
    if nodejs_report_path.exists():
        with open(nodejs_report_path, 'r', encoding='utf-8') as f:
            reports['nodejs'] = json.load(f)
    
    return reports


def generate_consolidated_report(reports, python_result, nodejs_result):
    """
    Gera relatório consolidado
    
    Args:
        reports: Relatórios individuais
        python_result: Resultado da auditoria Python
        nodejs_result: Resultado da auditoria Node.js
    """
    consolidated = {
        'timestamp': datetime.utcnow().isoformat(),
        'project': 'evento (backend + frontend)',
        'summary': {
            'python': {
                'status': 'passed' if python_result[0] == 0 else 'failed',
                'exit_code': python_result[0],
                'has_vulnerabilities': python_result[1]
            },
            'nodejs': {
                'status': 'passed' if nodejs_result[0] == 0 else 'failed',
                'exit_code': nodejs_result[0],
                'has_vulnerabilities': nodejs_result[1]
            }
        },
        'reports': reports
    }
    
    # Salvar relatório consolidado
    output_path = Path('audit_reports/consolidated_audit.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(consolidated, f, indent=2, ensure_ascii=False)
    
    print_success(f"Relatório consolidado salvo em: audit_reports/consolidated_audit.json")
    
    return consolidated


def print_final_summary(consolidated):
    """Imprime resumo final"""
    print_header("RESUMO FINAL DA AUDITORIA PRÉ-DEPLOY")
    
    python_status = consolidated['summary']['python']
    nodejs_status = consolidated['summary']['nodejs']
    
    print(f"{Colors.BOLD}Backend (Python):{Colors.RESET}")
    if python_status['status'] == 'passed':
        print_success("  Aprovado - Sem vulnerabilidades")
    else:
        if python_status['has_vulnerabilities']:
            print_error("  Reprovado - Vulnerabilidades encontradas")
        else:
            print_warning("  Erro na execução")
    
    print(f"\n{Colors.BOLD}Frontend (Node.js/React):{Colors.RESET}")
    if nodejs_status['status'] == 'passed':
        print_success("  Aprovado - Sem vulnerabilidades")
    else:
        if nodejs_status['has_vulnerabilities']:
            print_error("  Reprovado - Vulnerabilidades encontradas")
        else:
            print_warning("  Erro na execução")
    
    # Decisão final
    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.RESET}")
    
    if python_status['status'] == 'passed' and nodejs_status['status'] == 'passed':
        print(f"{Colors.GREEN}{Colors.BOLD}✓ DEPLOY APROVADO{Colors.RESET}")
        print(f"{Colors.GREEN}Nenhuma vulnerabilidade encontrada. Seguro para deploy.{Colors.RESET}")
        return 0
    elif python_status['has_vulnerabilities'] or nodejs_status['has_vulnerabilities']:
        print(f"{Colors.RED}{Colors.BOLD}✗ DEPLOY BLOQUEADO{Colors.RESET}")
        print(f"{Colors.RED}Vulnerabilidades de segurança detectadas.{Colors.RESET}")
        print(f"{Colors.YELLOW}Execute com --fix para tentar corrigir automaticamente.{Colors.RESET}")
        return 1
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ DEPLOY COM AVISOS{Colors.RESET}")
        print(f"{Colors.YELLOW}Erros na execução da auditoria. Verifique os logs acima.{Colors.RESET}")
        return 2


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auditoria de segurança pré-deploy (Python + Node.js)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Tenta corrigir vulnerabilidades automaticamente'
    )
    parser.add_argument(
        '--fail-on',
        choices=['any', 'high', 'critical'],
        default='any',
        help='Nível mínimo para bloquear deploy (padrão: any)'
    )
    parser.add_argument(
        '--skip-python',
        action='store_true',
        help='Pula auditoria Python'
    )
    parser.add_argument(
        '--skip-nodejs',
        action='store_true',
        help='Pula auditoria Node.js'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Apenas gera relatório sem bloquear deploy'
    )
    
    args = parser.parse_args()
    
    print_header("AUDITORIA DE SEGURANÇA PRÉ-DEPLOY")
    print_info(f"Projeto: evento (backend + frontend)")
    print_info(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Política de falha: {args.fail_on}")
    print_info(f"Correção automática: {'Sim' if args.fix else 'Não'}")
    
    # Executar auditorias
    python_result = (0, False)
    nodejs_result = (0, False)
    
    if not args.skip_python:
        python_result = run_python_audit(fix=args.fix, fail_on=args.fail_on)
    else:
        print_warning("Auditoria Python pulada (--skip-python)")
    
    if not args.skip_nodejs:
        nodejs_result = run_nodejs_audit(fix=args.fix, fail_on=args.fail_on)
    else:
        print_warning("Auditoria Node.js pulada (--skip-nodejs)")
    
    # Carregar relatórios
    reports = load_audit_reports()
    
    # Gerar relatório consolidado
    consolidated = generate_consolidated_report(reports, python_result, nodejs_result)
    
    # Imprimir resumo final
    exit_code = print_final_summary(consolidated)
    
    # Modo somente relatório
    if args.report_only:
        print_info("Modo --report-only: Deploy não será bloqueado")
        return 0
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
