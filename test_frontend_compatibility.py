#!/usr/bin/env python
"""
Test frontend field name compatibility for Flock API
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from farms.models import Farm, PoultryHouse
from flock_management.models import Flock
from flock_management.views import FlockView
from rest_framework.test import APIRequestFactory
from datetime import date

def test_frontend_fields():
    print("=" * 80)
    print("TESTING FRONTEND FIELD NAME COMPATIBILITY")
    print("=" * 80)
    
    # Get test farm
    farm = Farm.objects.first()
    if not farm:
        print("❌ No farm found")
        return False
    
    user = farm.user
    poultry_house = PoultryHouse.objects.filter(farm=farm).first()
    
    print(f"\n✅ Using farm: {farm.farm_name}")
    if poultry_house:
        print(f"✅ Using poultry house: {poultry_house.house_name} (ID: {poultry_house.id})")
    
    # Test with FRONTEND field names (as shown in screenshot)
    print("\n" + "-" * 80)
    print("TEST: Creating flock with FRONTEND field names")
    print("-" * 80)
    
    frontend_data = {
        'flock_name': 'Some Name',
        'batch_number': '000003',
        'bird_type': 'Layers',
        'breed': 'some breed',
        'expected_end_date': '2025-12-24',
        'initial_quantity': 1000,
        'placement_date': '2025-12-08',
        'poultry_house_id': str(poultry_house.id) if poultry_house else None
    }
    
    print(f"Frontend payload: {frontend_data}")
    
    # Create API request
    factory = APIRequestFactory()
    request = factory.post('/api/flocks/', frontend_data, format='json')
    request.user = user
    
    view = FlockView()
    response = view.post(request)
    
    print(f"\nResponse status: {response.status_code}")
    print(f"Response data: {response.data}")
    
    if response.status_code == 201:
        print("\n✅ SUCCESS! Flock created with frontend field names")
        flock_id = response.data.get('flock_id')
        
        # Verify flock was created
        flock = Flock.objects.get(id=flock_id)
        print(f"   Flock Number: {flock.flock_number}")
        print(f"   Flock Type: {flock.flock_type}")
        print(f"   Breed: {flock.breed}")
        print(f"   Initial Count: {flock.initial_count}")
        print(f"   Arrival Date: {flock.arrival_date}")
        if flock.housed_in:
            print(f"   Housed In: {flock.housed_in.house_name}")
        
        # Cleanup
        flock.delete()
        print("\n✅ Test flock deleted")
        
        return True
    else:
        print(f"\n❌ FAILED! Error: {response.data}")
        return False

if __name__ == '__main__':
    success = test_frontend_fields()
    print("\n" + "=" * 80)
    if success:
        print("✅ FRONTEND COMPATIBILITY TEST PASSED!")
        print("The API now accepts both frontend and backend field names:")
        print("   - batch_number ↔ flock_number")
        print("   - bird_type ↔ flock_type")
        print("   - placement_date ↔ arrival_date")
        print("   - initial_quantity ↔ initial_count")
        print("   - poultry_house_id ↔ housed_in_id")
    else:
        print("❌ FRONTEND COMPATIBILITY TEST FAILED!")
    print("=" * 80)
    sys.exit(0 if success else 1)
