#!/bin/bash

# Deploy SSL-enabled nginx configurations
# Run this on the server after obtaining SSL certificates

echo "=========================================="
echo "Deploying SSL-enabled nginx configurations"
echo "=========================================="

# Backup existing configurations
echo "Creating backups..."
sudo cp /opt/nginx/conf/conf.d/pms_backend.conf /opt/nginx/conf/conf.d/pms_backend.conf.backup.$(date +%Y%m%d_%H%M%S)
sudo cp /opt/nginx/conf/conf.d/pms_frontend.conf /opt/nginx/conf/conf.d/pms_frontend.conf.backup.$(date +%Y%m%d_%H%M%S)

# Deploy backend SSL config
echo "Deploying backend SSL configuration..."
sudo tee /opt/nginx/conf/conf.d/pms_backend.conf > /dev/null << 'EOF'
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name pmsapi.alphalogiquetechnologies.com;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        alias /var/www/YEA/PMS/pms-backend/staticfiles/.well-known/acme-challenge/;
        allow all;
    }
    
    # Redirect all other HTTP traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name pmsapi.alphalogiquetechnologies.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/pmsapi.alphalogiquetechnologies.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pmsapi.alphalogiquetechnologies.com/privkey.pem;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # CORS headers for frontend
    add_header 'Access-Control-Allow-Origin' 'https://pms.alphalogiquetechnologies.com' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, X-Requested-With' always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;
    
    # Logging
    access_log /var/www/YEA/PMS/pms-backend/logs/access.log;
    error_log /var/www/YEA/PMS/pms-backend/logs/error.log;
    
    # Max upload size
    client_max_body_size 50M;
    
    # Static files
    location /static/ {
        alias /var/www/YEA/PMS/pms-backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /var/www/YEA/PMS/pms-backend/media/;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    # Proxy to Django application
    location / {
        # Handle preflight OPTIONS requests
        if ($request_method = 'OPTIONS') {
            return 204;
        }
        
        proxy_pass http://unix:/var/www/YEA/PMS/pms-backend/gunicorn.sock;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeout settings
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
EOF

# Deploy frontend SSL config
echo "Deploying frontend SSL configuration..."
sudo tee /opt/nginx/conf/conf.d/pms_frontend.conf > /dev/null << 'EOF'
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name pms.alphalogiquetechnologies.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        allow all;
    }

    # Redirect all other HTTP traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name pms.alphalogiquetechnologies.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/pms.alphalogiquetechnologies.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pms.alphalogiquetechnologies.com/privkey.pem;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/pms_frontend_access.log;
    error_log /var/log/nginx/pms_frontend_error.log;

    # Proxy to frontend application (Vite dev server or built app)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Test nginx configuration
echo "Testing nginx configuration..."
sudo /opt/nginx/sbin/nginx -t

if [ $? -eq 0 ]; then
    echo "Configuration test passed!"
    echo "Reloading nginx..."
    sudo systemctl reload nginx
    
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS! Nginx reloaded with SSL configurations"
        echo ""
        echo "SSL is now active for:"
        echo "  - Backend API: https://pmsapi.alphalogiquetechnologies.com"
        echo "  - Frontend: https://pms.alphalogiquetechnologies.com"
        echo ""
        echo "Certificates expire on: 2026-03-10"
        echo "Auto-renewal is configured via certbot"
    else
        echo "❌ ERROR: Failed to reload nginx"
        exit 1
    fi
else
    echo "❌ ERROR: Nginx configuration test failed"
    exit 1
fi
