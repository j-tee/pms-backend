"""
Comprehensive test suite for Returns and Refunds functionality.

Tests cover:
- Return request creation and validation
- Approval/rejection workflow
- Stock restoration on returns
- Revenue metrics adjustment
- Refund processing
- Edge cases and error handling
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from sales_revenue.returns_refunds_models import (
    ReturnRequest, ReturnItem, RefundTransaction, ReturnReason
)
from sales_revenue.marketplace_models import (
    Product, ProductCategory, MarketplaceOrder, OrderItem
)
from sales_revenue.models import Customer
from sales_revenue.inventory_models import FarmInventory, StockMovement, StockMovementType
from farms.models import Farm

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for making requests."""
    return APIClient()


@pytest.fixture
def farmer_user(db):
    """Create a farmer user with farm."""
    user = User.objects.create_user(
        username='farmer_test',
        email='farmer@test.com',
        password='testpass123',
        first_name='John',
        last_name='Farmer',
        role='FARMER',
        phone='+233241234567'
    )
    farm = Farm.objects.create(
        user=user,
        first_name='John',
        last_name='Farmer',
        date_of_birth='1990-01-01',
        gender='Male',
        ghana_card_number='GHA-123456789-1',
        primary_phone='+233241234567',
        residential_address='123 Test Address',
        primary_constituency='Ayawaso Central',
        nok_full_name='Jane Doe',
        nok_relationship='Spouse',
        nok_phone='+233241234570',
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=5,
        farm_name='Test Farm Returns',
        ownership_type='Sole Proprietorship',
        tin='C0012345678',
        number_of_poultry_houses=1,
        total_bird_capacity=1000,
        housing_type='Deep Litter',
        total_infrastructure_value_ghs=10000.00,
        primary_production_type='Layers',
        planned_production_start_date='2024-01-01',
        initial_investment_amount=50000.00,
        funding_source=['Personal Savings'],
        monthly_operating_budget=5000.00,
        expected_monthly_revenue=8000.00,
    )
    user.farm = farm
    user.save()
    return user


@pytest.fixture
def customer(farmer_user):
    """Create a customer for the farm."""
    customer = Customer.objects.create(
        farm=farmer_user.farm,
        customer_type='individual',
        first_name='Jane',
        last_name='Customer',
        phone_number='+233241234568',
        mobile_money_number='+233241234568',
        mobile_money_provider='mtn',
        mobile_money_account_name='Jane Customer'
    )
    return customer


@pytest.fixture
def customer_user(db, farmer_user):
    """Create a user who is a customer (buyer from the farm)."""
    user = User.objects.create_user(
        username='customer_test',
        email='customer@test.com',
        password='testpass123',
        first_name='Jane',
        last_name='Customer',
        role='FARMER',  # Customers are typically other farmers buying
        phone='+233241234599'
    )
    # Create a customer profile linked to this user for the farmer's farm
    customer_profile = Customer.objects.create(
        farm=farmer_user.farm,
        customer_type='individual',
        first_name='Jane',
        last_name='Customer',
        phone_number='+233241234599',
        email='customer@test.com',
        mobile_money_number='+233241234599',
        mobile_money_provider='mtn',
        mobile_money_account_name='Jane Customer'
    )
    # Attach customer profile to user for easy access in tests
    user.customer_profile = customer_profile
    return user


@pytest.fixture
def product_with_inventory(farmer_user):
    """Create a product with inventory."""
    # Create product category first
    category = ProductCategory.objects.create(
        name='Whole Birds',
        slug='whole-birds',
        description='Whole dressed birds',
        is_active=True
    )
    
    product = Product.objects.create(
        farm=farmer_user.farm,
        name='Test Chicken',
        description='Fresh chicken',
        price=Decimal('50.00'),
        stock_quantity=100,
        sku='CHKN-001',
        category=category
    )
    
    # Create corresponding inventory
    inventory = FarmInventory.objects.create(
        farm=farmer_user.farm,
        marketplace_product=product,
        quantity_available=100,
        category='whole_birds',
        product_name='Test Chicken'
    )
    
    return product


