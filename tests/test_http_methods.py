"""
Testes de Validação de Métodos HTTP

Este arquivo testa se os endpoints críticos (login, registro) aceitam apenas POST,
garantindo que dados sensíveis (senha, CPF) não sejam expostos em URLs via GET.

Endpoints testados:
- /api/login (Participante) - Deve aceitar apenas POST
- /api/resgatar-ingresso (Cadastro) - Deve aceitar apenas POST
- /api/user/login (Admin) - Deve aceitar apenas POST
- /api/user/register (Admin) - Deve aceitar apenas POST

Security:
- Senhas e CPFs NUNCA devem ser enviados via GET (apareceriam em logs, URLs, histórico)
- GET requests devem retornar 405 Method Not Allowed
"""

import sys
import os

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from flask import Flask
from flask_cors import CORS
from src.models.db import db
from src.models.participante import Participante
from src.models.user import User
from src.routes.evento import evento_bp
from src.routes.user import user_bp


@pytest.fixture
def app():
    """Criar aplicação Flask para testes"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Inicializar extensões
    db.init_app(app)
    CORS(app)
    
    # Registrar blueprints
    app.register_blueprint(evento_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente de testes Flask"""
    return app.test_client()


@pytest.fixture
def participante_teste(app):
    """Criar um participante de teste"""
    with app.app_context():
        participante = Participante(
            nome='João Silva',
            email='joao@example.com',
            cpf='12345678901',
            telefone='11987654321',
            senha='senha123'
        )
        db.session.add(participante)
        db.session.commit()
        return participante


@pytest.fixture
def user_teste(app):
    """Criar um usuário admin de teste"""
    with app.app_context():
        user = User(
            username='admin_test',
            email='admin@example.com'
        )
        user.set_password('senha123')
        db.session.add(user)
        db.session.commit()
        return user


class TestParticipanteLoginHTTPMethods:
    """Testes para validar métodos HTTP no endpoint de login de participante"""
    
    def test_login_participante_post_permitido(self, client, participante_teste):
        """POST deve ser aceito no login de participante"""
        response = client.post('/api/login', json={
            'email': 'joao@example.com',
            'senha': 'senha123'
        })
        
        # Deve retornar 200 (sucesso) ou 401 (credenciais inválidas)
        # Não deve retornar 405 (método não permitido)
        assert response.status_code in [200, 401], \
            f"POST deve ser aceito, mas retornou {response.status_code}"
    
    def test_login_participante_get_bloqueado(self, client):
        """GET deve ser BLOQUEADO no login de participante"""
        # Tentar GET com credenciais na URL (inseguro!)
        response = client.get('/api/login?email=joao@example.com&senha=senha123')
        
        # Deve retornar 405 Method Not Allowed
        assert response.status_code == 405, \
            f"GET deve ser bloqueado (405), mas retornou {response.status_code}"
        
        # Verificar mensagem de erro
        if response.json:
            assert 'method' in response.json.get('error', '').lower() or \
                   'not allowed' in response.json.get('error', '').lower() or \
                   response.json.get('message', '').lower().find('allowed') != -1, \
                "Mensagem de erro deve indicar método não permitido"
    
    def test_login_participante_put_bloqueado(self, client):
        """PUT deve ser bloqueado no login"""
        response = client.put('/api/login', json={
            'email': 'joao@example.com',
            'senha': 'senha123'
        })
        
        assert response.status_code == 405, \
            f"PUT deve ser bloqueado (405), mas retornou {response.status_code}"
    
    def test_login_participante_delete_bloqueado(self, client):
        """DELETE deve ser bloqueado no login"""
        response = client.delete('/api/login')
        
        assert response.status_code == 405, \
            f"DELETE deve ser bloqueado (405), mas retornou {response.status_code}"
    
    def test_login_participante_patch_bloqueado(self, client):
        """PATCH deve ser bloqueado no login"""
        response = client.patch('/api/login', json={
            'email': 'joao@example.com',
            'senha': 'senha123'
        })
        
        assert response.status_code == 405, \
            f"PATCH deve ser bloqueado (405), mas retornou {response.status_code}"


