"""
Modelo de Pagamento com Dados Criptografados

Este modelo armazena informações de pagamento de forma segura usando:
- Criptografia AES-256-GCM para dados sensíveis em repouso
- Chave de criptografia gerenciada separadamente
- Hash Argon2 para senhas
- Mascaramento de dados para exibição
"""

from src.models.db import db
from src.utils.encryption import encrypt_field, decrypt_field, mask_sensitive_data
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Pagamento(db.Model):
    """
    Modelo de Pagamento com campos criptografados.
    
    Campos criptografados:
    - numero_cartao_encrypted: Número do cartão de crédito
    - cvv_encrypted: Código de segurança
    - titular_encrypted: Nome do titular (se diferente do participante)
    - cpf_titular_encrypted: CPF do titular do cartão
    
    Campos em texto claro (não sensíveis):
    - participante_id: Referência ao participante
    - valor: Valor do pagamento
    - status: Status do pagamento (pendente, aprovado, recusado)
    - metodo_pagamento: Tipo de pagamento (credito, debito, pix)
    - data_pagamento: Timestamp do pagamento
    """
    
    __tablename__ = 'pagamento'
    
    id = db.Column(db.Integer, primary_key=True)
    participante_id = db.Column(db.Integer, db.ForeignKey('participante.id'), nullable=False)
    
    # Dados do pagamento (não sensíveis)
    valor = db.Column(db.Float, nullable=False)
    metodo_pagamento = db.Column(db.String(20), nullable=False)  # credito, debito, pix, boleto
    status = db.Column(db.String(20), default='pendente')  # pendente, aprovado, recusado, cancelado
    data_pagamento = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Dados do cartão - CRIPTOGRAFADOS em repouso
    numero_cartao_encrypted = db.Column(db.Text, nullable=True)  # Text para armazenar base64
    cvv_encrypted = db.Column(db.Text, nullable=True)
    validade_mes = db.Column(db.Integer, nullable=True)  # 1-12 (não sensível o suficiente para criptografar)
    validade_ano = db.Column(db.Integer, nullable=True)  # ex: 2025
    
    # Dados do titular - CRIPTOGRAFADOS
    titular_encrypted = db.Column(db.Text, nullable=True)
    cpf_titular_encrypted = db.Column(db.Text, nullable=True)
    
    # Metadata de auditoria
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    participante = db.relationship('Participante', backref='pagamentos')
    
    def __init__(self, participante_id, valor, metodo_pagamento, **kwargs):
        """
        Inicializa um novo pagamento.
        
        Args:
            participante_id (int): ID do participante
            valor (float): Valor do pagamento
            metodo_pagamento (str): Método de pagamento
            **kwargs: Dados do cartão (serão criptografados automaticamente)
                - numero_cartao (str)
                - cvv (str)
                - validade_mes (int)
                - validade_ano (int)
                - titular (str)
                - cpf_titular (str)
        """
        self.participante_id = participante_id
        self.valor = valor
        self.metodo_pagamento = metodo_pagamento
        self.status = 'pendente'
        
        # Criptografar dados sensíveis se fornecidos
        if 'numero_cartao' in kwargs:
            self.set_numero_cartao(kwargs['numero_cartao'])
        
        if 'cvv' in kwargs:
            self.set_cvv(kwargs['cvv'])
        
        if 'validade_mes' in kwargs:
            self.validade_mes = kwargs['validade_mes']
        
        if 'validade_ano' in kwargs:
            self.validade_ano = kwargs['validade_ano']
        
        if 'titular' in kwargs:
            self.set_titular(kwargs['titular'])
        
        if 'cpf_titular' in kwargs:
            self.set_cpf_titular(kwargs['cpf_titular'])
    
    # ==========================================
    # MÉTODOS DE CRIPTOGRAFIA/DESCRIPTOGRAFIA
    # ==========================================
    
    def set_numero_cartao(self, numero_cartao):
        """
        Criptografa e armazena o número do cartão.
        
        Args:
            numero_cartao (str): Número do cartão (sem formatação)
        """
        try:
            # Remover espaços e formatação
            numero_limpo = numero_cartao.replace(' ', '').replace('-', '')
            self.numero_cartao_encrypted = encrypt_field(numero_limpo)
            logger.info(f"Número de cartão criptografado para pagamento")
        except Exception as e:
            logger.error(f"Erro ao criptografar número do cartão: {str(e)}", exc_info=True)
            raise
    
    def get_numero_cartao(self):
        """
        Descriptografa e retorna o número do cartão.
        
        Returns:
            str: Número do cartão descriptografado
        
        Raises:
            ValueError: Se falhar ao descriptografar
        """
        if not self.numero_cartao_encrypted:
            return None
        
        try:
            return decrypt_field(self.numero_cartao_encrypted)
        except Exception as e:
            logger.error(f"Erro ao descriptografar número do cartão: {str(e)}", exc_info=True)
            raise ValueError("Falha ao descriptografar número do cartão")
    
    def get_numero_cartao_mascarado(self):
        """
        Retorna o número do cartão mascarado para exibição.
        
        Returns:
            str: Número mascarado (ex: ************1234)
        """
        try:
            numero = self.get_numero_cartao()
            return mask_sensitive_data(numero, visible_chars=4)
        except:
            return "****"
    
    def set_cvv(self, cvv):
        """
        Criptografa e armazena o CVV.
        
        Args:
            cvv (str): Código de segurança
        """
        try:
            self.cvv_encrypted = encrypt_field(cvv)
            logger.info(f"CVV criptografado para pagamento")
        except Exception as e:
            logger.error(f"Erro ao criptografar CVV: {str(e)}", exc_info=True)
            raise
    
    def get_cvv(self):
        """
        Descriptografa e retorna o CVV.
        
        ATENÇÃO: CVV NUNCA deve ser armazenado após processamento inicial.
        Este método existe apenas para validação durante o processamento.
        
        Returns:
            str: CVV descriptografado
        """
        if not self.cvv_encrypted:
            return None
        
        try:
            return decrypt_field(self.cvv_encrypted)
        except Exception as e:
            logger.error(f"Erro ao descriptografar CVV: {str(e)}", exc_info=True)
            raise ValueError("Falha ao descriptografar CVV")
    
    def set_titular(self, titular):
        """
        Criptografa e armazena o nome do titular.
        
        Args:
            titular (str): Nome do titular do cartão
        """
        try:
            self.titular_encrypted = encrypt_field(titular)
        except Exception as e:
            logger.error(f"Erro ao criptografar titular: {str(e)}", exc_info=True)
            raise
    
    def get_titular(self):
        """
        Descriptografa e retorna o nome do titular.
        
        Returns:
            str: Nome do titular
        """
        if not self.titular_encrypted:
            return None
        
        try:
            return decrypt_field(self.titular_encrypted)
        except Exception as e:
            logger.error(f"Erro ao descriptografar titular: {str(e)}", exc_info=True)
            raise ValueError("Falha ao descriptografar titular")
    
    def set_cpf_titular(self, cpf):
        """
        Criptografa e armazena o CPF do titular.
        
        Args:
            cpf (str): CPF do titular (sem formatação)
        """
        try:
            # Remover formatação
            cpf_limpo = cpf.replace('.', '').replace('-', '').replace(' ', '')
            self.cpf_titular_encrypted = encrypt_field(cpf_limpo)
        except Exception as e:
            logger.error(f"Erro ao criptografar CPF titular: {str(e)}", exc_info=True)
            raise
    
    def get_cpf_titular(self):
        """
        Descriptografa e retorna o CPF do titular.
        
        Returns:
            str: CPF do titular
        """
        if not self.cpf_titular_encrypted:
            return None
        
        try:
            return decrypt_field(self.cpf_titular_encrypted)
        except Exception as e:
            logger.error(f"Erro ao descriptografar CPF titular: {str(e)}", exc_info=True)
            raise ValueError("Falha ao descriptografar CPF titular")
    
    def get_cpf_titular_mascarado(self):
        """
        Retorna o CPF do titular mascarado.
        
        Returns:
            str: CPF mascarado (ex: ***.***.***-12)
        """
        try:
            cpf = self.get_cpf_titular()
            if not cpf:
                return None
            return f"***.***.***-{cpf[-2:]}"
        except:
            return "***.***.***-**"
    
    # ==========================================
    # MÉTODOS DE VALIDAÇÃO
    # ==========================================
    
    def validar_cartao(self):
        """
        Valida os dados do cartão (Algoritmo de Luhn).
        
        Returns:
            bool: True se o cartão é válido
        """
        try:
            numero = self.get_numero_cartao()
            if not numero or not numero.isdigit():
                return False
            
            # Algoritmo de Luhn
            def luhn_checksum(card_number):
                def digits_of(n):
                    return [int(d) for d in str(n)]
                
                digits = digits_of(card_number)
                odd_digits = digits[-1::-2]
                even_digits = digits[-2::-2]
                checksum = sum(odd_digits)
                for d in even_digits:
                    checksum += sum(digits_of(d * 2))
                return checksum % 10
            
            return luhn_checksum(numero) == 0
        except:
            return False
    
    # ==========================================
    # MÉTODOS DE AUDITORIA
    # ==========================================
    
    def aprovar(self):
        """Marca o pagamento como aprovado"""
        self.status = 'aprovado'
        self.atualizado_em = datetime.utcnow()
        logger.info(f"Pagamento {self.id} aprovado")
    
    def recusar(self):
        """Marca o pagamento como recusado"""
        self.status = 'recusado'
        self.atualizado_em = datetime.utcnow()
        logger.info(f"Pagamento {self.id} recusado")
    
    def cancelar(self):
        """Marca o pagamento como cancelado"""
        self.status = 'cancelado'
        self.atualizado_em = datetime.utcnow()
        logger.info(f"Pagamento {self.id} cancelado")
    
    # ==========================================
    # SERIALIZAÇÃO
    # ==========================================
    
    def to_dict(self, include_sensitive=False):
        """
        Converte o pagamento para dicionário.
        
        Args:
            include_sensitive (bool): Se True, inclui dados descriptografados
                                     (NUNCA usar para retornar ao frontend!)
        
        Returns:
            dict: Dados do pagamento
        """
        result = {
            'id': self.id,
            'participante_id': self.participante_id,
            'valor': self.valor,
            'metodo_pagamento': self.metodo_pagamento,
            'status': self.status,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }
        
        # Dados mascarados (seguros para frontend)
        if self.numero_cartao_encrypted:
            result['numero_cartao_mascarado'] = self.get_numero_cartao_mascarado()
        
        if self.validade_mes and self.validade_ano:
            result['validade'] = f"{self.validade_mes:02d}/{self.validade_ano}"
        
        if self.cpf_titular_encrypted:
            result['cpf_titular_mascarado'] = self.get_cpf_titular_mascarado()
        
        # Dados descriptografados (APENAS para processamento interno)
        if include_sensitive:
            try:
                if self.numero_cartao_encrypted:
                    result['_numero_cartao'] = self.get_numero_cartao()
                if self.titular_encrypted:
                    result['_titular'] = self.get_titular()
                if self.cpf_titular_encrypted:
                    result['_cpf_titular'] = self.get_cpf_titular()
            except Exception as e:
                logger.error(f"Erro ao descriptografar dados sensíveis: {str(e)}")
        
        return result
    
    def __repr__(self):
        return f'<Pagamento {self.id} - {self.metodo_pagamento} - R$ {self.valor} - {self.status}>'
