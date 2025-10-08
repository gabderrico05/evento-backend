import requests
import json

# URL base da API
BASE_URL = "http://localhost:5000/api"

def test_register():
    """Testa o registro de usuário"""
    url = f"{BASE_URL}/auth/register"
    data = {
        "username": "testuser",
        "email": "test@exemplo.com",
        "password": "senha123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Registro - Status: {response.status_code}")
        print(f"Resposta: {response.json()}")
        
        if response.status_code == 201:
            return response.json().get('token')
    except Exception as e:
        print(f"Erro no registro: {e}")
    
    return None

def test_login():
    """Testa o login"""
    url = f"{BASE_URL}/auth/login"
    data = {
        "login": "testuser",
        "password": "senha123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Login - Status: {response.status_code}")
        print(f"Resposta: {response.json()}")
        
        if response.status_code == 200:
            return response.json().get('token')
    except Exception as e:
        print(f"Erro no login: {e}")
    
    return None

def test_protected_route(token):
    """Testa uma rota protegida"""
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Rota protegida - Status: {response.status_code}")
        print(f"Resposta: {response.json()}")
    except Exception as e:
        print(f"Erro na rota protegida: {e}")

if __name__ == "__main__":
    print("=== Testando Sistema de Login ===\n")
    
    # Teste 1: Registro
    print("1. Testando registro...")
    token = test_register()
    print()
    
    # Teste 2: Login (caso registro falhe)
    if not token:
        print("2. Tentando login...")
        token = test_login()
        print()
    
    # Teste 3: Rota protegida
    if token:
        print("3. Testando rota protegida...")
        test_protected_route(token)
    else:
        print("3. Não foi possível obter token para testar rota protegida")
    
    print("\n=== Fim dos testes ===")