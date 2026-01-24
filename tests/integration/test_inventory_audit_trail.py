"""
Tests for Inventory Audit Trail

Verifies that ALL stock movements create proper audit records via StockMovement.
This ensures complete accountability for government reporting.

Flow tested:
1. Product.reduce_stock() → FarmInventory.remove_stock() → StockMovement created
2. Product.restore_stock() → FarmInventory.add_stock() → StockMovement created
3. Auto-creation of FarmInventory when Product doesn't have one linked
"""

import pytest
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone

from sales_revenue.marketplace_models import Product, ProductCategory
from sales_revenue.inventory_models import FarmInventory, StockMovement, InventoryCategory, StockMovementType


@pytest.fixture
def product_category(db):
    """Create a product category for testing."""
    return ProductCategory.objects.create(
        name='Fresh Eggs',
        slug='fresh-eggs',
        is_active=True
    )


@pytest.fixture
def farmer_user(db, django_user_model):
    """Create a farmer user."""
    return django_user_model.objects.create_user(
        username='test_farmer_audit',
        phone='+233501234599',
        password='testpass123',
        role='FARMER',
        email='audit_farmer@test.com'
    )


@pytest.fixture
def farm(db, farmer_user):
    """Create a farm with all required fields."""
    from farms.models import Farm
    
    farm = Farm.objects.create(
        user=farmer_user,
        first_name='Audit',
        last_name='Farmer',
        email='audit_farmer@test.com',
        primary_phone='+233501234599',
        date_of_birth='1990-01-01',
        gender='Male',
        ghana_card_number='GHA-123456789-A',
        residential_address='Test Address',
        primary_constituency='Ayawaso Central',  # This determines region
        nok_full_name='Test NOK',
        nok_relationship='Spouse',
        nok_phone='+233501234500',
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=5,
        farm_name='Audit Test Farm',
        ownership_type='Sole Proprietorship',
        tin='C0012345699',
        number_of_poultry_houses=2,
        total_bird_capacity=5000,
        housing_type='Deep Litter',
        total_infrastructure_value_ghs=25000.00,
        primary_production_type='Layers',
        planned_production_start_date='2025-01-01',
        initial_investment_amount=50000.00,
        funding_source=['Personal Savings'],
        monthly_operating_budget=5000.00,
        expected_monthly_revenue=8000.00,
        farm_status='Active',
        application_status='Approved',
    )
    
    farmer_user.farm = farm
    farmer_user.save()
    
    return farm


@pytest.fixture
def product_without_inventory(db, farm, product_category):
    """Create a product NOT linked to FarmInventory."""
    return Product.objects.create(
        farm=farm,
        category=product_category,
        name='Fresh Eggs (No Inventory Link)',
        price=Decimal('35.00'),
        unit='crate',
        stock_quantity=100,
        track_inventory=True,
        status='active',
        min_order_quantity=1,
    )


@pytest.fixture
def product_with_inventory(db, farm, product_category):
    """Create a product with linked FarmInventory."""
    product = Product.objects.create(
        farm=farm,
        category=product_category,
        name='Fresh Eggs (With Inventory)',
        price=Decimal('40.00'),
        unit='crate',
        stock_quantity=150,
        track_inventory=True,
        status='active',
        min_order_quantity=1,
    )
    
    # Create linked inventory
    inventory = FarmInventory.objects.create(
        farm=farm,
        marketplace_product=product,
        category=InventoryCategory.EGGS,
        product_name='Fresh Eggs (With Inventory)',
        unit='crate',
        quantity_available=150,
        unit_cost=Decimal('30.00'),
        low_stock_threshold=20,
    )
    
    return product


# ==============================================================================
# TEST: AUTO-CREATE INVENTORY
# ==============================================================================

@pytest.mark.django_db
class TestAutoCreateInventory:
    """Tests for automatic FarmInventory creation."""
    
    def test_reduce_stock_creates_inventory_if_missing(self, product_without_inventory):
        """When reduce_stock() is called, FarmInventory is auto-created."""
        product = product_without_inventory
        
        # Verify no inventory exists initially
        assert not hasattr(product, 'inventory_record') or product.inventory_record is None
        
        # Call reduce_stock
        product.reduce_stock(quantity=10)
        
        # Refresh from DB
        product.refresh_from_db()
        
        # Verify inventory was created
        assert FarmInventory.objects.filter(marketplace_product=product).exists()
        
        # Verify inventory is now linked
        inventory = FarmInventory.objects.get(marketplace_product=product)
        assert inventory.farm == product.farm
        assert inventory.category == InventoryCategory.EGGS  # Auto-detected from product name
    
    def test_auto_created_inventory_has_correct_initial_values(self, product_without_inventory):
        """Auto-created inventory has correct initial stock and metadata."""
        product = product_without_inventory
        initial_stock = product.stock_quantity
        
        # First call will create inventory
        product.reduce_stock(quantity=5)
        
        # Refresh and check
        inventory = FarmInventory.objects.get(marketplace_product=product)
        
        # Quantity should be initial - deducted
        # Note: The initial stock at creation was product.stock_quantity, then 5 was deducted
        assert inventory.quantity_available == initial_stock - 5
        assert inventory.product_name == product.name
        assert inventory.unit == product.unit


