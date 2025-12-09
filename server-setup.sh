#!/bin/bash

# =============================================================================
# Quick Server Setup Script
# Run this on the production server for initial configuration
# =============================================================================

set -e

echo "🚀 YEA PMS Backend - Server Setup Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "❌ Please do not run as root. Run as a regular user with sudo privileges."
   exit 1
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y \
    python3.13 \
    python3.13-venv \
    python3-pip \
    postgresql-15 \
    postgresql-15-postgis-3 \
    postgresql-contrib \
    redis-server \
    nginx \
    git \
    curl \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    supervisor \
    certbot \
    python3-certbot-nginx

# Create deploy user if doesn't exist
if ! id "deploy" &>/dev/null; then
    echo "👤 Creating deploy user..."
    sudo adduser --disabled-password --gecos "" deploy
    sudo usermod -aG www-data deploy
fi

# Setup PostgreSQL
echo "🗄️  Configuring PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database (you'll need to set password manually)
echo ""
echo "📝 PostgreSQL Setup Instructions:"
echo "Run the following commands to setup the database:"
echo ""
echo "sudo -u postgres psql << 'EOF'"
echo "CREATE DATABASE yea_pms_production;"
echo "CREATE USER pms_user WITH PASSWORD 'YOUR_SECURE_PASSWORD_HERE';"
echo "GRANT ALL PRIVILEGES ON DATABASE yea_pms_production TO pms_user;"
echo "\\c yea_pms_production"
echo "CREATE EXTENSION postgis;"
echo "CREATE EXTENSION postgis_topology;"
echo "\\q"
echo "EOF"
echo ""

# Configure Redis
echo "🔴 Configuring Redis..."
sudo systemctl start redis
sudo systemctl enable redis

# Create project directories
echo "📁 Creating project directories..."
sudo mkdir -p /var/www/YEA/PMS
sudo chown -R deploy:deploy /var/www/YEA

sudo mkdir -p /var/log/pms-backend
sudo mkdir -p /var/log/celery-pms
sudo chown -R deploy:deploy /var/log/pms-backend
sudo chown -R deploy:deploy /var/log/celery-pms

sudo mkdir -p /var/run/celery-pms
sudo chown deploy:deploy /var/run/celery-pms

# Configure firewall
echo "🔥 Configuring firewall..."
if ! sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 7822/tcp  # SSH
    sudo ufw allow 80/tcp    # HTTP
    sudo ufw allow 443/tcp   # HTTPS
    sudo ufw --force enable
fi

echo ""
echo "✅ Server setup completed!"
echo ""
echo "📋 Next Steps:"
echo "1. Switch to deploy user: sudo su - deploy"
echo "2. Clone repository: git clone https://github.com/j-tee/pms-backend.git /var/www/YEA/PMS/pms-backend"
echo "3. Setup database using the commands shown above"
echo "4. Follow DEPLOYMENT_GUIDE.md for complete setup"
echo ""
