#!/bin/bash

# PMS Backend Nginx Configuration Deployment Script

set -e  # Exit on error

# Configuration
SERVER="deploy@68.66.251.79"
SSH_PORT="7822"
LOCAL_CONF="deployment/nginx/pms_backend.conf"
REMOTE_CONF_DIR="/opt/nginx/conf/conf.d"
REMOTE_CONF_FILE="pms_backend.conf"
LOGS_DIR="/var/www/YEA/PMS/pms-backend/logs"

echo "========================================"
echo "PMS Backend Nginx Configuration Setup"
echo "========================================"
echo ""

# Check if local config file exists
if [ ! -f "$LOCAL_CONF" ]; then
    echo "Error: Local config file not found: $LOCAL_CONF"
    exit 1
fi

echo "Step 1: Copying nginx configuration to server..."
scp -P $SSH_PORT "$LOCAL_CONF" $SERVER:~/$REMOTE_CONF_FILE

echo ""
echo "Step 2: Creating logs directory if it doesn't exist..."
ssh -p $SSH_PORT $SERVER "sudo mkdir -p $LOGS_DIR && sudo chown deploy:deploy $LOGS_DIR"

echo ""
echo "Step 3: Moving configuration to nginx conf.d directory..."
ssh -p $SSH_PORT $SERVER "sudo mv ~/$REMOTE_CONF_FILE $REMOTE_CONF_DIR/$REMOTE_CONF_FILE"

echo ""
echo "Step 4: Testing nginx configuration..."
if ssh -p $SSH_PORT $SERVER "sudo nginx -t"; then
    echo "✓ Nginx configuration is valid"
else
    echo "✗ Nginx configuration has errors"
    echo "Please fix the errors before proceeding"
    exit 1
fi

echo ""
echo "Step 5: Reloading nginx..."
ssh -p $SSH_PORT $SERVER "sudo systemctl reload nginx"

echo ""
echo "========================================"
echo "✓ Configuration deployed successfully!"
echo "========================================"
echo ""
echo "IMPORTANT: The backend is now running on HTTP only."
echo ""
echo "Next steps:"
echo ""
echo "1. Ensure DNS is configured:"
echo "   - pmsapi.alphalogiquetechnologies.com → 68.66.251.79"
echo ""
echo "2. Test the backend is working (HTTP):"
echo "   curl http://pmsapi.alphalogiquetechnologies.com/admin/"
echo ""
echo "3. Once DNS is working, obtain SSL certificate:"
echo ""
echo "   ssh -p $SSH_PORT $SERVER"
echo "   sudo certbot --nginx -d pmsapi.alphalogiquetechnologies.com"
echo ""
echo "   Certbot will automatically:"
echo "   - Obtain the SSL certificate"
echo "   - Update the nginx config to enable HTTPS"
echo "   - Set up HTTP to HTTPS redirect"
echo "   - Reload nginx"
echo ""
echo "4. After SSL is set up, manually update CORS origins:"
echo "   Edit /opt/nginx/conf/conf.d/pms_backend.conf"
echo "   Change 'http://pms.alphalogiquetechnologies.com' to 'https://pms.alphalogiquetechnologies.com'"
echo "   Then: sudo systemctl reload nginx"
echo ""
echo "Useful commands:"
echo "  Check nginx status:  ssh -p $SSH_PORT $SERVER 'sudo systemctl status nginx'"
echo "  View error logs:     ssh -p $SSH_PORT $SERVER 'sudo tail -f /var/www/YEA/PMS/pms-backend/logs/nginx_error.log'"
echo "  View access logs:    ssh -p $SSH_PORT $SERVER 'sudo tail -f /var/www/YEA/PMS/pms-backend/logs/nginx_access.log'"
