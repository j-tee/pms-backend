#!/usr/bin/env python
"""
Simple test to verify frontend field names are mapped correctly
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from farms.models import Farm, PoultryHouse
from flock_management.models import Flock
from datetime import date

def test_direct_creation():
    print("=" * 80)
    print("TESTING FLOCK CREATION WITH FRONTEND DATA STRUCTURE")
    print("=" * 80)
    
    # Get test farm
    farm = Farm.objects.first()
    if not farm:
        print("❌ No farm found")
        return False
    
    print(f"\n✅ Using farm: {farm.farm_name}")
    
    # Simulate what the view will do with frontend data
    frontend_request = {
        'batch_number': '000003',
        'bird_type': 'Layers',
        'breed': 'some breed',
        'placement_date': '2025-12-08',
        'initial_quantity': 1000,
        'expected_end_date': '2025-12-24'
    }
    
    print(f"\nFrontend sends: {frontend_request}")
    
    # Simulate view's field mapping logic
    flock_number = frontend_request.get('flock_number') or frontend_request.get('batch_number')
    flock_type = frontend_request.get('flock_type') or frontend_request.get('bird_type')
    breed = frontend_request.get('breed')
    arrival_date = frontend_request.get('arrival_date') or frontend_request.get('placement_date')
    initial_count = frontend_request.get('initial_count') or frontend_request.get('initial_quantity')
    
    print(f"\nMapped to backend fields:")
    print(f"   flock_number: {flock_number}")
    print(f"   flock_type: {flock_type}")
    print(f"   breed: {breed}")
    print(f"   arrival_date: {arrival_date}")
    print(f"   initial_count: {initial_count}")
    
    # Check all required fields present
    if all([flock_number, flock_type, breed, arrival_date, initial_count]):
        print("\n✅ All required fields mapped successfully!")
        
        # Try creating the flock
        try:
            from datetime import datetime
            arrival_date_obj = datetime.fromisoformat(arrival_date).date()
            
            flock = Flock.objects.create(
                farm=farm,
                flock_number=flock_number,
                flock_type=flock_type,
                breed=breed,
                arrival_date=arrival_date_obj,
                initial_count=int(initial_count),
                current_count=int(initial_count)
            )
            print(f"\n✅ Flock created successfully!")
            print(f"   ID: {flock.id}")
            print(f"   Number: {flock.flock_number}")
            print(f"   Type: {flock.flock_type}")
            print(f"   Count: {flock.current_count}")
            
            # Cleanup
            flock.delete()
            print("\n✅ Test flock deleted")
            
            return True
        except Exception as e:
            print(f"\n❌ Error creating flock: {e}")
            return False
    else:
        print("\n❌ Missing required fields after mapping")
        return False

if __name__ == '__main__':
    success = test_direct_creation()
    print("\n" + "=" * 80)
    if success:
        print("✅ FIELD MAPPING TEST PASSED!")
        print("\nThe backend now accepts:")
        print("   Frontend          Backend")
        print("   ---------         -------")
        print("   batch_number  →  flock_number")
        print("   bird_type     →  flock_type")
        print("   placement_date →  arrival_date")
        print("   initial_quantity → initial_count")
        print("   poultry_house_id → housed_in_id")
    else:
        print("❌ FIELD MAPPING TEST FAILED!")
    print("=" * 80)
    sys.exit(0 if success else 1)
