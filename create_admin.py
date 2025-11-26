#!/usr/bin/env python
"""
Script to create a superuser account.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Update or create superuser
try:
    user, created = User.objects.get_or_create(
        username='TeeJay',
        defaults={
            'email': 'juliustetteh@gmail.com',
            'first_name': 'Julius',
            'last_name': 'Tetteh',
            'phone': '0000000000',
            'role': 'platform_admin',
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
        }
    )
    
    if not created:
        # Update existing user
        user.email = 'juliustetteh@gmail.com'
        user.first_name = 'Julius'
        user.last_name = 'Tetteh'
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.role = 'platform_admin'
    
    # Set password
    user.set_password('rojutet11')
    user.save()
    
    if created:
        print(f"✅ Superuser created successfully!")
    else:
        print(f"✅ Superuser updated successfully!")
    
    print(f"   Username: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Role: {user.role}")
    print(f"   Password: rojutet11")
    print(f"\nYou can now login at: http://127.0.0.1:8000/admin/")
except Exception as e:
    print(f"❌ Error: {e}")
