"""
Comprehensive Test Suite for Guest Order Atomicity & Idempotency

Tests cover:
1. Backend-generated content hash duplicate detection
2. Idempotent API responses (returning existing order, not error)
3. Race condition prevention with select_for_update()
4. Atomic stock operations
5. Atomic farmer actions (confirm, complete, cancel)
6. Atomic customer cancellation
7. Edge cases and error handling

Run with: pytest tests/integration/test_guest_order_atomicity_idempotency.py -v
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, connection
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
import uuid
import hashlib
import json
import threading
import time

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def farmer_user(db):
    """Create a farmer user."""
    user = User.objects.create_user(
        username='test_farmer_guest_order',
        email='farmer_guest@example.com',
        password='testpass123',
        role='FARMER',
        first_name='Test',
        last_name='Farmer',
        phone='+233241234501'
    )
    return user


@pytest.fixture
def farmer_user_2(db):
    """Create a second farmer user."""
    user = User.objects.create_user(
        username='test_farmer_guest_order_2',
        email='farmer_guest2@example.com',
        password='testpass123',
        role='FARMER',
        first_name='Test2',
        last_name='Farmer2',
        phone='+233241234502'
    )
    return user


@pytest.fixture
def farm(db, farmer_user):
    """Create a test farm with all required fields."""
    from farms.models import Farm
    
    unique_id = str(uuid.uuid4())[:8]
    
    farm = Farm.objects.create(
        user=farmer_user,
        # Section 1.1: Basic Info
        first_name=farmer_user.first_name,
        last_name=farmer_user.last_name,
        date_of_birth='1990-01-01',
        gender='Male',
        ghana_card_number=f'GHA-{unique_id.upper()}-1',
        # Section 1.2: Contact
        primary_phone=farmer_user.phone,
        residential_address='Test Address, Accra',
        primary_constituency='Ablekuma South',
        # Section 1.3: Next of Kin
        nok_full_name='Test NOK',
        nok_relationship='Parent',
        nok_phone=f'+23324{unique_id[:7]}',
        # Section 1.4: Education
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=5,
        # Section 2: Farm Info
        farm_name=f'Test Farm {unique_id}',
        ownership_type='Sole Proprietorship',
        tin=f'C00{unique_id[:5].upper()}0',
        # Section 4: Infrastructure
        total_bird_capacity=1000,
        number_of_poultry_houses=2,
        housing_type='Deep Litter',
        total_infrastructure_value_ghs=25000.00,
        # Section 5: Production (required)
        primary_production_type='Layers',
        planned_production_start_date='2025-01-01',
        # Section 7: Financial
        initial_investment_amount=50000.00,
        funding_source=['Personal Savings'],
        monthly_operating_budget=5000.00,
        expected_monthly_revenue=8000.00,
        # Marketplace
        marketplace_enabled=True,
    )
    farmer_user.farm = farm
    farmer_user.save()
    return farm


@pytest.fixture
def product_category(db):
    """Create a product category."""
    from sales_revenue.marketplace_models import ProductCategory
    category, _ = ProductCategory.objects.get_or_create(
        name='Eggs',
        defaults={'slug': 'eggs', 'is_active': True}
    )
    return category


@pytest.fixture
def product(db, farm, product_category):
    """Create a test product with stock."""
    from sales_revenue.marketplace_models import Product
    
    product = Product.objects.create(
        farm=farm,
        category=product_category,
        name='Fresh Eggs (Crate)',
        price=Decimal('35.00'),
        unit='crate',
        stock_quantity=100,
        track_inventory=True,
        status='active',
        min_order_quantity=1,
        max_order_quantity=50,
    )
    return product


@pytest.fixture
def product_2(db, farm, product_category):
    """Create a second test product."""
    from sales_revenue.marketplace_models import Product
    
    product = Product.objects.create(
        farm=farm,
        category=product_category,
        name='Fresh Eggs (Tray)',
        price=Decimal('15.00'),
        unit='tray',
        stock_quantity=200,
        track_inventory=True,
        status='active',
        min_order_quantity=1,
    )
    return product


@pytest.fixture
def guest_customer(db):
    """Create a guest customer."""
    from sales_revenue.guest_order_models import GuestCustomer
    
    customer = GuestCustomer.objects.create(
        phone_number='+233241999888',
        name='Test Customer',
        phone_verified=True,
        phone_verified_at=timezone.now(),
    )
    return customer


@pytest.fixture
def guest_order(db, farm, guest_customer, product):
    """Create a guest order."""
    from sales_revenue.guest_order_models import GuestOrder, GuestOrderItem
    
    order = GuestOrder.objects.create(
        farm=farm,
        guest_customer=guest_customer,
        status='pending_confirmation',
        delivery_method='pickup',
        subtotal=Decimal('70.00'),
        total_amount=Decimal('70.00'),
    )
    
    GuestOrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        product_sku=product.sku or '',
        unit=product.unit,
        unit_price=product.price,
        quantity=2,
        line_total=Decimal('70.00'),
    )
    
    return order


# =============================================================================
# CONTENT HASH GENERATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestContentHashGeneration:
    """Test the content hash generation for duplicate detection."""
    
    def test_generate_content_hash_returns_64_char_string(self, farm, product):
        """Content hash should be a 64-character SHA-256 hex string."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash = GuestOrder.generate_content_hash(
            '+233241234567',
            str(farm.id),
            items
        )
        
        assert len(content_hash) == 64
        assert all(c in '0123456789abcdef' for c in content_hash)
    
    def test_same_input_produces_same_hash(self, farm, product):
        """Same order details should produce identical hash."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        
        hash1 = GuestOrder.generate_content_hash('+233241234567', str(farm.id), items)
        hash2 = GuestOrder.generate_content_hash('+233241234567', str(farm.id), items)
        
        assert hash1 == hash2
    
    def test_phone_normalization_in_hash(self, farm, product):
        """Different phone formats should normalize to same hash."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        
        # Different phone formats that should normalize to +233241234567
        hash1 = GuestOrder.generate_content_hash('0241234567', str(farm.id), items)
        hash2 = GuestOrder.generate_content_hash('+233241234567', str(farm.id), items)
        hash3 = GuestOrder.generate_content_hash('233241234567', str(farm.id), items)
        
        assert hash1 == hash2 == hash3
    
    def test_different_phone_produces_different_hash(self, farm, product):
        """Different phone numbers should produce different hashes."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        
        hash1 = GuestOrder.generate_content_hash('+233241234567', str(farm.id), items)
        hash2 = GuestOrder.generate_content_hash('+233241234568', str(farm.id), items)
        
        assert hash1 != hash2
    
    def test_different_quantity_produces_different_hash(self, farm, product):
        """Different quantities should produce different hashes."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items1 = [{'product_id': str(product.id), 'quantity': 2}]
        items2 = [{'product_id': str(product.id), 'quantity': 3}]
        
        hash1 = GuestOrder.generate_content_hash('+233241234567', str(farm.id), items1)
        hash2 = GuestOrder.generate_content_hash('+233241234567', str(farm.id), items2)
        
        assert hash1 != hash2
    
    def test_items_order_does_not_affect_hash(self, farm, product, product_2):
        """Items in different order should produce same hash (sorted internally)."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items1 = [
            {'product_id': str(product.id), 'quantity': 2},
            {'product_id': str(product_2.id), 'quantity': 5},
        ]
        items2 = [
            {'product_id': str(product_2.id), 'quantity': 5},
            {'product_id': str(product.id), 'quantity': 2},
        ]
        
        hash1 = GuestOrder.generate_content_hash('+233241234567', str(farm.id), items1)
        hash2 = GuestOrder.generate_content_hash('+233241234567', str(farm.id), items2)
        
        assert hash1 == hash2


# =============================================================================
# DUPLICATE DETECTION TESTS
# =============================================================================

@pytest.mark.django_db
class TestDuplicateDetection:
    """Test the find_duplicate functionality."""
    
    def test_find_duplicate_within_time_window(self, farm, guest_customer, product):
        """Should find duplicate order within 10 minute window."""
        from sales_revenue.guest_order_models import GuestOrder, GuestOrderItem
        
        # Create order with content hash
        items = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash = GuestOrder.generate_content_hash(
            guest_customer.phone_number,
            str(farm.id),
            items
        )
        
        order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            content_hash=content_hash,
            status='pending_confirmation',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
        )
        
        # Should find the duplicate
        duplicate = GuestOrder.find_duplicate(content_hash)
        assert duplicate is not None
        assert duplicate.id == order.id
    
    def test_find_duplicate_outside_time_window_returns_none(self, farm, guest_customer, product):
        """Should NOT find duplicate order outside 10 minute window."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash = GuestOrder.generate_content_hash(
            guest_customer.phone_number,
            str(farm.id),
            items
        )
        
        # Create old order (15 minutes ago)
        order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            content_hash=content_hash,
            status='pending_confirmation',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
        )
        # Manually set created_at to 15 minutes ago
        GuestOrder.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=15)
        )
        
        # Should NOT find duplicate (too old)
        duplicate = GuestOrder.find_duplicate(content_hash)
        assert duplicate is None
    
    def test_find_duplicate_ignores_completed_orders(self, farm, guest_customer, product):
        """Should NOT consider completed orders as duplicates."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash = GuestOrder.generate_content_hash(
            guest_customer.phone_number,
            str(farm.id),
            items
        )
        
        # Create completed order
        order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            content_hash=content_hash,
            status='completed',  # Completed status
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
        )
        
        # Should NOT find duplicate (completed orders don't count)
        duplicate = GuestOrder.find_duplicate(content_hash)
        assert duplicate is None
    
    def test_find_duplicate_ignores_cancelled_orders(self, farm, guest_customer, product):
        """Should NOT consider cancelled orders as duplicates."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash = GuestOrder.generate_content_hash(
            guest_customer.phone_number,
            str(farm.id),
            items
        )
        
        # Create cancelled order
        order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            content_hash=content_hash,
            status='cancelled',  # Cancelled status
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
        )
        
        # Should NOT find duplicate (cancelled orders don't count)
        duplicate = GuestOrder.find_duplicate(content_hash)
        assert duplicate is None
    
    def test_find_duplicate_considers_pending_orders(self, farm, guest_customer, product):
        """Should consider pending_verification, pending_confirmation, confirmed as duplicates."""
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash = GuestOrder.generate_content_hash(
            guest_customer.phone_number,
            str(farm.id),
            items
        )
        
        for order_status in ['pending_verification', 'pending_confirmation', 'confirmed']:
            # Clean up first
            GuestOrder.objects.filter(content_hash=content_hash).delete()
            
            # Create order with status
            order = GuestOrder.objects.create(
                farm=farm,
                guest_customer=guest_customer,
                content_hash=content_hash,
                status=order_status,
                subtotal=Decimal('70.00'),
                total_amount=Decimal('70.00'),
            )
            
            # Should find duplicate
            duplicate = GuestOrder.find_duplicate(content_hash)
            assert duplicate is not None, f"Should find duplicate for status {order_status}"
            assert duplicate.id == order.id