# ==============================================================================
# TEST: STOCK MOVEMENT AUDIT TRAIL
# ==============================================================================

@pytest.mark.django_db
class TestStockMovementAuditTrail:
    """Tests for StockMovement audit records."""
    
    def test_reduce_stock_creates_stock_movement(self, product_with_inventory, farmer_user):
        """reduce_stock() creates a StockMovement audit record."""
        product = product_with_inventory
        initial_count = StockMovement.objects.count()
        
        # Reduce stock with reference
        product.reduce_stock(
            quantity=10,
            reference_record=None,  # Could be an order item
            unit_price=product.price,
            notes='Test deduction',
            recorded_by=farmer_user
        )
        
        # Verify StockMovement was created
        assert StockMovement.objects.count() == initial_count + 1
        
        movement = StockMovement.objects.latest('created_at')
        assert movement.movement_type == StockMovementType.SALE
        assert movement.quantity == -10  # Negative for deductions
        assert movement.notes == 'Test deduction'
        assert movement.recorded_by == farmer_user
    
    def test_restore_stock_creates_stock_movement(self, product_with_inventory, farmer_user):
        """restore_stock() creates a StockMovement audit record."""
        product = product_with_inventory
        
        # First reduce (to have stock to restore)
        product.reduce_stock(quantity=20)
        initial_count = StockMovement.objects.count()
        
        # Now restore
        product.restore_stock(
            quantity=15,
            reference_record=None,
            notes='Test restoration',
            recorded_by=farmer_user
        )
        
        # Verify StockMovement was created
        assert StockMovement.objects.count() == initial_count + 1
        
        movement = StockMovement.objects.latest('created_at')
        assert movement.movement_type == StockMovementType.RETURN
        assert movement.quantity == 15  # Positive for additions
        assert movement.notes == 'Test restoration'
    
    def test_stock_movement_tracks_balance(self, product_with_inventory):
        """StockMovement records balance after each operation."""
        product = product_with_inventory
        inventory = product.inventory_record
        initial_balance = inventory.quantity_available
        
        # Reduce stock
        product.reduce_stock(quantity=30)
        
        movement = StockMovement.objects.latest('created_at')
        assert movement.balance_after == initial_balance - 30
    
    def test_stock_movement_tracks_source_type(self, product_with_inventory, farm, product_category):
        """StockMovement records the source type (model name)."""
        product = product_with_inventory
        
        # Create a mock order item as reference
        from sales_revenue.marketplace_models import MarketplaceOrder, OrderItem
        from sales_revenue.models import Customer
        
        customer = Customer.objects.create(
            farm=farm,
            first_name='Test',
            last_name='Customer',
            phone_number='+233501111111'
        )
        
        order = MarketplaceOrder.objects.create(
            farm=farm,
            customer=customer,
            status='pending'
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit=product.unit,
            unit_price=product.price,
            quantity=5,
            line_total=product.price * 5
        )
        
        # Reduce with reference record
        product.reduce_stock(
            quantity=5,
            reference_record=order_item,
            notes='Order sale'
        )
        
        movement = StockMovement.objects.latest('created_at')
        assert movement.source_type == 'OrderItem'
        assert movement.source_id == str(order_item.id)


# ==============================================================================
# TEST: INVENTORY SYNC
# ==============================================================================

@pytest.mark.django_db
class TestInventorySync:
    """Tests for FarmInventory <-> Product synchronization."""
    
    def test_inventory_syncs_to_product(self, product_with_inventory):
        """FarmInventory.save() syncs quantity to Product."""
        product = product_with_inventory
        inventory = product.inventory_record
        
        # Manually update inventory
        inventory.quantity_available = 75
        inventory.save()
        
        # Refresh product
        product.refresh_from_db()
        
        # Product should be synced
        assert product.stock_quantity == 75
    
    def test_inventory_updates_product_status_to_out_of_stock(self, product_with_inventory):
        """When inventory hits zero, Product status becomes 'out_of_stock'."""
        product = product_with_inventory
        inventory = product.inventory_record
        
        # Set inventory to zero
        inventory.quantity_available = 0
        inventory.save()
        
        # Refresh product
        product.refresh_from_db()
        
        assert product.stock_quantity == 0
        assert product.status == 'out_of_stock'
    
    def test_inventory_restores_product_status_to_active(self, product_with_inventory):
        """When inventory is replenished, Product status becomes 'active'."""
        product = product_with_inventory
        inventory = product.inventory_record
        
        # Set to zero first
        inventory.quantity_available = 0
        inventory.save()
        
        product.refresh_from_db()
        assert product.status == 'out_of_stock'
        
        # Replenish
        inventory.quantity_available = 50
        inventory.save()
        
        product.refresh_from_db()
        assert product.status == 'active'


