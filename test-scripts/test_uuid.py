#!/usr/bin/env python
"""
UUID Primary Key Verification Test
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User
from accounts.roles import Role, UserRole, Permission, RolePermission
from farms.models import (
    Farm, FarmLocation, PoultryHouse, Equipment,
    Utilities, Biosecurity, SupportNeeds, FarmDocument
)
from django.db import connection

print("=" * 60)
print("UUID PRIMARY KEY VERIFICATION")
print("=" * 60)
print()

# Check models with UUID primary keys
models_to_check = [
    ('User', User),
    ('Role', Role),
    ('UserRole', UserRole),
    ('Permission', Permission),
    ('RolePermission', RolePermission),
    ('Farm', Farm),
    ('FarmLocation', FarmLocation),
    ('PoultryHouse', PoultryHouse),
    ('Equipment', Equipment),
    ('Utilities', Utilities),
    ('Biosecurity', Biosecurity),
    ('SupportNeeds', SupportNeeds),
    ('FarmDocument', FarmDocument),
]

print("Checking primary key field types:\n")

all_uuid = True
for model_name, model in models_to_check:
    pk_field = model._meta.pk
    field_type = pk_field.get_internal_type()
    is_uuid = field_type == 'UUIDField'
    
    status = "✅" if is_uuid else "❌"
    print(f"{status} {model_name:20} -> {field_type}")
    
    if not is_uuid:
        all_uuid = False

print()
print("=" * 60)

if all_uuid:
    print("✅ ALL MODELS USE UUID PRIMARY KEYS")
else:
    print("❌ SOME MODELS DO NOT USE UUID PRIMARY KEYS")

print("=" * 60)
print()

# Verify in database
print("Database Column Types:")
print()

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 
            table_name, 
            column_name, 
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND column_name = 'id'
        AND table_name IN (
            'users', 'roles', 'user_roles', 'permissions', 'role_permissions',
            'farms', 'farm_locations', 'poultry_houses', 'farm_equipment',
            'farm_utilities', 'farm_biosecurity', 'support_needs', 'farm_documents'
        )
        ORDER BY table_name;
    """)
    
    results = cursor.fetchall()
    
    for table, column, data_type in results:
        status = "✅" if data_type == 'uuid' else "❌"
        print(f"{status} {table:25} | {column:10} | {data_type}")

print()
print("=" * 60)
print("✅ UUID VERIFICATION COMPLETED")
print("=" * 60)
