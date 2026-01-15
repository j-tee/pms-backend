"""
Quick test script for the new permission system.

Run with: python manage.py shell < test_permission_system.py
"""

from accounts.models import User
from accounts.roles import Permission, UserPermission
from accounts.services.permission_management_service import PermissionManagementService

print("\n" + "="*70)
print("PERMISSION SYSTEM TEST")
print("="*70)

# 1. Check that permissions were synced
perm_count = Permission.objects.count()
print(f"\n✅ Total permissions in database: {perm_count}")

# 2. Show permission categories
from accounts.permissions_config import PERMISSION_CATEGORIES
print(f"\n📂 Permission Categories ({len(PERMISSION_CATEGORIES)}):")
for code, name in PERMISSION_CATEGORIES.items():
    count = Permission.objects.filter(category=code).count()
    print(f"   - {name}: {count} permissions")

# 3. Test permission checking (if we have a user)
try:
    # Try to get first NATIONAL_STAFF user
    staff_user = User.objects.filter(role='NATIONAL_STAFF').first()
    if staff_user:
        print(f"\n👤 Testing with user: {staff_user.email} ({staff_user.role})")
        
        # Check a few permissions
        test_perms = ['view_users', 'create_users', 'manage_permissions']
        for perm in test_perms:
            has_perm = staff_user.has_permission(perm)
            print(f"   - {perm}: {'✅' if has_perm else '❌'}")
    else:
        print("\n⚠️  No NATIONAL_STAFF users found to test permissions")
except Exception as e:
    print(f"\n⚠️  Could not test permissions: {e}")

# 4. Show some permissions
print(f"\n📋 Sample Permissions:")
for perm in Permission.objects.all()[:5]:
    print(f"   - [{perm.category}] {perm.name}")
    print(f"     {perm.description}")

print("\n" + "="*70)
print("Test completed successfully!")
print("="*70 + "\n")
