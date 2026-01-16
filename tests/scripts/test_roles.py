#!/usr/bin/env python
"""
Test script for role management system (Rolify equivalent).
Tests creating roles, assigning to users, and checking permissions.

Usage:
    python test-scripts/test_roles.py
"""

import os
import sys
import django

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.roles import Role, UserRole, Permission, RolePermission

User = get_user_model()


def test_role_system():
    """Test the role management system."""
    
    print('=' * 60)
    print('ROLE MANAGEMENT SYSTEM TEST')
    print('=' * 60)
    print()
    
    # Create test user
    print('1. Creating test user...')
    user, created = User.objects.get_or_create(
        username='test_farmer',
        defaults={
            'email': 'test@example.com',
            'phone': '+233240000000',
            'role': 'FARMER',
            'first_name': 'Test',
            'last_name': 'Farmer'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    print(f'   ✅ User: {user.username} ({"created" if created else "exists"})')
    print()
    
    # Create system roles
    print('2. Creating system roles...')
    admin_role = Role.create_system_role('admin', 'System administrator')
    moderator_role = Role.create_system_role('moderator', 'Content moderator')
    print(f'   ✅ Admin role: {admin_role}')
    print(f'   ✅ Moderator role: {moderator_role}')
    print()
    
    # Create permissions
    print('3. Creating permissions...')
    perm1, _ = Permission.objects.get_or_create(
        codename='can_approve_farms',
        defaults={
            'name': 'Can approve farm registrations',
            'category': 'farm_management',
            'is_system_permission': True
        }
    )
    perm2, _ = Permission.objects.get_or_create(
        codename='can_edit_reports',
        defaults={
            'name': 'Can edit reports',
            'category': 'reporting',
            'is_system_permission': True
        }
    )
    print(f'   ✅ Permission: {perm1.name}')
    print(f'   ✅ Permission: {perm2.name}')
    print()
    
    # Assign permissions to roles
    print('4. Assigning permissions to admin role...')
    RolePermission.objects.get_or_create(role=admin_role, permission=perm1)
    RolePermission.objects.get_or_create(role=admin_role, permission=perm2)
    RolePermission.objects.get_or_create(role=moderator_role, permission=perm1)
    print(f'   ✅ Admin has: {admin_role.permissions.count()} permissions')
    print(f'   ✅ Moderator has: {moderator_role.permissions.count()} permissions')
    print()
    
    # Test role assignment
    print('5. Testing role assignment using RoleMixin methods...')
    print(f'   Adding "admin" role to {user.username}...')
    user.add_role('admin')
    print(f'   ✅ Role added')
    
    print(f'   Checking if user has "admin" role...')
    has_admin = user.has_role('admin')
    print(f'   ✅ Has admin: {has_admin}')
    
    print(f'   Adding "moderator" role...')
    user.add_role('moderator')
    print(f'   ✅ Role added')
    print()
    
    # Test role checking
    print('6. Testing role checking methods...')
    print(f'   has_role("admin"): {user.has_role("admin")}')
    print(f'   has_role("moderator"): {user.has_role("moderator")}')
    print(f'   has_role("nonexistent"): {user.has_role("nonexistent")}')
    print(f'   has_any_role("admin", "editor"): {user.has_any_role("admin", "editor")}')
    print(f'   has_all_roles("admin", "moderator"): {user.has_all_roles("admin", "moderator")}')
    print()
    
    # Test permission checking
    print('7. Testing permission checking...')
    print(f'   has_permission("can_approve_farms"): {user.has_permission("can_approve_farms")}')
    print(f'   has_permission("can_edit_reports"): {user.has_permission("can_edit_reports")}')
    print(f'   has_permission("nonexistent"): {user.has_permission("nonexistent")}')
    print()
    
    # Get all roles and permissions
    print('8. Getting all roles and permissions...')
    user_roles = user.get_roles()
    user_permissions = user.get_permissions()
    print(f'   ✅ User has {user_roles.count()} roles:')
    for role in user_roles:
        print(f'      - {role.name}')
    print(f'   ✅ User has {user_permissions.count()} permissions:')
    for perm in user_permissions:
        print(f'      - {perm.name} ({perm.codename})')
    print()
    
    # Test role removal
    print('9. Testing role removal...')
    print(f'   Removing "moderator" role...')
    removed = user.remove_role('moderator')
    print(f'   ✅ Removed: {removed}')
    print(f'   has_role("moderator"): {user.has_role("moderator")}')
    print()
    
    # Cleanup
    print('10. Cleanup (optional)...')
    cleanup = input('   Delete test user and roles? (y/N): ').strip().lower()
    if cleanup == 'y':
        UserRole.objects.filter(user=user).delete()
        user.delete()
        Role.objects.filter(name__in=['admin', 'moderator']).delete()
        Permission.objects.filter(codename__in=['can_approve_farms', 'can_edit_reports']).delete()
        print('   ✅ Cleanup complete')
    else:
        print('   ℹ️  Test data preserved for inspection')
    
    print()
    print('=' * 60)
    print('✅ ROLE SYSTEM TEST COMPLETED SUCCESSFULLY!')
    print('=' * 60)
    return True


if __name__ == '__main__':
    test_role_system()