class TestCadastroParticipanteHTTPMethods:
    """Testes para validar métodos HTTP no endpoint de cadastro de participante"""
    
    def test_cadastro_post_permitido(self, client):
        """POST deve ser aceito no cadastro"""
        response = client.post('/api/resgatar-ingresso', json={
            'nome': 'Maria Santos',
            'email': 'maria@example.com',
            'cpf': '98765432109',
            'telefone': '11987654321',
            'senha': 'senha123'
        })
        
        # Deve retornar 201 (criado) ou 400 (validação)
        # Não deve retornar 405 (método não permitido)
        assert response.status_code in [201, 400], \
            f"POST deve ser aceito, mas retornou {response.status_code}"
    
    def test_cadastro_get_bloqueado(self, client):
        """GET deve ser BLOQUEADO no cadastro (dados sensíveis)"""
        # Tentar GET com dados na URL (MUITO INSEGURO!)
        response = client.get(
            '/api/resgatar-ingresso?nome=Maria&email=maria@example.com'
            '&cpf=98765432109&telefone=11987654321&senha=senha123'
        )
        
        # Deve retornar 405 Method Not Allowed
        assert response.status_code == 405, \
            f"GET deve ser bloqueado (405), mas retornou {response.status_code}"
    
    def test_cadastro_put_bloqueado(self, client):
        """PUT deve ser bloqueado no cadastro"""
        response = client.put('/api/resgatar-ingresso', json={
            'nome': 'Maria Santos',
            'email': 'maria@example.com',
            'cpf': '98765432109',
            'telefone': '11987654321',
            'senha': 'senha123'
        })
        
        assert response.status_code == 405, \
            f"PUT deve ser bloqueado (405), mas retornou {response.status_code}"
    
    def test_cadastro_delete_bloqueado(self, client):
        """DELETE deve ser bloqueado no cadastro"""
        response = client.delete('/api/resgatar-ingresso')
        
        assert response.status_code == 405, \
            f"DELETE deve ser bloqueado (405), mas retornou {response.status_code}"


class TestUserLoginHTTPMethods:
    """Testes para validar métodos HTTP no endpoint de login de usuário admin"""
    
    def test_user_login_post_permitido(self, client, user_teste):
        """POST deve ser aceito no login de usuário"""
        response = client.post('/api/user/login', json={
            'username': 'admin_test',
            'password': 'senha123'
        })
        
        # Deve retornar 200 (sucesso) ou 401 (credenciais inválidas)
        assert response.status_code in [200, 401], \
            f"POST deve ser aceito, mas retornou {response.status_code}"
    
    def test_user_login_get_bloqueado(self, client):
        """GET deve ser BLOQUEADO no login de usuário"""
        response = client.get('/api/user/login?username=admin&password=senha123')
        
        assert response.status_code == 405, \
            f"GET deve ser bloqueado (405), mas retornou {response.status_code}"
    
    def test_user_login_outros_metodos_bloqueados(self, client):
        """Outros métodos HTTP devem ser bloqueados"""
        metodos = [
            ('PUT', client.put),
            ('DELETE', client.delete),
            ('PATCH', client.patch)
        ]
        
        for nome_metodo, metodo_func in metodos:
            response = metodo_func('/api/user/login', json={
                'username': 'admin',
                'password': 'senha123'
            })
            
            assert response.status_code == 405, \
                f"{nome_metodo} deve ser bloqueado (405), mas retornou {response.status_code}"


class TestUserRegisterHTTPMethods:
    """Testes para validar métodos HTTP no endpoint de registro de usuário admin"""
    
    def test_user_register_post_permitido(self, client):
        """POST deve ser aceito no registro"""
        response = client.post('/api/user/register', json={
            'username': 'novo_admin',
            'email': 'novo@example.com',
            'password': 'senha123'
        })
        
        # Deve retornar 201 (criado) ou 400/409 (validação/duplicado)
        assert response.status_code in [201, 400, 409], \
            f"POST deve ser aceito, mas retornou {response.status_code}"
    
    def test_user_register_get_bloqueado(self, client):
        """GET deve ser BLOQUEADO no registro"""
        response = client.get(
            '/api/user/register?username=novo&email=novo@example.com&password=senha123'
        )
        
        assert response.status_code == 405, \
            f"GET deve ser bloqueado (405), mas retornou {response.status_code}"
    
    def test_user_register_outros_metodos_bloqueados(self, client):
        """Outros métodos devem ser bloqueados"""
        for metodo in [client.put, client.delete, client.patch]:
            response = metodo('/api/user/register', json={
                'username': 'novo',
                'email': 'novo@example.com',
                'password': 'senha123'
            })
            
            assert response.status_code == 405, \
                f"Método deve ser bloqueado (405), mas retornou {response.status_code}"


