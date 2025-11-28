"""
Testes de Segurança - Identificadores Públicos

Valida que IDs internos não são expostos em URLs, responses ou logs.

Para executar:
    pytest tests/test_security_public_ids.py -v
"""

import pytest
import json
from src.main import app
from src.models.db import db
from src.models.participante import Participante


@pytest.fixture
def client():
    """Fixture para criar cliente de teste"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client


@pytest.fixture
def participante_teste(client):
    """Fixture que cria um participante de teste"""
    with app.app_context():
        participante = Participante(
            nome='João Silva',
            email='joao@test.com',
            cpf='12345678901',
            telefone='11987654321',
            senha='senha123'
        )
        db.session.add(participante)
        db.session.commit()
        
        # Retornar dados (incluindo ID interno para testes)
        return {
            'id': participante.id,
            'numero_ingresso': participante.numero_ingresso,
            'nome': participante.nome,
            'email': participante.email
        }


class TestPublicIdentifiers:
    """Testes para garantir uso de identificadores públicos"""
    
    def test_endpoint_usa_numero_ingresso_nao_id(self, client, participante_teste):
        """Teste: Endpoint aceita numero_ingresso, não ID numérico"""
        numero_ingresso = participante_teste['numero_ingresso']
        
        # Endpoint com numero_ingresso deve funcionar
        response = client.get(f'/api/participante/{numero_ingresso}')
        assert response.status_code == 200
        
        data = response.json
        assert data['numeroIngresso'] == numero_ingresso
    
    def test_endpoint_com_id_nao_funciona(self, client, participante_teste):
        """Teste: Endpoint com ID numérico não deve funcionar"""
        participante_id = participante_teste['id']
        
        # Tentar acessar com ID numérico
        response = client.get(f'/api/participante/{participante_id}')
        
        # Deve retornar 404 (não encontrado) ou 400 (formato inválido)
        assert response.status_code in [404, 400]
    
    def test_numero_ingresso_formato_correto(self, client, participante_teste):
        """Teste: numero_ingresso tem formato esperado (EVTXXXXXXXX)"""
        numero_ingresso = participante_teste['numero_ingresso']
        
        # Verificar formato
        assert numero_ingresso.startswith('EVT')
        assert len(numero_ingresso) >= 10  # EVT + 8 caracteres
        assert numero_ingresso.isupper()
        assert numero_ingresso.replace('EVT', '').isalnum()


class TestNoInternalIdExposure:
    """Testes para garantir que ID interno nunca é exposto"""
    
    def test_response_nao_contem_id_interno(self, client, participante_teste):
        """Teste: Response JSON não contém ID interno"""
        numero_ingresso = participante_teste['numero_ingresso']
        
        response = client.get(f'/api/participante/{numero_ingresso}')
        assert response.status_code == 200
        
        data = response.json
        
        # Verificar que ID não está no response
        assert 'id' not in data
        assert '_internal_id' not in data
        
        # Verificar que numero_ingresso está presente
        assert 'numeroIngresso' in data
    
    def test_criar_participante_nao_retorna_id(self, client):
        """Teste: Criar participante não retorna ID interno"""
        response = client.post('/api/resgatar-ingresso', json={
            'nome': 'Maria Santos',
            'email': 'maria@test.com',
            'cpf': '98765432100',
            'telefone': '11912345678',
            'senha': 'senha456'
        })
        
        assert response.status_code == 201
        data = response.json
        
        # ID não deve estar no response
        assert 'id' not in data
        assert '_internal_id' not in data
        
        # numero_ingresso deve estar presente
        assert 'numeroIngresso' in data
        assert data['numeroIngresso'].startswith('EVT')
    
    def test_listar_participantes_nao_retorna_ids(self, client, participante_teste):
        """Teste: Listagem não retorna IDs internos"""
        response = client.get('/api/participantes')
        assert response.status_code == 200
        
        participantes = response.json
        assert len(participantes) > 0
        
        for participante in participantes:
            # ID interno não deve estar presente
            assert 'id' not in participante
            assert '_internal_id' not in participante
            
            # numero_ingresso deve estar presente
            assert 'numeroIngresso' in participante
    
    def test_login_nao_retorna_id(self, client, participante_teste):
        """Teste: Login não retorna ID interno"""
        response = client.post('/api/login', json={
            'email': participante_teste['email'],
            'senha': 'senha123'
        })
        
        assert response.status_code == 200
        data = response.json
        
        # ID não deve estar no response
        assert 'id' not in data
        assert '_internal_id' not in data
        
        # numero_ingresso deve estar presente
        assert 'numeroIngresso' in data


class TestToDict:
    """Testes para os métodos to_dict() e to_dict_safe()"""
    
    def test_to_dict_padrao_nao_inclui_id(self, client):
        """Teste: to_dict() padrão não inclui ID interno"""
        with app.app_context():
            participante = Participante(
                nome='Teste Usuario',
                email='teste@test.com',
                cpf='11122233344',
                telefone='11999999999',
                senha='senha789'
            )
            db.session.add(participante)
            db.session.commit()
            
            # to_dict padrão
            data = participante.to_dict()
            
            assert 'id' not in data
            assert '_internal_id' not in data
            assert 'numeroIngresso' in data
    
    def test_to_dict_com_flag_admin_inclui_id(self, client):
        """Teste: to_dict(include_internal_id=True) inclui ID para admin"""
        with app.app_context():
            participante = Participante(
                nome='Admin Test',
                email='admin@test.com',
                cpf='55566677788',
                telefone='11888888888',
                senha='admin123'
            )
            db.session.add(participante)
            db.session.commit()
            
            # to_dict com flag admin
            data = participante.to_dict(include_internal_id=True)
            
            assert '_internal_id' in data
            assert data['_internal_id'] == participante.id
            assert 'numeroIngresso' in data
    
    def test_to_dict_safe_mascara_dados(self, client):
        """Teste: to_dict_safe() mascara dados sensíveis"""
        with app.app_context():
            participante = Participante(
                nome='Safe Test',
                email='safe@test.com',
                cpf='99988877766',
                telefone='11777777777',
                senha='safe123'
            )
            db.session.add(participante)
            db.session.commit()
            
            # to_dict_safe
            data = participante.to_dict_safe()
            
            # Verificar mascaramento
            assert 'id' not in data
            assert '_internal_id' not in data
            assert '***' in data['email']  # Email mascarado
            assert '***' in data['cpf']    # CPF mascarado
            assert 'numeroIngresso' in data


class TestInputValidation:
    """Testes de validação de entrada"""
    
    def test_numero_ingresso_invalido_retorna_erro(self, client):
        """Teste: numero_ingresso inválido retorna erro apropriado"""
        # Muito curto
        response = client.get('/api/participante/AB')
        assert response.status_code == 400
        
        # Vazio
        response = client.get('/api/participante/')
        assert response.status_code in [404, 405]  # Not Found ou Method Not Allowed
    
    def test_numero_ingresso_nao_existente_retorna_404(self, client):
        """Teste: numero_ingresso que não existe retorna 404"""
        response = client.get('/api/participante/EVTINVALID999')
        assert response.status_code == 404
        
        data = response.json
        assert 'error' in data
    
    def test_numero_ingresso_case_insensitive(self, client, participante_teste):
        """Teste: numero_ingresso aceita lowercase (normalizado para uppercase)"""
        numero_ingresso = participante_teste['numero_ingresso']
        
        # Teste com lowercase
        response = client.get(f'/api/participante/{numero_ingresso.lower()}')
        assert response.status_code == 200
        
        data = response.json
        # Response deve ter uppercase
        assert data['numeroIngresso'] == numero_ingresso.upper()


class TestSecurityVulnerabilities:
    """Testes de vulnerabilidades de segurança"""
    
    def test_enumeracao_impossivel_com_numero_ingresso(self, client, participante_teste):
        """Teste: Enumeração de participantes é impossível"""
        # Com IDs sequenciais, atacante poderia fazer:
        # /api/participante/1, /api/participante/2, etc.
        
        # Com numero_ingresso, tentativas aleatórias falham
        tentativas = ['EVT12345678', 'EVT99999999', 'EVTAAAAAAAA', 'EVTZZZZZZZ']
        
        for tentativa in tentativas:
            if tentativa != participante_teste['numero_ingresso']:
                response = client.get(f'/api/participante/{tentativa}')
                assert response.status_code == 404
    
    def test_injecao_sql_protegida(self, client):
        """Teste: Proteção contra SQL injection"""
        # Tentativas de SQL injection no numero_ingresso
        payloads = [
            "EVT' OR '1'='1",
            "EVT'; DROP TABLE participante;--",
            "EVT' UNION SELECT * FROM participante--"
        ]
        
        for payload in payloads:
            response = client.get(f'/api/participante/{payload}')
            # Deve retornar 404 (não encontrado) sem causar erro de SQL
            assert response.status_code in [404, 400]
    
    def test_xss_protegido_em_numero_ingresso(self, client):
        """Teste: Proteção contra XSS no numero_ingresso"""
        # Tentativa de XSS
        payload = "EVT<script>alert('XSS')</script>"
        
        response = client.get(f'/api/participante/{payload}')
        
        # Deve retornar 404 sem executar script
        assert response.status_code in [404, 400]
        
        # Response não deve conter script não escapado
        if response.data:
            assert b'<script>' not in response.data


class TestUniqueIdentifiers:
    """Testes de unicidade dos identificadores"""
    
    def test_numero_ingresso_unico(self, client):
        """Teste: Cada participante tem numero_ingresso único"""
        with app.app_context():
            # Criar múltiplos participantes
            participantes = []
            for i in range(5):
                p = Participante(
                    nome=f'Teste {i}',
                    email=f'teste{i}@test.com',
                    cpf=f'{i:011d}',
                    telefone=f'119{i:08d}',
                    senha=f'senha{i}'
                )
                db.session.add(p)
                participantes.append(p)
            
            db.session.commit()
            
            # Verificar que todos têm numero_ingresso diferente
            numeros = [p.numero_ingresso for p in participantes]
            assert len(numeros) == len(set(numeros))  # Todos únicos
    
    def test_numero_ingresso_nao_muda_apos_criacao(self, client):
        """Teste: numero_ingresso não muda após criação"""
        with app.app_context():
            participante = Participante(
                nome='Teste Imutavel',
                email='imutavel@test.com',
                cpf='12312312312',
                telefone='11912312312',
                senha='senha'
            )
            db.session.add(participante)
            db.session.commit()
            
            numero_original = participante.numero_ingresso
            
            # Atualizar outros campos
            participante.nome = 'Nome Atualizado'
            db.session.commit()
            
            # numero_ingresso não deve mudar
            assert participante.numero_ingresso == numero_original


class TestRepr:
    """Testes de representação do objeto"""
    
    def test_repr_nao_expoe_id(self, client):
        """Teste: __repr__ não expõe ID interno"""
        with app.app_context():
            participante = Participante(
                nome='Repr Test',
                email='repr@test.com',
                cpf='44455566677',
                telefone='11666666666',
                senha='repr123'
            )
            db.session.add(participante)
            db.session.commit()
            
            repr_str = repr(participante)
            
            # Não deve conter ID numérico
            assert str(participante.id) not in repr_str
            
            # Deve conter numero_ingresso
            assert participante.numero_ingresso in repr_str
            assert 'EVT' in repr_str


# Script para executar testes
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
