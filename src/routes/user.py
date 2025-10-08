from flask import Blueprint, jsonify, request
from src.models.user import User, db
from src.auth import login_required, get_current_user

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
@login_required
def get_users():
    """Lista todos os usuários (apenas para usuários autenticados)"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users', methods=['POST'])
@login_required  
def create_user():
    """Cria um novo usuário (apenas para usuários autenticados)"""
    try:
        data = request.json
        
        # Validação básica
        if not data or not all(k in data for k in ('username', 'email', 'password')):
            return jsonify({'error': 'Username, email e password são obrigatórios'}), 400
        
        # Verifica se usuário já existe
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({'error': 'Username ou email já está em uso'}), 409
        
        user = User(username=data['username'], email=data['email'])
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """Busca um usuário por ID"""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Atualiza um usuário (apenas o próprio usuário pode se atualizar)"""
    try:
        current_user = get_current_user()
        
        # Verifica se o usuário está tentando atualizar seus próprios dados
        if current_user.id != user_id:
            return jsonify({'error': 'Você só pode atualizar seus próprios dados'}), 403
        
        user = User.query.get_or_404(user_id)
        data = request.json
        
        # Atualiza apenas campos permitidos
        if 'username' in data:
            # Verifica se o novo username não está em uso
            existing_user = User.query.filter(
                User.username == data['username'], 
                User.id != user_id
            ).first()
            if existing_user:
                return jsonify({'error': 'Username já está em uso'}), 409
            user.username = data['username']
        
        if 'email' in data:
            # Verifica se o novo email não está em uso
            existing_user = User.query.filter(
                User.email == data['email'], 
                User.id != user_id
            ).first()
            if existing_user:
                return jsonify({'error': 'Email já está em uso'}), 409
            user.email = data['email']
        
        db.session.commit()
        return jsonify(user.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Deleta um usuário (apenas o próprio usuário pode se deletar)"""
    try:
        current_user = get_current_user()
        
        # Verifica se o usuário está tentando deletar seus próprios dados
        if current_user.id != user_id:
            return jsonify({'error': 'Você só pode deletar sua própria conta'}), 403
        
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Usuário deletado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500