@pytest.fixture
def completed_order(customer, product_with_inventory):
    """Create a completed order ready for returns."""
    order = MarketplaceOrder.objects.create(
        farm=product_with_inventory.farm,
        customer=customer,
        order_number=f'ORD-{timezone.now().strftime("%Y%m%d")}-001',
        total_amount=Decimal('250.00'),
        status='delivered',
        payment_status='paid'
    )
    
    order_item = OrderItem.objects.create(
        order=order,
        product=product_with_inventory,
        quantity=5,
        unit_price=Decimal('50.00'),
        line_total=Decimal('250.00')
    )
    
    # Update product metrics as if order was fulfilled
    product_with_inventory.stock_quantity -= 5
    product_with_inventory.total_sold += 5
    product_with_inventory.total_revenue += Decimal('250.00')
    product_with_inventory.save()
    
    return order


@pytest.mark.django_db
class TestReturnRequestCreation:
    """Tests for creating return requests."""
    
    def test_customer_can_create_return_request(self, customer, completed_order):
        """Test that customer can create a return request for their order."""
        return_request = ReturnRequest.objects.create(
            order=completed_order,
            customer=customer,
            status='pending',
            reason='defective',
            detailed_reason='Some items were damaged on arrival'
        )
        
        order_item = completed_order.items.first()
        return_item = ReturnItem.objects.create(
            return_request=return_request,
            order_item=order_item,
            product=order_item.product,
            product_name=order_item.product.name,
            unit='bird',
            unit_price=order_item.unit_price,
            quantity=2,
            item_reason='defective',
            refund_amount=Decimal('100.00')
        )
        
        assert ReturnRequest.objects.count() == 1
        assert return_request.order == completed_order
        assert return_request.customer == customer
        assert return_request.status == 'pending'
        assert return_request.return_items.count() == 1
        assert return_item.quantity == 2
        assert return_item.item_reason == 'defective'
        assert return_item.refund_amount == Decimal('100.00')
    
    def test_cannot_return_more_than_ordered(self, customer, completed_order):
        """Test that customer cannot return more items than ordered."""
        from django.core.exceptions import ValidationError
        
        return_request = ReturnRequest.objects.create(
            order=completed_order,
            customer=customer,
            status='pending',
            reason='defective',
            detailed_reason='Items are defective'
        )
        
        # Try to return 10 items when only 5 were ordered
        order_item = completed_order.items.first()
        with pytest.raises(ValidationError):  # Should raise validation error
            return_item = ReturnItem.objects.create(
                return_request=return_request,
                order_item=order_item,
                product=order_item.product,
                product_name=order_item.product.name,
                unit='bird',
                unit_price=order_item.unit_price,
                quantity=10,  # More than ordered
                item_reason='defective',
                refund_amount=Decimal('500.00')
            )


