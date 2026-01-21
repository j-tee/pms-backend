"""
Comprehensive tests for Farmer Delivery History API.

Edge Cases Covered:
1. Farmer with no deliveries
2. Farmer with no farm (unregistered)
3. Non-farmer user trying to access
4. Delivery with missing optional fields (null weights, no verification)
5. Delivery with all fields populated
6. Pagination / limit parameter
7. Limit edge cases (0, negative, very large)
8. Multiple deliveries ordered by date
9. Deliveries from multiple orders
10. Unauthenticated user access
11. Delivery with quality failed
12. Delivery with high mortality
13. Invalid limit parameter (string)
14. Service layer edge cases
"""

import pytest
from decimal import Decimal
from datetime import date, time, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
import uuid
import os

from farms.models import Farm
from procurement.models import (
    ProcurementOrder,
    OrderAssignment,
    DeliveryConfirmation,
)
from dashboards.services.farmer import FarmerDashboardService

User = get_user_model()

pytestmark = pytest.mark.django_db

# Test password - use environment variable or default for CI/testing only
TEST_USER_PASSWORD = os.environ.get('TEST_USER_PASSWORD', 'test-only-not-real')


# =============================================================================
# HELPER FUNCTION
# =============================================================================

def create_test_farm(user, unique_suffix=''):
    """Helper to create a farm with all required fields."""
    unique_id = str(uuid.uuid4())[:8]
    short_id = unique_id[:6].upper()  # 6 chars for field constraints
    return Farm.objects.create(
        user=user,
        # Basic Info
        first_name=user.first_name or 'Test',
        last_name=user.last_name or 'Farmer',
        date_of_birth='1990-01-15',
        gender='Male',
        # Ghana card format: GHA-XXXXXXXXX-X (max 20 chars)
        ghana_card_number=f'GHA-{short_id}000-0',
        # Contact
        primary_phone=user.phone or f'024{unique_id[:7]}',
        residential_address='Test Farm Address',
        primary_constituency='Ablekuma South',
        # Next of Kin
        nok_full_name='Test NOK',
        nok_relationship='Spouse',
        nok_phone='+233241000000',
        # Education
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=3,
        # Farm Info
        farm_name=f'Test Farm {short_id}',
        ownership_type='Sole Proprietorship',
        tin=f'T{short_id}',
        # Infrastructure
        number_of_poultry_houses=2,
        housing_type='Deep Litter',
        total_bird_capacity=5000,
        current_bird_count=3000,
        total_infrastructure_value_ghs=Decimal('15000.00'),
        # Production
        primary_production_type='Broilers',
        broiler_breed='Cobb 500',
        planned_monthly_bird_sales=100,
        planned_production_start_date='2025-01-01',
        # Financial
        initial_investment_amount=Decimal('30000.00'),
        funding_source=['Personal Savings'],
        monthly_operating_budget=Decimal('5000.00'),
        expected_monthly_revenue=Decimal('8000.00'),
        # Paystack - unique per farm (max 20 chars)
        paystack_subaccount_code=f'ACCT{short_id}',
        # Status
        farm_status='Active',
        application_status='Approved',
    )


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    """API client for making requests."""
    return APIClient()


