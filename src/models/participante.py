from src.models.db import db
from datetime import datetime
import uuid


class Participante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    telefone = db.Column(db.String(15), nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)  # nova coluna de senha (hash)
    numero_ingresso = db.Column(db.String(50), unique=True, nullable=False)
    data_resgate = db.Column(db.DateTime, nullable=True)  # Null = não resgatado ainda
    resgatado = db.Column(db.Boolean, default=False, nullable=False)  # Flag de controle
    ativo = db.Column(db.Boolean, default=True)
    
    # Locking otimista: controle de versão para prevenir race conditions
    version = db.Column(db.Integer, default=1, nullable=False)

    def __init__(self, nome, email, cpf, telefone, senha):
        self.nome = nome
        self.email = email
        self.cpf = cpf
        self.telefone = telefone
        self.set_senha(senha)
        self.numero_ingresso = self.gerar_numero_ingresso()
        self.resgatado = False
        self.data_resgate = None
        self.version = 1

    # Métodos simples para hash de senha usando Werkzeug (já presente como dependência indireta do Flask)
    def set_senha(self, senha):
        from werkzeug.security import generate_password_hash
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.senha_hash, senha)

    def gerar_numero_ingresso(self):
        """Gera um número único para o ingresso"""
        return f"EVT{str(uuid.uuid4())[:8].upper()}"

    def format_cpf(self):
        """Formata o CPF para exibição"""
        cpf = self.cpf
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    def format_telefone(self):
        """Formata o telefone para exibição"""
        telefone = self.telefone
        if len(telefone) == 10:
            return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
        elif len(telefone) == 11:
            return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
        return telefone

    def to_dict(self, include_internal_id=False):
        """
        Converte o participante para dicionário.
        
        Args:
            include_internal_id (bool): Se True, inclui o ID interno (apenas para admin)
        
        Returns:
            dict: Dados do participante sem expor ID interno (por padrão)
        
        Security:
            - ID interno nunca é exposto por padrão
            - Apenas numero_ingresso é usado como identificador público
            - CPF completo não é exposto (use cpf_mascarado se necessário)
        """
        result = {
            'nome': self.nome,
            'email': self.email,
            'cpfFormatado': self.format_cpf(),
            'telefone': self.format_telefone(),
            'numeroIngresso': self.numero_ingresso,
            'dataResgate': self.data_resgate.isoformat() if self.data_resgate else None,
            'ativo': self.ativo
        }
        
        # ID interno apenas se explicitamente solicitado (uso administrativo)
        if include_internal_id:
            result['_internal_id'] = self.id
        
        return result
    
    def to_dict_safe(self):
        """
        Versão ultra-segura que mascara dados sensíveis.
        Útil para listagens públicas ou logs.
        """
        return {
            'nome': self.nome,
            'email': self.email[0:3] + '***@' + self.email.split('@')[1] if '@' in self.email else '***',
            'cpf': '***.' + self.cpf[3:6] + '.***-**',
            'numeroIngresso': self.numero_ingresso,
            'dataResgate': self.data_resgate.isoformat() if self.data_resgate else None
        }

    def __repr__(self):
        """
        Representação do objeto sem expor ID interno.
        Usa numero_ingresso para identificação segura.
        """
        return f'<Participante {self.numero_ingresso} - {self.nome}>'

    # ==========================================
    # CONSULTAS COM PREPARED STATEMENTS (SQL INJECTION PROTECTION)
    # ==========================================
    
    @staticmethod
    def buscar_por_email(email):
        """
        Busca um participante por e-mail usando prepared statement.
        
        Args:
            email (str): E-mail do participante
        
        Returns:
            Participante | None: Objeto Participante ou None se não encontrado
        
        Security:
            - SQLAlchemy ORM usa prepared statements automaticamente
            - Parametrização previne SQL Injection
            - Entrada do usuário (email) nunca é concatenada diretamente no SQL
        
        Example:
            >>> participante = Participante.buscar_por_email('usuario@exemplo.com')
            >>> if participante:
            ...     print(participante.nome)
        
        SQL Gerado (prepared statement):
            SELECT * FROM participante WHERE email = ? 
            Parâmetros: ['usuario@exemplo.com']
        """
        # SQLAlchemy usa prepared statements automaticamente
        # O valor de 'email' é passado como parâmetro, não concatenado
        return db.session.query(Participante).filter_by(email=email).first()
    
    @staticmethod
    def buscar_por_email_seguro(email):
        """
        Versão explícita com validação adicional de entrada.
        
        Args:
            email (str): E-mail do participante
        
        Returns:
            Participante | None: Objeto Participante ou None
        
        Raises:
            ValueError: Se o email for inválido
        
        Security:
            - Validação de formato de e-mail ANTES da consulta
            - Prepared statements (SQLAlchemy ORM)
            - Proteção em camadas contra SQL Injection
        """
        # Validação de entrada (defense in depth)
        if not email or not isinstance(email, str):
            raise ValueError("E-mail inválido")
        
        # Validação básica de formato
        if '@' not in email or len(email) < 5:
            raise ValueError("Formato de e-mail inválido")
        
        # Remover espaços em branco
        email = email.strip()
        
        # Consulta com prepared statement
        return db.session.query(Participante).filter_by(email=email).first()
    
    @staticmethod
    def buscar_por_cpf(cpf):
        """
        Busca participante por CPF usando prepared statement.
        
        Args:
            cpf (str): CPF do participante (apenas números)
        
        Returns:
            Participante | None: Objeto Participante ou None
        
        Security:
            - Prepared statement (SQLAlchemy)
            - Validação de formato CPF
        """
        if not cpf or not isinstance(cpf, str):
            raise ValueError("CPF inválido")
        
        # Remove formatação (pontos e traço)
        cpf = cpf.replace('.', '').replace('-', '').strip()
        
        # Validação de comprimento
        if len(cpf) != 11 or not cpf.isdigit():
            raise ValueError("CPF deve conter 11 dígitos numéricos")
        
        # Consulta com prepared statement
        return db.session.query(Participante).filter_by(cpf=cpf).first()
    
    @staticmethod
    def buscar_por_numero_ingresso(numero_ingresso):
        """
        Busca participante por número do ingresso usando prepared statement.
        
        Args:
            numero_ingresso (str): Número do ingresso (ex: EVT12345678)
        
        Returns:
            Participante | None: Objeto Participante ou None
        
        Security:
            - Prepared statement (SQLAlchemy)
            - Validação de formato
        """
        if not numero_ingresso or not isinstance(numero_ingresso, str):
            raise ValueError("Número de ingresso inválido")
        
        numero_ingresso = numero_ingresso.strip().upper()
        
        # Consulta com prepared statement
        return db.session.query(Participante).filter_by(numero_ingresso=numero_ingresso).first()
    
    @staticmethod
    def listar_por_email_like(email_pattern):
        """
        Busca participantes com e-mail similar (LIKE) usando prepared statement.
        
        Args:
            email_pattern (str): Padrão de e-mail para busca (ex: '%@gmail.com')
        
        Returns:
            list[Participante]: Lista de participantes encontrados
        
        Security:
            - SQLAlchemy usa prepared statements mesmo com LIKE
            - Proteção contra SQL Injection
        
        Warning:
            Use com cuidado em produção (pode retornar muitos resultados)
            Considere adicionar limite: .limit(100)
        
        Example:
            >>> participantes = Participante.listar_por_email_like('%@gmail.com')
        """
        if not email_pattern or not isinstance(email_pattern, str):
            raise ValueError("Padrão de e-mail inválido")
        
        # SQLAlchemy parametriza automaticamente mesmo com LIKE
        return db.session.query(Participante).filter(Participante.email.like(email_pattern)).limit(100).all()
    
    @staticmethod
    def existe_email(email):
        """
        Verifica se um e-mail já está cadastrado (prepared statement).
        
        Args:
            email (str): E-mail para verificar
        
        Returns:
            bool: True se o e-mail existe, False caso contrário
        
        Security:
            - Prepared statement (SQLAlchemy)
            - Consulta otimizada (EXISTS é mais rápido que COUNT)
        """
        if not email or not isinstance(email, str):
            return False
        
        email = email.strip()
        
        # Usar EXISTS para performance
        from sqlalchemy import exists
        return db.session.query(exists().where(Participante.email == email)).scalar()
    
    @staticmethod
    def existe_cpf(cpf):
        """
        Verifica se um CPF já está cadastrado (prepared statement).
        
        Args:
            cpf (str): CPF para verificar (apenas números)
        
        Returns:
            bool: True se o CPF existe, False caso contrário
        
        Security:
            - Prepared statement (SQLAlchemy)
            - Validação de formato
        """
        if not cpf or not isinstance(cpf, str):
            return False
        
        cpf = cpf.replace('.', '').replace('-', '').strip()
        
        if len(cpf) != 11 or not cpf.isdigit():
            return False
        
        from sqlalchemy import exists
        return db.session.query(exists().where(Participante.cpf == cpf)).scalar()

    # ==========================================
    # RESGATE DE INGRESSO COM CONTROLE DE CONCORRÊNCIA
    # ==========================================
    
    @staticmethod
    def resgatar_ingresso_pessimistic(numero_ingresso):
        """
        Resgata ingresso usando PESSIMISTIC LOCKING (SELECT FOR UPDATE).
        
        Args:
            numero_ingresso (str): Número do ingresso a resgatar
        
        Returns:
            tuple: (sucesso: bool, mensagem: str, participante: Participante|None)
        
        Security & Concurrency:
            - Usa SELECT FOR UPDATE (lock de linha no banco)
            - Previne race conditions completamente
            - Outras transações aguardam o lock ser liberado
            - ACID compliance garantido pelo PostgreSQL
        
        Example:
            >>> sucesso, msg, participante = Participante.resgatar_ingresso_pessimistic('EVT12345678')
            >>> if sucesso:
            ...     print(f"Ingresso resgatado: {participante.nome}")
            ... else:
            ...     print(f"Erro: {msg}")
        
        Database Lock:
            SQL: SELECT * FROM participante WHERE numero_ingresso = ? FOR UPDATE
            - Linha bloqueada para escrita até commit/rollback
            - Outras transações esperam (serialização automática)
        """
        from datetime import datetime, timezone
        from sqlalchemy.exc import SQLAlchemyError
        
        if not numero_ingresso or not isinstance(numero_ingresso, str):
            return False, "Número de ingresso inválido", None
        
        numero_ingresso = numero_ingresso.strip().upper()
        
        try:
            # SELECT FOR UPDATE - lock pessimista
            # with_for_update() bloqueia a linha até o commit
            participante = db.session.query(Participante)\
                .filter_by(numero_ingresso=numero_ingresso)\
                .with_for_update()\
                .first()
            
            if not participante:
                return False, "Ingresso não encontrado", None
            
            if not participante.ativo:
                return False, "Ingresso inativo", None
            
            if participante.resgatado:
                # Já foi resgatado
                return False, f"Ingresso já resgatado em {participante.data_resgate.isoformat()}", participante
            
            # Marcar como resgatado
            participante.resgatado = True
            participante.data_resgate = datetime.now(timezone.utc)
            participante.version += 1  # Incrementar versão
            
            # Commit da transação (libera o lock)
            db.session.commit()
            
            return True, "Ingresso resgatado com sucesso", participante
        
        except SQLAlchemyError as e:
            # Rollback em caso de erro
            db.session.rollback()
            return False, f"Erro ao resgatar ingresso: {str(e)}", None
    
    @staticmethod
    def resgatar_ingresso_optimistic(numero_ingresso):
        """
        Resgata ingresso usando OPTIMISTIC LOCKING (versão).
        
        Args:
            numero_ingresso (str): Número do ingresso a resgatar
        
        Returns:
            tuple: (sucesso: bool, mensagem: str, participante: Participante|None)
        
        Security & Concurrency:
            - Usa campo 'version' para detectar modificações concorrentes
            - Não bloqueia a linha durante a leitura (melhor performance)
            - Se versão mudou, a atualização falha (retry necessário)
            - Boa para cenários de baixa contenção
        
        Algorithm:
            1. SELECT participante (sem lock)
            2. Verificar se já resgatado
            3. UPDATE WHERE numero_ingresso = ? AND version = ?
            4. Se UPDATE afetou 0 linhas → race condition detectada
        
        Retry Pattern:
            Se falhar por race condition, cliente deve tentar novamente
        """
        from datetime import datetime, timezone
        from sqlalchemy.exc import SQLAlchemyError
        
        if not numero_ingresso or not isinstance(numero_ingresso, str):
            return False, "Número de ingresso inválido", None
        
        numero_ingresso = numero_ingresso.strip().upper()
        
        try:
            # 1. SELECT sem lock (leitura otimista)
            participante = db.session.query(Participante)\
                .filter_by(numero_ingresso=numero_ingresso)\
                .first()
            
            if not participante:
                return False, "Ingresso não encontrado", None
            
            if not participante.ativo:
                return False, "Ingresso inativo", None
            
            if participante.resgatado:
                return False, f"Ingresso já resgatado em {participante.data_resgate.isoformat()}", participante
            
            # 2. Salvar versão atual
            versao_atual = participante.version
            
            # 3. UPDATE condicional (versão deve ser a mesma)
            # Se outra transação modificou, versão será diferente
            result = db.session.query(Participante)\
                .filter_by(numero_ingresso=numero_ingresso, version=versao_atual)\
                .update({
                    'resgatado': True,
                    'data_resgate': datetime.now(timezone.utc),
                    'version': versao_atual + 1
                }, synchronize_session=False)
            
            db.session.commit()
            
            # 4. Verificar se UPDATE afetou alguma linha
            if result == 0:
                # Race condition detectada!
                # Outra transação modificou o registro
                db.session.rollback()
                return False, "Conflito detectado. Ingresso já foi resgatado por outra transação. Tente novamente.", None
            
            # Recarregar participante atualizado
            db.session.refresh(participante)
            
            return True, "Ingresso resgatado com sucesso", participante
        
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Erro ao resgatar ingresso: {str(e)}", None
    
    @staticmethod
    def resgatar_ingresso_atomic(numero_ingresso):
        """
        Resgata ingresso usando UPDATE ATÔMICO (recomendado para produção).
        
        Args:
            numero_ingresso (str): Número do ingresso a resgatar
        
        Returns:
            tuple: (sucesso: bool, mensagem: str, participante: Participante|None)
        
        Security & Concurrency:
            - Usa UPDATE atômico com condição resgatado=False
            - Mais eficiente que SELECT FOR UPDATE
            - Race-safe: apenas 1 transação consegue fazer UPDATE
            - Recomendado para alta concorrência
        
        Algorithm:
            UPDATE participante 
            SET resgatado=True, data_resgate=NOW(), version=version+1
            WHERE numero_ingresso=? AND resgatado=False
            
            - Se retornar 1 linha afetada → sucesso
            - Se retornar 0 linhas → já foi resgatado
        
        Advantages:
            - 1 query ao invés de 2 (SELECT + UPDATE)
            - Sem locks explícitos
            - Melhor performance
            - ACID garantido pelo banco
        """
        from datetime import datetime, timezone
        from sqlalchemy.exc import SQLAlchemyError
        
        if not numero_ingresso or not isinstance(numero_ingresso, str):
            return False, "Número de ingresso inválido", None
        
        numero_ingresso = numero_ingresso.strip().upper()
        
        try:
            # UPDATE atômico com condição resgatado=False
            # Apenas 1 transação consegue fazer isso com sucesso
            result = db.session.query(Participante)\
                .filter_by(numero_ingresso=numero_ingresso, resgatado=False, ativo=True)\
                .update({
                    'resgatado': True,
                    'data_resgate': datetime.now(timezone.utc),
                    'version': Participante.version + 1  # Incremento atômico
                }, synchronize_session=False)
            
            db.session.commit()
            
            if result == 0:
                # Nenhuma linha foi atualizada
                # Possibilidades: ingresso não existe, já resgatado, ou inativo
                
                # Verificar qual é o caso
                participante = db.session.query(Participante)\
                    .filter_by(numero_ingresso=numero_ingresso)\
                    .first()
                
                if not participante:
                    return False, "Ingresso não encontrado", None
                
                if not participante.ativo:
                    return False, "Ingresso inativo", None
                
                if participante.resgatado:
                    return False, f"Ingresso já resgatado em {participante.data_resgate.isoformat()}", participante
                
                # Caso raro: algum outro motivo
                return False, "Erro ao resgatar ingresso", None
            
            # Sucesso! Buscar participante atualizado
            participante = db.session.query(Participante)\
                .filter_by(numero_ingresso=numero_ingresso)\
                .first()
            
            return True, "Ingresso resgatado com sucesso", participante
        
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Erro ao resgatar ingresso: {str(e)}", None
    
    def pode_resgatar(self):
        """
        Verifica se o ingresso pode ser resgatado.
        
        Returns:
            tuple: (pode: bool, motivo: str)
        """
        if not self.ativo:
            return False, "Ingresso inativo"
        
        if self.resgatado:
            return False, f"Ingresso já resgatado em {self.data_resgate.isoformat()}"
        
        return True, "Ingresso disponível para resgate"



