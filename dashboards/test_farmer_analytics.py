"""
Comprehensive tests for Farmer Analytics endpoints.
Tests permissions, farm scoping, data accuracy, and edge cases.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from farms.models import Farm
from flock_management.models import Flock, DailyProduction, MortalityRecord
from sales_revenue.marketplace_models import Product, MarketplaceOrder, OrderItem
from sales_revenue.processing_models import ProcessingOutput
from feed_inventory.models import FeedPurchase

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for making requests."""
    return APIClient()


@pytest.fixture
def farmer_user(db):
    """Create farmer user."""
    user = User.objects.create_user(
        email='farmer@test.com',
        password='testpass123',
        first_name='John',
        last_name='Farmer',
        phone_number='+233200000001',
        role='FARMER'
    )
    return user


@pytest.fixture
def another_farmer(db):
    """Create another farmer user for cross-farm testing."""
    user = User.objects.create_user(
        email='other@test.com',
        password='testpass123',
        first_name='Jane',
        last_name='Farmer',
        phone_number='+233200000002',
        role='FARMER'
    )
    return user


@pytest.fixture
def farmer_with_farm(db, farmer_user):
    """Create farmer with complete farm setup."""
    farm = Farm.objects.create(
        user=farmer_user,
        farm_name='Test Farm',
        region='Greater Accra',
        constituency='Ayawaso West',
        farm_status='OPERATIONAL',
        total_bird_capacity=2000,
        subscription_type='government_subsidized',
        marketplace_enabled=True
    )
    
    # Create multiple flocks with different ages
    flocks = []
    
    # Active young flock (30 weeks old)
    flock1 = Flock.objects.create(
        farm=farm,
        batch_number='BATCH-001',
        initial_count=500,
        current_count=480,
        breed='Layer',
        placement_date=timezone.now().date() - timedelta(weeks=30),
        status='ACTIVE'
    )
    flocks.append(flock1)
    
    # Active peak flock (50 weeks old)
    flock2 = Flock.objects.create(
        farm=farm,
        batch_number='BATCH-002',
        initial_count=600,
        current_count=550,
        breed='Layer',
        placement_date=timezone.now().date() - timedelta(weeks=50),
        status='ACTIVE'
    )
    flocks.append(flock2)
    
    # Create daily production for last 30 days
    for i in range(30):
        date = timezone.now().date() - timedelta(days=i)
        
        # Flock 1 production
        DailyProduction.objects.create(
            flock=flock1,
            production_date=date,
            total_eggs=250 + (i % 30),
            good_eggs=230 + (i % 25),
            small_eggs=15,
            soft_shell_eggs=5,
            mortality_count=i % 2  # 0-1 deaths
        )
        
        # Flock 2 production (higher production)
        DailyProduction.objects.create(
            flock=flock2,
            production_date=date,
            total_eggs=350 + (i % 40),
            good_eggs=320 + (i % 35),
            small_eggs=20,
            soft_shell_eggs=10,
            mortality_count=i % 3  # 0-2 deaths
        )
    
    # Create mortality records
    MortalityRecord.objects.create(
        flock=flock1,
        date=timezone.now().date() - timedelta(days=10),
        count=5,
        reason='Disease',
        notes='Minor respiratory issue'
    )
    
    MortalityRecord.objects.create(
        flock=flock2,
        date=timezone.now().date() - timedelta(days=5),
        count=8,
        reason='Unknown',
        notes='Sudden deaths'
    )
    
    # Create marketplace items
    egg_item = MarketplaceItem.objects.create(
        farm=farm,
        item_type='EGGS',
        title='Fresh Layer Eggs',
        description='Grade A eggs',
        unit_price=Decimal('35.00'),
        stock_quantity=150,
        is_active=True
    )
    
    # Create processed products
    ProcessingOutput.objects.create(
        farm=farm,
        product_name='Culled Hens',
        stock_quantity=10,
        unit_price=Decimal('80.00')
    )
    
    # Create orders
    buyer = User.objects.create_user(
        email='buyer@test.com',
        password='testpass123',
        first_name='Buyer',
        last_name='Test',
        phone_number='+233200000099',
        role='FARMER'
    )
    
    for i in range(5):
        order = Order.objects.create(
            farm=farm,
            buyer=buyer,
            status='COMPLETED',
            total_amount=Decimal('350.00'),
            created_at=timezone.now() - timedelta(days=i*5)
        )
        
        OrderItem.objects.create(
            order=order,
            item=egg_item,
            quantity=10,
            unit_price=Decimal('35.00')
        )
    
    # Create feed purchases
    for i in range(3):
        FeedPurchase.objects.create(
            farm=farm,
            feed_type='Layer Mash',
            quantity_kg=1000,
            unit_price_ghs=Decimal('2.80'),
            purchase_date=timezone.now().date() - timedelta(days=i*10)
        )
    
    return {'farm': farm, 'user': farmer_user, 'flocks': flocks}


