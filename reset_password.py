#!/usr/bin/env python
"""Quick password reset script"""
import os
import sys
import django
import getpass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User

# Get username from environment or prompt
username = os.environ.get('ADMIN_USERNAME')
if not username:
    username = input('Enter username: ').strip()
    if not username:
        print('❌ Error: Username is required')
        sys.exit(1)

try:
    user = User.objects.get(username=username)
except User.DoesNotExist:
    print(f'❌ Error: User "{username}" not found')
    sys.exit(1)

# Get password securely
password = getpass.getpass('Enter new password: ')
confirm_password = getpass.getpass('Confirm new password: ')

if password != confirm_password:
    print('❌ Error: Passwords do not match')
    sys.exit(1)

if len(password) < 8:
    print('❌ Error: Password must be at least 8 characters')
    sys.exit(1)

# Set the password
user.set_password(password)
user.save()

print('✅ Password has been reset successfully!')
print(f'Username: {user.username}')
print(f'Email: {user.email}')
