#!/bin/bash

# =============================================================================
# YEA PMS Backend - Deployment Script
# =============================================================================
# This script should be placed on the production server and run manually
# for initial setup. After that, GitHub Actions will handle deployments.
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="pms-backend"
PROJECT_PATH="/var/www/YEA/PMS/$PROJECT_NAME"
REPO_URL="https://github.com/j-tee/pms-backend.git"
BRANCH="main"
VENV_PATH="$PROJECT_PATH/venv"
PYTHON_VERSION="python3.13"

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_message "$BLUE" "======================================="
print_message "$BLUE" "YEA PMS Backend - Deployment Script"
print_message "$BLUE" "======================================="

# Check if running as deploy user
if [ "$USER" != "deploy" ]; then
    print_message "$RED" "❌ This script should be run as the 'deploy' user"
    print_message "$YELLOW" "Switch to deploy user: sudo su - deploy"
    exit 1
fi

# Step 1: Clone or update repository
print_message "$GREEN" "\n📥 Step 1: Updating repository..."
if [ -d "$PROJECT_PATH/.git" ]; then
    cd "$PROJECT_PATH"
    print_message "$YELLOW" "Repository exists, pulling latest changes..."
    git fetch origin
    git reset --hard origin/$BRANCH
else
    print_message "$YELLOW" "Cloning repository..."
    mkdir -p "$(dirname "$PROJECT_PATH")"
    git clone -b $BRANCH "$REPO_URL" "$PROJECT_PATH"
    cd "$PROJECT_PATH"
fi

# Step 2: Setup virtual environment
print_message "$GREEN" "\n🐍 Step 2: Setting up Python virtual environment..."
if [ ! -d "$VENV_PATH" ]; then
    print_message "$YELLOW" "Creating virtual environment..."
    $PYTHON_VERSION -m venv "$VENV_PATH"
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Upgrade pip
print_message "$YELLOW" "Upgrading pip..."
pip install --upgrade pip

# Step 3: Install dependencies
print_message "$GREEN" "\n📦 Step 3: Installing Python dependencies..."
pip install -r requirements.txt

# Step 4: Check environment file
print_message "$GREEN" "\n⚙️  Step 4: Checking environment configuration..."
if [ ! -f "$PROJECT_PATH/.env.production" ]; then
    print_message "$RED" "❌ .env.production file not found!"
    print_message "$YELLOW" "Please create .env.production with production settings"
    print_message "$YELLOW" "You can copy from .env.example and modify the values"
    exit 1
else
    print_message "$GREEN" "✅ Environment file found"
fi

# Step 5: Run database migrations
print_message "$GREEN" "\n🗃️  Step 5: Running database migrations..."
python manage.py migrate --no-input

# Step 6: Collect static files
print_message "$GREEN" "\n📁 Step 6: Collecting static files..."
python manage.py collectstatic --no-input --clear

# Step 7: Create superuser (only for initial setup)
print_message "$GREEN" "\n👤 Step 7: Creating superuser (if needed)..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@yea-pms.gov.gh').exists():
    print("Creating superuser...")
    # You'll need to set this via admin interface or Django shell
else:
    print("Superuser already exists")
EOF

# Step 8: Set proper permissions
print_message "$GREEN" "\n🔒 Step 8: Setting file permissions..."
# Set ownership to deploy user
sudo chown -R deploy:deploy "$PROJECT_PATH"
# Set directory permissions
find "$PROJECT_PATH" -type d -exec chmod 755 {} \;
# Set file permissions
find "$PROJECT_PATH" -type f -exec chmod 644 {} \;
# Make manage.py executable
chmod +x "$PROJECT_PATH/manage.py"
# Ensure media directory is writable
mkdir -p "$PROJECT_PATH/media"
chmod 755 "$PROJECT_PATH/media"

# Step 9: Test configuration
print_message "$GREEN" "\n🧪 Step 9: Testing configuration..."
python manage.py check --deploy

# Step 10: Restart services
print_message "$GREEN" "\n🔄 Step 10: Restarting services..."
sudo systemctl restart pms-backend
sudo systemctl restart celery-pms
sudo systemctl reload nginx

# Step 11: Check service status
print_message "$GREEN" "\n✅ Step 11: Checking service status..."
echo ""
if sudo systemctl is-active --quiet pms-backend; then
    print_message "$GREEN" "✓ Django service (pms-backend) is running"
else
    print_message "$RED" "✗ Django service (pms-backend) is not running"
    print_message "$YELLOW" "Check logs: sudo journalctl -u pms-backend -n 50"
fi

if sudo systemctl is-active --quiet celery-pms; then
    print_message "$GREEN" "✓ Celery service (celery-pms) is running"
else
    print_message "$RED" "✗ Celery service (celery-pms) is not running"
    print_message "$YELLOW" "Check logs: sudo journalctl -u celery-pms -n 50"
fi

if sudo systemctl is-active --quiet nginx; then
    print_message "$GREEN" "✓ Nginx service is running"
else
    print_message "$RED" "✗ Nginx service is not running"
    print_message "$YELLOW" "Check logs: sudo journalctl -u nginx -n 50"
fi

print_message "$BLUE" "\n======================================="
print_message "$GREEN" "🎉 Deployment completed!"
print_message "$BLUE" "======================================="
print_message "$YELLOW" "\nUseful commands:"
print_message "$NC" "  View Django logs:  sudo journalctl -u pms-backend -f"
print_message "$NC" "  View Celery logs:  sudo journalctl -u celery-pms -f"
print_message "$NC" "  View Nginx logs:   sudo tail -f /var/log/nginx/error.log"
print_message "$NC" "  Restart Django:    sudo systemctl restart pms-backend"
print_message "$NC" "  Restart Celery:    sudo systemctl restart celery-pms"
print_message "$NC" "  Restart Nginx:     sudo systemctl restart nginx"