# =============================================================================
# IDEMPOTENT API RESPONSE TESTS
# =============================================================================

@pytest.mark.django_db
class TestIdempotentAPIResponse:
    """Test that duplicate submissions return the existing order (not error)."""
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_duplicate_order_returns_200_with_existing_order(
        self, mock_sms, mock_captcha, api_client, farm, product, guest_customer
    ):
        """Duplicate submission should return 200 OK with existing order, not error."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        from sales_revenue.guest_order_models import GuestOrder
        
        # Create first order with content hash
        items = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash = GuestOrder.generate_content_hash(
            guest_customer.phone_number,
            str(farm.id),
            items
        )
        
        first_order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            content_hash=content_hash,
            status='pending_verification',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
        )
        
        # Try to create duplicate order via API
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'phone_number': guest_customer.phone_number,
            'name': guest_customer.name,
            'items': [{'product_id': str(product.id), 'quantity': 2}],
            'delivery_method': 'pickup',
        }, format='json')
        
        # Should return 200 OK (not 400 or 201)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_duplicate'] is True
        assert response.data['order_number'] == first_order.order_number
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_new_order_returns_201_created(
        self, mock_sms, mock_captcha, api_client, farm, product
    ):
        """New order should return 201 Created with is_duplicate=False."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        # Create new order via API
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'phone_number': '+233241777666',
            'name': 'New Customer',
            'items': [{'product_id': str(product.id), 'quantity': 1}],
            'delivery_method': 'pickup',
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['is_duplicate'] is False
        assert 'order_number' in response.data
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_different_quantity_creates_new_order(
        self, mock_sms, mock_captcha, api_client, farm, product, guest_customer
    ):
        """Order with different quantity should create new order, not duplicate."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        from sales_revenue.guest_order_models import GuestOrder
        
        # Create first order
        items1 = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash1 = GuestOrder.generate_content_hash(
            guest_customer.phone_number,
            str(farm.id),
            items1
        )
        
        first_order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            content_hash=content_hash1,
            status='pending_verification',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
        )
        
        # Try to create order with different quantity
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'phone_number': guest_customer.phone_number,
            'name': guest_customer.name,
            'items': [{'product_id': str(product.id), 'quantity': 5}],  # Different quantity
            'delivery_method': 'pickup',
        }, format='json')
        
        # Should create new order
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['is_duplicate'] is False
        assert response.data['order_number'] != first_order.order_number


# =============================================================================
# ATOMIC STOCK OPERATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestAtomicStockOperations:
    """Test atomic stock operations during order creation."""
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_stock_is_reduced_atomically_on_order_creation(
        self, mock_sms, mock_captcha, api_client, farm, product
    ):
        """Stock should be reduced atomically when order is created."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        initial_stock = product.stock_quantity
        order_quantity = 5
        
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'phone_number': '+233241555444',
            'name': 'Stock Test Customer',
            'items': [{'product_id': str(product.id), 'quantity': order_quantity}],
            'delivery_method': 'pickup',
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Refresh product from DB
        product.refresh_from_db()
        assert product.stock_quantity == initial_stock - order_quantity
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_insufficient_stock_returns_error_no_partial_creation(
        self, mock_sms, mock_captcha, api_client, farm, product
    ):
        """Order with insufficient stock should fail completely, no partial order."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        from sales_revenue.guest_order_models import GuestOrder
        
        initial_stock = product.stock_quantity
        order_count_before = GuestOrder.objects.filter(farm=farm).count()
        
        # Try to order more than available
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'phone_number': '+233241555444',
            'name': 'Stock Test Customer',
            'items': [{'product_id': str(product.id), 'quantity': initial_stock + 100}],
            'delivery_method': 'pickup',
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Stock should be unchanged
        product.refresh_from_db()
        assert product.stock_quantity == initial_stock
        
        # No order should be created
        order_count_after = GuestOrder.objects.filter(farm=farm).count()
        assert order_count_after == order_count_before
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_multiple_products_stock_reduced_atomically(
        self, mock_sms, mock_captcha, api_client, farm, product, product_2
    ):
        """Multiple products should have stock reduced atomically together."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        initial_stock_1 = product.stock_quantity
        initial_stock_2 = product_2.stock_quantity
        
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'phone_number': '+233241555444',
            'name': 'Multi Product Customer',
            'items': [
                {'product_id': str(product.id), 'quantity': 3},
                {'product_id': str(product_2.id), 'quantity': 7},
            ],
            'delivery_method': 'pickup',
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Both products should have stock reduced
        product.refresh_from_db()
        product_2.refresh_from_db()
        assert product.stock_quantity == initial_stock_1 - 3
        assert product_2.stock_quantity == initial_stock_2 - 7


