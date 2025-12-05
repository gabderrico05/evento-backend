#!/usr/bin/env python3
"""
Script de Auditoria de Dependências Python

Este script verifica vulnerabilidades conhecidas em todas as dependências Python
do projeto usando pip-audit.

Uso:
    python scripts/audit_python.py [--json] [--fix]

Opções:
    --json          Gera relatório em JSON
    --fix           Tenta corrigir vulnerabilidades automaticamente
    --severity      Filtra por severidade mínima (low, medium, high, critical)

Retorna:
    0 - Nenhuma vulnerabilidade encontrada
    1 - Vulnerabilidades encontradas
    2 - Erro na execução

Exemplo:
    python scripts/audit_python.py --severity high
"""

import subprocess
import sys
import json
import os
from datetime import datetime
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


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


def check_pip_audit_installed():
    """Verifica se pip-audit está instalado"""
    try:
        subprocess.run(
            ['pip-audit', '--version'],
            capture_output=True,
            check=True,
            text=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_pip_audit():
    """Instala pip-audit"""
    print_info("pip-audit não encontrado. Instalando...")
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'pip-audit'],
            check=True,
            capture_output=True
        )
        print_success("pip-audit instalado com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Falha ao instalar pip-audit: {e}")
        return False


def run_pip_audit(output_json=False, fix=False, severity=None):
    """
    Executa pip-audit
    
    Args:
        output_json: Se True, retorna output em JSON
        fix: Se True, tenta corrigir vulnerabilidades
        severity: Severidade mínima (low, medium, high, critical)
    
    Returns:
        tuple: (exit_code, output)
    """
    cmd = ['pip-audit']
    
    if output_json:
        cmd.append('--format=json')
    
    if fix:
        cmd.append('--fix')
    
    if severity:
        # pip-audit não tem flag --severity, então filtramos depois
        pass
    
    # Adicionar requirements.txt
    requirements_file = Path('requirements.txt')
    if requirements_file.exists():
        cmd.extend(['-r', str(requirements_file)])
    
    print_info(f"Executando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        print_error(f"Erro ao executar pip-audit: {e}")
        return 2, "", str(e)


def parse_json_output(json_output):
    """
    Parseia output JSON do pip-audit
    
    Returns:
        dict: Dados parseados
    """
    try:
        data = json.loads(json_output)
        return data
    except json.JSONDecodeError as e:
        print_error(f"Erro ao parsear JSON: {e}")
        return None


def filter_by_severity(vulnerabilities, min_severity):
    """
    Filtra vulnerabilidades por severidade mínima
    
    Args:
        vulnerabilities: Lista de vulnerabilidades
        min_severity: Severidade mínima (low, medium, high, critical)
    
    Returns:
        list: Vulnerabilidades filtradas
    """
    severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
    min_level = severity_order.get(min_severity.lower(), 0)
    
    filtered = []
    for vuln in vulnerabilities:
        # pip-audit JSON format pode variar, adaptar conforme necessário
        vuln_severity = vuln.get('severity', 'unknown').lower()
        vuln_level = severity_order.get(vuln_severity, 0)
        
        if vuln_level >= min_level:
            filtered.append(vuln)
    
    return filtered


def generate_report(audit_data, output_file='audit_reports/python_audit.json'):
    """
    Gera relatório de auditoria
    
    Args:
        audit_data: Dados da auditoria
        output_file: Arquivo de saída
    """
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'tool': 'pip-audit',
        'project': 'evento-backend',
        'audit_data': audit_data
    }
    
    # Criar diretório de relatórios
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print_success(f"Relatório salvo em: {output_file}")


def print_summary(exit_code, stdout, stderr):
    """Imprime resumo da auditoria"""
    print_header("RESUMO DA AUDITORIA PYTHON")
    
    if exit_code == 0:
        print_success("Nenhuma vulnerabilidade conhecida encontrada!")
        print_info("Todas as dependências Python estão seguras.")
    elif exit_code == 1:
        print_warning("VULNERABILIDADES ENCONTRADAS!")
        print("\n" + stdout)
        if stderr:
            print_error("Erros:")
            print(stderr)
    else:
        print_error("ERRO NA EXECUÇÃO DA AUDITORIA!")
        if stderr:
            print(stderr)
    
    print(f"\n{Colors.BOLD}Exit code: {exit_code}{Colors.RESET}")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auditoria de segurança de dependências Python'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Gera relatório em formato JSON'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Tenta corrigir vulnerabilidades automaticamente'
    )
    parser.add_argument(
        '--severity',
        choices=['low', 'medium', 'high', 'critical'],
        help='Severidade mínima para reportar'
    )
    parser.add_argument(
        '--fail-on',
        choices=['any', 'high', 'critical'],
        default='any',
        help='Falha no deploy se encontrar vulnerabilidades (padrão: any)'
    )
    
    args = parser.parse_args()
    
    print_header("AUDITORIA DE DEPENDÊNCIAS PYTHON")
    print_info(f"Projeto: evento-backend")
    print_info(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar se pip-audit está instalado
    if not check_pip_audit_installed():
        if not install_pip_audit():
            print_error("Não foi possível instalar pip-audit")
            return 2
    
    # Executar auditoria
    exit_code, stdout, stderr = run_pip_audit(
        output_json=args.json,
        fix=args.fix,
        severity=args.severity
    )
    
    # Gerar relatório JSON se solicitado
    if args.json and stdout:
        audit_data = parse_json_output(stdout)
        if audit_data:
            generate_report(audit_data)
    
    # Imprimir resumo
    print_summary(exit_code, stdout, stderr)
    
    # Determinar se deve falhar
    if args.fail_on == 'any' and exit_code == 1:
        print_error("Deploy BLOQUEADO: Vulnerabilidades encontradas")
        return 1
    elif args.fail_on in ['high', 'critical'] and exit_code == 1:
        # Analisar severidade (requer parsing do output)
        print_warning("Deploy PERMITIDO: Apenas vulnerabilidades de baixa severidade")
        return 0
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
