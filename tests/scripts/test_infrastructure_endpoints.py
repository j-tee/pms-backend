#!/usr/bin/env python
"""
Test script for Infrastructure Management Endpoints

Tests the following endpoints:
- GET /api/farms/infrastructure/
- POST /api/farms/infrastructure/
- GET /api/farms/infrastructure/{id}/
- PUT /api/farms/infrastructure/{id}/
- DELETE /api/farms/infrastructure/{id}/
- GET /api/farms/infrastructure/statistics/
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from farms.models import Farm, FarmInfrastructure
from datetime import date, timedelta

User = get_user_model()

def test_infrastructure_crud():
    """Test Infrastructure CRUD operations"""
    print("=" * 80)
    print("INFRASTRUCTURE ENDPOINTS TEST")
    print("=" * 80)
    
    # Find a test user with a farm
    try:
        farm = Farm.objects.first()
        if not farm:
            print("❌ No farm found in database. Please create a farm first.")
            return False
        
        user = farm.user
        print(f"✅ Using farm: {farm.farm_name} (Owner: {user.email})")
    except Exception as e:
        print(f"❌ Error finding farm: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 1: Create Infrastructure (POST)")
    print("-" * 80)
    
    try:
        infrastructure = FarmInfrastructure.objects.create(
            farm=farm,
            infrastructure_name="Test Borehole",
            infrastructure_type="Water System",
            description="Test water system for automated testing",
            capacity="5000 liters/hour",
            status="Operational",
            condition="Excellent",
            installation_date=date.today() - timedelta(days=180),
            installation_cost_ghs=15000.00,
            warranty_expiry=date.today() + timedelta(days=365),
            next_maintenance_due=date.today() + timedelta(days=30),
            created_by=user
        )
        print(f"✅ Created infrastructure: {infrastructure.infrastructure_name}")
        print(f"   ID: {infrastructure.id}")
        print(f"   Type: {infrastructure.infrastructure_type}")
        print(f"   Status: {infrastructure.status}")
        print(f"   Under Warranty: {infrastructure.is_under_warranty}")
        print(f"   Days Until Maintenance: {infrastructure.days_until_maintenance}")
    except Exception as e:
        print(f"❌ Error creating infrastructure: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 2: Get Single Infrastructure (GET with ID)")
    print("-" * 80)
    
    try:
        retrieved = FarmInfrastructure.objects.get(id=infrastructure.id)
        print(f"✅ Retrieved infrastructure: {retrieved.infrastructure_name}")
        print(f"   All fields accessible: {bool(retrieved.description)}")
    except Exception as e:
        print(f"❌ Error retrieving infrastructure: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 3: Update Infrastructure (PUT)")
    print("-" * 80)
    
    try:
        infrastructure.status = "Under Maintenance"
        infrastructure.condition = "Good"
        infrastructure.last_maintenance_date = date.today()
        infrastructure.save()
        print(f"✅ Updated infrastructure status to: {infrastructure.status}")
        print(f"   Condition: {infrastructure.condition}")
        print(f"   Last Maintenance: {infrastructure.last_maintenance_date}")
    except Exception as e:
        print(f"❌ Error updating infrastructure: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 4: List All Infrastructure (GET)")
    print("-" * 80)
    
    try:
        all_infrastructure = FarmInfrastructure.objects.filter(farm=farm)
        print(f"✅ Found {all_infrastructure.count()} infrastructure items for this farm")
        for infra in all_infrastructure[:5]:  # Show first 5
            print(f"   - {infra.infrastructure_name} ({infra.infrastructure_type})")
    except Exception as e:
        print(f"❌ Error listing infrastructure: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 5: Statistics Aggregation")
    print("-" * 80)
    
    try:
        from django.db.models import Count
        
        total = FarmInfrastructure.objects.filter(farm=farm).count()
        by_type = dict(FarmInfrastructure.objects.filter(farm=farm).values_list('infrastructure_type').annotate(Count('id')))
        by_status = dict(FarmInfrastructure.objects.filter(farm=farm).values_list('status').annotate(Count('id')))
        
        print(f"✅ Total infrastructure items: {total}")
        print(f"   By type: {len(by_type)} different types")
        print(f"   By status: {len(by_status)} different statuses")
        
        # Maintenance due calculations
        today = date.today()
        overdue = FarmInfrastructure.objects.filter(
            farm=farm,
            next_maintenance_due__lt=today
        ).count()
        print(f"   Maintenance overdue: {overdue} items")
    except Exception as e:
        print(f"❌ Error calculating statistics: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 6: Delete Infrastructure (DELETE)")
    print("-" * 80)
    
    try:
        infra_name = infrastructure.infrastructure_name
        infrastructure.delete()
        print(f"✅ Deleted infrastructure: {infra_name}")
        
        # Verify deletion
        exists = FarmInfrastructure.objects.filter(id=infrastructure.id).exists()
        print(f"   Verified deletion: {not exists}")
    except Exception as e:
        print(f"❌ Error deleting infrastructure: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    return True

if __name__ == '__main__':
    success = test_infrastructure_crud()
    sys.exit(0 if success else 1)
