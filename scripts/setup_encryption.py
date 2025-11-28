"""
Script de Inicialização Automática do Sistema de Criptografia

Este script automatiza:
1. Geração de ENCRYPTION_KEY segura (se não existir)
2. Atualização do arquivo .env
3. Instalação de dependências (cryptography)
4. Criação da tabela pagamento no PostgreSQL
5. Validação da configuração

Execute: python scripts/setup_encryption.py
"""

import os
import sys
import secrets
import subprocess
from pathlib import Path

# Adicionar src ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Cores para output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_step(step_number, message):
    """Imprime passo do processo"""
    print(f"\n{BLUE}[{step_number}/5]{RESET} {message}")

def print_success(message):
    """Imprime mensagem de sucesso"""
    print(f"{GREEN}✓{RESET} {message}")

def print_warning(message):
    """Imprime mensagem de aviso"""
    print(f"{YELLOW}⚠{RESET} {message}")

def print_error(message):
    """Imprime mensagem de erro"""
    print(f"{RED}✗{RESET} {message}")

def generate_encryption_key():
    """Gera uma chave de criptografia forte"""
    return secrets.token_hex(32)  # 256 bits

def update_env_file():
    """Atualiza arquivo .env com ENCRYPTION_KEY"""
    print_step(1, "Verificando arquivo .env...")
    
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        print_error(f"Arquivo .env não encontrado em {env_path}")
        print_warning("Copie .env.example para .env primeiro!")
        return False
    
    # Ler arquivo .env
    with open(env_path, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    # Verificar se já tem ENCRYPTION_KEY
    if 'ENCRYPTION_KEY=' in env_content:
        # Verificar se é a chave de exemplo
        if 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6' in env_content:
            print_warning("ENCRYPTION_KEY de exemplo encontrada. Gerando nova chave segura...")
            new_key = generate_encryption_key()
            
            # Substituir chave de exemplo
            env_content = env_content.replace(
                'ENCRYPTION_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2',
                f'ENCRYPTION_KEY={new_key}'
            )
            
            # Salvar
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            print_success(f"Nova ENCRYPTION_KEY gerada e salva em .env")
            print(f"   Chave: {new_key[:20]}...{new_key[-20:]}")
        else:
            print_success("ENCRYPTION_KEY já configurada")
    else:
        print_warning("ENCRYPTION_KEY não encontrada. Adicionando...")
        new_key = generate_encryption_key()
        
        # Adicionar após SECRET_KEY ou no final
        if 'SECRET_KEY=' in env_content:
            env_content = env_content.replace(
                'FLASK_ENV=development',
                f'FLASK_ENV=development\n\n# Encryption Key for AES-256 (NUNCA versionar esta chave!)\n# Gere uma nova chave forte: python -c "import secrets; print(secrets.token_hex(32))"\nENCRYPTION_KEY={new_key}'
            )
        else:
            env_content += f'\n\n# Encryption Key for AES-256\nENCRYPTION_KEY={new_key}\n'
        
        # Salvar
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print_success(f"ENCRYPTION_KEY adicionada ao .env")
        print(f"   Chave: {new_key[:20]}...{new_key[-20:]}")
    
    return True

def install_dependencies():
    """Instala dependências Python necessárias"""
    print_step(2, "Instalando dependências...")
    
    try:
        # Verificar se cryptography está instalado
        import cryptography
        print_success("Pacote 'cryptography' já instalado")
        return True
    except ImportError:
        print_warning("Pacote 'cryptography' não encontrado. Instalando...")
        
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', 
                'cryptography==42.0.5', '--quiet'
            ])
            print_success("Pacote 'cryptography' instalado com sucesso")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Erro ao instalar cryptography: {e}")
            print_warning("Execute manualmente: pip install cryptography==42.0.5")
            return False

