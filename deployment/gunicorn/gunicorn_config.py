bind = "unix:/var/www/YEA/PMS/pms-backend/gunicorn.sock"
workers = 4
worker_class = "sync"
worker_tmp_dir = "/dev/shm"
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/log/pms-backend/access.log"
errorlog = "/var/log/pms-backend/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "pms-backend"

# Server mechanics
daemon = False
pidfile = "/var/run/pms-backend/gunicorn.pid"
user = "deploy"
group = "deploy"
umask = 0o007

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Gunicorn server")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn server")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Gunicorn server is ready. Spawning workers")

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info("Worker received SIGINT or SIGQUIT signal")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")