class TestSecurityImplications:
    """Testes de implicações de segurança dos métodos HTTP"""
    
    def test_senha_nao_aparece_em_url_logs(self, client):
        """
        Verificar que GET é bloqueado para evitar senhas em logs
        
        Security Risk:
        - GET requests são logados em:
          - Logs do servidor web (nginx, apache)
          - Logs do proxy reverso
          - Histórico do navegador
          - Cache do navegador
          - Analytics e monitoramento
        
        - Senhas em URLs podem ser:
          - Armazenadas em plain text nos logs
          - Compartilhadas acidentalmente (copiar/colar URL)
          - Expostas em screenshots
          - Vazadas em referer headers
        """
        # Tentar enviar senha via GET
        response = client.get('/api/login?email=teste@example.com&senha=SuperSecret123!')
        
        # Deve ser bloqueado
        assert response.status_code == 405, \
            "Senhas NUNCA devem ser aceitas via GET (risco de logs)"
        
        # Mesmo para cadastro
        response = client.get('/api/resgatar-ingresso?senha=SuperSecret123!')
        assert response.status_code == 405, \
            "Cadastro via GET exporia senhas em logs"
    
    def test_cpf_nao_aparece_em_url(self, client):
        """
        Verificar que CPF não é enviado via GET (LGPD compliance)
        
        LGPD/GDPR Risk:
        - CPF é dado pessoal sensível
        - URLs com CPF podem ser logadas em múltiplos pontos
        - Viola princípios de minimização de dados
        """
        response = client.get('/api/resgatar-ingresso?cpf=12345678901')
        
        assert response.status_code == 405, \
            "CPF NUNCA deve ser aceito via GET (compliance LGPD)"
    
    def test_post_com_https_recomendado(self, client):
        """
        Documentar que POST deve ser usado com HTTPS em produção
        
        Security Note:
        Este teste documenta a necessidade de HTTPS.
        POST protege contra logs de URL, mas ainda precisa HTTPS para:
        - Criptografia em trânsito
        - Proteção contra man-in-the-middle
        - Integridade dos dados
        """
        # Este é um teste de documentação
        # Em produção, app.config['SESSION_COOKIE_SECURE'] = True
        # e app.config['SESSION_COOKIE_HTTPONLY'] = True devem estar ativos
        
        response = client.post('/api/login', json={
            'email': 'teste@example.com',
            'senha': 'senha123'
        })
        
        # POST é aceito (200 ou 401), mas HTTPS é necessário em produção
        assert response.status_code in [200, 401, 400], \
            "POST aceito, mas lembre-se: HTTPS obrigatório em produção!"


class TestHTTPMethodsAllowHeader:
    """Testes para verificar header Allow em respostas 405"""
    
    def test_login_allow_header(self, client):
        """Resposta 405 deve incluir header Allow informando métodos aceitos"""
        response = client.get('/api/login')
        
        assert response.status_code == 405
        
        # Flask inclui automaticamente o header Allow
        # Verificar se existe (opcional, Flask faz isso por padrão)
        if 'Allow' in response.headers:
            assert 'POST' in response.headers['Allow'], \
                "Header Allow deve listar POST como método permitido"
            assert 'GET' not in response.headers['Allow'], \
                "Header Allow NÃO deve listar GET"


def test_summary_endpoints_post_only():
    """
    Resumo: Endpoints que DEVEM aceitar apenas POST
    
    ✓ /api/login - Login de participante
    ✓ /api/resgatar-ingresso - Cadastro de participante
    ✓ /api/user/login - Login de usuário admin
    ✓ /api/user/register - Registro de usuário admin
    ✓ /api/logout - Logout de participante
    ✓ /api/user/logout - Logout de admin
    ✓ /api/user/login/mfa - Verificação MFA
    
    Motivos:
    1. Senhas NUNCA devem aparecer em URLs
    2. CPFs e dados pessoais não devem ser logados em URLs
    3. Compliance com LGPD/GDPR
    4. Prevenção de vazamento em logs, cache, histórico
    5. Proteção contra shoulder surfing (senhas visíveis na URL)
    """
    # Este é um teste de documentação
    assert True, "Documentação de endpoints POST-only"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
