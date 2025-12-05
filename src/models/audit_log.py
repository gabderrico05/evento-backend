"""
Modelo de Auditoria para Logging Estruturado

Este módulo implementa um sistema de logging estruturado que registra
todos os eventos importantes do sistema, incluindo:
- Tentativas de login (sucesso e falha)
- Resgates de ingresso (sucesso e falha)
- Erros de validação
- Operações sensíveis

Cada log inclui:
- Timestamp exato (UTC)
- IP de origem
- User-Agent
- Tipo de evento
- Status (success/failure)
- Detalhes adicionais (JSON)
"""

from src.models.db import db
from datetime import datetime, timezone
from flask import request
import json


class AuditLog(db.Model):
    """Modelo para registro de auditoria estruturado"""
    
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Timestamp do evento (UTC)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Tipo de evento (login, ticket_redemption, validation_error, etc)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    
    # Status do evento (success, failure, error)
    status = db.Column(db.String(20), nullable=False, index=True)
    
    # Identificação do usuário/participante (pode ser email, username, CPF)
    user_identifier = db.Column(db.String(255), nullable=True, index=True)
    
    # ID do usuário (se aplicável)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    
    # IP de origem
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 pode ter até 45 caracteres
    
    # User-Agent
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Mensagem descritiva
    message = db.Column(db.String(500), nullable=False)
    
    # Detalhes adicionais em JSON (erros, stack traces, dados extras)
    details = db.Column(db.Text, nullable=True)
    
    # Severidade (info, warning, error, critical)
    severity = db.Column(db.String(20), nullable=False, default='info', index=True)
    
    # Endpoint/rota acessada
    endpoint = db.Column(db.String(255), nullable=True)
    
    # Método HTTP
    http_method = db.Column(db.String(10), nullable=True)
    
    def __init__(self, event_type, status, message, user_identifier=None, user_id=None,
                 ip_address=None, user_agent=None, details=None, severity='info',
                 endpoint=None, http_method=None):
        """
        Inicializa um registro de auditoria
        
        Args:
            event_type: Tipo do evento (login, ticket_redemption, validation_error)
            status: Status (success, failure, error)
            message: Mensagem descritiva
            user_identifier: Email, username ou CPF do usuário
            user_id: ID do usuário no banco
            ip_address: IP de origem (auto-detectado se None)
            user_agent: User-Agent (auto-detectado se None)
            details: Detalhes adicionais (dict ou string)
            severity: Severidade (info, warning, error, critical)
            endpoint: Endpoint/rota acessada (auto-detectado se None)
            http_method: Método HTTP (auto-detectado se None)
        """
        self.timestamp = datetime.now(timezone.utc)
        self.event_type = event_type
        self.status = status
        self.message = message
        self.user_identifier = user_identifier
        self.user_id = user_id
        self.severity = severity
        
        # Auto-detectar informações da requisição se não fornecidas
        if request:
            self.ip_address = ip_address or self._get_ip_address()
            self.user_agent = user_agent or request.headers.get('User-Agent', 'Unknown')
            self.endpoint = endpoint or request.endpoint
            self.http_method = http_method or request.method
        else:
            self.ip_address = ip_address
            self.user_agent = user_agent
            self.endpoint = endpoint
            self.http_method = http_method
        
        # Serializar detalhes se for dict
        if isinstance(details, dict):
            self.details = json.dumps(details, ensure_ascii=False)
        else:
            self.details = details
    
    def _get_ip_address(self):
        """Obtém o IP real do cliente, considerando proxies"""
        # Verificar headers de proxy (X-Forwarded-For, X-Real-IP)
        if request.headers.get('X-Forwarded-For'):
            # Pega o primeiro IP da lista (cliente original)
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr
    
    @staticmethod
    def log_event(event_type, status, message, **kwargs):
        """
        Método estático para registrar um evento de forma simplificada
        
        Args:
            event_type: Tipo do evento
            status: Status do evento
            message: Mensagem descritiva
            **kwargs: Argumentos adicionais (user_identifier, user_id, details, etc)
        
        Returns:
            AuditLog: Objeto criado (não commitado)
        
        Exemplo:
            AuditLog.log_event(
                event_type='login',
                status='success',
                message='Login bem-sucedido',
                user_identifier='usuario@email.com',
                user_id=123
            )
            db.session.commit()
        """
        log = AuditLog(
            event_type=event_type,
            status=status,
            message=message,
            **kwargs
        )
        db.session.add(log)
        return log
    
    @staticmethod
    def log_login_success(user_identifier, user_id=None, details=None):
        """Registra login bem-sucedido"""
        return AuditLog.log_event(
            event_type='login',
            status='success',
            message=f'Login bem-sucedido: {user_identifier}',
            user_identifier=user_identifier,
            user_id=user_id,
            details=details,
            severity='info'
        )
    
    @staticmethod
    def log_login_failure(user_identifier, reason, details=None):
        """Registra falha de login"""
        return AuditLog.log_event(
            event_type='login',
            status='failure',
            message=f'Falha de login: {user_identifier} - {reason}',
            user_identifier=user_identifier,
            details=details,
            severity='warning'
        )
    
    @staticmethod
    def log_ticket_redemption_success(user_identifier, ticket_number, user_id=None, details=None):
        """Registra resgate de ingresso bem-sucedido"""
        return AuditLog.log_event(
            event_type='ticket_redemption',
            status='success',
            message=f'Ingresso resgatado: {ticket_number} por {user_identifier}',
            user_identifier=user_identifier,
            user_id=user_id,
            details=details or {'ticket_number': ticket_number},
            severity='info'
        )
    
    @staticmethod
    def log_ticket_redemption_failure(user_identifier, ticket_number, reason, details=None):
        """Registra falha no resgate de ingresso"""
        return AuditLog.log_event(
            event_type='ticket_redemption',
            status='failure',
            message=f'Falha ao resgatar ingresso {ticket_number}: {reason}',
            user_identifier=user_identifier,
            details=details or {'ticket_number': ticket_number, 'reason': reason},
            severity='warning'
        )
    
    @staticmethod
    def log_validation_error(field, value, reason, user_identifier=None, details=None):
        """Registra erro de validação"""
        return AuditLog.log_event(
            event_type='validation_error',
            status='error',
            message=f'Erro de validação no campo {field}: {reason}',
            user_identifier=user_identifier,
            details=details or {'field': field, 'value': value, 'reason': reason},
            severity='warning'
        )
    
    @staticmethod
    def log_security_event(event_description, user_identifier=None, details=None, severity='warning'):
        """Registra evento de segurança"""
        return AuditLog.log_event(
            event_type='security',
            status='alert',
            message=event_description,
            user_identifier=user_identifier,
            details=details,
            severity=severity
        )
    
    @staticmethod
    def get_user_activity(user_identifier, limit=50):
        """
        Obtém histórico de atividades de um usuário
        
        Args:
            user_identifier: Email, username ou CPF
            limit: Número máximo de registros
        
        Returns:
            list: Lista de AuditLog ordenada por timestamp (mais recentes primeiro)
        """
        return AuditLog.query.filter_by(user_identifier=user_identifier)\
                            .order_by(AuditLog.timestamp.desc())\
                            .limit(limit)\
                            .all()
    
    @staticmethod
    def get_events_by_type(event_type, limit=100):
        """
        Obtém eventos de um tipo específico
        
        Args:
            event_type: Tipo do evento
            limit: Número máximo de registros
        
        Returns:
            list: Lista de AuditLog
        """
        return AuditLog.query.filter_by(event_type=event_type)\
                            .order_by(AuditLog.timestamp.desc())\
                            .limit(limit)\
                            .all()
    
    @staticmethod
    def get_failed_events(limit=100):
        """
        Obtém eventos com falha
        
        Args:
            limit: Número máximo de registros
        
        Returns:
            list: Lista de AuditLog com status=failure ou error
        """
        return AuditLog.query.filter(AuditLog.status.in_(['failure', 'error']))\
                            .order_by(AuditLog.timestamp.desc())\
                            .limit(limit)\
                            .all()
    
    @staticmethod
    def get_security_events(limit=100):
        """
        Obtém eventos de segurança
        
        Args:
            limit: Número máximo de registros
        
        Returns:
            list: Lista de AuditLog de eventos de segurança
        """
        return AuditLog.query.filter_by(event_type='security')\
                            .order_by(AuditLog.timestamp.desc())\
                            .limit(limit)\
                            .all()
    
    @staticmethod
    def cleanup_old_logs(days=90):
        """
        Remove logs antigos (retention policy)
        
        Args:
            days: Número de dias para manter os logs
        
        Returns:
            int: Número de registros removidos
        """
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        old_logs = AuditLog.query.filter(AuditLog.timestamp < cutoff_date).all()
        count = len(old_logs)
        
        for log in old_logs:
            db.session.delete(log)
        
        db.session.commit()
        return count
    
    def to_dict(self):
        """Converte o log para dicionário"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'status': self.status,
            'user_identifier': self.user_identifier,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'message': self.message,
            'details': json.loads(self.details) if self.details else None,
            'severity': self.severity,
            'endpoint': self.endpoint,
            'http_method': self.http_method
        }
    
    def __repr__(self):
        return f'<AuditLog {self.id}: {self.event_type} - {self.status} - {self.timestamp}>'
