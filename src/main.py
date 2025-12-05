import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, session, jsonify, request, redirect
from datetime import timedelta, datetime, timezone
from src.models.db import db
from src.models.participante import Participante
from src.models.login_attempt import LoginAttempt
from src.models.audit_log import AuditLog
from src.routes.user import user_bp
from src.routes.evento import evento_bp
from src.config import get_config
import logging
import traceback
from sqlalchemy.exc import SQLAlchemyError

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Carregar configurações centralizadas (incluindo banco de dados com permissões restritas)
config_class = get_config()
config_class.init_app(app)

# ============================================
# HTTPS/SECURITY CONFIGURATION (PRODUCTION)
# ============================================

# Forçar HTTPS em produção
if not app.config['DEBUG']:
    @app.before_request
    def redirect_to_https():
        """
        Força redirecionamento para HTTPS em produção.
        
        Verifica o header X-Forwarded-Proto enviado pelo Nginx/Apache
        para determinar se a requisição original era HTTP.
        
        Security:
        - Previne downgrade attacks
        - Garante que todas as comunicações sejam criptografadas
        - Protege cookies de sessão (SESSION_COOKIE_SECURE)
        """
        # Ignorar health check
        if request.path == '/health':
            return None
            
        if request.headers.get('X-Forwarded-Proto') == 'http':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)
    
    # Configurações de segurança para produção
    app.config.update(
        # Session cookies apenas via HTTPS
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        
        # Prefer HTTPS
        PREFERRED_URL_SCHEME='https',
    )
    
    # Aplicar ProxyFix para headers X-Forwarded-*
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,      # X-Forwarded-For
        x_proto=1,    # X-Forwarded-Proto
        x_host=1,     # X-Forwarded-Host
        x_prefix=1    # X-Forwarded-Prefix
    )
    
    logger.info("🔒 HTTPS enforcement enabled (Production mode)")
    logger.info("✓ SESSION_COOKIE_SECURE=True")
    logger.info("✓ PREFERRED_URL_SCHEME=https")
    logger.info("✓ ProxyFix middleware enabled")
else:
    # Desenvolvimento: permitir HTTP
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    logger.warning("⚠️  Development mode: HTTP allowed (HTTPS required in production)")

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(evento_bp, url_prefix='/api')

# Inicializar banco de dados
db.init_app(app)
with app.app_context():
    db.create_all()

# ==========================================
# TRATAMENTO GLOBAL DE EXCEÇÕES
# ==========================================

@app.errorhandler(SQLAlchemyError)
def handle_database_error(e):
    """
    Tratamento global para erros de banco de dados.
    
    - Registra stack trace completo no log do servidor
    - Retorna apenas mensagem genérica ao frontend (segurança)
    - Status 500 Internal Server Error
    """
    # Log completo do erro (stack trace)
    logger.error(f"Database error: {str(e)}")
    logger.error(f"Stack trace:\n{traceback.format_exc()}")
    
    # Rollback da transação em caso de erro
    db.session.rollback()
    
    # Retornar apenas mensagem genérica ao frontend
    return jsonify({
        'error': 'Erro interno do servidor',
        'internal_error': True
    }), 500

@app.errorhandler(Exception)
def handle_generic_error(e):
    """
    Tratamento global para exceções não capturadas.
    
    - Registra stack trace completo no log do servidor
    - Retorna apenas mensagem genérica ao frontend (segurança)
    - Status 500 Internal Server Error
    """
    # Log completo do erro (stack trace)
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(f"Stack trace:\n{traceback.format_exc()}")
    
    # Retornar apenas mensagem genérica ao frontend
    return jsonify({
        'error': 'Erro interno do servidor',
        'internal_error': True
    }), 500

@app.errorhandler(404)
def handle_not_found(e):
    """Tratamento para rotas não encontradas"""
    logger.warning(f"404 Not Found: {str(e)}")
    return jsonify({
        'error': 'Recurso não encontrado',
        'not_found': True
    }), 404

@app.errorhandler(405)
def handle_method_not_allowed(e):
    """Tratamento para métodos HTTP não permitidos"""
    logger.warning(f"405 Method Not Allowed: {str(e)}")
    return jsonify({
        'error': 'Método não permitido',
        'method_not_allowed': True
    }), 405

# ==========================================
# SECURITY HEADERS MIDDLEWARE
# ==========================================

