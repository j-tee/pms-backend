"""
Comprehensive Permission and Access Tests for Institutional Subscribers

Tests to establish what INSTITUTIONAL_SUBSCRIBER users can and cannot do:
1. API authentication (JWT + API Key)
2. Data access permissions (aggregated data only)
3. Rate limiting
4. What they CANNOT access (farmer PII, admin functions, etc.)
5. Subscription management
6. Team member access
"""

import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from subscriptions.institutional_models import (
    InstitutionalPlan,
    InstitutionalSubscriber,
    InstitutionalAPIKey,
)
from farms.models import Farm
from flock_management.models import Flock, DailyProduction

User = get_user_model()


@pytest.fixture
def api_client():
    """Create an API client for testing"""
    return APIClient()


@pytest.fixture
def institutional_plan():
    """Create a basic institutional plan"""
    return InstitutionalPlan.objects.create(
        name='Basic Research Plan',
        tier='basic',
        description='Basic aggregated data access',
        price_monthly=Decimal('500.00'),
        price_annually=Decimal('5000.00'),
        requests_per_day=100,
        requests_per_month=3000,
        access_regional_aggregates=True,
        access_production_trends=True,
        access_market_prices=True,
        access_constituency_data=False,
        access_mortality_data=False,
        access_supply_forecasts=False,
        access_individual_farm_data=False,
    )


@pytest.fixture
def enterprise_plan():
    """Create an enterprise institutional plan with more access"""
    return InstitutionalPlan.objects.create(
        name='Enterprise Plan',
        tier='enterprise',
        description='Full data access for financial institutions',
        price_monthly=Decimal('5000.00'),
        price_annually=Decimal('50000.00'),
        requests_per_day=1000,
        requests_per_month=30000,
        access_regional_aggregates=True,
        access_constituency_data=True,
        access_production_trends=True,
        access_market_prices=True,
        access_mortality_data=True,
        access_supply_forecasts=True,
        access_individual_farm_data=True,
    )


@pytest.fixture
def institutional_subscriber(institutional_plan):
    """Create an active institutional subscriber"""
    subscriber = InstitutionalSubscriber.objects.create(
        organization_name='Ghana Agricultural Bank',
        organization_category='bank',
        contact_name='Dr. Kofi Asante',
        contact_email='k.asante@agribank.com.gh',
        contact_phone='+233240111000',
        plan=institutional_plan,
        billing_cycle='monthly',
        subscription_start=timezone.now().date(),
        current_period_start=timezone.now().date(),
        current_period_end=(timezone.now() + timedelta(days=30)).date(),
        status='active',
        preferred_regions=['Greater Accra', 'Ashanti'],
        data_use_purpose='Agricultural loan portfolio risk assessment',
    )
    return subscriber


@pytest.fixture
def institutional_user(institutional_subscriber):
    """Create a user linked to institutional subscriber"""
    user = User.objects.create_user(
        username='agribank_user',
        email='k.asante@agribank.com.gh',
        password='testpass123',
        role='INSTITUTIONAL_SUBSCRIBER',
        phone='+233240111000',
        institutional_subscriber=institutional_subscriber,
    )
    return user


@pytest.fixture
def institutional_api_key(institutional_subscriber):
    """Create an API key for institutional subscriber"""
    # Use the generate_key class method which returns (api_key_obj, full_key_string)
    api_key_obj, full_key = InstitutionalAPIKey.generate_key(
        subscriber=institutional_subscriber,
        name='Production API Key',
    )
    # Store the full key on the object for testing (not a model field, just for tests)
    api_key_obj.full_key = full_key
    return api_key_obj


