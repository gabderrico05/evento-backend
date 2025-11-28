"""
Testes para o Sistema de Gerenciamento de Sessão

Para executar os testes:
    pytest tests/test_session_management.py -v

Certifique-se de instalar as dependências:
    pip install pytest pytest-flask
"""

import pytest
import time
from datetime import datetime, timedelta
from flask import session
from src.main import app
from src.models.db import db
from src.models.user import User


@pytest.fixture
def client():
    """Fixture para criar cliente de teste"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)
    app.config['SESSION_MAX_LIFETIME'] = timedelta(minutes=60)
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Criar usuário de teste
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
        yield client


@pytest.fixture
def authenticated_client(client):
    """Fixture para cliente autenticado"""
    # Fazer login
    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'password123'
    })
    
    assert response.status_code == 200
    data = response.json
    
    return {
        'client': client,
        'token': data['token'],
        'user': data['user']
    }


class TestSessionCreation:
    """Testes de criação de sessão"""
    
    def test_login_creates_session(self, client):
        """Teste: Login cria sessão com dados corretos"""
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = response.json
        
        # Verificar resposta
        assert 'token' in data
        assert 'user' in data
        assert 'session_info' in data
        assert data['session_info']['inactivity_timeout'] == 15
        assert data['session_info']['max_lifetime'] == 60
        
        # Verificar sessão
        with client.session_transaction() as sess:
            assert 'user_id' in sess
            assert 'username' in sess
            assert 'session_created_at' in sess
            assert 'last_activity' in sess
            assert sess['username'] == 'testuser'
    
    def test_login_invalid_credentials_no_session(self, client):
        """Teste: Login com credenciais inválidas não cria sessão"""
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
        
        # Verificar que não criou sessão
        with client.session_transaction() as sess:
            assert 'user_id' not in sess


class TestSessionStatus:
    """Testes de verificação de status da sessão"""
    
    def test_session_status_active(self, authenticated_client):
        """Teste: Verificar status de sessão ativa"""
        client = authenticated_client['client']
        
        response = client.get('/api/session/status')
        
        assert response.status_code == 200
        data = response.json
        
        assert data['active'] is True
        assert 'user_id' in data
        assert 'username' in data
        assert 'inactivity_remaining_seconds' in data
        assert 'lifetime_remaining_seconds' in data
        assert data['inactivity_remaining_seconds'] > 0
        assert data['lifetime_remaining_seconds'] > 0
    
    def test_session_status_inactive(self, client):
        """Teste: Verificar status sem sessão"""
        response = client.get('/api/session/status')
        
        assert response.status_code == 200
        data = response.json
        
        assert data['active'] is False
        assert data['message'] == 'Nenhuma sessão ativa'


class TestSessionRefresh:
    """Testes de renovação de sessão"""
    
    def test_refresh_session_updates_activity(self, authenticated_client):
        """Teste: Renovar sessão atualiza last_activity"""
        client = authenticated_client['client']
        token = authenticated_client['token']
        
        # Capturar last_activity inicial
        with client.session_transaction() as sess:
            initial_activity = sess['last_activity']
        
        # Aguardar um pouco
        time.sleep(2)
        
        # Renovar sessão
        response = client.post('/api/session/refresh', 
                              headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = response.json
        
        assert 'last_activity' in data
        assert data['message'] == 'Sessão renovada com sucesso'
        
        # Verificar que last_activity foi atualizada
        with client.session_transaction() as sess:
            assert sess['last_activity'] > initial_activity
    
    def test_refresh_without_token_fails(self, authenticated_client):
        """Teste: Renovar sem token falha"""
        client = authenticated_client['client']
        
        response = client.post('/api/session/refresh')
        
        assert response.status_code == 401


class TestSessionExpiry:
    """Testes de expiração de sessão"""
    
    def test_inactivity_expiry(self, authenticated_client):
        """Teste: Sessão expira por inatividade"""
        client = authenticated_client['client']
        token = authenticated_client['token']
        
        # Simular inatividade de 16 minutos
        with client.session_transaction() as sess:
            past_time = datetime.utcnow() - timedelta(minutes=16)
            sess['last_activity'] = past_time.isoformat()
        
        # Tentar acessar rota protegida
        response = client.get('/api/mfa/status',
                            headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 401
        data = response.json
        
        assert data['session_expired'] is True
        assert data['reason'] == 'inactivity'
        assert 'inatividade' in data['error'].lower()
    
    def test_max_lifetime_expiry(self, authenticated_client):
        """Teste: Sessão expira por tempo máximo"""
        client = authenticated_client['client']
        token = authenticated_client['token']
        
        # Simular sessão de 61 minutos
        with client.session_transaction() as sess:
            past_time = datetime.utcnow() - timedelta(minutes=61)
            sess['session_created_at'] = past_time.isoformat()
            # Atualizar atividade recente (não expirou por inatividade)
            sess['last_activity'] = datetime.utcnow().isoformat()
        
        # Tentar acessar rota protegida
        response = client.get('/api/mfa/status',
                            headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 401
        data = response.json
        
        assert data['session_expired'] is True
        assert data['reason'] == 'max_lifetime'
        assert 'máximo' in data['error'].lower()


class TestLogout:
    """Testes de logout"""
    
    def test_logout_clears_session(self, authenticated_client):
        """Teste: Logout limpa sessão"""
        client = authenticated_client['client']
        
        response = client.post('/api/logout')
        
        assert response.status_code == 200
        data = response.json
        
        assert data['logged_out'] is True
        assert 'desconectado' in data['message'].lower()
        
        # Verificar que sessão foi limpa
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'username' not in sess
    
    def test_logout_without_session(self, client):
        """Teste: Logout sem sessão ativa"""
        response = client.post('/api/logout')
        
        assert response.status_code == 200
        data = response.json
        
        assert data['logged_out'] is True


class TestProtectedRoutes:
    """Testes de rotas protegidas"""
    
    def test_protected_route_requires_session(self, client):
        """Teste: Rota protegida exige sessão válida"""
        # Criar token válido mas sem sessão
        from src.routes.user import generate_token
        
        with app.app_context():
            token = generate_token(user_id=1)
        
        response = client.get('/api/mfa/status',
                            headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 401
        data = response.json
        
        assert data['session_expired'] is True
    
    def test_protected_route_with_valid_session(self, authenticated_client):
        """Teste: Rota protegida aceita sessão válida"""
        client = authenticated_client['client']
        token = authenticated_client['token']
        
        response = client.get('/api/mfa/status',
                            headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200


class TestSessionSecurity:
    """Testes de segurança da sessão"""
    
    def test_token_user_mismatch_clears_session(self, authenticated_client):
        """Teste: Token com user_id diferente da sessão limpa sessão"""
        client = authenticated_client['client']
        
        # Criar token com user_id diferente
        from src.routes.user import generate_token
        
        with app.app_context():
            fake_token = generate_token(user_id=999)
        
        response = client.get('/api/mfa/status',
                            headers={'Authorization': f'Bearer {fake_token}'})
        
        assert response.status_code == 401
        
        # Verificar que sessão foi limpa
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
    
    def test_session_cookie_httponly(self, client):
        """Teste: Cookie de sessão tem flag HTTPOnly"""
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        
        # Verificar cookie
        cookies = response.headers.getlist('Set-Cookie')
        session_cookie = [c for c in cookies if 'evento_session' in c][0]
        
        assert 'HttpOnly' in session_cookie
    
    def test_session_cookie_samesite(self, client):
        """Teste: Cookie de sessão tem SameSite"""
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        
        cookies = response.headers.getlist('Set-Cookie')
        session_cookie = [c for c in cookies if 'evento_session' in c][0]
        
        assert 'SameSite' in session_cookie


class TestMFASession:
    """Testes de sessão com MFA"""
    
    def test_mfa_creates_temp_session(self, client):
        """Teste: Login com MFA cria sessão temporária"""
        # Criar usuário com MFA habilitado
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            user.is_sensitive_account = True
            user.generate_mfa_secret()
            user.enable_mfa()
            db.session.commit()
        
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = response.json
        
        assert data['requires_mfa'] is True
        assert 'temp_token' in data
        
        # Verificar sessão temporária
        with client.session_transaction() as sess:
            assert 'temp_user_id' in sess
            assert 'mfa_pending' in sess
            assert sess['mfa_pending'] is True


# Script para executar testes manualmente
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
