#!/usr/bin/env python
"""
Script to create or update a Super Administrator account.

This script creates the highest privilege user account with complete system control.
Super Admin can:
- Access all system features and data
- Invite YEA Officials (elevated admins)
- Manage all users, farms, and applications
- Configure system settings
"""
import os
import sys
import django
import getpass

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def create_super_admin():
    """Create or update the Super Administrator account."""
    
    print("=" * 60)
    print("YEA PMS - Super Administrator Account Setup")
    print("=" * 60)
    print()
    
    # Get user input
    print("Enter Super Admin details:")
    username = input("Username [alphalogiquetechnologies@gmail.com]: ").strip() or 'alphalogiquetechnologies@gmail.com'
    email = input("Email [alphalogiquetechnologies@gmail.com]: ").strip() or 'alphalogiquetechnologies@gmail.com'
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    phone = input("Phone (Ghana format +233...): ").strip()
    
    # Validate required fields
    if not email or not first_name or not last_name:
        print("\n❌ Error: Email, First Name, and Last Name are required!")
        sys.exit(1)
    
    # Get password securely
    while True:
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm Password: ")
        
        if password == password_confirm:
            if len(password) < 8:
                print("❌ Password must be at least 8 characters long!")
                continue
            break
        else:
            print("❌ Passwords do not match! Try again.")
    
    try:
        # Check if user exists
        user, created = User.objects.update_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone or '+233000000000',
                'role': 'SUPER_ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'is_verified': True,
                'email_verified': True,
                'phone_verified': True,
            }
        )
        
        # Set password
        user.set_password(password)
        user.save()
        
        # Add SUPER_ADMIN role to roles table as well
        user.add_role('SUPER_ADMIN')
        
        print()
        print("=" * 60)
        if created:
            print("✅ Super Administrator account created successfully!")
        else:
            print("✅ Super Administrator account updated successfully!")
        print("=" * 60)
        print()
        print("Account Details:")
        print(f"  Username:  {user.username}")
        print(f"  Email:     {user.email}")
        print(f"  Name:      {user.first_name} {user.last_name}")
        print(f"  Role:      {user.get_role_display()}")
        print(f"  Phone:     {user.phone}")
        print()
        print("Permissions:")
        print("  ✓ Full system access")
        print("  ✓ Can invite YEA Officials")
        print("  ✓ Can manage all users and roles")
        print("  ✓ Can access all farms and applications")
        print("  ✓ Can configure system settings")
        print()
        print("Login URLs:")
        print("  Development: http://127.0.0.1:8000/admin/")
        print("  Production:  https://pmsapi.alphalogiquetechnologies.com/admin/")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    create_super_admin()
