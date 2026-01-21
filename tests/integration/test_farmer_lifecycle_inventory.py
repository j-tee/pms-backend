"""
Comprehensive Farmer Lifecycle & Inventory Test

This test simulates a complete farmer journey from receiving day-old chicks
to selling/disposing of all birds through various channels.

SCENARIO:
=========
- Farmer starts with 500 day-old chicks (broilers)
- Over the growth period:
  - 35 birds die (mortality)
  - 78 birds sold as live birds to local customers
  - 56 birds processed (slaughtered) and products sold
  - Remaining 331 birds procured by government

PRICING (realistic Ghana market prices):
========================================
- Day-old chicks: GHS 15 per bird
- Live broiler (mature): GHS 85 per bird
- Processed whole bird: GHS 95 per kg (avg 2.5kg = GHS 237.50 per bird)
- Government procurement: GHS 75 per bird (bulk discount)

OPERATIONAL COSTS (realistic Ghana market):
==========================================
- Feed: ~GHS 9.50/kg (broiler finisher), ~4.2 kg per bird over 6 weeks
- Vaccination/Medication: ~GHS 3.50 per bird
- Labor: ~GHS 350/week for caretaker
- Utilities: ~GHS 120/week (water, electricity)
- Litter/Bedding: ~GHS 400 for 500 birds
- Processing: ~GHS 8/bird (slaughter, cleaning, packaging)

Note: Feed typically accounts for 60-70% of total production costs.

INVENTORY TRACKING VERIFICATION:
================================
At each step, we verify:
1. Flock current_count matches expected
2. Total mortality tracked correctly
3. Inventory deductions are accurate
4. Sales revenue calculations are correct
5. Processing batch creates correct inventory
6. Procurement assignments reflect correctly

Edge Cases Tested:
- Processing batch deduction from flock
- Inventory sync with marketplace products
- Multiple partial deliveries for procurement
- Stock movement audit trail
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APIClient
from rest_framework import status
import uuid

User = get_user_model()

pytestmark = pytest.mark.django_db


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def setup_test_environment():
    """
    Create all necessary objects for the farmer lifecycle test.
    """
    from farms.models import Farm
    from accounts.models import User
    
    unique_id = uuid.uuid4().hex[:8]
    
    # Create farmer user
    farmer_user = User.objects.create_user(
        username=f'farmer_{unique_id}',
        email=f'testfarmer_{unique_id}@example.com',
        phone=f'+23324123{unique_id[:4]}',
        first_name='Kwame',
        last_name='Asante',
        role='FARMER',
        password='testpass123'
    )
    
    # Create farm with all required fields
    farm = Farm.objects.create(
        user=farmer_user,
        # Section 1.1: Basic Info
        first_name='Kwame',
        last_name='Asante',
        date_of_birth='1985-06-15',
        gender='Male',
        ghana_card_number=f'GHA-{unique_id[:9].upper()}-1',
        # Section 1.2: Contact
        primary_phone=f'+23324123{unique_id[:4]}',
        residential_address='123 Farm Road, Dome',
        primary_constituency='Dome-Kwabenya',  # Greater Accra constituency
        # Section 1.3: Next of Kin
        nok_full_name='Akua Asante',
        nok_relationship='Spouse',
        nok_phone='+233241234999',
        # Section 1.4: Education
        education_level='SHS/Technical',
        literacy_level='Can Read & Write',
        years_in_poultry=3,
        # Section 2: Farm Info
        farm_name='Golden Poultry Farm',
        ownership_type='Sole Proprietorship',
        tin=f'C{unique_id[:10].upper()}',
        # Section 4: Infrastructure
        number_of_poultry_houses=2,
        total_bird_capacity=1000,
        current_bird_count=0,
        housing_type='Deep Litter',
        total_infrastructure_value_ghs=25000.00,
        # Section 5: Production
        primary_production_type='Broilers',
        broiler_breed='Cobb 500',
        planned_monthly_bird_sales=200,
        planned_production_start_date='2025-01-01',
        # Section 7: Financial
        initial_investment_amount=50000.00,
        funding_source=['Personal Savings'],
        monthly_operating_budget=8000.00,
        expected_monthly_revenue=15000.00,
        # Registration source (determines government farmer status)
        registration_source='government_initiative',  # Makes is_government_farmer=True
        yea_program_batch='YEA-2026-Q1',
        # Status
        application_status='Approved',
        farm_status='Active',
        marketplace_enabled=True,
    )
    
    # Create admin/officer user for procurement
    admin_user = User.objects.create_user(
        username=f'admin_{unique_id}',
        email=f'admin_{unique_id}@yea.gov.gh',
        phone=f'+23320987{unique_id[:4]}',
        first_name='Procurement',
        last_name='Officer',
        role='PROCUREMENT_OFFICER',
        password='adminpass123'
    )
    
    # Create a customer for sales
    from sales_revenue.models import Customer
    customer = Customer.objects.create(
        farm=farm,
        customer_type='business',
        first_name='Local',
        last_name='Buyer',
        business_name='Accra Poultry Wholesalers',
        phone_number=f'+23324000{unique_id[:4]}',
        mobile_money_number=f'+23324000{unique_id[:4]}',
        mobile_money_provider='mtn',
        mobile_money_account_name='Local Buyer',
        location='Accra Central',
    )
    
    return {
        'farmer': farmer_user,
        'farm': farm,
        'admin': admin_user,
        'customer': customer,
    }


@pytest.fixture
def api_client():
    return APIClient()


# =============================================================================
# STEP 1: CREATE FLOCK WITH 500 DAY-OLD CHICKS
# =============================================================================

class TestStep1FlockCreation:
    """
    Test Step 1: Farmer receives 500 day-old chicks.
    
    Expected State After:
    - Flock created with initial_count=500, current_count=500
    - Farm current_bird_count updated
    - No mortality, no sales yet
    """
    
    INITIAL_BIRD_COUNT = 500
    PURCHASE_PRICE_PER_BIRD = Decimal('15.00')  # GHS 15 per day-old chick
    
    def test_create_flock_with_500_chicks(self, setup_test_environment):
        """Create a flock of 500 broiler chicks."""
        from flock_management.models import Flock
        
        farm = setup_test_environment['farm']
        
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-2026-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            supplier_name='National Hatchery Ltd',
            arrival_date=timezone.now().date() - timedelta(days=42),  # 6 weeks ago
            initial_count=self.INITIAL_BIRD_COUNT,
            current_count=self.INITIAL_BIRD_COUNT,
            age_at_arrival_weeks=Decimal('0'),  # Day-old chicks
            purchase_price_per_bird=self.PURCHASE_PRICE_PER_BIRD,
            status='Active',
            notes='YEA program batch - comprehensive test'
        )
        
        # Verify flock state
        assert flock.initial_count == self.INITIAL_BIRD_COUNT
        assert flock.current_count == self.INITIAL_BIRD_COUNT
        assert flock.total_mortality == 0
        assert flock.mortality_rate_percent == 0
        
        # Verify financial tracking
        expected_total_cost = self.INITIAL_BIRD_COUNT * self.PURCHASE_PRICE_PER_BIRD
        assert flock.total_acquisition_cost == expected_total_cost
        
        # Verify survival rate
        assert flock.survival_rate_percent == 100
        
        return flock
    
    def test_flock_age_tracking(self, setup_test_environment):
        """Verify flock age is tracked correctly."""
        from flock_management.models import Flock
        
        farm = setup_test_environment['farm']
        
        # Create flock that arrived 6 weeks ago
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-2026-002',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=500,
            current_count=500,
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        # At 6 weeks, broilers should be market-ready
        assert flock.current_age_weeks >= 6


# =============================================================================
# STEP 2: RECORD MORTALITY (35 BIRDS LOST)
# =============================================================================

class TestStep2Mortality:
    """
    Test Step 2: 35 birds die over the growth period.
    
    Expected State After:
    - Flock current_count = 500 - 35 = 465
    - total_mortality = 35
    - mortality_rate = 7%
    """
    
    MORTALITY_COUNT = 35
    
    def test_record_mortality_reduces_flock(self, setup_test_environment):
        """Record mortality and verify flock count reduces."""
        from flock_management.models import Flock, MortalityRecord
        
        farm = setup_test_environment['farm']
        user = setup_test_environment['farmer']
        
        # Create flock first
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-MORT-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=500,
            current_count=500,
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        assert flock.current_count == 500
        
        # Record mortality incidents over time
        # Week 1: 10 birds (adjustment period)
        # Week 2: 8 birds (disease)
        # Week 3: 7 birds (heat stress)
        # Week 4: 5 birds (random)
        # Week 5: 3 birds (random)
        # Week 6: 2 birds (random)
        # Total: 35 birds
        
        mortality_events = [
            (10, 'Heat Stress', 'First week adjustment'),
            (8, 'Disease', 'Coccidiosis outbreak - treated'),
            (7, 'Heat Stress', 'Heat wave'),
            (5, 'Unknown', 'Sporadic deaths'),
            (3, 'Unknown', 'Random mortality'),
            (2, 'Cannibalism', 'Pecking injury'),
        ]
        
        total_mortality = 0
        for count, cause, notes in mortality_events:
            # Create detailed mortality record
            MortalityRecord.objects.create(
                farm=farm,
                flock=flock,
                date_discovered=timezone.now().date() - timedelta(days=42 - total_mortality),
                number_of_birds=count,
                probable_cause=cause,
                notes=notes,
                reported_by=user,
            )
            
            # Manually update flock count (simulating API behavior)
            flock.current_count -= count
            flock.save()
            
            total_mortality += count
        
        # Refresh from DB
        flock.refresh_from_db()
        
        # Verify counts
        assert total_mortality == self.MORTALITY_COUNT
        assert flock.current_count == 500 - self.MORTALITY_COUNT  # 465
        assert flock.total_mortality == self.MORTALITY_COUNT
        
        # Verify mortality rate
        expected_mortality_rate = (Decimal('35') / Decimal('500')) * 100
        assert abs(flock.mortality_rate_percent - expected_mortality_rate) < Decimal('0.01')
        
        # Verify survival rate
        expected_survival = (Decimal('465') / Decimal('500')) * 100
        assert abs(flock.survival_rate_percent - expected_survival) < Decimal('0.01')
        
        return flock


# =============================================================================
# STEP 3: LIVE BIRD SALES (78 BIRDS)
# =============================================================================

class TestStep3LiveBirdSales:
    """
    Test Step 3: Sell 78 birds as live birds to local customer.
    
    Starting count: 465 (after mortality)
    Sold: 78 birds @ GHS 85 each
    Expected count after: 465 - 78 = 387
    Revenue: 78 × 85 = GHS 6,630
    """
    
    BIRDS_TO_SELL = 78
    PRICE_PER_BIRD = Decimal('85.00')  # GHS 85 per mature broiler
    
    def test_live_bird_sale_deducts_from_flock(self, setup_test_environment):
        """Record live bird sales and verify inventory updates."""
        from flock_management.models import Flock
        from sales_revenue.models import BirdSale
        from sales_revenue.inventory_models import FarmInventory, InventoryCategory
        
        farm = setup_test_environment['farm']
        customer = setup_test_environment['customer']
        
        # Create flock with 465 birds (after mortality)
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-SALES-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=500,
            current_count=465,  # After 35 mortality
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        # Record bird sale
        bird_sale = BirdSale.objects.create(
            farm=farm,
            customer=customer,
            flock=flock,
            sale_date=timezone.now().date(),
            bird_type='broiler',
            quantity=self.BIRDS_TO_SELL,
            price_per_bird=self.PRICE_PER_BIRD,
            status='completed',
            notes='Bulk sale to wholesaler',
        )
        
        # Verify sale amounts
        expected_subtotal = self.BIRDS_TO_SELL * self.PRICE_PER_BIRD
        assert bird_sale.subtotal == expected_subtotal
        assert bird_sale.total_amount == expected_subtotal
        
        # Since commission is disabled, farmer gets 100%
        assert bird_sale.farmer_payout == expected_subtotal
        assert bird_sale.platform_commission == Decimal('0')
        
        # Manually update flock count (simulating complete flow)
        flock.current_count -= self.BIRDS_TO_SELL
        flock.save()
        
        # Verify flock count
        flock.refresh_from_db()
        assert flock.current_count == 465 - self.BIRDS_TO_SELL  # 387 birds remaining
        
        return flock, bird_sale


# =============================================================================
# STEP 4: BIRD PROCESSING (56 BIRDS → PRODUCTS)
# =============================================================================

class TestStep4Processing:
    """
    Test Step 4: Process 56 birds and add products to inventory.
    
    Starting count: 387 (after live sales)
    Processed: 56 birds
    Average weight: 2.5 kg per bird
    Products: Whole dressed birds (140 kg total)
    Expected count after: 387 - 56 = 331
    """
    
    BIRDS_TO_PROCESS = 56
    AVG_BIRD_WEIGHT_KG = Decimal('2.5')
    COST_PER_KG = Decimal('75.00')  # Processing cost per kg
    SALE_PRICE_PER_KG = Decimal('95.00')  # Selling price per kg
    
    def test_processing_batch_deducts_from_flock(self, setup_test_environment):
        """Create processing batch and verify flock deduction."""
        from flock_management.models import Flock
        from sales_revenue.processing_models import (
            ProcessingBatch, ProcessingOutput, ProcessingBatchStatus,
            ProcessingType, ProductCategory, ProductGrade
        )
        from sales_revenue.inventory_models import FarmInventory, InventoryCategory
        
        farm = setup_test_environment['farm']
        user = setup_test_environment['farmer']
        
        # Create flock with 387 birds (after live sales)
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-PROC-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=500,
            current_count=387,  # After mortality and live sales
            age_at_arrival_weeks=Decimal('0'),
            purchase_price_per_bird=Decimal('15.00'),
            status='Active',
        )
        
        initial_count = flock.current_count
        
        # Create processing batch
        processing_batch = ProcessingBatch.objects.create(
            farm=farm,
            source_flock=flock,
            birds_processed=self.BIRDS_TO_PROCESS,
            average_bird_weight_kg=self.AVG_BIRD_WEIGHT_KG,
            processing_date=timezone.now().date(),
            processing_type=ProcessingType.SLAUGHTER,
            labor_cost=Decimal('200.00'),
            processing_cost=Decimal('150.00'),
            packaging_cost=Decimal('100.00'),
            birds_lost_in_processing=2,  # 2 birds lost during processing
            loss_reason='Equipment malfunction',
            status=ProcessingBatchStatus.IN_PROGRESS,
            processed_by=user,
        )
        
        # Deduct from flock
        processing_batch.deduct_from_flock()
        
        # Verify flock count reduced
        flock.refresh_from_db()
        assert flock.current_count == initial_count - self.BIRDS_TO_PROCESS
        assert flock.current_count == 331  # This matches our expected final count!
        
        # Create processing outputs (whole dressed birds)
        # 56 birds - 2 lost = 54 successfully processed
        # 54 birds × 2.5 kg = 135 kg total output
        total_output_kg = Decimal('135.00')  # Accounting for 2 lost birds
        
        # allocated_cost = cost_per_kg * weight_kg
        allocated_cost = self.COST_PER_KG * total_output_kg
        
        output = ProcessingOutput.objects.create(
            processing_batch=processing_batch,
            product_category=ProductCategory.WHOLE_BIRD,
            grade=ProductGrade.A,
            quantity=54,  # Pieces (not primary, but tracked)
            weight_kg=total_output_kg,  # PRIMARY: Weight in kg
            allocated_cost=allocated_cost,  # cost_per_kg is derived from this
        )
        
        # Complete batch and update inventory
        processing_batch.complete_and_update_inventory(user=user)
        
        # Verify batch completed
        processing_batch.refresh_from_db()
        assert processing_batch.status == ProcessingBatchStatus.COMPLETED
        assert processing_batch.inventory_updated == True
        assert processing_batch.actual_yield_weight_kg == total_output_kg
        
        # Verify inventory created
        inventory = FarmInventory.objects.filter(
            farm=farm,
            category=InventoryCategory.PROCESSED
        ).first()
        
        assert inventory is not None
        assert inventory.quantity_available == total_output_kg
        assert inventory.unit == 'kg'
        
        # Verify processing metrics
        assert processing_batch.birds_successfully_processed == 54
        assert processing_batch.loss_rate_percent == pytest.approx(3.57, rel=0.1)  # 2/56
        
        return flock, processing_batch, output
    
    def test_sell_processed_products(self, setup_test_environment):
        """Sell processed products and verify inventory deduction."""
        from flock_management.models import Flock
        from sales_revenue.processing_models import (
            ProcessingBatch, ProcessingOutput, ProcessingBatchStatus,
            ProcessingType, ProductCategory, ProductGrade
        )
        from sales_revenue.inventory_models import (
            FarmInventory, InventoryCategory, StockMovementType
        )
        from sales_revenue.marketplace_models import (
            MarketplaceOrder, OrderItem, ProductCategory as MPCategory
        )
        
        farm = setup_test_environment['farm']
        customer = setup_test_environment['customer']
        user = setup_test_environment['farmer']
        
        # Create flock and process birds (abbreviated setup)
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-PROC-SELL-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=500,
            current_count=387,
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        # Create and complete processing
        batch = ProcessingBatch.objects.create(
            farm=farm,
            source_flock=flock,
            birds_processed=56,
            average_bird_weight_kg=Decimal('2.5'),
            processing_date=timezone.now().date(),
            processing_type=ProcessingType.SLAUGHTER,
            birds_lost_in_processing=2,
            status=ProcessingBatchStatus.IN_PROGRESS,
            processed_by=user,
        )
        batch.deduct_from_flock()
        
        output = ProcessingOutput.objects.create(
            processing_batch=batch,
            product_category=ProductCategory.WHOLE_BIRD,
            grade=ProductGrade.A,
            quantity=54,
            weight_kg=Decimal('135.00'),
            allocated_cost=Decimal('75.00') * Decimal('135.00'),  # cost_per_kg derived from allocated_cost/weight
        )
        
        batch.complete_and_update_inventory(user=user)
        
        # Get inventory record
        inventory = FarmInventory.objects.get(
            farm=farm,
            category=InventoryCategory.PROCESSED
        )
        initial_stock = inventory.quantity_available  # 135 kg
        
        # Sell 100 kg of processed products
        kg_to_sell = Decimal('100.00')
        sale_price = self.SALE_PRICE_PER_KG
        
        # Remove from inventory (simulating sale)
        inventory.remove_stock(
            quantity=kg_to_sell,
            movement_type=StockMovementType.SALE,
            unit_price=sale_price,
            notes='Sold to local market',
            recorded_by=user,
        )
        
        # Verify inventory reduced
        inventory.refresh_from_db()
        assert inventory.quantity_available == initial_stock - kg_to_sell  # 35 kg remaining
        
        # Verify revenue tracked
        expected_revenue = kg_to_sell * sale_price
        assert inventory.total_sold == kg_to_sell
        assert inventory.total_revenue == expected_revenue
        
        # Sell remaining 35 kg
        inventory.remove_stock(
            quantity=Decimal('35.00'),
            movement_type=StockMovementType.SALE,
            unit_price=sale_price,
            notes='Final batch sold',
            recorded_by=user,
        )
        
        inventory.refresh_from_db()
        assert inventory.quantity_available == Decimal('0')  # All sold
        assert inventory.total_sold == Decimal('135.00')
        
        return flock, batch, inventory


# =============================================================================
# STEP 5: GOVERNMENT PROCUREMENT (331 REMAINING BIRDS)
# =============================================================================

class TestStep5GovernmentProcurement:
    """
    Test Step 5: Government procures remaining 331 birds.
    
    Starting count: 331 (after processing)
    Procured: 331 birds @ GHS 75 each (bulk rate)
    Expected count after: 0 (all birds accounted for)
    Revenue: 331 × 75 = GHS 24,825
    """
    
    BIRDS_TO_PROCURE = 331
    GOVT_PRICE_PER_BIRD = Decimal('75.00')  # Government bulk price
    
    def test_government_procurement_order(self, setup_test_environment):
        """Create government procurement order and assign farm."""
        from flock_management.models import Flock
        from procurement.models import (
            ProcurementOrder, OrderAssignment, DeliveryConfirmation, ProcurementInvoice
        )
        
        farm = setup_test_environment['farm']
        admin = setup_test_environment['admin']
        farmer = setup_test_environment['farmer']
        
        # Create flock with 331 birds (remaining after all other activities)
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-GOVT-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=500,
            current_count=331,  # Remaining after mortality, sales, processing
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        # Create government procurement order
        order = ProcurementOrder.objects.create(
            title='School Feeding Program - Q1 2026',
            description='Broilers for school feeding program in Greater Accra',
            production_type='Broilers',
            quantity_needed=self.BIRDS_TO_PROCURE,
            unit='birds',
            min_weight_per_bird_kg=Decimal('2.0'),
            quality_requirements='Live, healthy birds. Minimum 2kg average weight.',
            price_per_unit=self.GOVT_PRICE_PER_BIRD,
            total_budget=self.BIRDS_TO_PROCURE * self.GOVT_PRICE_PER_BIRD,
            delivery_location='Ministry of Food HQ, Accra',
            delivery_deadline=timezone.now().date() + timedelta(days=7),
            delivery_instructions='Deliver between 6am-10am. Contact officer on arrival.',
            auto_assign=False,
            preferred_region='Greater Accra',
            created_by=admin,
            assigned_procurement_officer=admin,
            status='published',
            priority='high',
        )
        
        # Verify order created correctly
        assert order.order_number is not None
        assert order.quantity_needed == self.BIRDS_TO_PROCURE
        assert order.total_budget == self.BIRDS_TO_PROCURE * self.GOVT_PRICE_PER_BIRD
        
        # Assign farm to fulfill order
        assignment = OrderAssignment.objects.create(
            order=order,
            farm=farm,
            quantity_assigned=self.BIRDS_TO_PROCURE,
            price_per_unit=self.GOVT_PRICE_PER_BIRD,
            status='accepted',
            accepted_at=timezone.now(),
            expected_ready_date=timezone.now().date() + timedelta(days=2),
            selection_reason='CAPACITY_MATCH',
        )
        
        # Verify assignment
        assert assignment.assignment_number is not None
        assert assignment.total_value == self.BIRDS_TO_PROCURE * self.GOVT_PRICE_PER_BIRD
        
        # Update order quantities
        order.quantity_assigned = self.BIRDS_TO_PROCURE
        order.status = 'assigned'
        order.save()
        
        return flock, order, assignment
    
    def test_procurement_delivery_and_payment(self, setup_test_environment):
        """Complete procurement delivery and verify final state."""
        from flock_management.models import Flock
        from procurement.models import (
            ProcurementOrder, OrderAssignment, DeliveryConfirmation, ProcurementInvoice
        )
        
        farm = setup_test_environment['farm']
        admin = setup_test_environment['admin']
        
        # Create flock with 331 birds
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-GOVT-DEL-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=500,
            current_count=331,
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        # Create order and assignment
        order = ProcurementOrder.objects.create(
            title='School Feeding Program Delivery Test',
            description='Test delivery',
            production_type='Broilers',
            quantity_needed=331,
            unit='birds',
            price_per_unit=Decimal('75.00'),
            total_budget=Decimal('24825.00'),
            delivery_location='Accra',
            delivery_deadline=timezone.now().date() + timedelta(days=7),
            created_by=admin,
            assigned_procurement_officer=admin,
            status='assigned',
        )
        
        assignment = OrderAssignment.objects.create(
            order=order,
            farm=farm,
            quantity_assigned=331,
            price_per_unit=Decimal('75.00'),
            status='accepted',
            accepted_at=timezone.now(),
        )
        
        # Record delivery
        delivery = DeliveryConfirmation.objects.create(
            assignment=assignment,
            quantity_delivered=331,
            delivery_date=timezone.now().date(),
            delivery_time=timezone.now().time(),
            received_by=admin,
            quality_passed=True,
            average_weight_per_bird=Decimal('2.3'),
            mortality_count=0,
            delivery_confirmed=True,
        )
        
        # Verify delivery
        assert delivery.delivery_number is not None
        assert delivery.quantity_delivered == 331
        
        # Update assignment status
        assignment.quantity_delivered = 331
        assignment.status = 'delivered'
        assignment.delivery_date = timezone.now().date()
        assignment.save()
        
        # Update flock - all birds delivered
        flock.current_count = 0
        flock.status = 'Sold'
        flock.save()
        
        # Verify final state
        flock.refresh_from_db()
        assert flock.current_count == 0
        assert flock.status == 'Sold'
        
        # Verify assignment completion
        assignment.refresh_from_db()
        assert assignment.is_fully_delivered == True
        assert assignment.fulfillment_percentage == 100
        
        # Update order status
        order.quantity_delivered = 331
        order.status = 'fully_delivered'
        order.save()
        
        # Create invoice for payment
        # Note: subtotal and total_amount are auto-calculated in save()
        invoice = ProcurementInvoice.objects.create(
            assignment=assignment,
            farm=farm,
            order=order,
            quantity_invoiced=331,
            unit_price=Decimal('75.00'),
            # Deduction fields (defaults to 0)
            quality_deduction=Decimal('0.00'),
            mortality_deduction=Decimal('0.00'),
            other_deductions=Decimal('0.00'),
            payment_status='pending',
            payment_method='mobile_money',
            due_date=timezone.now().date() + timedelta(days=30),  # Required field
        )
        
        # Verify invoice
        assert invoice.invoice_number is not None
        assert invoice.total_amount == Decimal('24825.00')
        
        return flock, order, assignment, delivery, invoice


# =============================================================================
# COMPREHENSIVE LIFECYCLE TEST
# =============================================================================

class TestCompleteLifecycle:
    """
    Complete end-to-end test of farmer lifecycle.
    
    Timeline:
    Day 0: Receive 500 day-old chicks
    Days 1-42: Growth period
      - 35 birds die (mortality)
      - Birds mature to market weight
    Day 42: Marketing activities
      - 78 birds sold live
      - 56 birds processed → products sold
      - 331 birds procured by government
    
    Final Verification:
    - All 500 birds accounted for
    - Correct revenue tracking
    - Accurate inventory at each step
    """
    
    def test_complete_farmer_journey(self, setup_test_environment):
        """
        Comprehensive test of complete farmer journey.
        
        This is the MAIN TEST that validates the entire scenario.
        """
        from flock_management.models import Flock, MortalityRecord
        from sales_revenue.models import BirdSale
        from sales_revenue.processing_models import (
            ProcessingBatch, ProcessingOutput, ProcessingBatchStatus,
            ProcessingType, ProductCategory, ProductGrade
        )
        from sales_revenue.inventory_models import (
            FarmInventory, InventoryCategory, StockMovementType, StockMovement
        )
        from procurement.models import ProcurementOrder, OrderAssignment
        
        farm = setup_test_environment['farm']
        farmer = setup_test_environment['farmer']
        admin = setup_test_environment['admin']
        customer = setup_test_environment['customer']
        
        # =====================================================================
        # STEP 1: CREATE FLOCK WITH 500 DAY-OLD CHICKS
        # =====================================================================
        print("\n" + "="*70)
        print("STEP 1: Creating flock with 500 day-old chicks")
        print("="*70)
        
        flock = Flock.objects.create(
            farm=farm,
            flock_number='LIFECYCLE-2026-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            supplier_name='Ghana National Hatchery',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=500,
            current_count=500,
            age_at_arrival_weeks=Decimal('0'),
            purchase_price_per_bird=Decimal('15.00'),
            status='Active',
            notes='Comprehensive lifecycle test batch',
        )
        
        print(f"  ✓ Flock created: {flock.flock_number}")
        print(f"  ✓ Initial count: {flock.initial_count}")
        print(f"  ✓ Current count: {flock.current_count}")
        print(f"  ✓ Total acquisition cost: GHS {flock.total_acquisition_cost}")
        
        assert flock.current_count == 500
        
        # =====================================================================
        # STEP 1B: TRACK OPERATIONAL EXPENSES
        # =====================================================================
        print("\n" + "="*70)
        print("STEP 1B: Tracking operational expenses over 6 weeks")
        print("="*70)
        
        from expenses.models import Expense, ExpenseCategory
        
        # Track 6 weeks of labor at GHS 50/day (7 days/week)
        for week in range(6):
            Expense.objects.create(
                farm=farm,
                flock=flock,
                category=ExpenseCategory.LABOR,
                description=f'Caretaker wage - Week {week + 1}',
                expense_date=flock.arrival_date + timedelta(days=week * 7),
                quantity=Decimal('7'),
                unit='days',
                unit_cost=Decimal('50.00'),
                payment_status='PAID',
                created_by=farmer,
            )
        
        # Track 6 weeks of utilities at GHS 140/week
        for week in range(6):
            Expense.objects.create(
                farm=farm,
                flock=flock,
                category=ExpenseCategory.UTILITIES,
                description=f'Electricity/water - Week {week + 1}',
                expense_date=flock.arrival_date + timedelta(days=week * 7),
                quantity=Decimal('1'),
                unit='week',
                unit_cost=Decimal('140.00'),
                payment_status='PAID',
            )
        
        # Track bedding costs
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Initial bedding - wood shavings',
            expense_date=flock.arrival_date,
            quantity=Decimal('16'),
            unit='bags',
            unit_cost=Decimal('25.00'),
        )
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Bedding top-up',
            expense_date=flock.arrival_date + timedelta(days=21),
            quantity=Decimal('4'),
            unit='bags',
            unit_cost=Decimal('25.00'),
        )
        
        # Track 4 transport trips for feed delivery
        for trip in range(4):
            Expense.objects.create(
                farm=farm,
                flock=flock,
                category=ExpenseCategory.TRANSPORT,
                description=f'Feed delivery trip {trip + 1}',
                expense_date=flock.arrival_date + timedelta(days=trip * 10),
                quantity=Decimal('1'),
                unit='trip',
                unit_cost=Decimal('75.00'),
            )
        
        # Track maintenance
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MAINTENANCE,
            description='Feeder repair',
            expense_date=flock.arrival_date + timedelta(days=14),
            quantity=Decimal('1'),
            unit='repair',
            unit_cost=Decimal('150.00'),
        )
        
        # Track overhead
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.OVERHEAD,
            description='Pro-rata insurance and admin',
            expense_date=flock.arrival_date,
            quantity=Decimal('1'),
            unit='month',
            unit_cost=Decimal('250.00'),
        )
        
        # Track miscellaneous
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MISCELLANEOUS,
            description='Cleaning supplies, disinfectant',
            expense_date=flock.arrival_date,
            quantity=Decimal('3'),
            unit='items',
            unit_cost=Decimal('25.00'),
        )
        
        flock.refresh_from_db()
        print(f"  ✓ Labor costs tracked:       GHS {flock.total_labor_cost}")
        print(f"  ✓ Utilities costs tracked:   GHS {flock.total_utilities_cost}")
        print(f"  ✓ Bedding costs tracked:     GHS {flock.total_bedding_cost}")
        print(f"  ✓ Transport costs tracked:   GHS {flock.total_transport_cost}")
        print(f"  ✓ Maintenance costs tracked: GHS {flock.total_maintenance_cost}")
        print(f"  ✓ Overhead costs tracked:    GHS {flock.total_overhead_cost}")
        print(f"  ✓ Miscellaneous tracked:     GHS {flock.total_miscellaneous_cost}")
        
        assert flock.total_labor_cost == Decimal('2100.00')
        assert flock.total_utilities_cost == Decimal('840.00')
        assert flock.total_bedding_cost == Decimal('500.00')
        assert flock.total_transport_cost == Decimal('300.00')
        
        # =====================================================================
        # STEP 2: RECORD MORTALITY (35 BIRDS)
        # =====================================================================
        print("\n" + "="*70)
        print("STEP 2: Recording mortality - 35 birds lost")
        print("="*70)
        
        mortality_events = [
            (10, 'Heat Stress', 'Week 1 - adjustment period'),
            (8, 'Disease', 'Week 2 - coccidiosis'),
            (7, 'Heat Stress', 'Week 3 - heat wave'),
            (5, 'Unknown', 'Week 4 - sporadic'),
            (3, 'Unknown', 'Week 5 - random'),
            (2, 'Cannibalism', 'Week 6 - pecking'),
        ]
        
        total_mortality = 0
        for count, cause, notes in mortality_events:
            MortalityRecord.objects.create(
                farm=farm,
                flock=flock,
                date_discovered=timezone.now().date() - timedelta(days=35 - total_mortality),
                number_of_birds=count,
                probable_cause=cause,
                notes=notes,
                reported_by=farmer,
            )
            flock.current_count -= count
            flock.save()
            total_mortality += count
            print(f"  - Recorded: {count} birds ({cause})")
        
        flock.refresh_from_db()
        print(f"\n  ✓ Total mortality: {total_mortality}")
        print(f"  ✓ Current count: {flock.current_count}")
        print(f"  ✓ Mortality rate: {flock.mortality_rate_percent:.2f}%")
        print(f"  ✓ Survival rate: {flock.survival_rate_percent:.2f}%")
        
        assert flock.current_count == 465
        assert total_mortality == 35
        
        # Track mortality loss as an expense
        from expenses.models import Expense, ExpenseCategory
        
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MORTALITY_LOSS,
            description='Mortality economic loss - 35 birds',
            expense_date=timezone.now().date() - timedelta(days=14),
            quantity=Decimal('35'),
            unit='birds',
            unit_cost=Decimal('35.00'),  # Acquisition + feed invested per bird
            payment_status='PAID',
        )
        
        flock.refresh_from_db()
        print(f"  ✓ Mortality loss recorded: GHS {flock.total_mortality_loss_value}")
        
        assert flock.total_mortality_loss_value == Decimal('1225.00')
        
        # =====================================================================
        # STEP 3: LIVE BIRD SALES (78 BIRDS)
        # =====================================================================
        print("\n" + "="*70)
        print("STEP 3: Live bird sales - 78 birds @ GHS 85 each")
        print("="*70)
        
        live_bird_sale = BirdSale.objects.create(
            farm=farm,
            customer=customer,
            flock=flock,
            sale_date=timezone.now().date(),
            bird_type='broiler',
            quantity=78,
            price_per_bird=Decimal('85.00'),
            status='completed',
            notes='Bulk sale to Accra Poultry Wholesalers',
        )
        
        # Deduct from flock
        flock.current_count -= 78
        flock.save()
        
        print(f"  ✓ Birds sold: 78")
        print(f"  ✓ Price per bird: GHS 85.00")
        print(f"  ✓ Total revenue: GHS {live_bird_sale.subtotal}")
        print(f"  ✓ Farmer payout: GHS {live_bird_sale.farmer_payout}")
        print(f"  ✓ Flock count after sale: {flock.current_count}")
        
        flock.refresh_from_db()
        assert flock.current_count == 387
        assert live_bird_sale.subtotal == Decimal('6630.00')
        
        # =====================================================================
        # STEP 4: PROCESSING (56 BIRDS)
        # =====================================================================
        print("\n" + "="*70)
        print("STEP 4: Processing - 56 birds (2 lost in processing)")
        print("="*70)
        
        processing_batch = ProcessingBatch.objects.create(
            farm=farm,
            source_flock=flock,
            birds_processed=56,
            average_bird_weight_kg=Decimal('2.5'),
            processing_date=timezone.now().date(),
            processing_type=ProcessingType.SLAUGHTER,
            labor_cost=Decimal('200.00'),
            processing_cost=Decimal('150.00'),
            packaging_cost=Decimal('100.00'),
            birds_lost_in_processing=2,
            loss_reason='Equipment malfunction - 2 birds damaged',
            status=ProcessingBatchStatus.IN_PROGRESS,
            processed_by=farmer,
        )
        
        # Deduct from flock
        processing_batch.deduct_from_flock()
        
        print(f"  ✓ Birds sent for processing: 56")
        print(f"  ✓ Birds lost in processing: 2")
        print(f"  ✓ Birds successfully processed: {processing_batch.birds_successfully_processed}")
        
        flock.refresh_from_db()
        print(f"  ✓ Flock count after processing: {flock.current_count}")
        
        assert flock.current_count == 331
        
        # Create processing output
        output_weight_kg = Decimal('135.00')  # 54 birds × 2.5kg
        output = ProcessingOutput.objects.create(
            processing_batch=processing_batch,
            product_category=ProductCategory.WHOLE_BIRD,
            grade=ProductGrade.A,
            quantity=54,
            weight_kg=output_weight_kg,
            allocated_cost=Decimal('75.00') * output_weight_kg,  # cost_per_kg derived from allocated_cost/weight
        )
        
        # Complete processing and add to inventory
        processing_batch.complete_and_update_inventory(user=farmer)
        
        print(f"  ✓ Output: {output_weight_kg} kg of whole dressed birds")
        print(f"  ✓ Processing batch completed and inventory updated")
        
        # Verify inventory
        processed_inventory = FarmInventory.objects.filter(
            farm=farm,
            category=InventoryCategory.PROCESSED
        ).first()
        
        assert processed_inventory is not None
        print(f"  ✓ Inventory created: {processed_inventory.quantity_available} kg")
        assert processed_inventory.quantity_available == output_weight_kg
        
        # Sell all processed products
        processed_inventory.remove_stock(
            quantity=output_weight_kg,
            movement_type=StockMovementType.SALE,
            unit_price=Decimal('95.00'),
            notes='All processed products sold',
            recorded_by=farmer,
        )
        
        processed_inventory.refresh_from_db()
        processed_revenue = output_weight_kg * Decimal('95.00')
        print(f"  ✓ All processed products sold")
        print(f"  ✓ Revenue from processed: GHS {processed_revenue}")
        print(f"  ✓ Processed inventory now: {processed_inventory.quantity_available} kg")
        
        assert processed_inventory.quantity_available == Decimal('0')
        
        # =====================================================================
        # STEP 5: GOVERNMENT PROCUREMENT (331 BIRDS)
        # =====================================================================
        print("\n" + "="*70)
        print("STEP 5: Government procurement - 331 remaining birds")
        print("="*70)
        
        # Create procurement order
        order = ProcurementOrder.objects.create(
            title='School Feeding Program Q1-2026',
            description='Broilers for Greater Accra school feeding',
            production_type='Broilers',
            quantity_needed=331,
            unit='birds',
            min_weight_per_bird_kg=Decimal('2.0'),
            quality_requirements='Live, healthy birds. Min 2kg average.',
            price_per_unit=Decimal('75.00'),
            total_budget=Decimal('24825.00'),
            delivery_location='Ministry of Food HQ, Accra',
            delivery_deadline=timezone.now().date() + timedelta(days=7),
            created_by=admin,
            assigned_procurement_officer=admin,
            status='assigned',
            priority='high',
        )
        
        print(f"  ✓ Procurement order created: {order.order_number}")
        print(f"  ✓ Quantity needed: {order.quantity_needed} birds")
        print(f"  ✓ Price per bird: GHS {order.price_per_unit}")
        print(f"  ✓ Total budget: GHS {order.total_budget}")
        
        # Assign farm
        assignment = OrderAssignment.objects.create(
            order=order,
            farm=farm,
            quantity_assigned=331,
            price_per_unit=Decimal('75.00'),
            status='accepted',
            accepted_at=timezone.now(),
            expected_ready_date=timezone.now().date() + timedelta(days=2),
            selection_reason='CAPACITY_MATCH',
        )
        
        print(f"  ✓ Farm assigned: {assignment.assignment_number}")
        print(f"  ✓ Assignment value: GHS {assignment.total_value}")
        
        # Complete delivery
        flock.current_count = 0
        flock.status = 'Sold'
        flock.save()
        
        assignment.quantity_delivered = 331
        assignment.status = 'delivered'
        assignment.delivery_date = timezone.now().date()
        assignment.save()
        
        order.quantity_delivered = 331
        order.status = 'fully_delivered'
        order.save()
        
        print(f"  ✓ Delivery completed: 331 birds")
        print(f"  ✓ Flock status: {flock.status}")
        print(f"  ✓ Flock current count: {flock.current_count}")
        
        # =====================================================================
        # FINAL VERIFICATION
        # =====================================================================
        print("\n" + "="*70)
        print("FINAL VERIFICATION - STOCK RECONCILIATION")
        print("="*70)
        
        flock.refresh_from_db()
        
        # Verify all birds accounted for
        initial_birds = 500
        mortality = 35
        live_sales = 78
        processing = 56
        procurement = 331
        
        total_accounted = mortality + live_sales + processing + procurement
        
        print(f"\n  Starting birds:        {initial_birds}")
        print(f"  (-) Mortality:         {mortality}")
        print(f"  (-) Live sales:        {live_sales}")
        print(f"  (-) Processing:        {processing}")
        print(f"  (-) Govt procurement:  {procurement}")
        print(f"  ---------------------------------")
        print(f"  Total accounted:       {total_accounted}")
        print(f"  Remaining in flock:    {flock.current_count}")
        
        assert total_accounted == initial_birds
        assert flock.current_count == 0
        
        # Calculate total revenue
        live_sale_revenue = Decimal('6630.00')  # 78 × 85
        processed_revenue = Decimal('12825.00')  # 135 kg × 95
        procurement_revenue = Decimal('24825.00')  # 331 × 75
        total_revenue = live_sale_revenue + processed_revenue + procurement_revenue
        
        # =====================================================================
        # COMPREHENSIVE COST BREAKDOWN (Now Using Tracked Expenses!)
        # =====================================================================
        # Costs are now tracked in the system via the expenses app
        
        # 1. ACQUISITION COSTS (from flock)
        acquisition_cost = flock.total_acquisition_cost  # GHS 7,500
        
        # 2. FEED COSTS (from feed_inventory module - estimated)
        # Broilers consume ~4.2 kg feed over 6 weeks (average for Cobb 500)
        feed_per_bird_kg = Decimal('4.2')
        avg_birds_fed = Decimal('475')
        feed_price_per_kg = Decimal('9.50')
        total_feed_cost = feed_per_bird_kg * avg_birds_fed * feed_price_per_kg
        
        # 3. VACCINATION & MEDICATION (estimated - would be from medication module)
        vaccination_cost = Decimal('3.50') * Decimal('500')
        
        # 4. OPERATIONAL COSTS (NOW TRACKED via expenses app!)
        labor_cost = flock.total_labor_cost
        utilities_cost = flock.total_utilities_cost
        bedding_cost = flock.total_bedding_cost
        transport_cost = flock.total_transport_cost
        maintenance_cost = flock.total_maintenance_cost
        overhead_cost = flock.total_overhead_cost
        miscellaneous_cost = flock.total_miscellaneous_cost
        mortality_loss = flock.total_mortality_loss_value
        
        # Processing costs (from processing batch)
        processing_costs = Decimal('450.00')
        
        # Calculate totals
        total_production_costs = acquisition_cost + total_feed_cost + vaccination_cost
        total_operational_costs = flock.total_operational_cost
        total_variable_costs = total_production_costs + total_operational_costs + processing_costs
        
        # Net profit (accounting for mortality loss as economic impact)
        net_profit = total_revenue - total_variable_costs
        profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else Decimal('0')
        
        print(f"\n  FINANCIAL SUMMARY (Using System-Tracked Expenses):")
        print(f"  ==================================================")
        print(f"\n  REVENUE:")
        print(f"  ---------------------------------")
        print(f"  Live bird sales:       GHS {live_sale_revenue:>10,.2f}")
        print(f"  Processed sales:       GHS {processed_revenue:>10,.2f}")
        print(f"  Govt procurement:      GHS {procurement_revenue:>10,.2f}")
        print(f"  ---------------------------------")
        print(f"  TOTAL REVENUE:         GHS {total_revenue:>10,.2f}")
        
        print(f"\n  PRODUCTION COSTS:")
        print(f"  ---------------------------------")
        print(f"  Day-old chicks:        GHS {acquisition_cost:>10,.2f}")
        print(f"  Feed (4.2kg × 475):    GHS {total_feed_cost:>10,.2f}")
        print(f"  Vaccination/Meds:      GHS {vaccination_cost:>10,.2f}")
        print(f"  Processing:            GHS {processing_costs:>10,.2f}")
        print(f"  ---------------------------------")
        print(f"  Subtotal Production:   GHS {(total_production_costs + processing_costs):>10,.2f}")
        
        print(f"\n  OPERATIONAL COSTS (Tracked in System):")
        print(f"  ---------------------------------")
        print(f"  Labor (6 weeks):       GHS {labor_cost:>10,.2f}")
        print(f"  Utilities:             GHS {utilities_cost:>10,.2f}")
        print(f"  Litter/Bedding:        GHS {bedding_cost:>10,.2f}")
        print(f"  Transport:             GHS {transport_cost:>10,.2f}")
        print(f"  Maintenance:           GHS {maintenance_cost:>10,.2f}")
        print(f"  Overhead:              GHS {overhead_cost:>10,.2f}")
        print(f"  Miscellaneous:         GHS {miscellaneous_cost:>10,.2f}")
        print(f"  Mortality Loss:        GHS {mortality_loss:>10,.2f}")
        print(f"  ---------------------------------")
        print(f"  Subtotal Operational:  GHS {total_operational_costs:>10,.2f}")
        
        print(f"\n  ---------------------------------")
        print(f"  TOTAL ALL COSTS:       GHS {total_variable_costs:>10,.2f}")
        
        print(f"\n  PROFITABILITY:")
        print(f"  ---------------------------------")
        print(f"  GROSS PROFIT:          GHS {(total_revenue - total_production_costs - processing_costs):>10,.2f}")
        print(f"  NET PROFIT:            GHS {net_profit:>10,.2f}")
        print(f"  Profit Margin:         {profit_margin:>10.1f}%")
        
        # Verify operational costs are tracked correctly
        assert labor_cost == Decimal('2100.00'), f"Labor cost mismatch: {labor_cost}"
        assert utilities_cost == Decimal('840.00'), f"Utilities cost mismatch: {utilities_cost}"
        assert bedding_cost == Decimal('500.00'), f"Bedding cost mismatch: {bedding_cost}"
        assert transport_cost == Decimal('300.00'), f"Transport cost mismatch: {transport_cost}"
        assert maintenance_cost == Decimal('150.00'), f"Maintenance cost mismatch: {maintenance_cost}"
        assert overhead_cost == Decimal('250.00'), f"Overhead cost mismatch: {overhead_cost}"
        assert miscellaneous_cost == Decimal('75.00'), f"Misc cost mismatch: {miscellaneous_cost}"
        assert mortality_loss == Decimal('1225.00'), f"Mortality loss mismatch: {mortality_loss}"
        
        # total_operational_cost excludes mortality loss (tracked separately)
        # 2100 + 840 + 500 + 300 + 150 + 250 + 75 = 4215
        expected_operational = Decimal('4215.00')
        assert total_operational_costs == expected_operational, \
            f"Total operational mismatch: {total_operational_costs} != {expected_operational}"
        
        print(f"\n  ✓ Feed accounts for {(total_feed_cost / total_variable_costs * 100):.1f}% of total costs")
        print(f"  ✓ Operational costs: {(total_operational_costs / total_variable_costs * 100):.1f}% of total costs")
        
        assert total_revenue == Decimal('44280.00')
        
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - FARMER LIFECYCLE COMPLETE")
        print("  - All birds accounted for (500 = 35 + 78 + 56 + 331)")
        print("  - All operational expenses tracked in system")
        print("  - Flock accumulated costs verified")
        print("  - Revenue and profit calculated accurately")
        print("="*70)


# =============================================================================
# STOCK MOVEMENT AUDIT TRAIL TEST
# =============================================================================

class TestStockMovementAudit:
    """
    Verify that all stock movements are properly recorded for audit.
    """
    
    def test_stock_movement_audit_trail(self, setup_test_environment):
        """Verify stock movement history is complete."""
        from sales_revenue.inventory_models import (
            FarmInventory, InventoryCategory, StockMovement, StockMovementType
        )
        from sales_revenue.processing_models import (
            ProcessingBatch, ProcessingOutput, ProcessingBatchStatus,
            ProcessingType, ProductCategory, ProductGrade
        )
        from flock_management.models import Flock
        
        farm = setup_test_environment['farm']
        user = setup_test_environment['farmer']
        
        # Create a flock and process some birds
        flock = Flock.objects.create(
            farm=farm,
            flock_number='AUDIT-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=100,
            current_count=100,
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        # Process 50 birds
        batch = ProcessingBatch.objects.create(
            farm=farm,
            source_flock=flock,
            birds_processed=50,
            average_bird_weight_kg=Decimal('2.5'),
            processing_date=timezone.now().date(),
            processing_type=ProcessingType.SLAUGHTER,
            status=ProcessingBatchStatus.IN_PROGRESS,
            processed_by=user,
        )
        batch.deduct_from_flock()
        
        output = ProcessingOutput.objects.create(
            processing_batch=batch,
            product_category=ProductCategory.WHOLE_BIRD,
            grade=ProductGrade.A,
            quantity=50,
            weight_kg=Decimal('125.00'),
            allocated_cost=Decimal('75.00') * Decimal('125.00'),  # cost_per_kg derived from allocated_cost/weight
        )
        
        batch.complete_and_update_inventory(user=user)
        
        # Get inventory
        inventory = FarmInventory.objects.get(
            farm=farm,
            category=InventoryCategory.PROCESSED
        )
        
        # Sell some products
        inventory.remove_stock(
            quantity=Decimal('50.00'),
            movement_type=StockMovementType.SALE,
            unit_price=Decimal('95.00'),
            notes='First sale',
            recorded_by=user,
        )
        
        # Record spoilage
        inventory.remove_stock(
            quantity=Decimal('5.00'),
            movement_type=StockMovementType.SPOILAGE,
            notes='Products expired',
            recorded_by=user,
        )
        
        # Sell rest
        inventory.remove_stock(
            quantity=Decimal('70.00'),
            movement_type=StockMovementType.SALE,
            unit_price=Decimal('95.00'),
            notes='Final sale',
            recorded_by=user,
        )
        
        # Verify audit trail
        movements = StockMovement.objects.filter(inventory=inventory).order_by('created_at')
        
        print("\n  STOCK MOVEMENT AUDIT TRAIL:")
        print("  " + "-"*60)
        
        for m in movements:
            direction = "IN" if m.quantity > 0 else "OUT"
            print(f"  {m.created_at.strftime('%Y-%m-%d %H:%M')} | {direction:3} | "
                  f"{abs(m.quantity):>8.2f} kg | {m.movement_type:15} | Balance: {m.balance_after:>8.2f}")
        
        print("  " + "-"*60)
        
        # Verify movement types
        movement_types = list(movements.values_list('movement_type', flat=True))
        
        assert StockMovementType.PROCESSING in movement_types  # From processing
        assert StockMovementType.SALE in movement_types  # Sales
        assert StockMovementType.SPOILAGE in movement_types  # Spoilage
        
        # Verify final balance
        inventory.refresh_from_db()
        assert inventory.quantity_available == Decimal('0')
        
        # Verify totals
        assert inventory.total_added == Decimal('125.00')
        assert inventory.total_sold == Decimal('120.00')  # 50 + 70
        assert inventory.total_lost == Decimal('5.00')  # Spoilage
        
        print(f"\n  ✓ Total added:    {inventory.total_added} kg")
        print(f"  ✓ Total sold:     {inventory.total_sold} kg")
        print(f"  ✓ Total lost:     {inventory.total_lost} kg")
        print(f"  ✓ Final balance:  {inventory.quantity_available} kg")


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_cannot_process_more_than_available(self, setup_test_environment):
        """Verify processing cannot exceed flock count."""
        from flock_management.models import Flock
        from sales_revenue.processing_models import ProcessingBatch, ProcessingBatchStatus, ProcessingType
        from django.core.exceptions import ValidationError
        
        farm = setup_test_environment['farm']
        user = setup_test_environment['farmer']
        
        flock = Flock.objects.create(
            farm=farm,
            flock_number='EDGE-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date() - timedelta(days=42),
            initial_count=100,
            current_count=50,  # Only 50 birds left
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        # Try to process more than available
        batch = ProcessingBatch.objects.create(
            farm=farm,
            source_flock=flock,
            birds_processed=100,  # More than available
            processing_date=timezone.now().date(),
            processing_type=ProcessingType.SLAUGHTER,
            status=ProcessingBatchStatus.PENDING,
            processed_by=user,
        )
        
        # Should raise error when deducting
        with pytest.raises(ValidationError):
            batch.deduct_from_flock()
    
    def test_cannot_sell_more_than_inventory(self, setup_test_environment):
        """Verify sales cannot exceed inventory."""
        from sales_revenue.inventory_models import (
            FarmInventory, InventoryCategory, StockMovementType
        )
        
        farm = setup_test_environment['farm']
        user = setup_test_environment['farmer']
        
        # Create inventory with limited stock
        inventory = FarmInventory.objects.create(
            farm=farm,
            category=InventoryCategory.PROCESSED,
            product_name='Test Product',
            quantity_available=Decimal('50.00'),
            unit='kg',
        )
        
        # Try to remove more than available
        with pytest.raises(ValueError, match="Insufficient stock"):
            inventory.remove_stock(
                quantity=Decimal('100.00'),
                movement_type=StockMovementType.SALE,
                notes='Should fail',
                recorded_by=user,
            )
    
    def test_flock_count_cannot_go_negative(self, setup_test_environment):
        """Verify flock count stays non-negative."""
        from flock_management.models import Flock
        from django.core.exceptions import ValidationError
        
        farm = setup_test_environment['farm']
        
        flock = Flock(
            farm=farm,
            flock_number='EDGE-NEG-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date(),
            initial_count=100,
            current_count=-10,  # Invalid: negative
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        with pytest.raises(ValidationError):
            flock.full_clean()
    
    def test_current_count_cannot_exceed_initial(self, setup_test_environment):
        """Verify current count cannot exceed initial count."""
        from flock_management.models import Flock
        from django.core.exceptions import ValidationError
        
        farm = setup_test_environment['farm']
        
        flock = Flock(
            farm=farm,
            flock_number='EDGE-EXCEED-001',
            flock_type='Broilers',
            breed='Cobb 500',
            source='YEA Program',
            arrival_date=timezone.now().date(),
            initial_count=100,
            current_count=150,  # Invalid: exceeds initial
            age_at_arrival_weeks=Decimal('0'),
            status='Active',
        )
        
        with pytest.raises(ValidationError):
            flock.full_clean()
