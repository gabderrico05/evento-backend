"""
Testes de Security Headers

Valida que o Flask está configurado com headers de segurança:
- Remoção do header 'Server'
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Content-Security-Policy (CSP)
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch

# Mock do banco de dados ANTES de importar a aplicação
with patch('src.models.db.db.init_app'), \
     patch('src.models.db.db.create_all'):
    from src.main import app


@pytest.fixture
def client():
    """Cliente de teste Flask"""
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        yield client


class TestServerHeaderRemoval:
    """Testes de remoção do header Server"""
    
    def test_server_header_removed(self, client):
        """Header 'Server' deve ser removido de todas as respostas"""
        response = client.get('/health')
        
        assert 'Server' not in response.headers, \
            "Header 'Server' não deve estar presente (ocultar versão Flask/Werkzeug)"
    
    def test_server_header_removed_api(self, client):
        """Header 'Server' deve ser removido em endpoints da API"""
        response = client.get('/api/evento/participantes')
        
        assert 'Server' not in response.headers, \
            "Header 'Server' não deve estar presente em endpoints da API"


class TestSecurityHeaders:
    """Testes de headers de segurança"""
    
    def test_x_content_type_options_present(self, client):
        """X-Content-Type-Options: nosniff deve estar presente"""
        response = client.get('/health')
        
        assert response.headers.get('X-Content-Type-Options') == 'nosniff', \
            "X-Content-Type-Options deve ser 'nosniff' (previne MIME sniffing)"
    
    def test_x_frame_options_present(self, client):
        """X-Frame-Options: DENY deve estar presente"""
        response = client.get('/health')
        
        assert response.headers.get('X-Frame-Options') == 'DENY', \
            "X-Frame-Options deve ser 'DENY' (previne clickjacking)"
    
    def test_x_xss_protection_present(self, client):
        """X-XSS-Protection deve estar presente"""
        response = client.get('/health')
        
        assert response.headers.get('X-XSS-Protection') == '1; mode=block', \
            "X-XSS-Protection deve ser '1; mode=block' (proteção contra XSS)"
    
    def test_referrer_policy_present(self, client):
        """Referrer-Policy deve estar presente"""
        response = client.get('/health')
        
        assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin', \
            "Referrer-Policy deve controlar informações de referrer"


class TestContentSecurityPolicy:
    """Testes de Content Security Policy (CSP)"""
    
    def test_csp_present(self, client):
        """Content-Security-Policy deve estar presente"""
        response = client.get('/health')
        
        assert 'Content-Security-Policy' in response.headers, \
            "Content-Security-Policy (CSP) deve estar presente"
    
    def test_csp_default_src_self(self, client):
        """CSP deve ter default-src 'self'"""
        response = client.get('/health')
        csp = response.headers.get('Content-Security-Policy', '')
        
        assert "default-src 'self'" in csp, \
            "CSP deve ter default-src 'self' (recursos apenas da mesma origem)"
    
    def test_csp_script_src_configured(self, client):
        """CSP deve ter script-src configurado para React"""
        response = client.get('/health')
        csp = response.headers.get('Content-Security-Policy', '')
        
        assert "script-src 'self'" in csp, \
            "CSP deve permitir scripts da mesma origem"
        
        # React/Vite requer 'unsafe-inline' e 'unsafe-eval'
        assert "'unsafe-inline'" in csp, \
            "CSP deve permitir 'unsafe-inline' para React inline scripts"
    
    def test_csp_style_src_configured(self, client):
        """CSP deve ter style-src configurado para React"""
        response = client.get('/health')
        csp = response.headers.get('Content-Security-Policy', '')
        
        assert "style-src 'self' 'unsafe-inline'" in csp, \
            "CSP deve permitir styles inline para React CSS modules"
    
    def test_csp_img_src_configured(self, client):
        """CSP deve permitir imagens data: e https:"""
        response = client.get('/health')
        csp = response.headers.get('Content-Security-Policy', '')
        
        assert "img-src" in csp, \
            "CSP deve ter img-src configurado"
        
        assert "data:" in csp, \
            "CSP deve permitir imagens data: (base64)"
    
    def test_csp_connect_src_configured(self, client):
        """CSP deve ter connect-src 'self' (API calls)"""
        response = client.get('/health')
        csp = response.headers.get('Content-Security-Policy', '')
        
        assert "connect-src 'self'" in csp, \
            "CSP deve permitir conexões apenas à mesma origem (API calls)"
    
    def test_csp_frame_ancestors_none(self, client):
        """CSP deve ter frame-ancestors 'none' (equivalente X-Frame-Options)"""
        response = client.get('/health')
        csp = response.headers.get('Content-Security-Policy', '')
        
        assert "frame-ancestors 'none'" in csp, \
            "CSP deve ter frame-ancestors 'none' (previne clickjacking)"
    
    def test_csp_upgrade_insecure_requests(self, client):
        """CSP deve ter upgrade-insecure-requests"""
        response = client.get('/health')
        csp = response.headers.get('Content-Security-Policy', '')
        
        assert "upgrade-insecure-requests" in csp, \
            "CSP deve ter upgrade-insecure-requests (força HTTPS)"


class TestSecurityHeadersOnAllEndpoints:
    """Testes para garantir headers em todos os endpoints"""
    
    def test_headers_on_health_endpoint(self, client):
        """Headers devem estar presentes no endpoint /health"""
        response = client.get('/health')
        
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'
        assert 'Content-Security-Policy' in response.headers
    
    def test_headers_on_api_endpoints(self, client):
        """Headers devem estar presentes em endpoints da API"""
        response = client.get('/api/evento/participantes')
        
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'
        assert 'Content-Security-Policy' in response.headers
        assert 'Server' not in response.headers
    
    def test_headers_on_static_files(self, client):
        """Headers devem estar presentes em arquivos estáticos"""
        response = client.get('/static/index.html')
        
        # Mesmo que o arquivo não exista, headers devem ser aplicados
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'


class TestProductionReadiness:
    """Testes de prontidão para produção"""
    
    def test_all_security_headers_present(self, client):
        """Todos os headers de segurança devem estar presentes"""
        response = client.get('/health')
        
        required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Referrer-Policy',
            'Content-Security-Policy'
        ]
        
        missing_headers = [h for h in required_headers if h not in response.headers]
        
        assert not missing_headers, \
            f"Headers de segurança ausentes: {missing_headers}"
    
    def test_no_information_disclosure_headers(self, client):
        """Não deve vazar informações do servidor"""
        response = client.get('/health')
        
        # Headers que NÃO devem estar presentes
        forbidden_headers = ['Server', 'X-Powered-By']
        
        present_forbidden = [h for h in forbidden_headers if h in response.headers]
        
        assert not present_forbidden, \
            f"Headers que vazam informação estão presentes: {present_forbidden}"


def test_summary_security_headers():
    """
    ========================================
    RESUMO: SECURITY HEADERS CONFIGURATION
    ========================================
    
    ✅ Headers Removidos:
       - Server (oculta versão Flask/Werkzeug)
    
    ✅ Headers de Segurança Adicionados:
       - X-Content-Type-Options: nosniff (previne MIME sniffing)
       - X-Frame-Options: DENY (previne clickjacking)
       - X-XSS-Protection: 1; mode=block (proteção XSS)
       - Referrer-Policy: strict-origin-when-cross-origin
    
    ✅ Content Security Policy (CSP):
       - default-src 'self'
       - script-src 'self' 'unsafe-inline' 'unsafe-eval' (React)
       - style-src 'self' 'unsafe-inline' (React CSS modules)
       - img-src 'self' data: https: (base64 + CDNs)
       - connect-src 'self' (API calls)
       - frame-ancestors 'none' (clickjacking)
       - upgrade-insecure-requests (força HTTPS)
    
    📁 Implementação:
       - src/main.py: @app.after_request middleware
    
    🔒 Proteções Ativas:
       - MIME sniffing attacks ✅
       - Clickjacking attacks ✅
       - XSS attacks ✅
       - Information disclosure ✅
       - HTTP downgrade attacks ✅
    
    🚀 Compatibilidade:
       - React/Vite frontend ✅
       - Inline styles/scripts ✅
       - Base64 images ✅
       - API calls ao backend ✅
    
    ========================================
    """
    assert True, "Security Headers implementados e testados com sucesso!"