# ==============================================================================
# TEST: CATEGORY DETECTION
# ==============================================================================

@pytest.mark.django_db
class TestCategoryDetection:
    """Tests for automatic inventory category detection."""
    
    def test_eggs_detected_from_product_name(self, farm, product_category):
        """Products with 'egg' in name get EGGS category."""
        product = Product.objects.create(
            farm=farm,
            category=product_category,
            name='Fresh Layer Eggs',
            price=Decimal('35.00'),
            stock_quantity=100,
            track_inventory=True,
            status='active',
        )
        
        product.reduce_stock(quantity=5)
        
        inventory = FarmInventory.objects.get(marketplace_product=product)
        assert inventory.category == InventoryCategory.EGGS
    
    def test_processed_detected_from_product_name(self, farm):
        """Products with 'processed' or 'dressed' get PROCESSED category."""
        # Create a generic category that doesn't hint at eggs
        generic_category = ProductCategory.objects.create(
            name='Poultry Products',
            slug='poultry-products',
            is_active=True
        )
        
        product = Product.objects.create(
            farm=farm,
            category=generic_category,
            name='Dressed Chicken',
            price=Decimal('80.00'),
            stock_quantity=50,
            track_inventory=True,
            status='active',
        )
        
        product.reduce_stock(quantity=2)
        
        inventory = FarmInventory.objects.get(marketplace_product=product)
        assert inventory.category == InventoryCategory.PROCESSED
    
    def test_chicks_detected_from_product_name(self, farm):
        """Products with 'chick' get CHICKS category."""
        # Create a generic category
        generic_category = ProductCategory.objects.create(
            name='Live Animals',
            slug='live-animals',
            is_active=True
        )
        
        product = Product.objects.create(
            farm=farm,
            category=generic_category,
            name='Day Old Chicks',
            price=Decimal('15.00'),
            stock_quantity=500,
            track_inventory=True,
            status='active',
        )
        
        product.reduce_stock(quantity=50)
        
        inventory = FarmInventory.objects.get(marketplace_product=product)
        assert inventory.category == InventoryCategory.CHICKS
    
    def test_default_category_is_birds(self, farm):
        """Products without specific keywords default to BIRDS."""
        # Create a generic category
        generic_category = ProductCategory.objects.create(
            name='Live Stock',
            slug='live-stock',
            is_active=True
        )
        
        product = Product.objects.create(
            farm=farm,
            category=generic_category,
            name='Live Broilers 6 weeks',
            price=Decimal('50.00'),
            stock_quantity=200,
            track_inventory=True,
            status='active',
        )
        
        product.reduce_stock(quantity=10)
        
        inventory = FarmInventory.objects.get(marketplace_product=product)
        assert inventory.category == InventoryCategory.BIRDS


# ==============================================================================
# TEST: REVENUE TRACKING
# ==============================================================================

@pytest.mark.django_db
class TestRevenueTracking:
    """Tests for revenue tracking in inventory."""
    
    def test_sale_updates_inventory_revenue(self, product_with_inventory):
        """Sales should track revenue in FarmInventory."""
        product = product_with_inventory
        inventory = product.inventory_record
        initial_revenue = inventory.total_revenue
        
        # Make a sale
        product.reduce_stock(
            quantity=10,
            unit_price=Decimal('45.00'),
            notes='Sale'
        )
        
        # Refresh and check
        inventory.refresh_from_db()
        assert inventory.total_revenue == initial_revenue + (10 * Decimal('45.00'))
    
    def test_sale_updates_inventory_total_sold(self, product_with_inventory):
        """Sales should increment total_sold in FarmInventory."""
        product = product_with_inventory
        inventory = product.inventory_record
        initial_sold = inventory.total_sold
        
        product.reduce_stock(quantity=15)
        
        inventory.refresh_from_db()
        assert inventory.total_sold == initial_sold + 15


# ==============================================================================
# TEST: FALLBACK BEHAVIOR
# ==============================================================================

@pytest.mark.django_db
class TestFallbackBehavior:
    """Tests for fallback when track_inventory=False."""
    
    def test_no_audit_when_track_inventory_false(self, farm, product_category):
        """Products with track_inventory=False don't create audit records."""
        product = Product.objects.create(
            farm=farm,
            category=product_category,
            name='Untracked Product',
            price=Decimal('100.00'),
            stock_quantity=50,
            track_inventory=False,  # Tracking disabled
            status='active',
        )
        
        initial_movement_count = StockMovement.objects.count()
        
        product.reduce_stock(quantity=10)
        product.restore_stock(quantity=5)
        
        # No movements should be created
        assert StockMovement.objects.count() == initial_movement_count
        
        # No inventory should be created
        assert not FarmInventory.objects.filter(marketplace_product=product).exists()
