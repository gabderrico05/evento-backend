from flask import Blueprint, jsonify, request, session
from src.models.user import User, db
from sqlalchemy.exc import IntegrityError
import jwt
from datetime import datetime, timedelta
from functools import wraps
import os
import re
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

# Secret key para JWT (deve ser a mesma do app.config['SECRET_KEY'])
JWT_SECRET = os.getenv('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(hours=24)

# Expressão regular para validação de username (lista branca)
# Permite apenas letras (a-z, A-Z), números (0-9) e underscore (_)
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]+$')
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30


def validate_username(username):
    """
    Valida o nome de usuário usando uma lista branca (whitelist).
    
    Regras de validação:
    - Apenas caracteres alfanuméricos (a-z, A-Z, 0-9) e underscore (_)
    - Comprimento mínimo: 3 caracteres
    - Comprimento máximo: 30 caracteres
    - Rejeita qualquer caractere especial não permitido
    
    Args:
        username (str): Nome de usuário a ser validado
    
    Returns:
        tuple: (bool, str) - (válido, mensagem de erro)
               Se válido: (True, None)
               Se inválido: (False, mensagem descritiva do erro)
    
    Exemplos:
        >>> validate_username("usuario123")
        (True, None)
        
        >>> validate_username("user@123")
        (False, "Username contém caracteres não permitidos. Use apenas letras, números e underscore.")
        
        >>> validate_username("ab")
        (False, "Username deve ter entre 3 e 30 caracteres")
    """
    if not username:
        return False, "Username é obrigatório"
    
    if not isinstance(username, str):
        return False, "Username deve ser uma string"
    
    # Remover espaços em branco no início e fim
    username = username.strip()
    
    # Verificar comprimento
    if len(username) < USERNAME_MIN_LENGTH or len(username) > USERNAME_MAX_LENGTH:
        return False, f"Username deve ter entre {USERNAME_MIN_LENGTH} e {USERNAME_MAX_LENGTH} caracteres"
    
    # Verificar se contém apenas caracteres permitidos (lista branca)
    if not USERNAME_REGEX.match(username):
        return False, "Username contém caracteres não permitidos. Use apenas letras, números e underscore (_)"
    
    # Verificar se não começa com número ou underscore (boa prática)
    if username[0].isdigit() or username[0] == '_':
        return False, "Username não pode começar com número ou underscore"
    
    # Verificar se não termina com underscore (boa prática)
    if username[-1] == '_':
        return False, "Username não pode terminar com underscore"
    
    # Verificar se não contém underscores consecutivos (boa prática)
    if '__' in username:
        return False, "Username não pode conter underscores consecutivos"
    
    return True, None


