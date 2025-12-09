# Deployment Configuration Files

This directory contains all the configuration files needed for production deployment.

## Directory Structure

```
deployment/
├── nginx/
│   └── pms-backend.conf          # Nginx server configuration
├── systemd/
│   ├── pms-backend.service       # Django/Gunicorn service
│   └── celery-pms.service        # Celery worker service
└── gunicorn/
    └── gunicorn_config.py        # Gunicorn configuration
```

## Files Overview

### Nginx Configuration (`nginx/pms-backend.conf`)

- Configures reverse proxy to Gunicorn
- Handles SSL/TLS termination
- Serves static and media files
- Sets up security headers
- Configures timeouts and buffers

**Installation:**
```bash
sudo cp nginx/pms-backend.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/pms-backend.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Systemd Services

#### Django Service (`systemd/pms-backend.service`)

- Manages Django application via Gunicorn
- Auto-restart on failure
- Proper logging configuration
- Environment variable loading

**Installation:**
```bash
sudo cp systemd/pms-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pms-backend
sudo systemctl start pms-backend
```

#### Celery Service (`systemd/celery-pms.service`)

- Manages Celery workers for async tasks
- Handles periodic tasks (Celery Beat)
- Auto-restart on failure
- Proper PID and log management

**Installation:**
```bash
sudo cp systemd/celery-pms.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable celery-pms
sudo systemctl start celery-pms
```

### Gunicorn Configuration (`gunicorn/gunicorn_config.py`)

- Worker process configuration
- Socket binding configuration
- Logging setup
- Performance tuning
- Graceful restarts

**Usage:**
This file is referenced by the systemd service and doesn't need separate installation.

## Quick Start

1. **Copy all configuration files:**
   ```bash
   # From project root
   sudo cp deployment/nginx/pms-backend.conf /etc/nginx/sites-available/
   sudo cp deployment/systemd/*.service /etc/systemd/system/
   ```

2. **Enable Nginx site:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/pms-backend.conf /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

3. **Enable and start services:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable pms-backend celery-pms
   sudo systemctl start pms-backend celery-pms
   ```

4. **Verify everything is running:**
   ```bash
   sudo systemctl status pms-backend
   sudo systemctl status celery-pms
   sudo systemctl status nginx
   ```

## Configuration Variables

These files reference the following paths and values that you may need to adjust:

- **Project Path**: `/var/www/YEA/PMS/pms-backend`
- **Virtual Environment**: `/var/www/YEA/PMS/pms-backend/venv`
- **User/Group**: `deploy`
- **Socket File**: `/var/www/YEA/PMS/pms-backend/gunicorn.sock`
- **Log Directory**: `/var/log/pms-backend/` and `/var/log/celery-pms/`
- **Domain**: `api.yea-pms.gov.gh`

## Customization

If your setup differs from the defaults, edit the configuration files before copying them:

1. **Change project path**: Update all references to `/var/www/YEA/PMS/pms-backend`
2. **Change user**: Update `User=deploy` in systemd services
3. **Change domain**: Update `server_name` in Nginx config
4. **Adjust workers**: Modify `workers` count in Gunicorn config (typically 2-4 × CPU cores)

## Troubleshooting

### Service won't start
```bash
# Check service status and logs
sudo systemctl status pms-backend
sudo journalctl -u pms-backend -n 50

# Common issues:
# - Check file permissions
# - Verify .env.production exists
# - Confirm virtual environment is set up
# - Check database is running
```

### Nginx errors
```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Common issues:
# - Port already in use
# - SSL certificate paths incorrect
# - Upstream socket not found
```

### Socket connection errors
```bash
# Check socket exists and has correct permissions
ls -la /var/www/YEA/PMS/pms-backend/gunicorn.sock

# Should be owned by deploy:deploy or deploy:www-data
# Nginx user (www-data) must be able to access it
```

## See Also

- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [GITHUB_SECRETS.md](../GITHUB_SECRETS.md) - CI/CD setup guide
- [deploy.sh](../deploy.sh) - Deployment automation script
- [server-setup.sh](../server-setup.sh) - Initial server configuration script
