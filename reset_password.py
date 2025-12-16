#!/usr/bin/env python
"""Quick password reset script"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User

# Get the user
user = User.objects.get(username='alphalogiquetechnologies@gmail.com')

# Set the password
password = 'DontLetGo11'
user.set_password(password)
user.save()

print('✅ Password has been reset successfully!')
print(f'Username: {user.username}')
print(f'Email: {user.email}')
print(f'Test authentication: {user.check_password(password)}')