@pytest.fixture
def farm_without_data(db, farmer_user):
    """Create farm with no production data."""
    farm = Farm.objects.create(
        user=farmer_user,
        farm_name='Empty Farm',
        region='Ashanti',
        constituency='Kumasi Central',
        farm_status='PENDING',
        total_bird_capacity=500,
        subscription_type='none',
        marketplace_enabled=False
    )
    return farm


class TestFarmerAnalyticsPermissions:
    """Test authorization and farm scoping."""
    
    def test_unauthorized_access_rejected(self, api_client):
        """Test that unauthenticated requests are rejected."""
        response = api_client.get('/api/farms/analytics/overview/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_farmer_sees_only_own_farm(self, api_client, farmer_with_farm, another_farmer):
        """Test that farmers only see their own farm data."""
        # Create farm for another farmer
        other_farm = Farm.objects.create(
            user=another_farmer,
            farm_name='Other Farm',
            region='Ashanti',
            constituency='Kumasi',
            farm_status='OPERATIONAL',
            total_bird_capacity=1000
        )
        
        # Authenticate as first farmer
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/overview/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should only see own farm data
        assert data['farm']['farm_name'] == 'Test Farm'
    
    def test_admin_cannot_access_farmer_analytics(self, api_client):
        """Test that admin users cannot access farmer analytics endpoints."""
        admin = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            phone_number='+233200000010',
            role='NATIONAL_ADMIN'
        )
        
        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/farms/analytics/overview/')
        
        # Should be forbidden or not found (depends on permission setup)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


class TestAnalyticsOverview:
    """Test analytics overview endpoint."""
    
    def test_overview_structure(self, api_client, farmer_with_farm):
        """Test that overview returns all required sections."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/overview/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check all sections
        assert 'farm' in data
        assert 'production_summary' in data
        assert 'financial_summary' in data
        assert 'flock_summary' in data
        assert 'recent_activity' in data
        assert 'as_of' in data
    
    def test_farm_information_accuracy(self, api_client, farmer_with_farm):
        """Test farm information is accurate."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/overview/')
        
        data = response.json()
        farm_data = data['farm']
        
        assert farm_data['farm_name'] == 'Test Farm'
        assert farm_data['region'] == 'Greater Accra'
        assert farm_data['constituency'] == 'Ayawaso West'
        assert farm_data['farm_status'] == 'OPERATIONAL'
        assert farm_data['total_bird_capacity'] == 2000
    
    def test_production_summary(self, api_client, farmer_with_farm):
        """Test production summary calculations."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/overview/')
        
        data = response.json()
        prod = data['production_summary']
        
        assert prod['total_eggs_30d'] > 0
        assert prod['avg_daily_eggs'] > 0
        assert prod['egg_quality_rate'] >= 0
        assert prod['egg_quality_rate'] <= 100
        assert prod['total_birds'] == 1030  # 480 + 550
        assert prod['active_flocks'] == 2
    
    def test_flock_summary(self, api_client, farmer_with_farm):
        """Test flock summary data."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/overview/')
        
        data = response.json()
        flock = data['flock_summary']
        
        assert flock['total_birds'] == 1030
        assert flock['capacity_utilization'] > 0
        assert flock['mortality_30d'] >= 0
        assert flock['mortality_rate_30d'] >= 0


