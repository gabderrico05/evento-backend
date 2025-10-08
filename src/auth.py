import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from src.models.user import User


class AuthManager:
    @staticmethod
    def generate_token(user_id):
        """Gera um token JWT para o usuário"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        """Verifica e decodifica um token JWT"""
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


def login_required(f):
    """Decorator para rotas que requerem autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token de acesso requerido'}), 401
        
        try:
            # Remove "Bearer " do token se presente
            if token.startswith('Bearer '):
                token = token[7:]
            
            user_id = AuthManager.verify_token(token)
            if user_id is None:
                return jsonify({'error': 'Token inválido ou expirado'}), 401
            
            # Busca o usuário no banco
            user = User.query.filter(User.id == user_id).first()
            if not user or not user.is_active:
                return jsonify({'error': 'Usuário não encontrado ou inativo'}), 401
            
            # Adiciona o usuário ao contexto da requisição
            request.current_user = user
            
        except Exception as e:
            return jsonify({'error': 'Erro na autenticação'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user():
    """Retorna o usuário atual da requisição"""
    return getattr(request, 'current_user', None)