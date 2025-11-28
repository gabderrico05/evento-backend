# Gunicorn Configuration File
# Para rodar: gunicorn -c gunicorn_config.py src.main:app

import os
import multiprocessing

# Bind - endereço e porta onde o Gunicorn vai escutar
# Em produção, geralmente escuta em localhost e o Nginx faz proxy reverso
bind = "127.0.0.1:8000"

# Workers
# Recomendação: (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class
# sync: padrão, bloqueante
# gevent/eventlet: assíncrono, melhor para I/O
worker_class = "sync"

# Threads por worker (para worker_class sync)
threads = 2

# Timeout para requests (segundos)
timeout = 30

# Keep-alive
keepalive = 2

# Logging
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# Reload automático em mudanças de código (APENAS em desenvolvimento)
reload = os.getenv('FLASK_ENV') == 'development'

# Preload app (carrega app antes de fork workers - economiza memória)
preload_app = True

# Max requests por worker antes de restart (previne memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Security Headers via Gunicorn
def post_fork(server, worker):
    """Executado após fork de cada worker"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_fork(server, worker):
    """Executado antes de fork de cada worker"""
    pass

def when_ready(server):
    """Executado quando servidor está pronto"""
    server.log.info("Gunicorn server is ready. Spawning workers")

def on_exit(server):
    """Executado ao desligar servidor"""
    server.log.info("Shutting down Gunicorn")

# Process naming
proc_name = "evento_flask_app"

# Daemon mode (rodar em background)
# False para systemd/supervisor gerenciar
daemon = False

# PID file
pidfile = "logs/gunicorn.pid"

# User/Group (rodar como usuário não-root em produção)
# user = "www-data"
# group = "www-data"

# Umask
umask = 0o007

# Environment variables
raw_env = [
    f"FLASK_ENV=production",
]