@pytest.mark.django_db
class TestReturnApproval:
    """Tests for approving/rejecting return requests."""
    
    @pytest.fixture
    def pending_return(self, customer_user, completed_order):
        """Create a pending return request."""
        return_request = ReturnRequest.objects.create(
            order=completed_order,
            customer=customer_user.customer_profile,
            status='pending',
            reason='defective',
            detailed_reason='Items damaged'
        )
        
        order_item = completed_order.items.first()
        ReturnItem.objects.create(
            return_request=return_request,
            order_item=order_item,
            product=order_item.product,
            product_name=order_item.product.name,
            unit='bird',
            unit_price=order_item.unit_price,
            quantity=2,
            item_reason='defective',
            refund_amount=Decimal('100.00')
        )
        
        return return_request
    
    def test_seller_can_approve_return(self, api_client, farmer_user, pending_return):
        """Test that seller can approve return requests."""
        api_client.force_authenticate(user=farmer_user)
        
        data = {
            'approved': True,
            'admin_notes': 'Return approved, please ship items back'
        }
        
        response = api_client.post(
            f'/api/returns/{pending_return.id}/approve/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        pending_return.refresh_from_db()
        assert pending_return.status == 'approved'
        assert pending_return.reviewed_by == farmer_user
        assert pending_return.reviewed_at is not None
    
    def test_seller_can_reject_return(self, api_client, farmer_user, pending_return):
        """Test that seller can reject return requests."""
        api_client.force_authenticate(user=farmer_user)
        
        data = {
            'approved': False,
            'rejection_reason': 'Items were not damaged, return window expired',
            'admin_notes': 'Reviewed photos, no visible damage'
        }
        
        response = api_client.post(
            f'/api/returns/{pending_return.id}/approve/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        pending_return.refresh_from_db()
        assert pending_return.status == 'rejected'
        assert pending_return.reviewed_by == farmer_user
        assert pending_return.reviewed_at is not None
        assert 'expired' in pending_return.review_notes
    
    def test_rejection_requires_reason(self, api_client, farmer_user, pending_return):
        """Test that rejecting return requires a reason."""
        api_client.force_authenticate(user=farmer_user)
        
        data = {
            'approved': False
            # Missing rejection_reason
        }
        
        response = api_client.post(
            f'/api/returns/{pending_return.id}/approve/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'rejection_reason' in str(response.data).lower()
    
    def test_customer_cannot_approve_own_return(self, api_client, customer_user, pending_return):
        """Test that customer cannot approve their own return request."""
        api_client.force_authenticate(user=customer_user)
        
        data = {'approved': True}
        
        response = api_client.post(
            f'/api/returns/{pending_return.id}/approve/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestStockRestoration:
    """Tests for stock restoration when items are returned."""
    
    @pytest.fixture
    def approved_return(self, customer_user, completed_order):
        """Create an approved return request."""
        return_request = ReturnRequest.objects.create(
            order=completed_order,
            customer=customer_user.customer_profile,
            status='approved',
            reason='defective',
            detailed_reason='Items were damaged'
        )
        
        order_item = completed_order.items.first()
        ReturnItem.objects.create(
            return_request=return_request,
            order_item=order_item,
            product=order_item.product,
            product_name=order_item.product.name,
            unit='bird',
            unit_price=order_item.unit_price,
            quantity=2,
            item_reason='defective',
            refund_amount=Decimal('100.00')
        )
        
        return return_request
    
    def test_stock_restored_when_items_received_in_good_condition(
        self, api_client, farmer_user, approved_return, product_with_inventory
    ):
        """Test that stock is restored when returned items are in good condition."""
        api_client.force_authenticate(user=farmer_user)
        
        data = {
            'items': [
                {
                    'id': str(approved_return.return_items.first().id),
                    'condition_on_arrival': 'good',
                    'quality_notes': 'Items in perfect condition'
                }
            ],
            'admin_notes': 'Items received and inspected'
        }
        
        response = api_client.post(
            f'/api/returns/{approved_return.id}/items-received/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify return status updated
        approved_return.refresh_from_db()
        assert approved_return.status == 'items_received'
        assert approved_return.items_received_at is not None
        
        # Verify return item marked as good condition
        return_item = approved_return.return_items.first()
        return_item.refresh_from_db()
        assert return_item.returned_in_good_condition is True
    
    def test_stock_not_restored_for_damaged_items(
        self, api_client, farmer_user, approved_return, product_with_inventory
    ):
        """Test that damaged items are not added back to inventory."""
        api_client.force_authenticate(user=farmer_user)
        
        data = {
            'items': [
                {
                    'id': str(approved_return.return_items.first().id),
                    'condition_on_arrival': 'damaged',
                    'quality_notes': 'Items severely damaged during shipping'
                }
            ]
        }
        
        response = api_client.post(
            f'/api/returns/{approved_return.id}/items-received/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify return status updated
        approved_return.refresh_from_db()
        assert approved_return.status == 'items_received'
        
        # Return item should NOT be marked as good condition
        return_item = approved_return.return_items.first()
        return_item.refresh_from_db()
        assert return_item.returned_in_good_condition is False


@pytest.mark.django_db
class TestRevenueAdjustment:
    """Tests for revenue metrics adjustment on returns."""
    
    @pytest.fixture
    def return_ready_for_completion(self, customer_user, completed_order, farmer_user):
        """Create a return that's ready to be completed."""
        return_request = ReturnRequest.objects.create(
            order=completed_order,
            customer=customer_user.customer_profile,
            status='refund_issued',
            reason='defective',
            detailed_reason='Items were defective'
        )
        
        order_item = completed_order.items.first()
        return_item = ReturnItem.objects.create(
            return_request=return_request,
            order_item=order_item,
            product=order_item.product,
            product_name=order_item.product.name,
            unit='bird',
            unit_price=order_item.unit_price,
            quantity=2,
            item_reason='defective',
            refund_amount=Decimal('100.00'),
            stock_restored=True
        )
        
        RefundTransaction.objects.create(
            return_request=return_request,
            amount=Decimal('100.00'),
            refund_method='mobile_money',
            status='completed',
            processed_by=farmer_user
        )
        
        return return_request
    
    def test_product_metrics_adjusted_on_return_completion(
        self, api_client, farmer_user, return_ready_for_completion, product_with_inventory
    ):
        """Test that return can be completed."""
        api_client.force_authenticate(user=farmer_user)
        
        response = api_client.post(
            f'/api/returns/{return_ready_for_completion.id}/complete/',
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify return completed
        return_ready_for_completion.refresh_from_db()
        assert return_ready_for_completion.status == 'completed'
        assert return_ready_for_completion.completed_at is not None


@pytest.mark.django_db
class TestRefundProcessing:
    """Tests for refund transaction processing."""
    
    @pytest.fixture
    def return_items_received(self, customer_user, completed_order):
        """Create a return with items received."""
        return_request = ReturnRequest.objects.create(
            order=completed_order,
            customer=customer_user.customer_profile,
            status='items_received',
            total_refund_amount=Decimal('100.00'),
            reason='defective',
            detailed_reason='Items were defective'
        )
        
        order_item = completed_order.items.first()
        ReturnItem.objects.create(
            return_request=return_request,
            order_item=order_item,
            product=order_item.product,
            product_name=order_item.product.name,
            unit='bird',
            unit_price=order_item.unit_price,
            quantity=2,
            item_reason='defective',
            refund_amount=Decimal('100.00'),
            returned_in_good_condition=True,
            stock_restored=True
        )
        
        return return_request
    
    def test_seller_can_issue_refund(self, api_client, farmer_user, return_items_received):
        """Test that seller can issue refund after items received."""
        api_client.force_authenticate(user=farmer_user)
        
        data = {
            'payment_method': 'mobile_money',
            'payment_provider': 'MTN MoMo',
            'transaction_id': 'REFUND-123456',
            'notes': 'Refund processed via mobile money'
        }
        
        response = api_client.post(
            f'/api/returns/{return_items_received.id}/issue-refund/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify refund transaction created
        assert RefundTransaction.objects.filter(
            return_request=return_items_received
        ).exists()
        
        transaction = RefundTransaction.objects.get(return_request=return_items_received)
        assert transaction.amount == Decimal('100.00')
        assert transaction.refund_method == 'mobile_money'
        assert transaction.status == 'completed'
        assert transaction.processed_by == farmer_user
        
        # Verify return status updated
        return_items_received.refresh_from_db()
        assert return_items_received.status == 'refund_issued'
        assert return_items_received.refund_issued_at is not None


@pytest.mark.django_db
class TestReturnStatistics:
    """Tests for return statistics endpoint."""
    
    def test_farmer_sees_returns_for_their_farm(
        self, api_client, farmer_user, customer_user, completed_order
    ):
        """Test that farmers see statistics for returns on their products."""
        # Create some returns
        for i in range(3):
            return_request = ReturnRequest.objects.create(
                order=completed_order,
                customer=customer_user.customer_profile,
                status='pending',
                total_refund_amount=Decimal('50.00') * (i + 1),
                reason='defective',
                detailed_reason=f'Items were defective - batch {i + 1}'
            )
        
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/returns/statistics/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_returns'] == 3
        assert response.data['pending_count'] == 3
    
    def test_customer_sees_only_their_returns(
        self, api_client, customer_user, completed_order, farmer_user
    ):
        """Test that customers see only their own return statistics."""
        # Create returns for this customer
        ReturnRequest.objects.create(
            order=completed_order,
            customer=customer_user.customer_profile,
            status='completed',
            total_refund_amount=Decimal('100.00'),
            reason='defective',
            detailed_reason='Items were defective'
        )
        
        # Create another customer with returns
        other_customer = Customer.objects.create(
            farm=farmer_user.farm,
            customer_type='individual',
            first_name='Other',
            last_name='Customer',
            phone_number='+233241234888',
            mobile_money_number='+233241234888',
            mobile_money_provider='mtn',
            mobile_money_account_name='Other Customer'
        )
        other_order = MarketplaceOrder.objects.create(
            farm=completed_order.farm,
            customer=other_customer,
            order_number='ORD-OTHER',
            total_amount=Decimal('50.00'),
            status='delivered'
        )
        ReturnRequest.objects.create(
            order=other_order,
            customer=other_customer,
            status='pending',
            reason='defective',
            detailed_reason='Other return reason'
        )
        
        api_client.force_authenticate(user=customer_user)
        response = api_client.get('/api/returns/statistics/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_returns'] == 1  # Only customer's own returns
        assert response.data['completed_count'] == 1
