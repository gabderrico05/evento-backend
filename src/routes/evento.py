from flask import Blueprint, request, jsonify, session
from src.models.participante import Participante, db
from functools import wraps
import re
import logging

logger = logging.getLogger(__name__)

evento_bp = Blueprint('evento', __name__)

def participante_required(f):
    """
    Decorator para proteger rotas que requerem autenticação de participante.
    Verifica se existe uma sessão ativa de participante.
    
    Usage:
        @evento_bp.route('/rota-protegida')
        @participante_required
        def rota_protegida(participante_atual):
            # participante_atual é injetado automaticamente
            return jsonify(participante_atual.to_dict())
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se existe sessão de participante
        if 'participante_id' not in session:
            return jsonify({
                'error': 'Não autorizado. Faça login para acessar este recurso.',
                'auth_required': True
            }), 401
        
        # Buscar participante da sessão
        participante_id = session.get('participante_id')
        participante_atual = Participante.query.get(participante_id)
        
        if not participante_atual or not participante_atual.ativo:
            # Sessão inválida, limpar
            session.clear()
            return jsonify({
                'error': 'Sessão inválida. Faça login novamente.',
                'auth_required': True
            }), 401
        
        # Injetar participante_atual como primeiro argumento
        return f(participante_atual, *args, **kwargs)
    
    return decorated_function

def participante_required(f):
    """
    Decorator para proteger rotas que requerem autenticação de participante.
    Verifica se existe uma sessão ativa de participante.
    
    Usage:
        @evento_bp.route('/rota-protegida')
        @participante_required
        def rota_protegida(participante_atual):
            # participante_atual é injetado automaticamente
            return jsonify(participante_atual.to_dict())
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se existe sessão de participante
        if 'participante_id' not in session:
            return jsonify({
                'error': 'Não autorizado. Faça login para acessar este recurso.',
                'auth_required': True
            }), 401
        
        # Buscar participante da sessão
        participante_id = session.get('participante_id')
        participante_atual = Participante.query.get(participante_id)
        
        if not participante_atual or not participante_atual.ativo:
            # Sessão inválida, limpar
            session.clear()
            return jsonify({
                'error': 'Sessão inválida. Faça login novamente.',
                'auth_required': True
            }), 401
        
        # Injetar participante_atual como primeiro argumento
        return f(participante_atual, *args, **kwargs)
    
    return decorated_function

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
        campos_obrigatorios = ['nome', 'email', 'cpf', 'telefone', 'senha']
        for campo in campos_obrigatorios:
            if not data.get(campo) or not data[campo].strip():
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400
        
        nome = data['nome'].strip()
        email = data['email'].strip().lower()
        cpf = re.sub(r'\D', '', data['cpf'])
        telefone = re.sub(r'\D', '', data['telefone'])
        senha = data['senha']
        
        # Validações específicas
        if len(nome) < 2:
            return jsonify({'error': 'Nome deve ter pelo menos 2 caracteres'}), 400
        
        if not validar_email(email):
            return jsonify({'error': 'Email inválido'}), 400
        
        if not validar_cpf(cpf):
            return jsonify({'error': 'CPF inválido'}), 400
        
        if not validar_telefone(telefone):
            return jsonify({'error': 'Telefone inválido'}), 400
        
        # Verificar se o CPF já está cadastrado
        participante_existente = Participante.query.filter_by(cpf=cpf).first()
        if participante_existente:
            if participante_existente.ativo:
                return jsonify({'error': 'CPF já possui ingresso resgatado'}), 400
        
        # Verificar se o email já está cadastrado
        email_existente = Participante.query.filter_by(email=email).first()
        if email_existente and email_existente.ativo:
            return jsonify({'error': 'Email já possui ingresso resgatado'}), 400
        
        # Criar novo participante
        novo_participante = Participante(
            nome=nome,
            email=email,
            cpf=cpf,
            telefone=telefone,
            senha=senha
        )
        
        # Salvar no banco de dados
        db.session.add(novo_participante)
        db.session.commit()
        
        # Log de criação usando numero_ingresso (não ID)
        print(f"[INFO] Novo ingresso resgatado: {novo_participante.numero_ingresso} - {novo_participante.nome}")
        
        # Retornar dados do ingresso (sem ID interno)
        return jsonify(novo_participante.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao resgatar ingresso: {str(e)}", exc_info=True)
        # Erro tratado pelo handler global
        raise

@evento_bp.route('/participantes', methods=['GET'])
def listar_participantes():
    """
    Endpoint para listar todos os participantes (para fins de teste/admin).
    
    Security:
        - IDs internos não são expostos
        - Retorna apenas dados públicos
        - Logs não contêm IDs sequenciais
    """
    try:
        participantes = Participante.query.filter_by(ativo=True).all()
        print(f"[INFO] Listagem de participantes: {len(participantes)} registros encontrados")
        return jsonify([p.to_dict() for p in participantes]), 200
    except Exception as e:
        logger.error(f"Erro ao listar participantes: {str(e)}", exc_info=True)
        raise

@evento_bp.route('/participante/<string:numero_ingresso>', methods=['GET'])
def buscar_participante(numero_ingresso):
    """
    Endpoint para buscar um participante específico usando numero_ingresso.
    
    Args:
        numero_ingresso (str): Número do ingresso público (ex: EVTAB12CD34)
    
    Returns:
        JSON com dados do participante (sem expor ID interno)
    
    Security:
        - IDs internos não são expostos em URLs ou responses
        - Apenas numero_ingresso é usado como identificador público
        - Logs usam numero_ingresso ao invés de ID
    """
    try:
        # Validar formato do numero_ingresso
        if not numero_ingresso or len(numero_ingresso) < 3:
            return jsonify({'error': 'Número de ingresso inválido'}), 400
        
        # Buscar por numero_ingresso ao invés de ID
        participante = Participante.query.filter_by(
            numero_ingresso=numero_ingresso.upper(),
            ativo=True
        ).first()
        
        if not participante:
            # Log sem expor IDs internos
            print(f"[WARN] Ingresso não encontrado: {numero_ingresso}")
            return jsonify({'error': 'Participante não encontrado'}), 404
        
        # Log de acesso usando numero_ingresso
        print(f"[INFO] Acesso ao ingresso: {participante.numero_ingresso} - {participante.nome}")
        
        return jsonify(participante.to_dict()), 200
        
    except Exception as e:
        # Log de erro sem expor IDs internos
        print(f"[ERROR] Erro ao buscar ingresso {numero_ingresso}: {str(e)}")
        return jsonify({'error': 'Erro ao buscar participante'}), 500

## Rota de validação de código removida pois código de evento não é mais usado

@evento_bp.route('/login', methods=['POST'])
def login_participante():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não enviados'}), 400

        email = data.get('email', '').strip().lower()
        senha = data.get('senha', '')

        if not email or not senha:
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400

        participante = Participante.query.filter_by(email=email).first()
        if not participante or not participante.ativo:
            return jsonify({'error': 'Credenciais inválidas'}), 401

        if not participante.verificar_senha(senha):
            print(f"[WARN] Tentativa de login falhou para email: {email}")
            return jsonify({'error': 'Credenciais inválidas'}), 401

        # Criar sessão do participante
        session.clear()  # Limpar qualquer sessão anterior
        session['participante_id'] = participante.id
        session['participante_numero_ingresso'] = participante.numero_ingresso
        session['participante_nome'] = participante.nome
        session.permanent = True  # Usar configuração de tempo de sessão do app
        
        # Log de login bem-sucedido usando numero_ingresso
        print(f"[INFO] Login bem-sucedido: {participante.numero_ingresso} - {participante.email}")
        
        return jsonify({
            'message': 'Login realizado com sucesso',
            'participante': participante.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}", exc_info=True)
        raise

@evento_bp.route('/logout', methods=['POST'])
def logout_participante():
    """
    Endpoint de logout para participante.
    Limpa a sessão do servidor.
    """
    try:
        if 'participante_numero_ingresso' in session:
            numero_ingresso = session.get('participante_numero_ingresso')
            print(f"[INFO] Logout: {numero_ingresso}")
        
        session.clear()
        
        return jsonify({
            'message': 'Logout realizado com sucesso',
            'logged_out': True
        }), 200
    except Exception as e:
        logger.error(f"Erro no logout: {str(e)}", exc_info=True)
        session.clear()
        raise

@evento_bp.route('/ingresso/<string:numero_ingresso>', methods=['GET'])
@participante_required
def buscar_ingresso_autenticado(participante_atual, numero_ingresso):
    """
    Endpoint seguro para buscar ingresso com verificação de autorização.
    
    Args:
        participante_atual: Participante autenticado (injetado pelo decorator)
        numero_ingresso (str): Número do ingresso solicitado
    
    Returns:
        JSON com dados do ingresso
    
    Security:
        - Requer autenticação (sessão ativa)
        - Verifica se participante autenticado é dono do ingresso
        - IDs internos não são expostos
        - Logs seguros usando numero_ingresso
    
    Authorization:
        Apenas o dono do ingresso pode acessá-lo.
        Retorna 403 Forbidden se tentar acessar ingresso de outro participante.
    """
    try:
        # Validar formato do numero_ingresso
        if not numero_ingresso or len(numero_ingresso) < 3:
            return jsonify({'error': 'Número de ingresso inválido'}), 400
        
        # Normalizar para uppercase
        numero_ingresso = numero_ingresso.upper()
        
        # VERIFICAÇÃO DE AUTORIZAÇÃO:
        # Verificar se o numero_ingresso solicitado pertence ao participante autenticado
        if participante_atual.numero_ingresso != numero_ingresso:
            print(f"[WARN] Acesso negado: {participante_atual.numero_ingresso} tentou acessar {numero_ingresso}")
            return jsonify({
                'error': 'Acesso negado. Você só pode visualizar seu próprio ingresso.',
                'forbidden': True
            }), 403
        
        # Buscar ingresso (já sabemos que existe e pertence ao usuário)
        participante = Participante.query.filter_by(
            numero_ingresso=numero_ingresso,
            ativo=True
        ).first()
        
        if not participante:
            # Não deveria acontecer, mas por segurança
            logger.error(f"Inconsistência: ingresso {numero_ingresso} não encontrado após auth")
            return jsonify({'error': 'Ingresso não encontrado'}), 404
        
        # Log de acesso autorizado
        print(f"[INFO] Acesso autorizado ao ingresso: {participante.numero_ingresso} - {participante.nome}")
        
        return jsonify({
            'ingresso': participante.to_dict(),
            'authorized': True
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao buscar ingresso {numero_ingresso}: {str(e)}", exc_info=True)
        raise

@evento_bp.route('/meu-ingresso', methods=['GET'])
@participante_required
def buscar_meu_ingresso(participante_atual):
    """
    Endpoint para buscar o ingresso do participante autenticado.
    Retorna automaticamente o ingresso do participante logado.
    
    Args:
        participante_atual: Participante autenticado (injetado pelo decorator)
    
    Returns:
        JSON com dados do ingresso do participante autenticado
    
    Security:
        - Requer autenticação
        - Sempre retorna apenas o ingresso do usuário logado
        - Não permite acesso a ingressos de terceiros
    """
    try:
        print(f"[INFO] Acesso ao próprio ingresso: {participante_atual.numero_ingresso}")
        
        return jsonify({
            'ingresso': participante_atual.to_dict(),
            'authorized': True
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao buscar ingresso: {str(e)}", exc_info=True)
        raise
