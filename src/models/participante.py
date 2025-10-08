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
    data_resgate = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)

    def __init__(self, nome, email, cpf, telefone, senha):
        self.nome = nome
        self.email = email
        self.cpf = cpf
        self.telefone = telefone
        self.set_senha(senha)
        self.numero_ingresso = self.gerar_numero_ingresso()

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

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'cpf': self.cpf,
            'cpfFormatado': self.format_cpf(),
            'telefone': self.format_telefone(),
            'numeroIngresso': self.numero_ingresso,
            'dataResgate': self.data_resgate.isoformat() if self.data_resgate else None,
            'ativo': self.ativo
        }

    def __repr__(self):
        return f'<Participante {self.nome} - {self.numero_ingresso}>'
