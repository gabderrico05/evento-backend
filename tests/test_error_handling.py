"""
Testes de Tratamento de Exceções

Valida que:
1. Erros de banco de dados retornam apenas mensagens genéricas
2. Exceções não capturadas retornam mensagens genéricas
3. Stack traces NUNCA são expostos ao frontend
4. Logs completos são registrados no servidor
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch
import logging

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import app
from src.models.participante import db, Participante
from sqlalchemy.exc import SQLAlchemyError, OperationalError


@pytest.fixture
def client():
    """Cria um cliente de testes com banco em memória"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


class TestDatabaseErrorHandling:
    """Testes de tratamento de erros de banco de dados"""
    
    def test_database_error_returns_generic_message(self, client, mocker):
        """Teste: Erro de banco retorna mensagem genérica, não detalhes"""
        # Simular erro de banco de dados
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = OperationalError(
            "could not connect to server", None, None
        )
        
        response = client.get('/api/participantes')
        
        assert response.status_code == 500
        data = response.json
        assert data['error'] == 'Erro interno do servidor'
        assert data['internal_error'] == True
        
        # Garantir que detalhes do erro NÃO são expostos
        assert 'could not connect' not in data['error']
        assert 'OperationalError' not in str(data)
        assert 'server' not in data['error']
    
    def test_database_error_logs_full_details(self, client, mocker, caplog):
        """Teste: Erro de banco é logado com detalhes completos"""
        caplog.set_level(logging.ERROR)
        
        # Simular erro de banco
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = SQLAlchemyError(
            "Connection timeout"
        )
        
        response = client.get('/api/participantes')
        
        # Verificar que foi logado
        assert 'ERROR' in caplog.text
        # Stack trace deve estar no log
        assert 'Stack trace' in caplog.text or 'Traceback' in caplog.text
    
    def test_database_error_triggers_rollback(self, client, mocker):
        """Teste: Erro de banco dispara rollback de transação"""
        mock_rollback = mocker.patch('src.models.participante.db.session.rollback')
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = SQLAlchemyError("Error")
        
        response = client.get('/api/participantes')
        
        # Verificar que rollback foi chamado
        mock_rollback.assert_called_once()
        assert response.status_code == 500


class TestGenericErrorHandling:
    """Testes de tratamento de exceções genéricas"""
    
    def test_generic_exception_returns_generic_message(self, client, mocker):
        """Teste: Exceção genérica retorna mensagem segura"""
        # Simular exceção qualquer
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = Exception(
            "Some internal error with sensitive data: password=123456"
        )
        
        response = client.get('/api/participantes')
        
        assert response.status_code == 500
        data = response.json
        assert data['error'] == 'Erro interno do servidor'
        assert data['internal_error'] == True
        
        # Garantir que dados sensíveis NÃO são expostos
        assert 'password' not in str(data)
        assert '123456' not in str(data)
        assert 'sensitive data' not in data['error']
    
    def test_generic_exception_logs_full_stack_trace(self, client, mocker, caplog):
        """Teste: Exceção genérica loga stack trace completo"""
        caplog.set_level(logging.ERROR)
        
        # Simular exceção
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = RuntimeError(
            "Unexpected error"
        )
        
        response = client.get('/api/participantes')
        
        # Verificar que foi logado com detalhes
        assert 'ERROR' in caplog.text
        assert 'Unexpected error' in caplog.text


class TestHTTPErrorHandling:
    """Testes de tratamento de erros HTTP comuns"""
    
    def test_404_not_found(self, client):
        """Teste: Rota inexistente retorna 404"""
        response = client.get('/api/rota-inexistente')
        
        assert response.status_code == 404
        data = response.json
        assert 'não encontrado' in data['error'].lower()
        assert data.get('not_found') == True
    
    def test_405_method_not_allowed(self, client):
        """Teste: Método HTTP inválido retorna 405"""
        # Tentar DELETE em rota que só aceita GET
        response = client.delete('/api/participantes')
        
        assert response.status_code == 405
        data = response.json
        assert 'não permitido' in data['error'].lower()
        assert data.get('method_not_allowed') == True