@app.after_request
def add_security_headers(response):
    """
    Adiciona headers de segurança e remove headers desnecessários.
    
    Security Headers:
    - Remove 'Server' header (oculta versão do servidor)
    - X-Content-Type-Options: nosniff (previne MIME sniffing)
    - X-Frame-Options: DENY (previne clickjacking)
    - Content-Security-Policy: política restritiva para React frontend
    - X-XSS-Protection: proteção contra XSS (browsers legados)
    - Referrer-Policy: controla informações de referrer
    
    CSP configurado para React:
    - script-src 'self' 'unsafe-inline' (inline scripts do React)
    - style-src 'self' 'unsafe-inline' (CSS modules do React)
    - img-src 'self' data: (imagens base64)
    - connect-src 'self' (API calls)
    """
    # Remover header Server (ocultar versão Flask/Werkzeug)
    response.headers.pop('Server', None)
    
    # Headers de segurança
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy (CSP) otimizado para React
    # NOTA: 'unsafe-inline' necessário para React (Vite build inline styles/scripts)
    # Em produção, considerar usar nonce-based CSP para maior segurança
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # unsafe-eval para React DevTools
        "style-src 'self' 'unsafe-inline'",  # inline styles do React
        "img-src 'self' data: https:",  # data: para imagens base64, https: para CDNs
        "font-src 'self' data:",
        "connect-src 'self'",  # API calls ao próprio backend
        "frame-ancestors 'none'",  # equivalente a X-Frame-Options: DENY
        "base-uri 'self'",
        "form-action 'self'",
        "upgrade-insecure-requests"  # força upgrade de HTTP para HTTPS
    ]
    response.headers['Content-Security-Policy'] = '; '.join(csp_directives)
    
    return response

# ==========================================
# MIDDLEWARE DE SESSÃO
# ==========================================

@app.before_request
def manage_session():
    """
    Middleware para gerenciar sessão:
    - Marca sessão como permanente (usa PERMANENT_SESSION_LIFETIME)
    - Controla tempo máximo de vida da sessão (60 minutos)
    - Atualiza last_activity em cada requisição
    """
    # Ignorar rotas de login e registro
    if request.endpoint in ['user.login', 'user.verify_mfa', 'user.register_user', None]:
        return
    
    # Ignorar health check
    if request.path == '/health':
        return
    
    # Se a sessão existir, verificar tempos de expiração
    if 'user_id' in session:
        session.permanent = True  # Usa PERMANENT_SESSION_LIFETIME
        
        current_time = datetime.utcnow()
        
        # Verificar tempo máximo de vida (60 minutos desde criação)
        if 'session_created_at' in session:
            session_created = datetime.fromisoformat(session['session_created_at'])
            session_age = current_time - session_created
            
            if session_age > app.config['SESSION_MAX_LIFETIME']:
                # Sessão expirou por tempo máximo de vida
                session.clear()
                return jsonify({
                    'error': 'Sessão expirada por tempo máximo de vida. Faça login novamente.',
                    'session_expired': True,
                    'reason': 'max_lifetime'
                }), 401
        
        # Verificar tempo de inatividade (15 minutos desde última atividade)
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            inactive_time = current_time - last_activity
            
            if inactive_time > app.config['PERMANENT_SESSION_LIFETIME']:
                # Sessão expirou por inatividade
                session.clear()
                return jsonify({
                    'error': 'Sessão expirada por inatividade. Faça login novamente.',
                    'session_expired': True,
                    'reason': 'inactivity'
                }), 401
        
        # Atualizar tempo de última atividade
        session['last_activity'] = current_time.isoformat()

# ==========================================
# ROTAS
# ==========================================

@app.route('/health')
def health_check():
    """
    Health check endpoint para monitoramento e load balancer.
    
    Retorna status 200 se a aplicação está rodando.
    Pode ser usado por Nginx, Kubernetes, Docker, etc.
    """
    return {'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}, 200

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    # Desenvolvimento: rodar com Flask dev server
    # Produção: usar Gunicorn (ver gunicorn_config.py e PRODUCTION_DEPLOY.md)
    if app.config['DEBUG']:
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        logger.warning("⚠️  Production mode detected. Use Gunicorn instead:")
        logger.warning("   gunicorn -c gunicorn_config.py src.main:app")
        app.run(host='127.0.0.1', port=8000, debug=False)