# =============================================================================
# ATOMIC FARMER ACTION TESTS
# =============================================================================

@pytest.mark.django_db
class TestAtomicFarmerActions:
    """Test atomic farmer actions on guest orders."""
    
    def test_complete_action_updates_order_and_product_stats_atomically(
        self, api_client, farm, guest_order, farmer_user, product
    ):
        """Complete action should atomically update order status and product stats."""
        api_client.force_authenticate(user=farmer_user)
        
        initial_total_sold = product.total_sold or 0
        initial_total_revenue = product.total_revenue or Decimal('0')
        
        # Update order to confirmed status first (requirement for complete)
        guest_order.status = 'payment_confirmed'
        guest_order.save()
        
        response = api_client.post(
            f'/api/marketplace/guest-orders/{guest_order.id}/action/',
            {'action': 'complete'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Order should be completed
        guest_order.refresh_from_db()
        assert guest_order.status == 'completed'
        
        # Product stats should be updated
        product.refresh_from_db()
        assert product.total_sold == initial_total_sold + 2  # 2 items in order
        assert product.total_revenue == initial_total_revenue + Decimal('70.00')
    
    def test_cancel_action_restores_stock_atomically(
        self, api_client, farm, guest_order, farmer_user, product
    ):
        """Cancel action should atomically restore stock."""
        api_client.force_authenticate(user=farmer_user)
        
        # First reduce stock (simulate order creation)
        product.reduce_stock(2)
        product.refresh_from_db()
        stock_after_order = product.stock_quantity
        
        response = api_client.post(
            f'/api/marketplace/guest-orders/{guest_order.id}/action/',
            {'action': 'cancel', 'cancellation_reason': 'farmer_unavailable'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Order should be cancelled
        guest_order.refresh_from_db()
        assert guest_order.status == 'cancelled'
        
        # Stock should be restored
        product.refresh_from_db()
        assert product.stock_quantity == stock_after_order + 2
    
    def test_confirm_action_atomic(self, api_client, farm, guest_order, farmer_user):
        """Confirm action should atomically update order status."""
        api_client.force_authenticate(user=farmer_user)
        
        response = api_client.post(
            f'/api/marketplace/guest-orders/{guest_order.id}/action/',
            {'action': 'confirm'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        guest_order.refresh_from_db()
        assert guest_order.status == 'confirmed'
        assert guest_order.confirmed_at is not None


# =============================================================================
# ATOMIC CUSTOMER CANCEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestAtomicCustomerCancel:
    """Test atomic customer cancellation."""
    
    def test_customer_cancel_restores_stock_atomically(
        self, api_client, farm, guest_order, guest_customer, product
    ):
        """Customer cancel should atomically restore stock."""
        # First reduce stock (simulate order creation)
        product.reduce_stock(2)
        product.refresh_from_db()
        stock_after_order = product.stock_quantity
        
        response = api_client.post('/api/public/marketplace/order/cancel/', {
            'order_number': guest_order.order_number,
            'phone_number': guest_customer.phone_number,
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        # Order should be cancelled
        guest_order.refresh_from_db()
        assert guest_order.status == 'cancelled'
        
        # Stock should be restored
        product.refresh_from_db()
        assert product.stock_quantity == stock_after_order + 2
    
    def test_customer_cancel_updates_cancelled_orders_count(
        self, api_client, farm, guest_order, guest_customer
    ):
        """Customer cancel should increment cancelled_orders count atomically."""
        initial_cancelled = guest_customer.cancelled_orders
        
        response = api_client.post('/api/public/marketplace/order/cancel/', {
            'order_number': guest_order.order_number,
            'phone_number': guest_customer.phone_number,
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        guest_customer.refresh_from_db()
        assert guest_customer.cancelled_orders == initial_cancelled + 1
    
    def test_cannot_cancel_already_completed_order(
        self, api_client, farm, guest_order, guest_customer
    ):
        """Should not be able to cancel completed orders."""
        guest_order.status = 'completed'
        guest_order.save()
        
        response = api_client.post('/api/public/marketplace/order/cancel/', {
            'order_number': guest_order.order_number,
            'phone_number': guest_customer.phone_number,
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Order status should remain completed
        guest_order.refresh_from_db()
        assert guest_order.status == 'completed'


# =============================================================================
# CLIENT IDEMPOTENCY KEY TESTS (Optional Feature)
# =============================================================================

@pytest.mark.django_db
class TestClientIdempotencyKey:
    """Test the optional client-provided idempotency key."""
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_idempotency_key_stored_on_order(
        self, mock_sms, mock_captcha, api_client, farm, product
    ):
        """Client idempotency key should be stored on the order."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        idempotency_key = str(uuid.uuid4())
        
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'idempotency_key': idempotency_key,
            'phone_number': '+233241333222',
            'name': 'Idempotency Test Customer',
            'items': [{'product_id': str(product.id), 'quantity': 1}],
            'delivery_method': 'pickup',
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        from sales_revenue.guest_order_models import GuestOrder
        order = GuestOrder.objects.get(order_number=response.data['order_number'])
        assert order.idempotency_key == idempotency_key
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_duplicate_idempotency_key_returns_existing_order(
        self, mock_sms, mock_captcha, api_client, farm, product, guest_customer
    ):
        """Duplicate client idempotency key should return existing order."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        from sales_revenue.guest_order_models import GuestOrder
        
        idempotency_key = str(uuid.uuid4())
        
        # Create first order with idempotency key
        first_order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            idempotency_key=idempotency_key,
            status='pending_verification',
            subtotal=Decimal('35.00'),
            total_amount=Decimal('35.00'),
        )
        
        # Try to create another order with same idempotency key (different content)
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'idempotency_key': idempotency_key,
            'phone_number': guest_customer.phone_number,
            'name': guest_customer.name,
            'items': [{'product_id': str(product.id), 'quantity': 10}],  # Different content
            'delivery_method': 'pickup',
        }, format='json')
        
        # Should return existing order
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_duplicate'] is True
        assert response.data['order_number'] == first_order.order_number


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

@pytest.mark.django_db
class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_order_after_10_minutes_creates_new_order(
        self, mock_sms, mock_captcha, api_client, farm, product, guest_customer
    ):
        """Same content after 10 minutes should create new order."""
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        from sales_revenue.guest_order_models import GuestOrder
        
        items = [{'product_id': str(product.id), 'quantity': 2}]
        content_hash = GuestOrder.generate_content_hash(
            guest_customer.phone_number,
            str(farm.id),
            items
        )
        
        # Create old order (15 minutes ago)
        old_order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            content_hash=content_hash,
            status='pending_verification',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
        )
        GuestOrder.objects.filter(pk=old_order.pk).update(
            created_at=timezone.now() - timedelta(minutes=15)
        )
        
        # Create new order with same content
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'test-token',
            'phone_number': guest_customer.phone_number,
            'name': guest_customer.name,
            'items': [{'product_id': str(product.id), 'quantity': 2}],
            'delivery_method': 'pickup',
        }, format='json')
        
        # Should create new order (not duplicate)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['is_duplicate'] is False
        assert response.data['order_number'] != old_order.order_number
    
    def test_invalid_action_on_order(self, api_client, guest_order, farmer_user):
        """Invalid action should return error."""
        api_client.force_authenticate(user=farmer_user)
        
        response = api_client.post(
            f'/api/marketplace/guest-orders/{guest_order.id}/action/',
            {'action': 'invalid_action'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_confirm_already_confirmed_order(self, api_client, guest_order, farmer_user):
        """Confirming already confirmed order should return error."""
        api_client.force_authenticate(user=farmer_user)
        
        guest_order.status = 'confirmed'
        guest_order.save()
        
        response = api_client.post(
            f'/api/marketplace/guest-orders/{guest_order.id}/action/',
            {'action': 'confirm'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_customer_cancel_wrong_phone_number(self, api_client, guest_order):
        """Cancel with wrong phone should return 404."""
        response = api_client.post('/api/public/marketplace/order/cancel/', {
            'order_number': guest_order.order_number,
            'phone_number': '+233200000000',  # Wrong phone
        }, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_customer_cancel_nonexistent_order(self, api_client, guest_customer):
        """Cancel nonexistent order should return 404."""
        response = api_client.post('/api/public/marketplace/order/cancel/', {
            'order_number': 'GO-NONEXISTENT-123',
            'phone_number': guest_customer.phone_number,
        }, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    def test_missing_captcha_returns_error(self, mock_captcha, api_client, product):
        """Missing CAPTCHA should return error."""
        response = api_client.post('/api/public/marketplace/order/create/', {
            # No captcha_token
            'phone_number': '+233241234567',
            'name': 'Test Customer',
            'items': [{'product_id': str(product.id), 'quantity': 1}],
            'delivery_method': 'pickup',
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'CAPTCHA_MISSING'
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    def test_invalid_captcha_returns_error(self, mock_captcha, api_client, product):
        """Invalid CAPTCHA should return error."""
        mock_captcha.return_value = False
        
        response = api_client.post('/api/public/marketplace/order/create/', {
            'captcha_token': 'invalid-token',
            'phone_number': '+233241234567',
            'name': 'Test Customer',
            'items': [{'product_id': str(product.id), 'quantity': 1}],
            'delivery_method': 'pickup',
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['code'] == 'CAPTCHA_INVALID'


# =============================================================================
# CONCURRENT ORDER TESTS (Race Condition Prevention)
# =============================================================================

@pytest.mark.django_db(transaction=True)
class TestConcurrentOrderPrevention:
    """
    Test that race conditions are prevented with database locking.
    
    These tests verify that concurrent orders don't oversell stock.
    """
    
    @patch('core.turnstile_service.turnstile_service.verify_token')
    @patch('core.sms_service.HubtelSMSService.send_sms')
    def test_concurrent_orders_do_not_oversell(
        self, mock_sms, mock_captcha, farm, product
    ):
        """
        Concurrent orders should not oversell limited stock.
        
        If 10 units available and 2 concurrent requests each want 6,
        only one should succeed.
        """
        mock_captcha.return_value = True
        mock_sms.return_value = {'success': True}
        
        from sales_revenue.marketplace_models import Product
        
        # Set stock to 10
        Product.objects.filter(pk=product.pk).update(stock_quantity=10)
        
        results = []
        errors = []
        
        def create_order(phone_suffix):
            """Create order in a separate connection."""
            from django.test.client import Client
            from django.db import connection
            
            client = Client()
            
            try:
                response = client.post(
                    '/api/public/marketplace/order/create/',
                    data={
                        'captcha_token': 'test-token',
                        'phone_number': f'+23324100000{phone_suffix}',
                        'name': f'Concurrent Customer {phone_suffix}',
                        'items': [{'product_id': str(product.id), 'quantity': 6}],
                        'delivery_method': 'pickup',
                    },
                    content_type='application/json'
                )
                results.append({
                    'phone_suffix': phone_suffix,
                    'status_code': response.status_code,
                    'data': response.json() if response.content else None
                })
            except Exception as e:
                errors.append({'phone_suffix': phone_suffix, 'error': str(e)})
            finally:
                connection.close()
        
        # Create threads
        threads = [
            threading.Thread(target=create_order, args=(i,))
            for i in range(2)
        ]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=10)
        
        # Refresh product
        product.refresh_from_db()
        
        # Analyze results
        successes = [r for r in results if r['status_code'] == 201]
        failures = [r for r in results if r['status_code'] == 400]
        
        # At most one should succeed (can't both get 6 from 10)
        # Or both fail if they detected the race condition
        assert len(successes) <= 1, f"More than one order succeeded: {successes}"
        
        # Stock should not go negative
        assert product.stock_quantity >= 0, f"Stock went negative: {product.stock_quantity}"
        
        # If one succeeded, stock should be 4 (10 - 6)
        if len(successes) == 1:
            assert product.stock_quantity == 4, f"Unexpected stock: {product.stock_quantity}"


# =============================================================================
# COMPLETE ORDER STATS UPDATE TESTS
# =============================================================================

@pytest.mark.django_db
class TestCompleteOrderStatsUpdate:
    """Test that completing an order updates all stats atomically."""
    
    def test_complete_updates_customer_completed_orders(
        self, api_client, farm, guest_order, farmer_user, guest_customer
    ):
        """Complete action should increment customer's completed_orders."""
        api_client.force_authenticate(user=farmer_user)
        
        initial_completed = guest_customer.completed_orders
        
        guest_order.status = 'payment_confirmed'
        guest_order.save()
        
        response = api_client.post(
            f'/api/marketplace/guest-orders/{guest_order.id}/action/',
            {'action': 'complete'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        guest_customer.refresh_from_db()
        assert guest_customer.completed_orders == initial_completed + 1
    
    def test_complete_sets_completed_at_timestamp(
        self, api_client, farm, guest_order, farmer_user
    ):
        """Complete action should set completed_at timestamp."""
        api_client.force_authenticate(user=farmer_user)
        
        assert guest_order.completed_at is None
        
        guest_order.status = 'payment_confirmed'
        guest_order.save()
        
        before_complete = timezone.now()
        
        response = api_client.post(
            f'/api/marketplace/guest-orders/{guest_order.id}/action/',
            {'action': 'complete'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        guest_order.refresh_from_db()
        assert guest_order.completed_at is not None
        assert guest_order.completed_at >= before_complete