class TestEndpointErrorPropagation:
    """Testes de propagação de erros dos endpoints"""
    
    def test_login_error_propagation(self, client, mocker):
        """Teste: Erro no login propaga para handler global"""
        # Simular erro no endpoint de login
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.first.side_effect = Exception("DB error")
        
        response = client.post('/api/participante/login', json={
            'numero_ingresso': 'EVTTEST123',
            'senha': 'senha123'
        })
        
        assert response.status_code == 500
        data = response.json
        assert data['error'] == 'Erro interno do servidor'
        assert 'DB error' not in data['error']
    
    def test_resgate_error_propagation(self, client, mocker):
        """Teste: Erro no resgate propaga para handler global"""
        # Simular erro ao salvar no banco
        mock_commit = mocker.patch('src.models.participante.db.session.commit')
        mock_commit.side_effect = SQLAlchemyError("Constraint violation")
        
        response = client.post('/api/resgatar', json={
            'nome': 'Test',
            'email': 'test@example.com'
        })
        
        assert response.status_code == 500
        data = response.json
        assert data['error'] == 'Erro interno do servidor'
        assert 'Constraint' not in data['error']


class TestLoggingBehavior:
    """Testes de comportamento de logging"""
    
    def test_error_includes_exc_info(self, client, mocker, caplog):
        """Teste: Logs incluem exc_info=True para stack trace"""
        caplog.set_level(logging.ERROR)
        
        # Simular erro
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = ValueError("Test error")
        
        response = client.get('/api/participantes')
        
        # Verificar que stack trace está presente
        log_text = caplog.text
        assert 'ERROR' in log_text
        # Deve conter informações de traceback
        assert ('Traceback' in log_text or 'Stack trace' in log_text)
    
    def test_different_error_types_logged_separately(self, client, mocker, caplog):
        """Teste: Diferentes tipos de erro são logados distintamente"""
        caplog.set_level(logging.ERROR)
        
        # Erro de banco
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = SQLAlchemyError("DB error")
        
        response1 = client.get('/api/participantes')
        assert response1.status_code == 500
        
        # Verificar que tipo de erro está no log
        assert 'Database error' in caplog.text or 'DB error' in caplog.text


class TestSecurityAspects:
    """Testes de aspectos de segurança"""
    
    def test_no_stack_trace_in_response(self, client, mocker):
        """Teste: Stack trace NUNCA aparece na resposta"""
        # Simular erro complexo com stack trace profundo
        def raise_nested_error():
            def inner():
                def deeper():
                    raise Exception("Deep error with traceback")
                deeper()
            inner()
        
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = raise_nested_error
        
        response = client.get('/api/participantes')
        
        data = response.json
        response_str = str(data)
        
        # Garantir que nenhum elemento de stack trace aparece
        assert 'Traceback' not in response_str
        assert 'File "' not in response_str
        assert 'line ' not in response_str
        assert '.py"' not in response_str
    
    def test_no_sensitive_paths_in_response(self, client, mocker):
        """Teste: Caminhos de arquivos não são expostos"""
        # Simular erro que poderia conter paths
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = Exception(
            "/home/user/app/src/models/participante.py"
        )
        
        response = client.get('/api/participantes')
        
        data = response.json
        # Path não deve aparecer na resposta
        assert '/home/' not in str(data)
        assert '/src/' not in str(data)
        assert '.py' not in str(data)
    
    def test_no_config_details_in_response(self, client, mocker):
        """Teste: Detalhes de configuração não são expostos"""
        # Simular erro que poderia conter config
        mock_query = mocker.patch('src.models.participante.Participante.query')
        mock_query.filter_by.return_value.all.side_effect = Exception(
            "Database connection failed: postgresql://user:password@localhost:5432/db"
        )
        
        response = client.get('/api/participantes')
        
        data = response.json
        # Credenciais não devem aparecer
        assert 'password' not in str(data)
        assert 'postgresql://' not in str(data)
        assert ':5432' not in str(data)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