class TestProductionAnalytics:
    """Test production analytics endpoint."""
    
    def test_production_endpoint_structure(self, api_client, farmer_with_farm):
        """Test production analytics structure."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/production/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert 'summary' in data
        assert 'daily_trend' in data
        assert 'flock_breakdown' in data
        assert 'quality_metrics' in data
        assert 'as_of' in data
    
    def test_daily_trend_data(self, api_client, farmer_with_farm):
        """Test daily production trend."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/production/')
        
        data = response.json()
        daily_trend = data['daily_trend']
        
        assert len(daily_trend) == 30  # Default 30 days
        assert 'date' in daily_trend[0]
        assert 'total_eggs' in daily_trend[0]
        assert 'good_eggs' in daily_trend[0]
        assert 'mortality' in daily_trend[0]
    
    def test_production_period_filter(self, api_client, farmer_with_farm):
        """Test filtering by different periods."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        
        # Test 7-day period
        response = api_client.get('/api/farms/analytics/production/?days=7')
        data = response.json()
        assert len(data['daily_trend']) == 7
        
        # Test 90-day period
        response = api_client.get('/api/farms/analytics/production/?days=90')
        data = response.json()
        # Should have data for 30 days (that's what we created)
        assert len(data['daily_trend']) <= 90
    
    def test_flock_breakdown(self, api_client, farmer_with_farm):
        """Test per-flock production breakdown."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/production/')
        
        data = response.json()
        flocks = data['flock_breakdown']
        
        assert len(flocks) == 2
        
        # Each flock should have production data
        for flock in flocks:
            assert 'batch_number' in flock
            assert 'total_eggs' in flock
            assert 'avg_daily_eggs' in flock
            assert 'current_count' in flock


class TestFinancialAnalytics:
    """Test financial analytics endpoint."""
    
    def test_financial_endpoint_structure(self, api_client, farmer_with_farm):
        """Test financial analytics structure."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/financial/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert 'summary' in data
        assert 'revenue' in data
        assert 'expenses' in data
        assert 'profitability' in data
        assert 'as_of' in data
    
    def test_revenue_calculations(self, api_client, farmer_with_farm):
        """Test revenue calculations."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/financial/')
        
        data = response.json()
        revenue = data['revenue']
        
        assert 'total_revenue_30d' in revenue
        assert 'marketplace_sales' in revenue
        assert 'total_orders' in revenue
        assert revenue['total_orders'] == 5
    
    def test_expense_tracking(self, api_client, farmer_with_farm):
        """Test expense calculations."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/financial/')
        
        data = response.json()
        expenses = data['expenses']
        
        assert 'total_expenses_30d' in expenses
        assert 'feed_cost' in expenses
        assert expenses['feed_cost'] > 0  # We created feed purchases
    
    def test_profitability_metrics(self, api_client, farmer_with_farm):
        """Test profitability calculations."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/financial/')
        
        data = response.json()
        profit = data['profitability']
        
        assert 'gross_profit' in profit
        assert 'profit_margin_percent' in profit
        assert 'cost_per_egg' in profit


