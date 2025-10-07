from flask import Blueprint, request, jsonify
from src.models.participante import Participante, db
import re

evento_bp = Blueprint('evento', __name__)

def validar_cpf(cpf):
    """Valida CPF usando algoritmo oficial"""
    # Remove caracteres não numéricos
    cpf = re.sub(r'\D', '', cpf)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Validação do primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = (soma * 10) % 11
    if resto == 10 or resto == 11:
        resto = 0
    if resto != int(cpf[9]):
        return False
    
    # Validação do segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = (soma * 10) % 11
    if resto == 10 or resto == 11:
        resto = 0
    if resto != int(cpf[10]):
        return False
    
    return True

def validar_email(email):
    """Valida formato do email"""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None

def validar_telefone(telefone):
    """Valida telefone brasileiro"""
    telefone_limpo = re.sub(r'\D', '', telefone)
    return len(telefone_limpo) >= 10 and len(telefone_limpo) <= 11

@evento_bp.route('/resgatar-ingresso', methods=['POST'])
def resgatar_ingresso():
    try:
        data = request.get_json()
        
        # Validação dos dados obrigatórios
        campos_obrigatorios = ['nome', 'email', 'cpf', 'telefone', 'codigoEvento']
        for campo in campos_obrigatorios:
            if not data.get(campo) or not data[campo].strip():
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400
        
        nome = data['nome'].strip()
        email = data['email'].strip().lower()
        cpf = re.sub(r'\D', '', data['cpf'])
        telefone = re.sub(r'\D', '', data['telefone'])
        codigo_evento = data['codigoEvento'].strip().upper()
        
        # Validações específicas
        if len(nome) < 2:
            return jsonify({'error': 'Nome deve ter pelo menos 2 caracteres'}), 400
        
        if not validar_email(email):
            return jsonify({'error': 'Email inválido'}), 400
        
        if not validar_cpf(cpf):
            return jsonify({'error': 'CPF inválido'}), 400
        
        if not validar_telefone(telefone):
            return jsonify({'error': 'Telefone inválido'}), 400
        
        if len(codigo_evento) < 6:
            return jsonify({'error': 'Código do evento deve ter pelo menos 6 caracteres'}), 400
        
        # Verificar se o CPF já está cadastrado
        participante_existente = Participante.query.filter_by(cpf=cpf).first()
        if participante_existente:
            if participante_existente.ativo:
                return jsonify({'error': 'CPF já possui ingresso resgatado para este evento'}), 400
        
        # Verificar se o email já está cadastrado
        email_existente = Participante.query.filter_by(email=email).first()
        if email_existente and email_existente.ativo:
            return jsonify({'error': 'Email já possui ingresso resgatado para este evento'}), 400
        
        # Validar código do evento (códigos válidos fictícios)
        codigos_validos = ['EVENTO2025', 'ESPECIAL2025', 'PREMIUM2025', 'VIP2025']
        if codigo_evento not in codigos_validos:
            return jsonify({'error': 'Código do evento inválido'}), 400
        
        # Criar novo participante
        novo_participante = Participante(
            nome=nome,
            email=email,
            cpf=cpf,
            telefone=telefone,
            codigo_evento=codigo_evento
        )
        
        # Salvar no banco de dados
        db.session.add(novo_participante)
        db.session.commit()
        
        # Retornar dados do ingresso
        return jsonify(novo_participante.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro interno do servidor'}), 500

@evento_bp.route('/participantes', methods=['GET'])
def listar_participantes():
    """Endpoint para listar todos os participantes (para fins de teste)"""
    try:
        participantes = Participante.query.filter_by(ativo=True).all()
        return jsonify([p.to_dict() for p in participantes]), 200
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar participantes'}), 500

@evento_bp.route('/participante/<int:participante_id>', methods=['GET'])
def buscar_participante(participante_id):
    """Endpoint para buscar um participante específico"""
    try:
        participante = Participante.query.get(participante_id)
        if not participante or not participante.ativo:
            return jsonify({'error': 'Participante não encontrado'}), 404
        
        return jsonify(participante.to_dict()), 200
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar participante'}), 500

@evento_bp.route('/validar-codigo/<codigo>', methods=['GET'])
def validar_codigo_evento(codigo):
    """Endpoint para validar se um código de evento é válido"""
    try:
        codigos_validos = ['EVENTO2025', 'ESPECIAL2025', 'PREMIUM2025', 'VIP2025']
        codigo_upper = codigo.upper()
        
        if codigo_upper in codigos_validos:
            return jsonify({'valido': True, 'codigo': codigo_upper}), 200
        else:
            return jsonify({'valido': False, 'codigo': codigo_upper}), 200
    except Exception as e:
        return jsonify({'error': 'Erro ao validar código'}), 500
