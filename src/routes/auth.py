from flask import Blueprint, request, jsonify
from src.models.user import User, db
from src.auth import AuthManager, login_required, get_current_user
import re

auth_bp = Blueprint('auth', __name__)


def validate_email(email):
    """Valida formato do email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@auth_bp.route('/register', methods=['POST'])
def register():
    """Registra um novo usuário"""
    try:
        data = request.get_json()
        
        # Validação dos dados
        if not data or not all(k in data for k in ('username', 'email', 'password')):
            return jsonify({'error': 'Username, email e password são obrigatórios'}), 400
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        # Validações
        if len(username) < 3:
            return jsonify({'error': 'Username deve ter pelo menos 3 caracteres'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Email inválido'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Senha deve ter pelo menos 6 caracteres'}), 400
        
        # Verifica se usuário já existe
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                return jsonify({'error': 'Username já está em uso'}), 409
            else:
                return jsonify({'error': 'Email já está em uso'}), 409
        
        # Cria novo usuário
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Gera token para o usuário
        token = AuthManager.generate_token(user.id)
        
        return jsonify({
            'message': 'Usuário criado com sucesso',
            'user': user.to_dict(),
            'token': token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Autentica um usuário e retorna um token"""
    try:
        data = request.get_json()
        
        # Validação dos dados
        if not data or not all(k in data for k in ('login', 'password')):
            return jsonify({'error': 'Login e password são obrigatórios'}), 400
        
        login_field = data['login'].strip()
        password = data['password']
        
        # Busca usuário por username ou email
        user = User.query.filter(
            (User.username == login_field) | (User.email == login_field.lower())
        ).first()
        
        # Verifica se usuário existe e senha está correta
        if not user or not user.check_password(password):
            return jsonify({'error': 'Credenciais inválidas'}), 401
        
        # Verifica se usuário está ativo
        if not user.is_active:
            return jsonify({'error': 'Conta desativada'}), 401
        
        # Gera token
        token = AuthManager.generate_token(user.id)
        
        return jsonify({
            'message': 'Login realizado com sucesso',
            'user': user.to_dict(),
            'token': token
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Erro interno do servidor'}), 500


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user_info():
    """Retorna informações do usuário atual"""
    user = get_current_user()
    return jsonify({
        'user': user.to_dict()
    }), 200


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Altera a senha do usuário atual"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ('current_password', 'new_password')):
            return jsonify({'error': 'Senha atual e nova senha são obrigatórias'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        user = get_current_user()
        
        # Verifica senha atual
        if not user.check_password(current_password):
            return jsonify({'error': 'Senha atual incorreta'}), 400
        
        # Valida nova senha
        if len(new_password) < 6:
            return jsonify({'error': 'Nova senha deve ter pelo menos 6 caracteres'}), 400
        
        # Atualiza senha
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Senha alterada com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout do usuário (em uma implementação real, invalidaria o token)"""
    return jsonify({'message': 'Logout realizado com sucesso'}), 200