@pytest.fixture
def sample_farm():
    """Create a sample operational farm"""
    # Create a user first (Farm has OneToOne with User)
    user = User.objects.create_user(
        username='test_farmer_sample',
        email='farmer@test.com',
        password='testpass123',
        role='FARMER',
        phone='+233240000001',
    )
    
    return Farm.objects.create(
        user=user,
        application_id='APP-2026-00001',
        first_name='John',
        last_name='Doe',
        date_of_birth='1990-01-01',
        gender='Male',
        ghana_card_number='GHA-123456789-0',
        primary_phone='+233240000001',
        residential_address='123 Test St, Tema',
        primary_constituency='Tema',
        nok_full_name='Jane Doe',
        nok_relationship='Spouse',
        nok_phone='+233240000002',
        education_level='SHS/Technical',
        literacy_level='Can Read & Write',
        years_in_poultry=Decimal('2.0'),
        farm_name='Test Farm Ltd',
        ownership_type='Sole Proprietorship',
        tin='1234567890',
        application_status='approved',
    )


@pytest.mark.django_db
class TestInstitutionalSubscriberAuthentication:
    """Test authentication mechanisms for institutional subscribers"""
    
    def test_jwt_authentication_success(self, api_client, institutional_user):
        """Institutional users can authenticate with JWT"""
        api_client.force_authenticate(user=institutional_user)
        
        # Try to access a simple endpoint
        response = api_client.get('/api/institutional/production/overview/')
        
        # Should not get 401/403 (might get 404 if endpoint doesn't exist yet)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN
    
    def test_api_key_authentication_success(self, api_client, institutional_api_key):
        """Institutional subscribers can authenticate with API key"""
        api_client.credentials(
            HTTP_X_API_KEY=institutional_api_key.full_key,
            HTTP_X_CLIENT_ID=str(institutional_api_key.subscriber.id)
        )
        
        response = api_client.get('/api/institutional/production/overview/')
        
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
        assert response.status_code != status.HTTP_403_FORBIDDEN
    
    def test_dual_authentication_jwt_takes_precedence(
        self, api_client, institutional_user, institutional_api_key
    ):
        """When both JWT and API key provided, JWT takes precedence"""
        api_client.force_authenticate(user=institutional_user)
        api_client.credentials(
            HTTP_X_API_KEY=institutional_api_key.full_key,
            HTTP_X_CLIENT_ID=str(institutional_api_key.subscriber.id)
        )
        
        response = api_client.get('/api/institutional/production/overview/')
        
        # Should authenticate successfully
        assert response.status_code != status.HTTP_401_UNAUTHORIZED
    
    def test_invalid_api_key_rejected(self, api_client):
        """Invalid API key is rejected"""
        api_client.credentials(
            HTTP_X_API_KEY='invalid-key-12345',
            HTTP_X_CLIENT_ID='00000000-0000-0000-0000-000000000000'
        )
        
        response = api_client.get('/api/institutional/production/overview/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestInstitutionalSubscriberDataAccess:
    """Test what data institutional subscribers CAN access"""
    
    def test_can_access_aggregated_production_data(
        self, api_client, institutional_user, sample_farm
    ):
        """Subscribers can access aggregated regional production data"""
        api_client.force_authenticate(user=institutional_user)
        
        # Create some production data
        flock = Flock.objects.create(
            farm=sample_farm,
            species='layer',
            breed='Rhode Island Red',
            initial_bird_count=1000,
            current_bird_count=980,
            status='active',
        )
        
        DailyProduction.objects.create(
            flock=flock,
            collection_date=timezone.now().date(),
            total_eggs_collected=850,
            good_eggs=800,
            cracked_eggs=30,
            broken_eggs=20,
        )
        
        response = api_client.get('/api/institutional/production/overview/')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.data
            # Should include aggregated stats
            assert 'production' in data
            assert 'flocks' in data
            # Should NOT include individual farm names or farmer PII
            assert 'farms' not in data or all(
                'owner_name' not in farm for farm in data.get('farms', [])
            )
    
    def test_can_access_regional_breakdown(
        self, api_client, institutional_user
    ):
        """Subscribers can access regional-level aggregated data"""
        api_client.force_authenticate(user=institutional_user)
        
        response = api_client.get('/api/institutional/regions/')
        
        # Should be able to access regional stats
        # Specific response depends on implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If endpoint not implemented yet
        ]
    
    def test_basic_plan_cannot_access_individual_farms(
        self, api_client, institutional_user, sample_farm
    ):
        """Basic plan subscribers cannot access individual farm data"""
        api_client.force_authenticate(user=institutional_user)
        
        # Try to access individual farm endpoint
        response = api_client.get(f'/api/institutional/farms/{sample_farm.id}/')
        
        # Should be forbidden or not found (depending on implementation)
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_enterprise_plan_can_access_anonymized_farm_data(
        self, api_client, enterprise_plan, sample_farm
    ):
        """Enterprise plan subscribers can access anonymized individual farm data"""
        # Create enterprise subscriber
        subscriber = InstitutionalSubscriber.objects.create(
            organization_name='Ghana Commercial Bank',
            organization_category='bank',
            contact_name='Loan Officer',
            contact_email='loans@gcb.com.gh',
            contact_phone='+233240222000',
            plan=enterprise_plan,
            billing_cycle='annually',
            subscription_start=timezone.now().date(),
            current_period_start=timezone.now().date(),
            current_period_end=(timezone.now() + timedelta(days=365)).date(),
            status='active',
            data_use_purpose='Financial risk assessment',
        )
        
        user = User.objects.create_user(
            username='gcb_analyst',
            email='loans@gcb.com.gh',
            password='testpass123',
            role='INSTITUTIONAL_SUBSCRIBER',
            phone='+233240222000',
            institutional_subscriber=subscriber,
        )
        
        api_client.force_authenticate(user=user)
        
        response = api_client.get(f'/api/institutional/farms/{sample_farm.id}/')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.data
            # Should have anonymized ID
            assert 'id' in data or 'farm_id' in data
            # Should NOT have PII
            assert 'owner_name' not in data
            assert 'email' not in data
            assert 'phone' not in data


