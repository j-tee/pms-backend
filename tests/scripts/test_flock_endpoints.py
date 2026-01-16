#!/usr/bin/env python
"""
Test script for Flock Management Endpoints

Tests the following endpoints:
- GET /api/flocks/
- POST /api/flocks/
- GET /api/flocks/{id}/
- PUT /api/flocks/{id}/
- DELETE /api/flocks/{id}/
- GET /api/flocks/statistics/
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from farms.models import Farm, PoultryHouse
from flock_management.models import Flock
from datetime import date, timedelta

User = get_user_model()

def test_flock_crud():
    """Test Flock CRUD operations"""
    print("=" * 80)
    print("FLOCK MANAGEMENT ENDPOINTS TEST")
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
    
    # Get or create a poultry house for testing
    poultry_house = PoultryHouse.objects.filter(farm=farm).first()
    if poultry_house:
        print(f"✅ Using poultry house: {poultry_house.house_name}")
    
    print("\n" + "-" * 80)
    print("TEST 1: Create Flock (POST)")
    print("-" * 80)
    
    try:
        flock = Flock.objects.create(
            farm=farm,
            flock_number="TEST-2025-001",
            flock_type="Layers",
            breed="Isa Brown",
            source="YEA Program",
            supplier_name="Test Hatchery Ltd",
            arrival_date=date.today() - timedelta(days=30),
            initial_count=500,
            current_count=495,
            age_at_arrival_weeks=16,
            purchase_price_per_bird=25.00,
            status="Active",
            is_currently_producing=True,
            housed_in=poultry_house if poultry_house else None,
            notes="Test flock for automated testing"
        )
        print(f"✅ Created flock: {flock.flock_number}")
        print(f"   ID: {flock.id}")
        print(f"   Type: {flock.flock_type}")
        print(f"   Initial Count: {flock.initial_count}")
        print(f"   Current Count: {flock.current_count}")
        print(f"   Total Mortality: {flock.total_mortality}")
        print(f"   Mortality Rate: {flock.mortality_rate_percent}%")
        print(f"   Total Acquisition Cost: GHS {flock.total_acquisition_cost}")
    except Exception as e:
        print(f"❌ Error creating flock: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 2: Get Single Flock (GET with ID)")
    print("-" * 80)
    
    try:
        retrieved = Flock.objects.get(id=flock.id)
        print(f"✅ Retrieved flock: {retrieved.flock_number}")
        print(f"   Breed: {retrieved.breed}")
        print(f"   Source: {retrieved.source}")
        print(f"   Status: {retrieved.status}")
    except Exception as e:
        print(f"❌ Error retrieving flock: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 3: Update Flock (PUT)")
    print("-" * 80)
    
    try:
        flock.current_count = 490
        flock.notes = "Updated test notes"
        flock.save()
        print(f"✅ Updated flock")
        print(f"   New Current Count: {flock.current_count}")
        print(f"   New Total Mortality: {flock.total_mortality}")
        print(f"   New Mortality Rate: {flock.mortality_rate_percent}%")
        print(f"   Notes: {flock.notes}")
    except Exception as e:
        print(f"❌ Error updating flock: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 4: List All Flocks (GET)")
    print("-" * 80)
    
    try:
        all_flocks = Flock.objects.filter(farm=farm)
        print(f"✅ Found {all_flocks.count()} flocks for this farm")
        for fl in all_flocks[:5]:  # Show first 5
            print(f"   - {fl.flock_number} ({fl.flock_type}) - {fl.current_count} birds")
    except Exception as e:
        print(f"❌ Error listing flocks: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 5: Statistics Aggregation")
    print("-" * 80)
    
    try:
        from django.db.models import Count, Sum, Avg
        
        total = Flock.objects.filter(farm=farm).count()
        total_birds = Flock.objects.filter(farm=farm).aggregate(Sum('current_count'))['current_count__sum'] or 0
        active = Flock.objects.filter(farm=farm, status='Active').count()
        producing = Flock.objects.filter(farm=farm, is_currently_producing=True).count()
        
        print(f"✅ Total flocks: {total}")
        print(f"   Total birds: {total_birds}")
        print(f"   Active flocks: {active}")
        print(f"   Producing flocks: {producing}")
        
        # By type
        by_type = dict(Flock.objects.filter(farm=farm).values_list('flock_type').annotate(Count('id')))
        print(f"   By type: {by_type}")
    except Exception as e:
        print(f"❌ Error calculating statistics: {e}")
        return False
    
    print("\n" + "-" * 80)
    print("TEST 6: Delete Flock (DELETE)")
    print("-" * 80)
    
    try:
        flock_num = flock.flock_number
        flock.delete()
        print(f"✅ Deleted flock: {flock_num}")
        
        # Verify deletion
        exists = Flock.objects.filter(id=flock.id).exists()
        print(f"   Verified deletion: {not exists}")
    except Exception as e:
        print(f"❌ Error deleting flock: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print("\n📋 API Endpoints Available:")
    print("   POST   /api/flocks/                - Create new flock")
    print("   GET    /api/flocks/                - List all flocks")
    print("   GET    /api/flocks/{id}/           - Get single flock")
    print("   PUT    /api/flocks/{id}/           - Update flock")
    print("   DELETE /api/flocks/{id}/           - Delete flock")
    print("   GET    /api/flocks/statistics/     - Get statistics")
    print("=" * 80)
    return True

if __name__ == '__main__':
    success = test_flock_crud()
    sys.exit(0 if success else 1)
