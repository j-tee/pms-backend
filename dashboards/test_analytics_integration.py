"""
Integration tests for analytics system.
Tests end-to-end workflows, caching, and cross-module integration.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from farms.models import Farm
from farms.batch_enrollment_models import Batch, BatchEnrollmentApplication
from flock_management.models import Flock, DailyProduction
from sales_revenue.marketplace_models import Product, MarketplaceOrder, OrderItem
from accounts.models import Role

User = get_user_model()


@pytest.fixture
def complete_ecosystem(db):
    """Create a complete ecosystem with multiple farms, users, and data."""
    
    # Create admin users
    super_admin = User.objects.create_user(
        username='superadmin_test',
        email='superadmin@test.com',
        password='testpass123',
        first_name='Super',
        last_name='Admin',
        phone='+233500000001',
        role='SUPER_ADMIN'
    )
    
    regional_coord = User.objects.create_user(
        username='regional_coord_test',
        email='regional@test.com',
        password='testpass123',
        first_name='Regional',
        last_name='Coordinator',
        phone='+233500000002',
        role='REGIONAL_COORDINATOR'
    )
    regional_coord.assigned_region = 'Greater Accra'
    regional_coord.save()
    
    # Create batches
    batch = Batch.objects.create(
        batch_name='2025 Q1 Batch',
        batch_code='YEA-2025-Q1',
        description='First quarter recruitment',
        implementing_agency='Youth Employment Agency',
        target_region='Greater Accra',
        start_date=timezone.now().date() - timedelta(days=90),
        end_date=timezone.now().date() + timedelta(days=90),
        total_slots=100,
        is_active=True,
        is_published=True
    )
    
    # Create 10 farmers with varying data
    farmers = []
    farms = []
    
    for i in range(10):
        # Create farmer user
        farmer = User.objects.create_user(
            username=f'farmer{i}_test',
            email=f'farmer{i}@test.com',
            password='testpass123',
            first_name=f'Farmer{i}',
            last_name='Test',
            phone=f'+23350000{1000+i}',
            role='FARMER'
        )
        farmers.append(farmer)
        
        # Create farm
        farm = Farm.objects.create(
            user=farmer,
            farm_name=f'Farm {i}',
            primary_constituency='Ayawaso West' if i < 4 else ('Ablekuma Central' if i < 7 else 'Kumasi Central'),
            farm_status='OPERATIONAL' if i < 8 else 'PENDING',
            total_bird_capacity=1000 * (i + 1),
            subscription_type='government_subsidized' if i < 5 else 'standard',
            marketplace_enabled=i < 6,
            date_of_birth='1990-01-01',
            years_in_poultry=2,
            number_of_poultry_houses=2
        )
        farms.append(farm)
        
        # Enroll in batch (some farms)
        if i < 7:
            BatchEnrollmentApplication.objects.create(
                farm=farm,
                batch=batch,
                status='APPROVED'
            )
        
        # Create flocks and production for operational farms
        if i < 8:
            flock = Flock.objects.create(
                farm=farm,
                batch_number=f'BATCH-{i}',
                initial_count=500 * (i + 1),
                current_count=450 * (i + 1),
                breed='Layer',
                placement_date=timezone.now().date() - timedelta(days=60),
                status='ACTIVE'
            )
            
            # Create 30 days of production
            for day in range(30):
                date = timezone.now().date() - timedelta(days=day)
                DailyProduction.objects.create(
                    flock=flock,
                    production_date=date,
                    total_eggs=200 * (i + 1) + (day % 20),
                    good_eggs=180 * (i + 1) + (day % 15),
                    small_eggs=15,
                    soft_shell_eggs=5,
                    mortality_count=day % 2
                )
            
            # Create marketplace items for enabled farms
            if farm.marketplace_enabled:
                item = MarketplaceItem.objects.create(
                    farm=farm,
                    item_type='EGGS',
                    title=f'Eggs from Farm {i}',
                    unit_price=Decimal('30.00'),
                    stock_quantity=100,
                    is_active=True
                )
                
                # Create orders
                if i < 4:
                    buyer = farmers[(i + 1) % 10]
                    for order_num in range(3):
                        order = Order.objects.create(
                            farm=farm,
                            buyer=buyer,
                            status='COMPLETED',
                            total_amount=Decimal('300.00')
                        )
                        OrderItem.objects.create(
                            order=order,
                            item=item,
                            quantity=10,
                            unit_price=Decimal('30.00')
                        )
    
    return {
        'super_admin': super_admin,
        'regional_coord': regional_coord,
        'farmers': farmers,
        'farms': farms,
        'batch': batch
    }


class TestEndToEndWorkflows:
    """Test complete user workflows."""
    
    def test_admin_dashboard_to_farm_drill_down(self, api_client, complete_ecosystem):
        """Test navigating from national dashboard to individual farm."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Step 1: View executive dashboard
        response = api_client.get('/api/admin/reports/executive/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['program_performance']['summary']['total_farms'] == 10
        
        # Step 2: Get drill-down options
        response = api_client.get('/api/admin/reports/drill-down/')
        assert response.status_code == status.HTTP_200_OK
        regions = response.json()['regions']
        assert len(regions) == 2
        
        # Step 3: Drill into Greater Accra
        response = api_client.get('/api/admin/reports/executive/?region=Greater%20Accra')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['program_performance']['summary']['total_farms'] == 7
        
        # Step 4: Get constituencies in Greater Accra
        response = api_client.get('/api/admin/reports/drill-down/?region=Greater%20Accra')
        assert response.status_code == status.HTTP_200_OK
        constituencies = response.json()['constituencies']
        assert len(constituencies) == 2
        
        # Step 5: Drill into Ayawaso West
        response = api_client.get('/api/admin/reports/executive/?region=Greater%20Accra&constituency=Ayawaso%20West')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['program_performance']['summary']['total_farms'] == 4
        
        # Step 6: Get farm list
        response = api_client.get('/api/admin/reports/farms/?region=Greater%20Accra&constituency=Ayawaso%20West')
        assert response.status_code == status.HTTP_200_OK
        farms = response.json()['results']
        assert len(farms) == 4
    
    def test_farmer_analytics_full_workflow(self, api_client, complete_ecosystem):
        """Test farmer viewing all analytics sections."""
        farmer = complete_ecosystem['farmers'][0]
        api_client.force_authenticate(user=farmer)
        
        # Overview
        response = api_client.get('/api/farms/analytics/overview/')
        assert response.status_code == status.HTTP_200_OK
        overview = response.json()
        assert 'farm' in overview
        
        # Production details
        response = api_client.get('/api/farms/analytics/production/')
        assert response.status_code == status.HTTP_200_OK
        production = response.json()
        assert 'daily_trend' in production
        
        # Financial analytics
        response = api_client.get('/api/farms/analytics/financial/')
        assert response.status_code == status.HTTP_200_OK
        financial = response.json()
        assert 'revenue' in financial
        
        # Flock health
        response = api_client.get('/api/farms/analytics/flock-health/')
        assert response.status_code == status.HTTP_200_OK
        health = response.json()
        assert 'mortality_summary' in health
    
    def test_export_workflow(self, api_client, complete_ecosystem):
        """Test exporting reports in different formats."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Excel export
        response = api_client.get('/api/admin/reports/export/excel/executive/')
        assert response.status_code == status.HTTP_200_OK
        
        # PDF export
        response = api_client.get('/api/admin/reports/export/pdf/executive/')
        assert response.status_code == status.HTTP_200_OK
        
        # CSV exports
        for section in ['production', 'regional', 'financial']:
            response = api_client.get(f'/api/admin/reports/export/csv/{section}/')
            assert response.status_code == status.HTTP_200_OK


class TestCaching:
    """Test caching behavior."""
    
    def test_cache_invalidation_on_new_data(self, api_client, complete_ecosystem):
        """Test that cache is invalidated when new data is added."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Clear cache
        cache.clear()
        
        # First request (should cache)
        response1 = api_client.get('/api/admin/reports/production/')
        data1 = response1.json()
        initial_eggs = data1['production']['total_eggs']
        
        # Add new production
        farm = complete_ecosystem['farms'][0]
        flock = farm.flocks.first()
        DailyProduction.objects.create(
            flock=flock,
            production_date=timezone.now().date(),
            total_eggs=500,
            good_eggs=450
        )
        
        # Second request (should reflect new data)
        response2 = api_client.get('/api/admin/reports/production/')
        data2 = response2.json()
        new_eggs = data2['production']['total_eggs']
        
        # New total should be higher
        assert new_eggs > initial_eggs
    
    def test_different_scopes_cached_separately(self, api_client, complete_ecosystem):
        """Test that different geographic scopes are cached separately."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        cache.clear()
        
        # National level
        response1 = api_client.get('/api/admin/reports/production/')
        national_data = response1.json()
        
        # Regional level
        response2 = api_client.get('/api/admin/reports/production/?region=Greater%20Accra')
        regional_data = response2.json()
        
        # Should be different
        assert national_data['production']['total_eggs'] != regional_data['production']['total_eggs']


class TestConcurrentAccess:
    """Test concurrent access scenarios."""
    
    def test_multiple_admins_same_data(self, api_client, complete_ecosystem):
        """Test multiple admins accessing same data."""
        admin = complete_ecosystem['super_admin']
        regional = complete_ecosystem['regional_coord']
        
        # Both access national data
        client1 = APIClient()
        client1.force_authenticate(user=admin)
        
        client2 = APIClient()
        client2.force_authenticate(user=regional)
        
        response1 = client1.get('/api/admin/reports/executive/')
        response2 = client2.get('/api/admin/reports/executive/')
        
        # Super admin sees all
        assert response1.json()['program_performance']['summary']['total_farms'] == 10
        
        # Regional sees national by default but scoped to their region when filtered
        response3 = client2.get('/api/admin/reports/executive/?region=Greater%20Accra')
        assert response3.json()['program_performance']['summary']['total_farms'] == 7


class TestDataConsistency:
    """Test data consistency across endpoints."""
    
    def test_farm_count_consistency(self, api_client, complete_ecosystem):
        """Test that farm counts are consistent across endpoints."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Get count from executive dashboard
        response = api_client.get('/api/admin/reports/executive/')
        exec_count = response.json()['program_performance']['summary']['total_farms']
        
        # Get count from program performance
        response = api_client.get('/api/admin/reports/program-performance/')
        prog_count = response.json()['summary']['total_farms']
        
        # Get count from farms list
        response = api_client.get('/api/admin/reports/farms/')
        farms_count = response.json()['count']
        
        # All should match
        assert exec_count == prog_count == farms_count == 10
    
    def test_production_totals_consistency(self, api_client, complete_ecosystem):
        """Test that production totals match across views."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Executive dashboard
        response = api_client.get('/api/admin/reports/executive/')
        exec_eggs = response.json()['production']['production']['total_eggs']
        
        # Production endpoint
        response = api_client.get('/api/admin/reports/production/')
        prod_eggs = response.json()['production']['total_eggs']
        
        # Should match
        assert exec_eggs == prod_eggs
    
    def test_regional_totals_sum_to_national(self, api_client, complete_ecosystem):
        """Test that regional totals sum to national totals."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Get national total
        response = api_client.get('/api/admin/reports/production/')
        national_eggs = response.json()['production']['total_eggs']
        
        # Get regional comparison
        response = api_client.get('/api/admin/reports/production/regional-comparison/')
        regional_data = response.json()
        
        # Sum regional totals
        regional_sum = sum(r['total_eggs'] for r in regional_data['regions'])
        
        # Should match (or be very close accounting for rounding)
        assert abs(national_eggs - regional_sum) < 10


class TestPerformance:
    """Test performance with large datasets."""
    
    def test_query_efficiency_with_many_farms(self, api_client, complete_ecosystem):
        """Test that queries remain efficient with more data."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Time the request
        import time
        start = time.time()
        response = api_client.get('/api/admin/reports/executive/')
        duration = time.time() - start
        
        assert response.status_code == status.HTTP_200_OK
        # Should complete in reasonable time (adjust as needed)
        assert duration < 5.0  # 5 seconds max
    
    def test_pagination_works(self, api_client, complete_ecosystem):
        """Test that farm list pagination works correctly."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Get first page
        response = api_client.get('/api/admin/reports/farms/?page=1')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert 'count' in data
        assert 'next' in data
        assert 'previous' in data
        assert 'results' in data


class TestErrorRecovery:
    """Test error handling and recovery."""
    
    def test_graceful_handling_of_corrupted_data(self, api_client, complete_ecosystem):
        """Test system handles data anomalies gracefully."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Create a flock with impossible data
        farm = complete_ecosystem['farms'][0]
        Flock.objects.create(
            farm=farm,
            batch_number='CORRUPT',
            initial_count=100,
            current_count=200,  # More than initial (shouldn't happen)
            breed='Layer',
            placement_date=timezone.now().date(),
            status='ACTIVE'
        )
        
        # Should still return data without crashing
        response = api_client.get('/api/admin/reports/production/')
        assert response.status_code == status.HTTP_200_OK
    
    def test_missing_related_data(self, api_client, complete_ecosystem):
        """Test handling of missing related data."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        # Create farm without flocks
        farmer = User.objects.create_user(
            username='noflock_farmer',
            email='noflock@test.com',
            password='testpass123',
            first_name='No',
            last_name='Flock',
            phone='+233500009999',
            role='FARMER'
        )
        
        Farm.objects.create(
            user=farmer,
            farm_name='No Flock Farm',
            primary_constituency='Tamale',
            farm_status='OPERATIONAL',
            total_bird_capacity=1000,
            date_of_birth='1990-01-01',
            years_in_poultry=2,
            number_of_poultry_houses=1
        )
        
        # Should handle gracefully
        response = api_client.get('/api/admin/reports/production/')
        assert response.status_code == status.HTTP_200_OK


class TestBatchIntegration:
    """Test integration with batch enrollment system."""
    
    def test_batch_enrollment_metrics(self, api_client, complete_ecosystem):
        """Test that batch enrollment data is correctly reflected."""
        admin = complete_ecosystem['super_admin']
        api_client.force_authenticate(user=admin)
        
        response = api_client.get('/api/admin/reports/program-performance/')
        data = response.json()
        
        # Should show active batches
        assert data['enrollment']['active_batches'] == 1
        
        # Should show enrollments (7 farms enrolled)
        assert data['enrollment']['total_batch_enrollments'] >= 7
