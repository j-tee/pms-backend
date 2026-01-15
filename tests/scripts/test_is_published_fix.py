#!/usr/bin/env python3
"""
Test script to verify is_published field is included in batch list API response
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from farms.batch_enrollment_models import Batch
from accounts.models import User
from rest_framework.test import APIRequestFactory
from accounts.batch_admin_views import AdminBatchListView

def test_is_published_in_response():
    """Test that is_published field is included in list response"""
    
    # Get a super admin user
    user = User.objects.filter(role='super_admin', is_active=True).first()
    
    if not user:
        print("❌ No super admin user found. Using existing admin user...")
        user = User.objects.filter(is_staff=True, is_active=True).first()
        
    if not user:
        print("❌ No admin user available for testing")
        return
    
    print(f"✅ Using user: {user.email} (role: {user.role})")
    
    # Check if we have any batches
    batch_count = Batch.objects.filter(archived=False).count()
    print(f"✅ Found {batch_count} non-archived batches")
    
    if batch_count == 0:
        print("⚠️  No batches found to test")
        return
    
    # Create API request
    factory = APIRequestFactory()
    request = factory.get('/api/admin/batches/')
    request.user = user
    
    # Call the view
    view = AdminBatchListView.as_view()
    response = view(request)
    
    print(f"✅ API Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.data
        results = data.get('results', [])
        
        if results:
            first_batch = results[0]
            print(f"\n📋 First batch in response:")
            print(f"   - ID: {first_batch.get('id')}")
            print(f"   - Batch Code: {first_batch.get('batch_code')}")
            print(f"   - Batch Name: {first_batch.get('batch_name')}")
            print(f"   - is_active: {first_batch.get('is_active')}")
            print(f"   - is_published: {first_batch.get('is_published')}")
            print(f"   - is_accepting_applications: {first_batch.get('is_accepting_applications')}")
            
            if 'is_published' in first_batch:
                print(f"\n✅ SUCCESS: 'is_published' field IS included in response!")
                print(f"   Value: {first_batch['is_published']}")
            else:
                print(f"\n❌ FAILED: 'is_published' field is MISSING from response!")
                print(f"\n📄 Available fields: {list(first_batch.keys())}")
        else:
            print("⚠️  No results returned")
    else:
        print(f"❌ API request failed with status {response.status_code}")
        print(f"Response: {response.data}")

if __name__ == '__main__':
    print("=" * 60)
    print("Testing is_published field in batch list API response")
    print("=" * 60)
    test_is_published_in_response()
    print("=" * 60)