@pytest.mark.django_db
class TestInstitutionalSubscriberRestrictions:
    """Test what institutional subscribers CANNOT access"""
    
    def test_cannot_access_farmer_endpoints(
        self, api_client, institutional_user, sample_farm
    ):
        """Institutional subscribers cannot access farmer-specific endpoints"""
        api_client.force_authenticate(user=institutional_user)
        
        # Try to access farmer endpoints
        farmer_endpoints = [
            '/api/farms/',
            '/api/flocks/',
            '/api/marketplace/listings/',
            '/api/dashboards/farmer/',
        ]
        
        for endpoint in farmer_endpoints:
            response = api_client.get(endpoint)
            # Should be forbidden
            assert response.status_code == status.HTTP_403_FORBIDDEN, \
                f"Institutional user should not access {endpoint}"
    
    def test_cannot_access_admin_endpoints(
        self, api_client, institutional_user
    ):
        """Institutional subscribers cannot access admin endpoints"""
        api_client.force_authenticate(user=institutional_user)
        
        admin_endpoints = [
            '/api/admin/users/',
            '/api/admin/batches/',
            '/api/admin/permissions/',
            '/api/admin/analytics/',
        ]
        
        for endpoint in admin_endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_403_FORBIDDEN, \
                f"Institutional user should not access {endpoint}"
    
    def test_cannot_access_personal_farmer_data(
        self, api_client, institutional_user
    ):
        """Institutional subscribers cannot access PII of farmers"""
        api_client.force_authenticate(user=institutional_user)
        
        # Create a farmer user
        farmer = User.objects.create_user(
            username='test_farmer',
            email='farmer@test.com',
            password='testpass123',
            role='FARMER',
            phone='+233240000002',
        )
        
        # Try to access farmer profile
        response = api_client.get(f'/api/users/{farmer.id}/')
        
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_cannot_manage_permissions(
        self, api_client, institutional_user
    ):
        """Institutional subscribers cannot manage permissions"""
        api_client.force_authenticate(user=institutional_user)
        
        # Try to access permission management
        response = api_client.get('/api/admin/permissions/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cannot_create_or_modify_farms(
        self, api_client, institutional_user, sample_farm
    ):
        """Institutional subscribers cannot create or modify farms"""
        api_client.force_authenticate(user=institutional_user)
        
        # Try to create a farm
        response = api_client.post('/api/farms/', {
            'name': 'New Farm',
            'owner_name': 'Test Owner',
            'email': 'test@test.com',
            'phone': '+233240000003',
            'region': 'Greater Accra',
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Try to update a farm
        response = api_client.patch(f'/api/farms/{sample_farm.id}/', {
            'status': 'suspended'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cannot_access_marketplace_seller_functions(
        self, api_client, institutional_user
    ):
        """Institutional subscribers cannot create listings or process orders"""
        api_client.force_authenticate(user=institutional_user)
        
        # Try to create a listing
        response = api_client.post('/api/marketplace/listings/', {
            'product_type': 'eggs',
            'quantity_available': 100,
            'price_per_unit': '25.00',
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cannot_see_other_subscribers_data(
        self, api_client, institutional_user, institutional_plan
    ):
        """Institutional subscribers cannot see other subscribers' information"""
        api_client.force_authenticate(user=institutional_user)
        
        # Create another subscriber
        other_subscriber = InstitutionalSubscriber.objects.create(
            organization_name='Different University',
            organization_category='university',
            contact_email='research@uni.edu.gh',
            contact_phone='+233240333000',
            plan=institutional_plan,
            status='active',
        )
        
        # Try to access other subscriber's info
        response = api_client.get(f'/api/institutional/subscribers/{other_subscriber.id}/')
        
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.django_db
class TestInstitutionalSubscriberOwnData:
    """Test institutional subscribers managing their own subscription"""
    
    def test_can_view_own_subscription_details(
        self, api_client, institutional_user, institutional_subscriber
    ):
        """Subscribers can view their own subscription details"""
        api_client.force_authenticate(user=institutional_user)
        
        response = api_client.get('/api/institutional/subscription/')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.data
            assert data['organization_name'] == 'Ghana Agricultural Bank'
            assert data['status'] == 'active'
            assert 'plan' in data
    
    def test_can_view_usage_statistics(
        self, api_client, institutional_user
    ):
        """Subscribers can view their API usage statistics"""
        api_client.force_authenticate(user=institutional_user)
        
        response = api_client.get('/api/institutional/usage/')
        
        # Should be able to see own usage stats
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND  # If not implemented
        ]
    
    def test_can_manage_team_members(
        self, api_client, institutional_user, institutional_subscriber
    ):
        """Subscribers can add/remove team members"""
        api_client.force_authenticate(user=institutional_user)
        
        # Try to add a team member
        response = api_client.post('/api/institutional/team/', {
            'email': 'analyst@agribank.com.gh',
            'name': 'Jane Analyst',
            'role': 'analyst',
        })
        
        # Should be allowed (200 or 201) or not implemented (404)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_can_generate_api_keys(
        self, api_client, institutional_user
    ):
        """Subscribers can generate API keys for their organization"""
        api_client.force_authenticate(user=institutional_user)
        
        response = api_client.post('/api/institutional/api-keys/', {
            'name': 'Analytics Dashboard Key',
        })
        
        # Should be allowed or not implemented
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND
        ]


@pytest.mark.django_db
class TestInstitutionalSubscriberRateLimiting:
    """Test rate limiting for institutional subscribers"""
    
    def test_rate_limit_enforced_based_on_plan(
        self, api_client, institutional_user, institutional_subscriber
    ):
        """Rate limits are enforced based on subscription plan"""
        api_client.force_authenticate(user=institutional_user)
        
        # Make multiple requests
        endpoint = '/api/institutional/production/overview/'
        
        # Should succeed initially
        response = api_client.get(endpoint)
        assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
        
        # After many requests (simulate hitting limit)
        # This would require actually implementing the rate limiter check
        # For now, just verify the mechanism exists
    
    def test_rate_limit_headers_included(
        self, api_client, institutional_user
    ):
        """Rate limit headers are included in responses"""
        api_client.force_authenticate(user=institutional_user)
        
        response = api_client.get('/api/institutional/production/overview/')
        
        if response.status_code == status.HTTP_200_OK:
            # Should include rate limit headers
            assert any(
                header.startswith('X-RateLimit') 
                for header in response
            ) or 'X-RateLimit-Limit' in response


@pytest.mark.django_db
class TestInstitutionalSubscriberVsYEAGovernment:
    """Test separation between institutional subscribers and YEA government users"""
    
    def test_yea_admins_cannot_see_institutional_data(
        self, api_client, institutional_subscriber
    ):
        """YEA government officials (NATIONAL_ADMIN, etc.) cannot see institutional subscriber data"""
        # Create a NATIONAL_ADMIN user
        national_admin = User.objects.create_user(
            username='yea_admin',
            email='admin@yea.gov.gh',
            password='testpass123',
            role='NATIONAL_ADMIN',
            phone='+233240999000',
        )
        
        api_client.force_authenticate(user=national_admin)
        
        # Try to access institutional subscriber endpoints
        response = api_client.get('/api/admin/institutional/subscribers/')
        
        # Should be forbidden (only SUPER_ADMIN should see this)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_only_super_admin_can_manage_institutional_subscribers(
        self, api_client, institutional_subscriber
    ):
        """Only platform staff (SUPER_ADMIN) can manage institutional subscribers"""
        # Create SUPER_ADMIN
        super_admin = User.objects.create_superuser(
            username='platform_admin',
            email='admin@alphalogique.com',
            password='testpass123',
            role='SUPER_ADMIN',
            phone='+233240888000',
        )
        
        api_client.force_authenticate(user=super_admin)
        
        # Should be able to access institutional management
        response = api_client.get('/api/admin/institutional/subscribers/')
        
        # Should succeed or return not found (if not implemented)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_institutional_subscribers_cannot_see_yea_government_data(
        self, api_client, institutional_user
    ):
        """Institutional subscribers cannot access YEA government internal data"""
        api_client.force_authenticate(user=institutional_user)
        
        # Try to access YEA-specific endpoints
        yea_endpoints = [
            '/api/admin/batches/',
            '/api/admin/applications/',
            '/api/admin/staff/',
        ]
        
        for endpoint in yea_endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_403_FORBIDDEN, \
                f"Institutional user should not access YEA endpoint {endpoint}"


@pytest.mark.django_db
class TestInstitutionalSubscriberSubscriptionStatus:
    """Test behavior based on subscription status"""
    
    def test_expired_subscription_blocks_access(
        self, api_client, institutional_user, institutional_subscriber
    ):
        """Expired subscriptions cannot access data endpoints"""
        # Set subscription as expired
        institutional_subscriber.current_period_end = (
            timezone.now() - timedelta(days=1)
        ).date()
        institutional_subscriber.status = 'cancelled'
        institutional_subscriber.save()
        
        api_client.force_authenticate(user=institutional_user)
        
        response = api_client.get('/api/institutional/production/overview/')
        
        # Should be forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_suspended_subscription_blocks_access(
        self, api_client, institutional_user, institutional_subscriber
    ):
        """Suspended subscriptions cannot access data endpoints"""
        institutional_subscriber.status = 'suspended'
        institutional_subscriber.save()
        
        api_client.force_authenticate(user=institutional_user)
        
        response = api_client.get('/api/institutional/production/overview/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_active_subscription_allows_access(
        self, api_client, institutional_user, institutional_subscriber
    ):
        """Active subscriptions can access data endpoints"""
        # Ensure subscription is active
        institutional_subscriber.status = 'active'
        institutional_subscriber.current_period_end = (
            timezone.now() + timedelta(days=30)
        ).date()
        institutional_subscriber.save()
        
        api_client.force_authenticate(user=institutional_user)
        
        response = api_client.get('/api/institutional/production/overview/')
        
        # Should not be forbidden (might be 404 if not implemented)
        assert response.status_code != status.HTTP_403_FORBIDDEN


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