@pytest.fixture
def farmer_user(db):
    """Create a farmer user."""
    user = User.objects.create_user(
        username='test_farmer',
        email='farmer@test.com',
        phone='0241234567',
        password=TEST_USER_PASSWORD,
        role='FARMER',
        first_name='Test',
        last_name='Farmer',
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user (non-farmer)."""
    user = User.objects.create_user(
        username='test_admin',
        email='admin@test.com',
        phone='0249876543',
        password=TEST_USER_PASSWORD,
        role='NATIONAL_ADMIN',
        first_name='Test',
        last_name='Admin',
    )
    return user


@pytest.fixture
def officer_user(db):
    """Create a procurement officer for receiving deliveries."""
    user = User.objects.create_user(
        username='test_officer',
        email='officer@test.com',
        phone='0245551234',
        password=TEST_USER_PASSWORD,
        role='PROCUREMENT_OFFICER',
        first_name='Test',
        last_name='Officer',
    )
    return user


@pytest.fixture
def farm(db, farmer_user):
    """Create a farm for the farmer."""
    return create_test_farm(farmer_user)


@pytest.fixture
def procurement_order(db, admin_user):
    """Create a procurement order."""
    order = ProcurementOrder.objects.create(
        title='Bulk Broiler Order for Schools',
        description='500 broilers needed for school feeding program',
        production_type='Broilers',
        quantity_needed=500,
        unit='birds',
        price_per_unit=Decimal('85.00'),
        total_budget=Decimal('42500.00'),
        delivery_location='Ministry of Education, Accra',
        delivery_deadline=date.today() + timedelta(days=14),
        created_by=admin_user,
        status='assigned',
    )
    return order


@pytest.fixture
def order_assignment(db, procurement_order, farm):
    """Create an order assignment for the farm."""
    assignment = OrderAssignment.objects.create(
        order=procurement_order,
        farm=farm,
        quantity_assigned=200,
        price_per_unit=Decimal('85.00'),
        total_value=Decimal('17000.00'),
        status='delivered',
    )
    return assignment


@pytest.fixture
def delivery(db, order_assignment, officer_user):
    """Create a single delivery confirmation."""
    delivery = DeliveryConfirmation.objects.create(
        assignment=order_assignment,
        quantity_delivered=200,
        delivery_date=date.today(),
        delivery_time=time(9, 30),
        received_by=officer_user,
        verified_by=officer_user,
        verified_at=timezone.now(),
        quality_passed=True,
        average_weight_per_bird=Decimal('2.50'),
        mortality_count=2,
        delivery_note_number='DN-2026-001',
        vehicle_registration='GR-1234-21',
        driver_name='Kofi Driver',
        delivery_confirmed=True,
    )
    return delivery


@pytest.fixture
def multiple_deliveries(db, farm, admin_user, officer_user):
    """Create multiple deliveries across different orders."""
    deliveries = []
    
    for i in range(5):
        order = ProcurementOrder.objects.create(
            title=f'Order {i+1}',
            description=f'Test order {i+1}',
            production_type='Broilers',
            quantity_needed=100 * (i + 1),
            unit='birds',
            price_per_unit=Decimal('85.00'),
            total_budget=Decimal(str(8500 * (i + 1))),
            delivery_location='Test Location',
            delivery_deadline=date.today() + timedelta(days=14),
            created_by=admin_user,
            status='assigned',
        )
        
        assignment = OrderAssignment.objects.create(
            order=order,
            farm=farm,
            quantity_assigned=100 * (i + 1),
            price_per_unit=Decimal('85.00'),
            total_value=Decimal(str(8500 * (i + 1))),
            status='delivered',
        )
        
        # Create delivery with varying dates (older to newer)
        delivery = DeliveryConfirmation.objects.create(
            assignment=assignment,
            quantity_delivered=100 * (i + 1),
            delivery_date=date.today() - timedelta(days=5 - i),  # 5 days ago to today
            delivery_time=time(9, 0),
            received_by=officer_user,
            quality_passed=True,
            average_weight_per_bird=Decimal('2.30') + Decimal(str(i * 0.1)),
            mortality_count=i,
        )
        deliveries.append(delivery)
    
    return deliveries


# =============================================================================
# TEST: API Endpoint - Authentication & Authorization
# =============================================================================

class TestDeliveryHistoryAuthentication:
    """Test authentication and authorization for delivery history endpoint."""
    
    def test_unauthenticated_user_gets_401(self, api_client):
        """Unauthenticated user should receive 401."""
        response = api_client.get('/api/procurement/deliveries/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_non_farmer_user_gets_403(self, api_client, admin_user):
        """Non-farmer user should receive 403."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/procurement/deliveries/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_farmer_without_farm_gets_empty_list(self, api_client, db):
        """Farmer without a farm should get empty results (not error)."""
        # Create farmer without farm
        farmer_no_farm = User.objects.create_user(
            username='farmer_no_farm',
            email='nofarm@test.com',
            phone='0240001111',
            password=TEST_USER_PASSWORD,
            role='FARMER',
        )
        api_client.force_authenticate(user=farmer_no_farm)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []
    
    def test_farmer_with_farm_can_access(self, api_client, farmer_user, farm):
        """Farmer with farm should be able to access endpoint."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'results' in response.data


# =============================================================================
# TEST: API Endpoint - Empty States
# =============================================================================

class TestDeliveryHistoryEmptyStates:
    """Test empty state scenarios."""
    
    def test_farm_with_no_deliveries(self, api_client, farmer_user, farm):
        """Farm with no deliveries should return empty list."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []
    
    def test_farm_with_assignment_but_no_delivery(
        self, api_client, farmer_user, farm, order_assignment
    ):
        """Farm with assignment but no delivery should return empty list."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []


# =============================================================================
# TEST: API Endpoint - Basic Functionality
# =============================================================================

class TestDeliveryHistoryBasicFunctionality:
    """Test basic delivery history functionality."""
    
    def test_single_delivery_returns_correct_data(
        self, api_client, farmer_user, farm, delivery
    ):
        """Single delivery should return all expected fields."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        
        result = response.data['results'][0]
        assert 'delivery_number' in result
        assert 'order_number' in result
        assert 'quantity' in result
        assert 'delivery_date' in result
        assert 'quality_passed' in result
        assert 'average_weight' in result
        assert 'mortality_count' in result
        assert 'verified' in result
        assert 'verified_at' in result
        assert 'received_by' in result
    
    def test_delivery_data_values_are_correct(
        self, api_client, farmer_user, farm, delivery, order_assignment
    ):
        """Delivery data values should match database values."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        result = response.data['results'][0]
        
        assert result['delivery_number'] == delivery.delivery_number
        assert result['order_number'] == order_assignment.order.order_number
        assert result['quantity'] == 200
        assert result['quality_passed'] is True
        assert result['average_weight'] == 2.50
        assert result['mortality_count'] == 2
        assert result['verified'] is True
        assert result['received_by'] == 'Test Officer'
    
    def test_multiple_deliveries_ordered_by_date_descending(
        self, api_client, farmer_user, farm, multiple_deliveries
    ):
        """Multiple deliveries should be ordered by date descending (newest first)."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        
        results = response.data['results']
        dates = [r['delivery_date'] for r in results]
        
        # Verify descending order
        for i in range(len(dates) - 1):
            assert dates[i] >= dates[i + 1], "Deliveries not in descending date order"


# =============================================================================
# TEST: API Endpoint - Limit Parameter
# =============================================================================

class TestDeliveryHistoryLimitParameter:
    """Test limit query parameter handling."""
    
    def test_default_limit_is_50(self, api_client, farmer_user, farm, multiple_deliveries):
        """Default limit should be 50 (we have 5 deliveries, so all should return)."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
    
    def test_custom_limit_parameter(
        self, api_client, farmer_user, farm, multiple_deliveries
    ):
        """Custom limit should restrict number of results."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/?limit=3')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3
    
    def test_limit_zero_returns_empty(
        self, api_client, farmer_user, farm, multiple_deliveries
    ):
        """Limit of 0 should return empty list."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/?limit=0')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
    
    def test_limit_larger_than_available(
        self, api_client, farmer_user, farm, multiple_deliveries
    ):
        """Limit larger than available should return all available."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/?limit=100')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5  # Only 5 exist
    
    def test_invalid_limit_string_causes_error(
        self, api_client, farmer_user, farm, multiple_deliveries
    ):
        """Invalid limit (non-numeric) should cause 400 error."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/?limit=abc')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert response.data['code'] == 'INVALID_LIMIT'
    
    def test_negative_limit_returns_empty(
        self, api_client, farmer_user, farm, multiple_deliveries
    ):
        """Negative limit should be treated as 0 (empty results)."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/?limit=-5')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0


# =============================================================================
# TEST: API Endpoint - Delivery with Missing/Null Fields
# =============================================================================

class TestDeliveryHistoryNullFields:
    """Test handling of deliveries with null/missing optional fields."""
    
    def test_delivery_without_verification(
        self, api_client, farmer_user, farm, order_assignment, officer_user
    ):
        """Delivery without verification should show verified=False."""
        DeliveryConfirmation.objects.create(
            assignment=order_assignment,
            quantity_delivered=100,
            delivery_date=date.today(),
            delivery_time=time(10, 0),
            received_by=officer_user,
            # No verified_by, verified_at
            quality_passed=True,
        )
        
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        result = response.data['results'][0]
        
        assert result['verified'] is False
        assert result['verified_at'] is None
    
    def test_delivery_without_average_weight(
        self, api_client, farmer_user, farm, order_assignment, officer_user
    ):
        """Delivery without average weight should show null."""
        DeliveryConfirmation.objects.create(
            assignment=order_assignment,
            quantity_delivered=100,
            delivery_date=date.today(),
            delivery_time=time(10, 0),
            received_by=officer_user,
            quality_passed=True,
            # No average_weight_per_bird
        )
        
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        result = response.data['results'][0]
        
        assert result['average_weight'] is None
    
    def test_delivery_without_received_by(
        self, api_client, farmer_user, farm, order_assignment
    ):
        """Delivery without received_by should show null."""
        DeliveryConfirmation.objects.create(
            assignment=order_assignment,
            quantity_delivered=100,
            delivery_date=date.today(),
            delivery_time=time(10, 0),
            # No received_by
            quality_passed=True,
        )
        
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        result = response.data['results'][0]
        
        assert result['received_by'] is None


# =============================================================================
# TEST: API Endpoint - Quality and Mortality Edge Cases
# =============================================================================

class TestDeliveryHistoryQualityEdgeCases:
    """Test quality inspection and mortality edge cases."""
    
    def test_delivery_with_quality_failed(
        self, api_client, farmer_user, farm, order_assignment, officer_user
    ):
        """Delivery with failed quality should show quality_passed=False."""
        DeliveryConfirmation.objects.create(
            assignment=order_assignment,
            quantity_delivered=100,
            delivery_date=date.today(),
            delivery_time=time(10, 0),
            received_by=officer_user,
            quality_passed=False,
            quality_issues='Birds underweight, some sick',
        )
        
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        result = response.data['results'][0]
        
        assert result['quality_passed'] is False
    
    def test_delivery_with_high_mortality(
        self, api_client, farmer_user, farm, order_assignment, officer_user
    ):
        """Delivery with high mortality count should display correctly."""
        DeliveryConfirmation.objects.create(
            assignment=order_assignment,
            quantity_delivered=100,
            delivery_date=date.today(),
            delivery_time=time(10, 0),
            received_by=officer_user,
            quality_passed=False,
            mortality_count=25,  # 25% mortality
        )
        
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        result = response.data['results'][0]
        
        assert result['mortality_count'] == 25
    
    def test_delivery_with_zero_mortality(
        self, api_client, farmer_user, farm, order_assignment, officer_user
    ):
        """Delivery with zero mortality should display correctly."""
        DeliveryConfirmation.objects.create(
            assignment=order_assignment,
            quantity_delivered=100,
            delivery_date=date.today(),
            delivery_time=time(10, 0),
            received_by=officer_user,
            quality_passed=True,
            mortality_count=0,
        )
        
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        result = response.data['results'][0]
        
        assert result['mortality_count'] == 0


# =============================================================================
# TEST: Service Layer - FarmerDashboardService
# =============================================================================

class TestFarmerDashboardServiceDeliveryHistory:
    """Test the FarmerDashboardService.get_delivery_history method directly."""
    
    def test_service_with_no_farm(self, farmer_user):
        """Service should return empty list if user has no farm."""
        # User without farm
        user_no_farm = User.objects.create_user(
            username='no_farm_user',
            email='no@farm.com',
            phone='0240002222',
            password=TEST_USER_PASSWORD,
            role='FARMER',
        )
        
        service = FarmerDashboardService(user_no_farm)
        result = service.get_delivery_history()
        
        assert result == []
    
    def test_service_with_farm_no_deliveries(self, farmer_user, farm):
        """Service should return empty list if farm has no deliveries."""
        service = FarmerDashboardService(farmer_user)
        result = service.get_delivery_history()
        
        assert result == []
    
    def test_service_returns_correct_structure(
        self, farmer_user, farm, delivery, order_assignment
    ):
        """Service should return list of dicts with expected keys."""
        service = FarmerDashboardService(farmer_user)
        result = service.get_delivery_history()
        
        assert len(result) == 1
        
        expected_keys = {
            'delivery_number',
            'order_number',
            'quantity',
            'delivery_date',
            'quality_passed',
            'average_weight',
            'mortality_count',
            'verified',
            'verified_at',
            'received_by',
        }
        
        assert set(result[0].keys()) == expected_keys
    
    def test_service_respects_limit(
        self, farmer_user, farm, multiple_deliveries
    ):
        """Service should respect the limit parameter."""
        service = FarmerDashboardService(farmer_user)
        
        result_all = service.get_delivery_history(limit=100)
        assert len(result_all) == 5
        
        result_limited = service.get_delivery_history(limit=2)
        assert len(result_limited) == 2
    
    def test_service_default_limit(
        self, farmer_user, farm, multiple_deliveries
    ):
        """Service default limit should be 20."""
        service = FarmerDashboardService(farmer_user)
        result = service.get_delivery_history()  # No limit specified
        
        # We have 5 deliveries, all should be returned (20 > 5)
        assert len(result) == 5


# =============================================================================
# TEST: Data Isolation / Security
# =============================================================================

class TestDeliveryHistoryDataIsolation:
    """Test that farmers can only see their own deliveries."""
    
    def test_farmer_cannot_see_other_farms_deliveries(
        self, api_client, admin_user, officer_user
    ):
        """Farmer should only see deliveries from their own farm."""
        # Create two farmers with farms
        farmer1 = User.objects.create_user(
            username='farmer1',
            email='farmer1@test.com',
            phone='0241111111',
            password=TEST_USER_PASSWORD,
            role='FARMER',
            first_name='Farmer',
            last_name='One',
        )
        farm1 = create_test_farm(farmer1, 'F1')
        
        farmer2 = User.objects.create_user(
            username='farmer2',
            email='farmer2@test.com',
            phone='0242222222',
            password=TEST_USER_PASSWORD,
            role='FARMER',
            first_name='Farmer',
            last_name='Two',
        )
        farm2 = create_test_farm(farmer2, 'F2')
        
        # Create order and assignments for both farms
        order = ProcurementOrder.objects.create(
            title='Shared Order',
            description='Order for multiple farms',
            production_type='Broilers',
            quantity_needed=500,
            unit='birds',
            price_per_unit=Decimal('85.00'),
            total_budget=Decimal('42500.00'),
            delivery_location='Test Location',
            delivery_deadline=date.today() + timedelta(days=14),
            created_by=admin_user,
            status='assigned',
        )
        
        assignment1 = OrderAssignment.objects.create(
            order=order,
            farm=farm1,
            quantity_assigned=200,
            price_per_unit=Decimal('85.00'),
            total_value=Decimal('17000.00'),
            status='delivered',
        )
        
        assignment2 = OrderAssignment.objects.create(
            order=order,
            farm=farm2,
            quantity_assigned=300,
            price_per_unit=Decimal('85.00'),
            total_value=Decimal('25500.00'),
            status='delivered',
        )
        
        # Create deliveries for both farms
        delivery1 = DeliveryConfirmation.objects.create(
            assignment=assignment1,
            quantity_delivered=200,
            delivery_date=date.today(),
            delivery_time=time(9, 0),
            received_by=officer_user,
            quality_passed=True,
        )
        
        delivery2 = DeliveryConfirmation.objects.create(
            assignment=assignment2,
            quantity_delivered=300,
            delivery_date=date.today(),
            delivery_time=time(10, 0),
            received_by=officer_user,
            quality_passed=True,
        )
        
        # Farmer 1 should only see their delivery
        api_client.force_authenticate(user=farmer1)
        response1 = api_client.get('/api/procurement/deliveries/')
        
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data['count'] == 1
        assert response1.data['results'][0]['delivery_number'] == delivery1.delivery_number
        
        # Farmer 2 should only see their delivery
        api_client.force_authenticate(user=farmer2)
        response2 = api_client.get('/api/procurement/deliveries/')
        
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['count'] == 1
        assert response2.data['results'][0]['delivery_number'] == delivery2.delivery_number


# =============================================================================
# TEST: Response Format
# =============================================================================

class TestDeliveryHistoryResponseFormat:
    """Test the response format and structure."""
    
    def test_response_has_count_and_results(
        self, api_client, farmer_user, farm
    ):
        """Response should always have 'count' and 'results' keys."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'results' in response.data
        assert isinstance(response.data['count'], int)
        assert isinstance(response.data['results'], list)
    
    def test_delivery_date_is_iso_format(
        self, api_client, farmer_user, farm, delivery
    ):
        """delivery_date should be in ISO format."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        result = response.data['results'][0]
        
        # Should be ISO format: YYYY-MM-DD
        assert len(result['delivery_date']) == 10
        assert result['delivery_date'].count('-') == 2
    
    def test_verified_at_is_iso_format_when_set(
        self, api_client, farmer_user, farm, delivery
    ):
        """verified_at should be ISO format when set."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/procurement/deliveries/')
        
        result = response.data['results'][0]
        
        # Should be ISO datetime format
        assert 'T' in result['verified_at']  # ISO datetime contains 'T'
