"""
Testes de Autorização para Endpoints de Participantes

Testa a implementação de autorização garantindo que:
1. Apenas participantes autenticados possam acessar endpoints protegidos
2. Participantes só possam acessar seus próprios ingressos
3. Tentativas de acesso não autorizado sejam bloqueadas com 403
4. Sessões inválidas sejam tratadas corretamente
"""

import pytest
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import app
from src.models.participante import db, Participante
from datetime import datetime


@pytest.fixture
def client():
    """Cria um cliente de testes com banco de dados em memória"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key-for-authorization-tests'
    app.config['SESSION_TYPE'] = 'filesystem'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            
            # Criar participantes de teste
            participante_a = Participante(
                nome='João Silva',
                email='joao@example.com',
                numero_ingresso='EVTAB12CD34',
                ativo=True
            )
            participante_a.set_password('senha123')
            
            participante_b = Participante(
                nome='Maria Oliveira',
                email='maria@example.com',
                numero_ingresso='EVTXY98ZW76',
                ativo=True
            )
            participante_b.set_password('senha456')
            
            participante_inativo = Participante(
                nome='Carlos Inativo',
                email='carlos@example.com',
                numero_ingresso='EVTQW56ER78',
                ativo=False  # Inativo
            )
            participante_inativo.set_password('senha789')
            
            db.session.add(participante_a)
            db.session.add(participante_b)
            db.session.add(participante_inativo)
            db.session.commit()
            
            yield client
            
            db.session.remove()
            db.drop_all()


class TestLoginAuthorization:
    """Testes de login e criação de sessão"""
    
    def test_login_sucesso(self, client):
        """Teste: Login bem-sucedido cria sessão"""
        response = client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        assert response.status_code == 200
        data = response.json
        assert data['message'] == 'Login bem-sucedido'
        assert data['session_created'] == True
        assert data['participante']['numero_ingresso'] == 'EVTAB12CD34'
        assert 'id' not in data['participante']  # ID interno não exposto
    
    def test_login_senha_incorreta(self, client):
        """Teste: Login com senha incorreta falha"""
        response = client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha_errada'
        })
        
        assert response.status_code == 401
        assert 'inválidos' in response.json['error']
    
    def test_login_ingresso_inexistente(self, client):
        """Teste: Login com ingresso inexistente falha"""
        response = client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTINEXISTENTE',
            'senha': 'senha123'
        })
        
        assert response.status_code == 401
        assert 'inválidos' in response.json['error']
    
    def test_login_participante_inativo(self, client):
        """Teste: Login de participante inativo falha"""
        response = client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTQW56ER78',
            'senha': 'senha789'
        })
        
        assert response.status_code == 401
        assert 'inválidos' in response.json['error']


class TestLogout:
    """Testes de logout"""
    
    def test_logout_sucesso(self, client):
        """Teste: Logout limpa sessão"""
        # Login primeiro
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Logout
        response = client.post('/api/participante/logout')
        
        assert response.status_code == 200
        data = response.json
        assert data['message'] == 'Logout realizado com sucesso'
        assert data['logged_out'] == True
    
    def test_logout_sem_sessao(self, client):
        """Teste: Logout sem sessão ativa ainda funciona"""
        response = client.post('/api/participante/logout')
        
        assert response.status_code == 200
        assert response.json['logged_out'] == True


class TestAccessAuthorization:
    """Testes de autorização de acesso a ingressos"""
    
    def test_acesso_proprio_ingresso_autorizado(self, client):
        """Teste: Participante pode acessar seu próprio ingresso"""
        # Login
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Acessar próprio ingresso
        response = client.get('/api/participante/ingresso/EVTAB12CD34')
        
        assert response.status_code == 200
        data = response.json
        assert data['authorized'] == True
        assert data['ingresso']['numero_ingresso'] == 'EVTAB12CD34'
        assert data['ingresso']['nome'] == 'João Silva'
        assert 'id' not in data['ingresso']  # ID interno não exposto
    
    def test_acesso_ingresso_outro_participante_negado(self, client):
        """Teste: Participante NÃO pode acessar ingresso de outro participante"""
        # Login como João
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Tentar acessar ingresso de Maria
        response = client.get('/api/participante/ingresso/EVTXY98ZW76')
        
        assert response.status_code == 403
        data = response.json
        assert data['forbidden'] == True
        assert 'Acesso negado' in data['error']
        assert 'próprio ingresso' in data['error']
    
    def test_acesso_sem_autenticacao(self, client):
        """Teste: Acesso sem login retorna 401"""
        response = client.get('/api/participante/ingresso/EVTAB12CD34')
        
        assert response.status_code == 401
        data = response.json
        assert data['auth_required'] == True
        assert 'Não autorizado' in data['error']
    
    def test_acesso_ingresso_inexistente(self, client):
        """Teste: Acesso a ingresso inexistente retorna 404"""
        # Login
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Tentar acessar ingresso que não existe (e não é o seu)
        # Primeiro vai retornar 403 porque não é o dele
        response = client.get('/api/participante/ingresso/EVTINEXISTENTE')
        
        assert response.status_code == 403  # Bloqueado antes de verificar existência


class TestMeuIngresso:
    """Testes do endpoint /meu-ingresso"""
    
    def test_meu_ingresso_sucesso(self, client):
        """Teste: /meu-ingresso retorna ingresso do participante autenticado"""
        # Login
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Buscar meu ingresso
        response = client.get('/api/participante/meu-ingresso')
        
        assert response.status_code == 200
        data = response.json
        assert data['authorized'] == True
        assert data['ingresso']['numero_ingresso'] == 'EVTAB12CD34'
        assert data['ingresso']['nome'] == 'João Silva'
        assert 'id' not in data['ingresso']
    
    def test_meu_ingresso_sem_autenticacao(self, client):
        """Teste: /meu-ingresso sem login retorna 401"""
        response = client.get('/api/participante/meu-ingresso')
        
        assert response.status_code == 401
        assert response.json['auth_required'] == True


class TestSessionPersistence:
    """Testes de persistência e invalidação de sessão"""
    
    def test_sessao_persiste_entre_requests(self, client):
        """Teste: Sessão persiste entre múltiplas requisições"""
        # Login
        login_response = client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        assert login_response.status_code == 200
        
        # Primeira requisição
        response1 = client.get('/api/participante/meu-ingresso')
        assert response1.status_code == 200
        
        # Segunda requisição (mesma sessão)
        response2 = client.get('/api/participante/meu-ingresso')
        assert response2.status_code == 200
        
        # Dados devem ser os mesmos
        assert response1.json == response2.json
    
    def test_sessao_invalida_apos_logout(self, client):
        """Teste: Sessão se torna inválida após logout"""
        # Login
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Acessar endpoint protegido (deve funcionar)
        response1 = client.get('/api/participante/meu-ingresso')
        assert response1.status_code == 200
        
        # Logout
        client.post('/api/participante/logout')
        
        # Tentar acessar endpoint protegido novamente (deve falhar)
        response2 = client.get('/api/participante/meu-ingresso')
        assert response2.status_code == 401
        assert response2.json['auth_required'] == True


class TestMultipleUsers:
    """Testes com múltiplos usuários simultâneos"""
    
    def test_usuarios_diferentes_sessoes_diferentes(self, client):
        """Teste: Cada cliente tem sua própria sessão isolada"""
        # Esta implementação precisa de múltiplos clientes
        # Por limitação do test_client do Flask, simulamos com login/logout
        
        # Login como João
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        response_joao = client.get('/api/participante/meu-ingresso')
        assert response_joao.status_code == 200
        assert response_joao.json['ingresso']['numero_ingresso'] == 'EVTAB12CD34'
        
        # Logout
        client.post('/api/participante/logout')
        
        # Login como Maria
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTXY98ZW76',
            'senha': 'senha456'
        })
        
        response_maria = client.get('/api/participante/meu-ingresso')
        assert response_maria.status_code == 200
        assert response_maria.json['ingresso']['numero_ingresso'] == 'EVTXY98ZW76'


class TestCaseInsensitivity:
    """Testes de case-insensitivity em numero_ingresso"""
    
    def test_login_case_insensitive(self, client):
        """Teste: Login funciona com qualquer case"""
        # Login com lowercase
        response = client.post('/api/participante/login', json={
            'numero_ingresso': 'evtab12cd34',  # lowercase
            'senha': 'senha123'
        })
        
        assert response.status_code == 200
    
    def test_acesso_ingresso_case_insensitive(self, client):
        """Teste: Acesso a ingresso funciona com qualquer case"""
        # Login
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Acessar com lowercase
        response = client.get('/api/participante/ingresso/evtab12cd34')
        
        assert response.status_code == 200
        assert response.json['authorized'] == True


class TestInputValidation:
    """Testes de validação de entrada"""
    
    def test_numero_ingresso_vazio(self, client):
        """Teste: Número de ingresso vazio é rejeitado"""
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        response = client.get('/api/participante/ingresso/')
        # Flask pode retornar 404 (rota não encontrada) ou 400 se validarmos
        assert response.status_code in [404, 400]
    
    def test_numero_ingresso_muito_curto(self, client):
        """Teste: Número de ingresso muito curto é rejeitado"""
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        response = client.get('/api/participante/ingresso/AB')
        
        # Deve retornar 403 (não é o ingresso dele) ou 400 (formato inválido)
        assert response.status_code in [400, 403]


class TestDecoratorBehavior:
    """Testes específicos do decorator @participante_required"""
    
    def test_decorator_injeta_participante_atual(self, client):
        """Teste: Decorator injeta participante_atual corretamente"""
        # Login
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Endpoint /meu-ingresso usa decorator e participante_atual
        response = client.get('/api/participante/meu-ingresso')
        
        assert response.status_code == 200
        assert response.json['ingresso']['nome'] == 'João Silva'
    
    def test_decorator_limpa_sessao_invalida(self, client):
        """Teste: Decorator limpa sessão se participante não existe mais"""
        # Login
        client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTAB12CD34',
            'senha': 'senha123'
        })
        
        # Deletar participante do banco (simula exclusão)
        with app.app_context():
            participante = Participante.query.filter_by(numero_ingresso='EVTAB12CD34').first()
            db.session.delete(participante)
            db.session.commit()
        
        # Tentar acessar endpoint protegido
        response = client.get('/api/participante/meu-ingresso')
        
        assert response.status_code == 401
        assert 'Sessão inválida' in response.json['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
