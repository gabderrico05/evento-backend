"""
Modelo para controle de tentativas de login e prevenção de ataques de força bruta.

Este módulo implementa:
- Rastreamento de tentativas de login inválidas
- Bloqueio temporário após múltiplas tentativas falhas
- Rate limiting por e-mail
- Limpeza automática de registros antigos
"""

from src.models.db import db
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


class LoginAttempt(db.Model):
    """
    Modelo para rastrear tentativas de login e implementar rate limiting.
    
    Regras de bloqueio:
    - Após 5 tentativas inválidas em 5 minutos → bloqueia por 30 minutos
    - Após bloqueio expirar, contador é resetado
    - Login bem-sucedido reseta o contador
    """
    __tablename__ = 'login_attempt'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    attempt_time = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    success = db.Column(db.Boolean, nullable=False, default=False)
    ip_address = db.Column(db.String(45), nullable=True)  # Suporta IPv6
    user_agent = db.Column(db.String(255), nullable=True)
    blocked_until = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    
    # Configurações de rate limiting
    MAX_ATTEMPTS = 5
    ATTEMPT_WINDOW_MINUTES = 5
    BLOCK_DURATION_MINUTES = 30
    
    def __repr__(self):
        return f'<LoginAttempt {self.email} at {self.attempt_time}>'
    
    @staticmethod
    def register_attempt(email: str, success: bool, ip_address: str = None, user_agent: str = None) -> tuple[bool, str, int]:
        """
        Registra uma tentativa de login e verifica se o e-mail está bloqueado.
        
        Args:
            email: E-mail da tentativa de login
            success: Se o login foi bem-sucedido
            ip_address: IP do cliente (opcional)
            user_agent: User-Agent do navegador (opcional)
        
        Returns:
            tuple: (is_blocked, message, remaining_attempts)
                - is_blocked: True se o e-mail está bloqueado
                - message: Mensagem descritiva
                - remaining_attempts: Tentativas restantes (0 se bloqueado)
        """
        try:
            email = email.lower().strip()
            now = datetime.now(timezone.utc)
            
            # 1. Verificar se já está bloqueado
            is_blocked, block_info = LoginAttempt.is_blocked(email)
            if is_blocked:
                # Registrar tentativa durante bloqueio
                attempt = LoginAttempt(
                    email=email,
                    attempt_time=now,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    blocked_until=block_info['blocked_until']
                )
                db.session.add(attempt)
                db.session.commit()
                
                return (
                    True,
                    f"Conta bloqueada temporariamente até {block_info['blocked_until'].strftime('%H:%M:%S')} devido a múltiplas tentativas inválidas",
                    0
                )
            
            # 2. Se login bem-sucedido, resetar contador
            if success:
                attempt = LoginAttempt(
                    email=email,
                    attempt_time=now,
                    success=True,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                db.session.add(attempt)
                db.session.commit()
                
                logger.info(f"Login bem-sucedido para {email}")
                return (False, "Login bem-sucedido", LoginAttempt.MAX_ATTEMPTS)
            
            # 3. Login inválido - contar tentativas recentes
            window_start = now - timedelta(minutes=LoginAttempt.ATTEMPT_WINDOW_MINUTES)
            
            recent_failures = db.session.query(LoginAttempt).filter(
                LoginAttempt.email == email,
                LoginAttempt.success == False,
                LoginAttempt.attempt_time >= window_start
            ).count()
            
            # 4. Registrar tentativa falha
            attempt = LoginAttempt(
                email=email,
                attempt_time=now,
                success=False,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(attempt)
            
            # 5. Verificar se atingiu o limite
            if recent_failures + 1 >= LoginAttempt.MAX_ATTEMPTS:
                # BLOQUEAR por 30 minutos
                blocked_until = now + timedelta(minutes=LoginAttempt.BLOCK_DURATION_MINUTES)
                attempt.blocked_until = blocked_until
                
                db.session.commit()
                
                logger.warning(
                    f"E-mail {email} bloqueado até {blocked_until.strftime('%H:%M:%S')} "
                    f"após {recent_failures + 1} tentativas inválidas"
                )
                
                return (
                    True,
                    f"Conta bloqueada temporariamente até {blocked_until.strftime('%H:%M:%S')} "
                    f"devido a {recent_failures + 1} tentativas inválidas. Tente novamente mais tarde.",
                    0
                )
            
            db.session.commit()
            
            remaining = LoginAttempt.MAX_ATTEMPTS - (recent_failures + 1)
            logger.info(f"Tentativa inválida para {email}. Restam {remaining} tentativas")
            
            return (
                False,
                f"E-mail ou senha inválidos. Você tem {remaining} tentativa(s) restante(s) antes do bloqueio temporário.",
                remaining
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar tentativa de login: {str(e)}")
            return (False, "Erro ao processar login", LoginAttempt.MAX_ATTEMPTS)
    
    @staticmethod
    def is_blocked(email: str) -> tuple[bool, dict]:
        """
        Verifica se um e-mail está bloqueado.
        
        Args:
            email: E-mail a verificar
        
        Returns:
            tuple: (is_blocked, block_info)
                - is_blocked: True se bloqueado
                - block_info: {'blocked_until': datetime, 'remaining_seconds': int}
        """
        try:
            email = email.lower().strip()
            now = datetime.now(timezone.utc)
            
            # Buscar bloqueio ativo mais recente
            active_block = db.session.query(LoginAttempt).filter(
                LoginAttempt.email == email,
                LoginAttempt.blocked_until != None,
                LoginAttempt.blocked_until > now
            ).order_by(LoginAttempt.blocked_until.desc()).first()
            
            if active_block:
                remaining_seconds = int((active_block.blocked_until - now).total_seconds())
                return (True, {
                    'blocked_until': active_block.blocked_until,
                    'remaining_seconds': remaining_seconds,
                    'remaining_minutes': remaining_seconds // 60
                })
            
            return (False, {})
            
        except Exception as e:
            logger.error(f"Erro ao verificar bloqueio: {str(e)}")
            return (False, {})
    
    @staticmethod
    def get_recent_attempts(email: str, minutes: int = 5) -> int:
        """
        Retorna o número de tentativas falhas recentes.
        
        Args:
            email: E-mail a verificar
            minutes: Janela de tempo em minutos
        
        Returns:
            int: Número de tentativas falhas na janela de tempo
        """
        try:
            email = email.lower().strip()
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(minutes=minutes)
            
            count = db.session.query(LoginAttempt).filter(
                LoginAttempt.email == email,
                LoginAttempt.success == False,
                LoginAttempt.attempt_time >= window_start
            ).count()
            
            return count
            
        except Exception as e:
            logger.error(f"Erro ao contar tentativas: {str(e)}")
            return 0
    
    @staticmethod
    def cleanup_old_attempts(days: int = 30) -> int:
        """
        Remove tentativas de login antigas do banco de dados.
        
        Args:
            days: Remover tentativas mais antigas que X dias
        
        Returns:
            int: Número de registros removidos
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            deleted = db.session.query(LoginAttempt).filter(
                LoginAttempt.attempt_time < cutoff_date
            ).delete()
            
            db.session.commit()
            
            if deleted > 0:
                logger.info(f"Limpeza: {deleted} tentativas de login antigas removidas")
            
            return deleted
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao limpar tentativas antigas: {str(e)}")
            return 0
    
    @staticmethod
    def reset_attempts(email: str) -> bool:
        """
        Reseta todas as tentativas de login para um e-mail (apenas para testes/admin).
        
        Args:
            email: E-mail a resetar
        
        Returns:
            bool: True se resetado com sucesso
        """
        try:
            email = email.lower().strip()
            
            deleted = db.session.query(LoginAttempt).filter(
                LoginAttempt.email == email
            ).delete()
            
            db.session.commit()
            
            logger.info(f"Resetadas {deleted} tentativas para {email}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao resetar tentativas: {str(e)}")
            return False