def test_encryption():
    """Testa o módulo de criptografia"""
    print_step(3, "Testando módulo de criptografia...")
    
    try:
        # Recarregar dotenv
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        from src.utils.encryption import encrypt_field, decrypt_field, mask_sensitive_data
        
        # Teste 1: Criptografar e descriptografar
        test_data = "4111111111111111"
        encrypted = encrypt_field(test_data)
        decrypted = decrypt_field(encrypted)
        
        assert decrypted == test_data, "Falha na descriptografia"
        print_success("Teste de criptografia/descriptografia: OK")
        
        # Teste 2: Mascaramento
        masked = mask_sensitive_data(test_data, visible_chars=4)
        assert masked == "************1111", "Falha no mascaramento"
        print_success("Teste de mascaramento: OK")
        
        # Teste 3: Valores None
        assert encrypt_field(None) is None, "Falha com None"
        assert decrypt_field(None) is None, "Falha com None"
        print_success("Teste de valores None: OK")
        
        return True
    
    except Exception as e:
        print_error(f"Erro ao testar criptografia: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_database_table():
    """Cria a tabela pagamento no PostgreSQL"""
    print_step(4, "Criando tabela 'pagamento' no PostgreSQL...")
    
    # Carregar variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv()
    
    db_type = os.getenv('DATABASE_TYPE', 'sqlite')
    
    if db_type != 'postgresql':
        print_warning(f"DATABASE_TYPE={db_type}. Tabela só pode ser criada em PostgreSQL.")
        print_warning("Você pode criar manualmente quando migrar para PostgreSQL.")
        return True
    
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME')
    
    if not all([db_user, db_password, db_name]):
        print_warning("Credenciais do PostgreSQL não configuradas no .env")
        print_warning("Configure DB_USER, DB_PASSWORD e DB_NAME para criar a tabela automaticamente")
        return True
    
    # Tentar criar tabela via psycopg2
    try:
        import psycopg2
        
        # Conectar
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        cursor = conn.cursor()
        
        # Ler script SQL
        sql_path = Path(__file__).parent / 'create_pagamento_table.sql'
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Executar script
        cursor.execute(sql_script)
        conn.commit()
        
        print_success("Tabela 'pagamento' criada com sucesso")
        
        # Verificar tabela
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'pagamento'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print(f"   Colunas criadas: {len(columns)}")
        for col_name, col_type in columns[:5]:  # Mostrar primeiras 5
            print(f"      - {col_name} ({col_type})")
        
        cursor.close()
        conn.close()
        
        return True
    
    except ImportError:
        print_warning("Pacote 'psycopg2' não instalado")
        print_warning("Instale com: pip install psycopg2-binary")
        print_warning("Ou execute manualmente:")
        print(f"   psql -U {db_user} -d {db_name} -f scripts/create_pagamento_table.sql")
        return True
    
    except Exception as e:
        print_error(f"Erro ao criar tabela: {e}")
        print_warning("Execute manualmente:")
        print(f"   psql -U {db_user} -d {db_name} -f scripts/create_pagamento_table.sql")
        return True

def validate_setup():
    """Valida toda a configuração"""
    print_step(5, "Validando configuração completa...")
    
    issues = []
    
    # 1. Verificar .env
    env_path = Path(__file__).parent.parent / '.env'
    if not env_path.exists():
        issues.append(".env não encontrado")
    else:
        with open(env_path, 'r') as f:
            env_content = f.read()
            
            if 'ENCRYPTION_KEY=' not in env_content:
                issues.append("ENCRYPTION_KEY não configurada")
            elif len(os.getenv('ENCRYPTION_KEY', '')) < 32:
                issues.append("ENCRYPTION_KEY muito curta (< 32 caracteres)")
    
    # 2. Verificar módulo de criptografia
    try:
        from src.utils.encryption import EncryptionManager
        print_success("Módulo de criptografia: OK")
    except Exception as e:
        issues.append(f"Erro ao importar encryption.py: {e}")
    
    # 3. Verificar modelo de pagamento
    try:
        from src.models.pagamento import Pagamento
        print_success("Modelo de Pagamento: OK")
    except Exception as e:
        issues.append(f"Erro ao importar pagamento.py: {e}")
    
    # 4. Verificar cryptography
    try:
        import cryptography
        print_success("Pacote cryptography: OK")
    except ImportError:
        issues.append("Pacote cryptography não instalado")
    
    if issues:
        print_error("\nProblemas encontrados:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print_success("\n✓ Todas as validações passaram!")
        return True

def main():
    """Função principal"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}   Setup de Criptografia AES-256-GCM - Sistema de Eventos{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Passo 1: Atualizar .env
    if not update_env_file():
        print_error("\nSetup abortado.")
        sys.exit(1)
    
    # Passo 2: Instalar dependências
    if not install_dependencies():
        print_warning("\nContinuando sem cryptography...")
    
    # Passo 3: Testar criptografia
    if not test_encryption():
        print_error("\nTestes falharam. Verifique a configuração.")
        sys.exit(1)
    
    # Passo 4: Criar tabela
    create_database_table()
    
    # Passo 5: Validar
    if not validate_setup():
        print_warning("\nSetup concluído com avisos. Verifique os problemas acima.")
        sys.exit(1)
    
    # Sucesso!
    print(f"\n{GREEN}{'='*60}{RESET}")
    print(f"{GREEN}✓ Setup de criptografia concluído com sucesso!{RESET}")
    print(f"{GREEN}{'='*60}{RESET}\n")
    
    print("Próximos passos:")
    print("1. Verifique sua ENCRYPTION_KEY em .env (NUNCA versione!)")
    print("2. Teste o modelo de Pagamento:")
    print("   python -c \"from src.models.pagamento import Pagamento; print('OK')\"")
    print("3. Leia ENCRYPTION.md para documentação completa")
    print("\nDocumentação: evento-backend/ENCRYPTION.md")
    print(f"\n{BLUE}Sistema pronto para uso!{RESET}\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Setup cancelado pelo usuário{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Erro inesperado: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
