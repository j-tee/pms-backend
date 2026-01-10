#!/bin/bash
# Quick Secret Rotation Script for Production
# Run this on your production server after pulling commit cf896a2

set -e  # Exit on error

echo "========================================"
echo "YEA PMS - Production Secret Rotation"
echo "========================================"
echo ""

# Check if running in production directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Run this script from the pms-backend directory"
    exit 1
fi

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production file not found"
    echo "   Create it by copying: cp .env.example .env.production"
    exit 1
fi

echo "Step 1: Generating new SECRET_KEY..."
NEW_SECRET=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
echo "✅ Generated: $NEW_SECRET"
echo ""

echo "Step 2: Checking current .env.production..."
if grep -q "^SECRET_KEY=" .env.production; then
    OLD_SECRET=$(grep "^SECRET_KEY=" .env.production | cut -d= -f2)
    echo "   Current SECRET_KEY: ${OLD_SECRET:0:20}..."
else
    echo "⚠️  Warning: No SECRET_KEY found in .env.production"
fi
echo ""

echo "Step 3: Do you want to update SECRET_KEY in .env.production?"
echo "   New key will be: ${NEW_SECRET:0:20}..."
read -p "   Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Aborted. No changes made."
    exit 0
fi

# Backup .env.production
echo "Step 4: Creating backup..."
cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"
echo ""

# Update or add SECRET_KEY
echo "Step 5: Updating SECRET_KEY in .env.production..."
if grep -q "^SECRET_KEY=" .env.production; then
    # Replace existing
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$NEW_SECRET|" .env.production
else
    # Add new
    echo "SECRET_KEY=$NEW_SECRET" >> .env.production
fi
echo "✅ Updated .env.production"
echo ""

echo "Step 6: Verifying configuration..."
python manage.py check --deploy 2>&1 | head -20
echo ""

echo "Step 7: Services need to be restarted. Run these commands:"
echo ""
echo "   sudo systemctl restart pms-backend"
echo "   sudo systemctl restart celery-pms"
echo "   sudo systemctl status pms-backend"
echo ""
echo "⚠️  WARNING: Restarting will:"
echo "   - Invalidate all user sessions"
echo "   - Invalidate all JWT tokens"
echo "   - Users will need to log in again"
echo ""
read -p "Restart services now? (yes/no): " RESTART

if [ "$RESTART" == "yes" ]; then
    echo "Restarting services..."
    sudo systemctl restart pms-backend
    sudo systemctl restart celery-pms
    echo ""
    echo "Checking service status..."
    sudo systemctl status pms-backend --no-pager -l
    echo ""
    echo "✅ Secret rotation complete!"
else
    echo "⚠️  Services NOT restarted. Remember to restart manually:"
    echo "   sudo systemctl restart pms-backend celery-pms"
fi

echo ""
echo "========================================"
echo "Secret Rotation Summary"
echo "========================================"
echo "✅ New SECRET_KEY generated"
echo "✅ .env.production updated"
echo "✅ Backup created (.env.production.backup.*)"
echo ""
echo "Next steps:"
echo "1. Verify application is running: curl http://localhost:8000/api/health/"
echo "2. Check logs: sudo journalctl -u pms-backend -n 50"
echo "3. Test user login"
echo "4. Delete backup files after confirming everything works"
echo "========================================"