def token_required(f):
    """Decorator para proteger rotas que requerem autenticação"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Verificar sessão primeiro
        if 'user_id' not in session:
            return jsonify({
                'error': 'Sessão não encontrada. Faça login novamente.',
                'session_expired': True
            }), 401
        
        token = None
        
        # JWT é passado no header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Token inválido'}), 401
        
        if not token:
            return jsonify({'error': 'Token não fornecido'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Verificar se o user_id do token corresponde ao da sessão
            if data['user_id'] != session.get('user_id'):
                session.clear()
                return jsonify({
                    'error': 'Token não corresponde à sessão atual',
                    'session_expired': True
                }), 401
            
            current_user = User.query.get(data['user_id'])
            if not current_user:
                session.clear()
                return jsonify({'error': 'Usuário não encontrado'}), 401
                
        except jwt.ExpiredSignatureError:
            session.clear()
            return jsonify({
                'error': 'Token expirado',
                'session_expired': True
            }), 401
        except jwt.InvalidTokenError:
            session.clear()
            return jsonify({'error': 'Token inválido'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


def generate_token(user_id, mfa_verified=False):
    """Gera um JWT token"""
    payload = {
        'user_id': user_id,
        'mfa_verified': mfa_verified,
        'exp': datetime.utcnow() + JWT_EXPIRATION_DELTA,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_temp_token(user_id):
    """Gera um token temporário para autenticação MFA (válido por 5 minutos)"""
    payload = {
        'user_id': user_id,
        'temp': True,
        'exp': datetime.utcnow() + timedelta(minutes=5),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

@user_bp.route('/login', methods=['POST'])
def login():
    """
    Endpoint de login - Primeira etapa (senha)
    Espera JSON com: username/email, password
    Cria sessão com controle de tempo de inatividade e tempo máximo de vida
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        # Aceita username ou email
        identifier = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not identifier or not password:
            return jsonify({'error': 'Username/email e senha são obrigatórios'}), 400
        
        # Buscar usuário por username ou email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        
        if not user or not user.verify_password(password):
            return jsonify({'error': 'Credenciais inválidas'}), 401
        
        # Verificar se usuário requer MFA
        if user.requires_mfa():
            # Criar sessão temporária para MFA
            session.clear()
            session['temp_user_id'] = user.id
            session['mfa_pending'] = True
            session['temp_created_at'] = datetime.utcnow().isoformat()
            
            # Gerar token temporário para a segunda etapa
            temp_token = generate_temp_token(user.id)
            return jsonify({
                'message': 'Primeira etapa concluída',
                'requires_mfa': True,
                'temp_token': temp_token
            }), 200
        
        # Usuário não requer MFA, criar sessão completa
        session.clear()
        session.permanent = True  # Usa PERMANENT_SESSION_LIFETIME (15 min)
        session['user_id'] = user.id
        session['username'] = user.username
        session['session_created_at'] = datetime.utcnow().isoformat()
        session['last_activity'] = datetime.utcnow().isoformat()
        session['mfa_verified'] = False
        
        token = generate_token(user.id, mfa_verified=False)
        return jsonify({
            'message': 'Login realizado com sucesso',
            'requires_mfa': False,
            'token': token,
            'user': user.to_dict(include_mfa_status=True),
            'session_info': {
                'inactivity_timeout': 15,  # minutos
                'max_lifetime': 60  # minutos
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao fazer login: {str(e)}", exc_info=True)
        raise


@user_bp.route('/login/mfa', methods=['POST'])
def verify_mfa():
    """
    Endpoint de login - Segunda etapa (MFA)
    Espera JSON com: temp_token, totp_code
    Cria sessão completa após verificação MFA
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        temp_token = data.get('temp_token')
        totp_code = data.get('totp_code')
        
        if not temp_token or not totp_code:
            return jsonify({'error': 'Token temporário e código TOTP são obrigatórios'}), 400
        
        # Verificar sessão temporária
        if not session.get('mfa_pending') or not session.get('temp_user_id'):
            return jsonify({'error': 'Sessão MFA não encontrada. Faça login novamente.'}), 401
        
        # Validar token temporário
        try:
            payload = jwt.decode(temp_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if not payload.get('temp'):
                return jsonify({'error': 'Token inválido'}), 401
            
            user_id = payload.get('user_id')
            
            # Verificar se corresponde à sessão temporária
            if user_id != session.get('temp_user_id'):
                session.clear()
                return jsonify({'error': 'Token não corresponde à sessão'}), 401
            
            user = User.query.get(user_id)
            
            if not user:
                session.clear()
                return jsonify({'error': 'Usuário não encontrado'}), 401
            
        except jwt.ExpiredSignatureError:
            session.clear()
            return jsonify({'error': 'Token temporário expirado. Faça login novamente.'}), 401
        except jwt.InvalidTokenError:
            session.clear()
            return jsonify({'error': 'Token inválido'}), 401
        
        # Verificar código TOTP
        if not user.verify_totp(totp_code):
            return jsonify({'error': 'Código TOTP inválido'}), 401
        
        # MFA verificado com sucesso, criar sessão completa
        session.clear()
        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        session['session_created_at'] = datetime.utcnow().isoformat()
        session['last_activity'] = datetime.utcnow().isoformat()
        session['mfa_verified'] = True
        
        # MFA verificado com sucesso, gerar token final
        token = generate_token(user.id, mfa_verified=True)
        return jsonify({
            'message': 'Login com MFA realizado com sucesso',
            'token': token,
            'user': user.to_dict(include_mfa_status=True),
            'session_info': {
                'inactivity_timeout': 15,  # minutos
                'max_lifetime': 60  # minutos
            }
        }), 200
        
    except Exception as e:
        session.clear()
        logger.error(f"Erro ao verificar MFA: {str(e)}", exc_info=True)
        raise


@user_bp.route('/register', methods=['POST'])
def register_user():
    """
    Endpoint para registro de novos usuários.
    Espera JSON com: username, email, password
    """
    try:
        data = request.json
        
        # Validação de campos obrigatórios
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        required_fields = ['username', 'email', 'password']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': 'Campos obrigatórios faltando',
                'missing_fields': missing_fields
            }), 400
        
        # Validação de username usando lista branca
        is_valid, error_message = validate_username(data['username'])
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Validação básica de senha (mínimo 6 caracteres)
        if len(data['password']) < 6:
            return jsonify({'error': 'A senha deve ter no mínimo 6 caracteres'}), 400
        
        # Validação básica de email
        if '@' not in data['email']:
            return jsonify({'error': 'Email inválido'}), 400
        
        # Criar novo usuário
        user = User(
            username=data['username'],
            email=data['email'],
            is_sensitive_account=data.get('is_sensitive_account', False)
        )
        
        # Hash da senha usando Argon2
        user.set_password(data['password'])
        
        # Salvar no banco de dados
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'Usuário registrado com sucesso',
            'user': user.to_dict()
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Usuário ou email já existente'}), 409
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao registrar usuário: {str(e)}", exc_info=True)
        raise

@user_bp.route('/mfa/setup', methods=['POST'])
@token_required
def setup_mfa(current_user):
    """
    Configurar MFA para o usuário autenticado
    Gera QR code para configuração no app autenticador
    """
    try:
        if current_user.mfa_enabled:
            return jsonify({'error': 'MFA já está habilitado'}), 400
        
        # Gerar novo secret
        secret = current_user.generate_mfa_secret()
        db.session.commit()
        
        # Gerar QR code
        qr_code = current_user.generate_qr_code()
        
        return jsonify({
            'message': 'MFA configurado. Escaneie o QR code com seu app autenticador.',
            'qr_code': f'data:image/png;base64,{qr_code}',
            'secret': secret,  # Útil para entrada manual
            'totp_uri': current_user.get_totp_uri()
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao configurar MFA: {str(e)}", exc_info=True)
        raise


@user_bp.route('/mfa/enable', methods=['POST'])
@token_required
def enable_mfa(current_user):
    """
    Habilitar MFA após configuração
    Espera JSON com: totp_code (para verificar que foi configurado corretamente)
    """
    try:
        data = request.json
        
        if not data or 'totp_code' not in data:
            return jsonify({'error': 'Código TOTP é obrigatório'}), 400
        
        if current_user.mfa_enabled:
            return jsonify({'error': 'MFA já está habilitado'}), 400
        
        if not current_user.mfa_secret:
            return jsonify({'error': 'MFA não foi configurado. Execute /mfa/setup primeiro.'}), 400
        
        # Verificar código TOTP para confirmar configuração
        if not current_user.verify_totp(data['totp_code']):
            return jsonify({'error': 'Código TOTP inválido. Verifique seu app autenticador.'}), 401
        
        # Habilitar MFA
        current_user.enable_mfa()
        db.session.commit()
        
        return jsonify({
            'message': 'MFA habilitado com sucesso',
            'user': current_user.to_dict(include_mfa_status=True)
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao verificar MFA: {str(e)}", exc_info=True)
        raise


@user_bp.route('/mfa/disable', methods=['POST'])
@token_required
def disable_mfa(current_user):
    """
    Desabilitar MFA
    Espera JSON com: password, totp_code (para confirmação)
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        password = data.get('password')
        totp_code = data.get('totp_code')
        
        if not password:
            return jsonify({'error': 'Senha é obrigatória'}), 400
        
        # Verificar senha
        if not current_user.verify_password(password):
            return jsonify({'error': 'Senha incorreta'}), 401
        
        # Verificar TOTP se MFA estiver habilitado
        if current_user.mfa_enabled and totp_code:
            if not current_user.verify_totp(totp_code):
                return jsonify({'error': 'Código TOTP inválido'}), 401
        
        # Desabilitar MFA
        current_user.disable_mfa()
        db.session.commit()
        
        return jsonify({
            'message': 'MFA desabilitado com sucesso',
            'user': current_user.to_dict(include_mfa_status=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao desabilitar MFA: {str(e)}", exc_info=True)
        raise
        raise
        raise


@user_bp.route('/mfa/status', methods=['GET'])
@token_required
def mfa_status(current_user):
    """
    Verificar status do MFA do usuário autenticado
    """
    return jsonify({
        'mfa_enabled': current_user.mfa_enabled,
        'is_sensitive_account': current_user.is_sensitive_account,
        'requires_mfa': current_user.requires_mfa()
    }), 200


@user_bp.route('/logout', methods=['POST'])
def logout():
    """
    Endpoint de logout - Limpa a sessão do servidor
    """
    try:
        if 'user_id' in session:
            username = session.get('username', 'Usuário')
            session.clear()
            return jsonify({
                'message': f'{username} desconectado com sucesso',
                'logged_out': True
            }), 200
        else:
            return jsonify({
                'message': 'Nenhuma sessão ativa encontrada',
                'logged_out': True
            }), 200
    except Exception as e:
        session.clear()
        logger.error(f"Erro ao fazer logout: {str(e)}", exc_info=True)
        raise


@user_bp.route('/session/status', methods=['GET'])
def session_status():
    """
    Endpoint para verificar status da sessão atual
    Retorna informações sobre a sessão sem exigir token
    """
    try:
        if 'user_id' not in session:
            return jsonify({
                'active': False,
                'message': 'Nenhuma sessão ativa'
            }), 200
        
        current_time = datetime.utcnow()
        
        # Calcular tempo restante de inatividade
        last_activity = datetime.fromisoformat(session['last_activity'])
        inactive_time = current_time - last_activity
        inactivity_remaining = timedelta(minutes=15) - inactive_time
        
        # Calcular tempo restante de vida máxima
        session_created = datetime.fromisoformat(session['session_created_at'])
        session_age = current_time - session_created
        lifetime_remaining = timedelta(minutes=60) - session_age
        
        return jsonify({
            'active': True,
            'user_id': session['user_id'],
            'username': session.get('username'),
            'mfa_verified': session.get('mfa_verified', False),
            'session_created_at': session['session_created_at'],
            'last_activity': session['last_activity'],
            'inactivity_remaining_seconds': max(0, int(inactivity_remaining.total_seconds())),
            'lifetime_remaining_seconds': max(0, int(lifetime_remaining.total_seconds())),
            'will_expire_by': 'inactivity' if inactivity_remaining < lifetime_remaining else 'max_lifetime'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao verificar sessão: {str(e)}", exc_info=True)
        raise


@user_bp.route('/session/refresh', methods=['POST'])
@token_required
def refresh_session(current_user):
    """
    Endpoint para renovar a sessão (atualizar last_activity)
    Útil para manter a sessão ativa durante uso contínuo
    """
    try:
        current_time = datetime.utcnow()
        
        # Verificar se sessão não excedeu tempo máximo de vida
        session_created = datetime.fromisoformat(session['session_created_at'])
        session_age = current_time - session_created
        
        if session_age > timedelta(minutes=60):
            session.clear()
            return jsonify({
                'error': 'Sessão expirou por tempo máximo de vida',
                'session_expired': True,
                'reason': 'max_lifetime'
            }), 401
        
        # Atualizar última atividade
        session['last_activity'] = current_time.isoformat()
        
        # Calcular tempos restantes
        lifetime_remaining = timedelta(minutes=60) - session_age
        
        return jsonify({
            'message': 'Sessão renovada com sucesso',
            'last_activity': session['last_activity'],
            'inactivity_timeout_seconds': 15 * 60,
            'lifetime_remaining_seconds': int(lifetime_remaining.total_seconds())
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao renovar sessão: {str(e)}", exc_info=True)
        raise


@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users', methods=['POST'])
def create_user():
    
    data = request.json
    user = User(username=data['username'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return '', 204
