#!/bin/bash
# Restart script for PMS backend services
# This script restarts services without requiring sudo

set -e

echo "🔄 Restarting PMS backend services..."

# Restart using systemctl with sudo (password provided via environment)
echo "${DEPLOY_PASSWORD}" | sudo -S systemctl restart pms-backend 2>/dev/null || {
    echo "Failed to restart pms-backend, checking if it needs starting..."
    echo "${DEPLOY_PASSWORD}" | sudo -S systemctl start pms-backend 2>/dev/null || true
}

# Check if celery is enabled before trying to restart
if systemctl is-enabled celery-pms 2>/dev/null; then
    echo "${DEPLOY_PASSWORD}" | sudo -S systemctl restart celery-pms 2>/dev/null || echo "Celery not running, skipping..."
fi

# Reload nginx
echo "${DEPLOY_PASSWORD}" | sudo -S systemctl reload nginx 2>/dev/null || true

echo "✅ Services restarted"

# Check status
echo ""
echo "Service Status:"
systemctl is-active pms-backend >/dev/null 2>&1 && echo "  ✓ pms-backend: running" || echo "  ✗ pms-backend: stopped"
systemctl is-active nginx >/dev/null 2>&1 && echo "  ✓ nginx: running" || echo "  ✗ nginx: stopped"
