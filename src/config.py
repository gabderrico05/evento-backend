"""
Configuração centralizada da aplicação Flask

Este módulo gerencia todas as configurações da aplicação, incluindo:
- Banco de dados com permissões restritas
- Sessões
- Segurança
- Variáveis de ambiente
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()


class Config:
    """Configuração base da aplicação"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')  # MUDAR EM PRODUÇÃO
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = False  # Sobrescrito por subclasses
    
    # Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)  # Tempo de inatividade
    SESSION_MAX_LIFETIME = timedelta(minutes=60)  # Tempo máximo de vida
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'  # True em produção (HTTPS)
    SESSION_COOKIE_HTTPONLY = True  # Previne XSS
    SESSION_COOKIE_SAMESITE = 'Lax'  # Proteção CSRF
    SESSION_COOKIE_NAME = 'evento_session'
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_FILE_DIR = os.getenv('SESSION_FILE_DIR', '.flask_session')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG  # Log queries em desenvolvimento
    
    @staticmethod
    def get_database_uri():
        """
        Retorna URI do banco de dados baseado em variáveis de ambiente.
        
        Suporta:
        - SQLite (desenvolvimento)
        - PostgreSQL (produção - RECOMENDADO)
        - MySQL (produção - alternativa)
        
        Segurança:
        - Credenciais vem de variáveis de ambiente
        - Usuário deve ter APENAS permissões SELECT, INSERT, UPDATE
        - SEM permissões de DROP, DELETE, CREATE, ALTER
        """
        DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')
        
        if DATABASE_TYPE == 'postgresql':
            # PostgreSQL - Produção RECOMENDADO
            DB_USER = os.getenv('DB_USER', 'evento_app_user')
            DB_PASSWORD = os.getenv('DB_PASSWORD')
            DB_HOST = os.getenv('DB_HOST', 'localhost')
            DB_PORT = os.getenv('DB_PORT', '5432')
            DB_NAME = os.getenv('DB_NAME', 'evento_db')
            
            if not DB_PASSWORD:
                raise ValueError("DB_PASSWORD não configurada para PostgreSQL")
            
            # Opcional: SSL para conexões seguras
            ssl_mode = os.getenv('DB_SSL_MODE', '')
            ssl_param = f'?sslmode={ssl_mode}' if ssl_mode else ''
            
            return f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}{ssl_param}'
        
        elif DATABASE_TYPE == 'mysql':
            # MySQL - Produção alternativa
            DB_USER = os.getenv('DB_USER', 'evento_app_user')
            DB_PASSWORD = os.getenv('DB_PASSWORD')
            DB_HOST = os.getenv('DB_HOST', 'localhost')
            DB_PORT = os.getenv('DB_PORT', '3306')
            DB_NAME = os.getenv('DB_NAME', 'evento_db')
            
            if not DB_PASSWORD:
                raise ValueError("DB_PASSWORD não configurada para MySQL")
            
            # Opcional: SSL para conexões seguras
            ssl_ca = os.getenv('DB_SSL_CA', '')
            ssl_param = f'?ssl_ca={ssl_ca}' if ssl_ca else ''
            
            return f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}{ssl_param}'
        
        else:
            # SQLite - Apenas desenvolvimento/testes
            # ATENÇÃO: SQLite não possui controle granular de permissões
            # NÃO usar em produção
            if FLASK_ENV == 'production':
                print("[WARNING] SQLite não é recomendado para produção. Use PostgreSQL ou MySQL.")
            
            SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'src/database/app.db')
            
            # Garantir que o diretório existe
            db_dir = os.path.dirname(SQLITE_DB_PATH)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            return f'sqlite:///{SQLITE_DB_PATH}'
    
    @classmethod
    def init_app(cls, app):
        """
        Inicializa configurações na aplicação Flask
        
        Args:
            app: Instância do Flask
        """
        # Configurar URI do banco
        app.config['SQLALCHEMY_DATABASE_URI'] = cls.get_database_uri()
        
        # Aplicar demais configurações
        for key, value in cls.__dict__.items():
            if not key.startswith('_') and key.isupper():
                app.config[key] = value
        
        # Log de configuração (sem expor senhas)
        db_type = os.getenv('DATABASE_TYPE', 'sqlite')
        db_user = os.getenv('DB_USER', 'N/A')
        
        print(f"[CONFIG] Database: {db_type}")
        print(f"[CONFIG] User: {db_user}")
        print(f"[CONFIG] Environment: {cls.FLASK_ENV}")
        print(f"[CONFIG] Debug: {cls.DEBUG}")
        
        if db_type == 'sqlite' and cls.FLASK_ENV == 'production':
            print("[WARNING] ⚠️  SQLite em produção NÃO é recomendado!")
            print("[WARNING] ⚠️  Use PostgreSQL ou MySQL para produção")
        
        # Verificar permissões do usuário (apenas em desenvolvimento)
        if cls.DEBUG and db_type in ['postgresql', 'mysql']:
            print(f"[INFO] ✅ Usuário '{db_user}' deve ter APENAS permissões SELECT, INSERT, UPDATE")
            print(f"[INFO] ✅ Sem permissões de DROP, DELETE, CREATE, ALTER")


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # HTTPS obrigatório
    
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        
        # Validações extras para produção
        if not os.getenv('SECRET_KEY') or os.getenv('SECRET_KEY') == 'asdf#FGSgvasgf$5$WGT':
            raise ValueError("⚠️  SECRET_KEY padrão não pode ser usada em produção!")
        
        db_type = os.getenv('DATABASE_TYPE', 'sqlite')
        if db_type == 'sqlite':
            raise ValueError("⚠️  SQLite não pode ser usado em produção! Use PostgreSQL ou MySQL.")
        
        if not os.getenv('DB_PASSWORD'):
            raise ValueError("⚠️  DB_PASSWORD é obrigatória em produção!")


class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Banco em memória para testes
    WTF_CSRF_ENABLED = False


# Dicionário de configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """
    Retorna a configuração apropriada baseada em FLASK_ENV
    
    Returns:
        Config: Classe de configuração
    """
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
