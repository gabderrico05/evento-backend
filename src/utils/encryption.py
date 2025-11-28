"""
Módulo de Criptografia AES-256 para Dados Sensíveis

Este módulo fornece funções para criptografar e descriptografar dados confidenciais
usando AES-256 no modo GCM (Galois/Counter Mode) que fornece:
- Confidencialidade (criptografia)
- Integridade (autenticação)
- Proteção contra ataques de replay

A chave de criptografia é gerenciada separadamente e NUNCA deve ser versionada.
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Gerenciador de criptografia AES-256-GCM
    
    Características:
    - AES-256 no modo GCM (authenticated encryption)
    - Chave derivada de ENCRYPTION_KEY usando PBKDF2
    - Nonce único para cada operação de criptografia
    - Proteção contra adulteração (AEAD)
    """
    
    def __init__(self, encryption_key=None):
        """
        Inicializa o gerenciador de criptografia.
        
        Args:
            encryption_key (str): Chave mestra de criptografia (deve vir de variável de ambiente)
        
        Raises:
            ValueError: Se encryption_key não for fornecida ou for fraca
        """
        if not encryption_key:
            encryption_key = os.getenv('ENCRYPTION_KEY')
        
        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY não configurada. "
                "Defina ENCRYPTION_KEY no arquivo .env com uma chave forte de 32+ caracteres"
            )
        
        if len(encryption_key) < 32:
            raise ValueError(
                "ENCRYPTION_KEY muito fraca. "
                "Use uma chave com pelo menos 32 caracteres aleatórios"
            )
        
        # Derivar chave de 256 bits (32 bytes) usando PBKDF2
        # Salt fixo (em produção real, considere salt único por ambiente)
        salt = b'evento_app_encryption_salt_v1'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=480000,  # OWASP recomenda 480k+ para PBKDF2-HMAC-SHA256
        )
        
        self.key = kdf.derive(encryption_key.encode('utf-8'))
        self.aesgcm = AESGCM(self.key)
        
        logger.info("Encryption manager initialized successfully")
    
    def encrypt(self, plaintext):
        """
        Criptografa um texto usando AES-256-GCM.
        
        Args:
            plaintext (str): Texto a ser criptografado
        
        Returns:
            str: Texto criptografado em base64 (formato: nonce + ciphertext)
        
        Raises:
            ValueError: Se plaintext for None ou vazio
            Exception: Em caso de erro de criptografia
        """
        if not plaintext:
            raise ValueError("Plaintext não pode ser vazio")
        
        try:
            # Gerar nonce aleatório único (96 bits = 12 bytes para GCM)
            nonce = secrets.token_bytes(12)
            
            # Criptografar
            ciphertext = self.aesgcm.encrypt(
                nonce,
                plaintext.encode('utf-8'),
                None  # AAD (Additional Authenticated Data) - pode ser usado para contexto adicional
            )
            
            # Combinar nonce + ciphertext e codificar em base64
            encrypted_data = nonce + ciphertext
            return base64.b64encode(encrypted_data).decode('utf-8')
        
        except Exception as e:
            logger.error(f"Erro ao criptografar dados: {str(e)}", exc_info=True)
            raise
    
    def decrypt(self, encrypted_text):
        """
        Descriptografa um texto criptografado com AES-256-GCM.
        
        Args:
            encrypted_text (str): Texto criptografado em base64
        
        Returns:
            str: Texto descriptografado
        
        Raises:
            ValueError: Se encrypted_text for None ou inválido
            Exception: Em caso de erro de descriptografia (dados corrompidos ou chave errada)
        """
        if not encrypted_text:
            raise ValueError("Encrypted text não pode ser vazio")
        
        try:
            # Decodificar de base64
            encrypted_data = base64.b64decode(encrypted_text)
            
            # Separar nonce (12 bytes) e ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            # Descriptografar
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Erro ao descriptografar dados: {str(e)}", exc_info=True)
            raise ValueError("Falha ao descriptografar dados. Dados corrompidos ou chave inválida.")
    
    @staticmethod
    def generate_encryption_key():
        """
        Gera uma chave de criptografia forte e aleatória.
        
        Returns:
            str: Chave de 64 caracteres hexadecimais (256 bits de entropia)
        
        Usage:
            >>> key = EncryptionManager.generate_encryption_key()
            >>> print(f"ENCRYPTION_KEY={key}")
        """
        return secrets.token_hex(32)  # 32 bytes = 256 bits


# Instância global do gerenciador de criptografia
# Será inicializada na primeira vez que for usada
_encryption_manager = None


def get_encryption_manager():
    """
    Retorna a instância global do gerenciador de criptografia.
    
    Returns:
        EncryptionManager: Instância do gerenciador
    
    Raises:
        ValueError: Se ENCRYPTION_KEY não estiver configurada
    """
    global _encryption_manager
    
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    
    return _encryption_manager


def encrypt_field(plaintext):
    """
    Função auxiliar para criptografar um campo.
    
    Args:
        plaintext (str): Texto a ser criptografado
    
    Returns:
        str: Texto criptografado
    """
    if not plaintext:
        return None
    
    manager = get_encryption_manager()
    return manager.encrypt(plaintext)


def decrypt_field(encrypted_text):
    """
    Função auxiliar para descriptografar um campo.
    
    Args:
        encrypted_text (str): Texto criptografado
    
    Returns:
        str: Texto descriptografado
    """
    if not encrypted_text:
        return None
    
    manager = get_encryption_manager()
    return manager.decrypt(encrypted_text)


def mask_sensitive_data(data, visible_chars=4):
    """
    Mascara dados sensíveis para exibição.
    
    Args:
        data (str): Dados a serem mascarados
        visible_chars (int): Número de caracteres visíveis no final
    
    Returns:
        str: Dados mascarados (ex: ************1234)
    """
    if not data:
        return None
    
    if len(data) <= visible_chars:
        return '*' * len(data)
    
    return '*' * (len(data) - visible_chars) + data[-visible_chars:]