class TestFlockHealthAnalytics:
    """Test flock health analytics endpoint."""
    
    def test_flock_health_structure(self, api_client, farmer_with_farm):
        """Test flock health analytics structure."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/flock-health/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert 'mortality_summary' in data
        assert 'mortality_by_reason' in data
        assert 'flock_ages' in data
        assert 'health_alerts' in data
        assert 'as_of' in data
    
    def test_mortality_calculations(self, api_client, farmer_with_farm):
        """Test mortality calculations."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/flock-health/')
        
        data = response.json()
        mortality = data['mortality_summary']
        
        assert 'total_deaths_30d' in mortality
        assert 'mortality_rate_percent' in mortality
        assert mortality['total_deaths_30d'] >= 0
        assert mortality['mortality_rate_percent'] >= 0
    
    def test_mortality_by_reason(self, api_client, farmer_with_farm):
        """Test mortality breakdown by reason."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/flock-health/')
        
        data = response.json()
        by_reason = data['mortality_by_reason']
        
        assert isinstance(by_reason, list)
        # Should have at least the reasons we created
        reasons = [r['reason'] for r in by_reason]
        assert 'Disease' in reasons or 'Unknown' in reasons
    
    def test_flock_age_distribution(self, api_client, farmer_with_farm):
        """Test flock age distribution."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/flock-health/')
        
        data = response.json()
        ages = data['flock_ages']
        
        assert 'pullets_0_18_weeks' in ages
        assert 'young_layers_18_40_weeks' in ages
        assert 'peak_layers_40_72_weeks' in ages
        assert 'mature_layers_72_plus_weeks' in ages
        
        # We have one flock at 30 weeks and one at 50 weeks
        assert ages['young_layers_18_40_weeks'] == 480
        assert ages['peak_layers_40_72_weeks'] == 550


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_farm_without_production_data(self, api_client, farmer_user, farm_without_data):
        """Test analytics with no production data."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/farms/analytics/overview/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should return zero values, not error
        assert data['production_summary']['total_eggs_30d'] == 0
        assert data['flock_summary']['total_birds'] == 0
    
    def test_farmer_without_farm(self, api_client):
        """Test farmer with no farm."""
        farmer = User.objects.create_user(
            email='nofarm@test.com',
            password='testpass123',
            first_name='No',
            last_name='Farm',
            phone_number='+233200000020',
            role='FARMER'
        )
        
        api_client.force_authenticate(user=farmer)
        response = api_client.get('/api/farms/analytics/overview/')
        
        # Should return 404 or appropriate error
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_invalid_period_parameter(self, api_client, farmer_with_farm):
        """Test handling of invalid period."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        
        # Negative period
        response = api_client.get('/api/farms/analytics/production/?days=-5')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        
        # Non-numeric period
        response = api_client.get('/api/farms/analytics/production/?days=abc')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    
    def test_inactive_farm(self, api_client, farmer_user):
        """Test analytics for inactive farm."""
        farm = Farm.objects.create(
            user=farmer_user,
            farm_name='Inactive Farm',
            region='Western',
            constituency='Takoradi',
            farm_status='SUSPENDED',
            total_bird_capacity=500
        )
        
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/farms/analytics/overview/')
        
        # Should still return data (farm exists)
        assert response.status_code == status.HTTP_200_OK


class TestExportFunctionality:
    """Test farmer analytics export endpoints."""
    
    def test_excel_export_requires_auth(self, api_client):
        """Test Excel export requires authentication."""
        response = api_client.get('/api/farms/analytics/export/excel/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_excel_export_success(self, api_client, farmer_with_farm):
        """Test successful Excel export."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/export/excel/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'spreadsheet' in response['Content-Type'] or 'excel' in response['Content-Type'].lower()
    
    def test_pdf_export_success(self, api_client, farmer_with_farm):
        """Test successful PDF export."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/export/pdf/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'pdf' in response['Content-Type'].lower()
    
    def test_csv_export_sections(self, api_client, farmer_with_farm):
        """Test CSV export for different sections."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        
        sections = ['production', 'financial', 'flock-health']
        
        for section in sections:
            response = api_client.get(f'/api/farms/analytics/export/csv/{section}/')
            assert response.status_code == status.HTTP_200_OK
            assert 'csv' in response['Content-Type'].lower()


class TestDataAccuracy:
    """Test calculation accuracy and data integrity."""
    
    def test_egg_quality_rate_calculation(self, api_client, farmer_with_farm):
        """Test egg quality rate is calculated correctly."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/production/')
        
        data = response.json()
        quality_metrics = data['quality_metrics']
        
        # Quality rate should be between 0 and 100
        assert 0 <= quality_metrics['quality_rate_percent'] <= 100
        
        # Good eggs should be <= total eggs
        summary = data['summary']
        assert summary['good_eggs_30d'] <= summary['total_eggs_30d']
    
    def test_capacity_utilization_calculation(self, api_client, farmer_with_farm):
        """Test capacity utilization is accurate."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/overview/')
        
        data = response.json()
        flock = data['flock_summary']
        
        # Utilization = (total_birds / capacity) * 100
        expected_utilization = (1030 / 2000) * 100
        assert abs(flock['capacity_utilization'] - expected_utilization) < 0.1
    
    def test_mortality_rate_calculation(self, api_client, farmer_with_farm):
        """Test mortality rate calculation."""
        api_client.force_authenticate(user=farmer_with_farm['user'])
        response = api_client.get('/api/farms/analytics/flock-health/')
        
        data = response.json()
        mortality = data['mortality_summary']
        
        # Mortality rate should be reasonable
        assert 0 <= mortality['mortality_rate_percent'] <= 100
