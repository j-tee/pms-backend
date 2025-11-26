"""
Comprehensive Test Suite for Feed Inventory Module

Tests all feed inventory models with focus on:
- Data validation rules
- Auto-calculated fields
- Cross-module integrations
- Business logic constraints
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from farms.models import Farm
from flock_management.models import Flock, DailyProduction
from feed_inventory.models import (
    FeedType, FeedSupplier, FeedPurchase, FeedInventory, FeedConsumption
)
from accounts.models import User


class TestFeedInventoryModule:
    """Test suite for Feed Inventory module."""
    
    def __init__(self):
        self.test_results = []
        self.setup_test_data()
    
    def setup_test_data(self):
        """Create test data for all tests."""
        print("Setting up test data...")
        
        # Create test user
        self.user = User.objects.filter(email='test@example.com').first()
        if not self.user:
            self.user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123',
                first_name='Test',
                last_name='User'
            )
        
        # Create test farm
        self.farm = Farm.objects.filter(farm_name='Test Farm Feed').first()
        if not self.farm:
            self.farm = Farm.objects.create(
                user=self.user,
                farm_name='Test Farm Feed',
                first_name='Test',
                last_name='Farmer',
                date_of_birth=date(1990, 1, 1),
                gender='Male',
                ghana_card_number='GHA-123456789-0',
                marital_status='Single',
                primary_phone='+233201234567',
                preferred_contact_method='Phone Call',
                residential_address='Test Address',
                nok_full_name='Test Kin',
                nok_relationship='Sibling',
                nok_phone='+233201111111',
                nok_residential_address='Kin Address',
                education_level='Secondary',
                literacy_level='Can Read & Write',
                ownership_type='Sole Proprietorship',
                tin='1234567890',
                years_in_poultry=Decimal('2.0'),
                number_of_poultry_houses=1,
                total_bird_capacity=1000,
                housing_type='Deep Litter',
                total_infrastructure_value_ghs=Decimal('10000.00'),
                primary_production_type='Eggs',
                application_status='APPROVED',
                application_date=date.today()
            )
        
        # Create test flock
        self.flock = Flock.objects.filter(flock_number='TEST-FEED-001').first()
        if not self.flock:
            self.flock = Flock.objects.create(
                farm=self.farm,
                flock_number='TEST-FEED-001',
                flock_type='Layers',
                breed='Isa Brown',
                source='YEA Program',
                arrival_date=date.today() - timedelta(days=30),
                initial_count=1000,
                current_count=950,
                age_at_arrival_weeks=18
            )
        
        print("✓ Test data setup complete\n")
    
    def run_test(self, test_name, test_func):
        """Run a single test and record result."""
        try:
            test_func()
            self.test_results.append((test_name, 'PASS', None))
            print(f"✓ {test_name}")
        except AssertionError as e:
            self.test_results.append((test_name, 'FAIL', str(e)))
            print(f"✗ {test_name}: {e}")
        except Exception as e:
            self.test_results.append((test_name, 'ERROR', str(e)))
            print(f"✗ {test_name}: ERROR - {e}")
    
    # =========================================================================
    # FEED TYPE TESTS
    # =========================================================================
    
    def test_feed_type_creation(self):
        """Test basic FeedType creation."""
        feed = FeedType.objects.create(
            name='Test Layer Mash 16%',
            category='LAYER',
            form='MASH',
            manufacturer='Test Feeds Ltd',
            protein_content=Decimal('16.00'),
            calcium_content=Decimal('3.50')
        )
        assert feed.name == 'Test Layer Mash 16%'
        assert feed.is_active is True
        feed.delete()
    
    def test_feed_type_age_validation(self):
        """Test age range validation in FeedType."""
        feed = FeedType(
            name='Invalid Age Feed',
            category='STARTER',
            form='MASH',
            protein_content=Decimal('20.00'),
            recommended_age_weeks_min=10,
            recommended_age_weeks_max=5  # Invalid: max < min
        )
        try:
            feed.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'recommended_age_weeks_max' in e.message_dict
    
    def test_feed_type_layer_calcium(self):
        """Test layer feed calcium validation."""
        feed = FeedType(
            name='Low Calcium Layer Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00'),
            calcium_content=Decimal('2.00')  # Too low for layers
        )
        try:
            feed.full_clean()
            assert False, "Should have raised ValidationError for low calcium"
        except ValidationError as e:
            assert 'calcium_content' in e.message_dict
    
    # =========================================================================
    # FEED SUPPLIER TESTS
    # =========================================================================
    
    def test_feed_supplier_creation(self):
        """Test FeedSupplier creation."""
        supplier = FeedSupplier.objects.create(
            name='Test Feed Supplier',
            phone='0501234567',
            address='Test Address, Accra',
            payment_terms='NET30'
        )
        assert supplier.is_active is True
        assert supplier.total_purchases == Decimal('0.00')
        supplier.delete()
    
    # =========================================================================
    # FEED PURCHASE TESTS
    # =========================================================================
    
    def test_feed_purchase_total_calculation(self):
        """Test automatic total_cost calculation."""
        feed_type = FeedType.objects.create(
            name='Purchase Test Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        supplier = FeedSupplier.objects.create(
            name='Purchase Test Supplier',
            phone='0501234567',
            address='Test Address'
        )
        
        purchase = FeedPurchase.objects.create(
            farm=self.farm,
            supplier=supplier,
            feed_type=feed_type,
            purchase_date=date.today(),
            quantity_kg=Decimal('1000.00'),
            unit_price=Decimal('2.50'),
            total_cost=Decimal('0.00')  # Should be auto-calculated
        )
        
        assert purchase.total_cost == Decimal('2500.00')
        
        purchase.delete()
        supplier.delete()
        feed_type.delete()
    
    def test_feed_purchase_payment_status_validation(self):
        """Test payment status consistency validation."""
        feed_type = FeedType.objects.create(
            name='Payment Test Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        supplier = FeedSupplier.objects.create(
            name='Payment Test Supplier',
            phone='0501234567',
            address='Test Address'
        )
        
        purchase = FeedPurchase(
            farm=self.farm,
            supplier=supplier,
            feed_type=feed_type,
            purchase_date=date.today(),
            quantity_kg=Decimal('1000.00'),
            unit_price=Decimal('2.50'),
            total_cost=Decimal('2500.00'),
            amount_paid=Decimal('2500.00'),
            payment_status='PENDING'  # Should be PAID
        )
        
        try:
            purchase.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'payment_status' in e.message_dict
        
        supplier.delete()
        feed_type.delete()
    
    def test_feed_purchase_overpayment_validation(self):
        """Test that amount_paid cannot exceed total_cost."""
        feed_type = FeedType.objects.create(
            name='Overpayment Test Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        supplier = FeedSupplier.objects.create(
            name='Overpayment Test Supplier',
            phone='0501234567',
            address='Test Address'
        )
        
        purchase = FeedPurchase(
            farm=self.farm,
            supplier=supplier,
            feed_type=feed_type,
            purchase_date=date.today(),
            quantity_kg=Decimal('1000.00'),
            unit_price=Decimal('2.50'),
            total_cost=Decimal('2500.00'),
            amount_paid=Decimal('3000.00')  # Overpayment
        )
        
        try:
            purchase.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'amount_paid' in e.message_dict
        
        supplier.delete()
        feed_type.delete()
    
    # =========================================================================
    # FEED INVENTORY TESTS
    # =========================================================================
    
    def test_feed_inventory_creation(self):
        """Test FeedInventory creation and auto-calculations."""
        feed_type = FeedType.objects.create(
            name='Inventory Test Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        inventory = FeedInventory.objects.create(
            farm=self.farm,
            feed_type=feed_type,
            current_stock_kg=Decimal('500.00'),
            min_stock_level=Decimal('100.00'),
            max_stock_level=Decimal('1000.00'),
            average_cost_per_kg=Decimal('2.50')
        )
        
        # Test auto-calculated total_value
        assert inventory.total_value == Decimal('1250.00')
        
        # Test low_stock_alert (should be False as stock > min)
        assert inventory.low_stock_alert is False
        
        inventory.delete()
        feed_type.delete()
    
    def test_feed_inventory_low_stock_alert(self):
        """Test low stock alert auto-setting."""
        feed_type = FeedType.objects.create(
            name='Low Stock Test Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        inventory = FeedInventory.objects.create(
            farm=self.farm,
            feed_type=feed_type,
            current_stock_kg=Decimal('50.00'),  # Below min
            min_stock_level=Decimal('100.00'),
            max_stock_level=Decimal('1000.00'),
            average_cost_per_kg=Decimal('2.50')
        )
        
        assert inventory.low_stock_alert is True
        
        inventory.delete()
        feed_type.delete()
    
    def test_feed_inventory_stock_validation(self):
        """Test stock level validations."""
        feed_type = FeedType.objects.create(
            name='Stock Validation Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        # Test: min > max
        inventory = FeedInventory(
            farm=self.farm,
            feed_type=feed_type,
            current_stock_kg=Decimal('500.00'),
            min_stock_level=Decimal('1000.00'),  # Invalid
            max_stock_level=Decimal('500.00')
        )
        
        try:
            inventory.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'min_stock_level' in e.message_dict
        
        feed_type.delete()
    
    def test_feed_inventory_update_stock_method(self):
        """Test the update_stock helper method."""
        feed_type = FeedType.objects.create(
            name='Update Stock Test Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        inventory = FeedInventory.objects.create(
            farm=self.farm,
            feed_type=feed_type,
            current_stock_kg=Decimal('500.00'),
            min_stock_level=Decimal('100.00'),
            max_stock_level=Decimal('1000.00'),
            average_cost_per_kg=Decimal('2.50')
        )
        
        # Test purchase (positive change)
        inventory.update_stock(Decimal('300.00'), Decimal('2.60'))
        inventory.refresh_from_db()
        
        assert inventory.current_stock_kg == Decimal('800.00')
        assert inventory.average_cost_per_kg == Decimal('2.60')
        assert inventory.last_purchase_date == date.today()
        
        # Test consumption (negative change)
        inventory.update_stock(Decimal('-100.00'))
        inventory.refresh_from_db()
        
        assert inventory.current_stock_kg == Decimal('700.00')
        assert inventory.last_consumption_date == date.today()
        
        inventory.delete()
        feed_type.delete()
    
    # =========================================================================
    # FEED CONSUMPTION TESTS
    # =========================================================================
    
    def test_feed_consumption_creation(self):
        """Test FeedConsumption creation with auto-calculations."""
        feed_type = FeedType.objects.create(
            name='Consumption Test Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        # Create DailyProduction record
        daily_prod = DailyProduction.objects.create(
            farm=self.farm,
            flock=self.flock,
            production_date=date.today(),
            feed_consumed_kg=Decimal('150.00')
        )
        
        consumption = FeedConsumption.objects.create(
            daily_production=daily_prod,
            farm=self.farm,
            flock=self.flock,
            feed_type=feed_type,
            date=date.today(),
            quantity_consumed_kg=Decimal('150.00'),
            cost_per_kg=Decimal('2.50'),
            birds_count_at_consumption=950
        )
        
        # Test auto-calculated fields
        assert consumption.total_cost == Decimal('375.00')
        expected_grams = (Decimal('150.00') / 950) * 1000
        assert abs(consumption.consumption_per_bird_grams - expected_grams) < Decimal('0.01')
        
        consumption.delete()
        daily_prod.delete()
        feed_type.delete()
    
    def test_feed_consumption_farm_consistency(self):
        """Test farm consistency validation."""
        # Create another farm
        other_farm = Farm.objects.create(
            name='Other Farm',
            registration_number='OF001',
            primary_contact_name='Other Farmer',
            primary_contact_phone='0209876543',
            registration_date=date.today()
        )
        
        feed_type = FeedType.objects.create(
            name='Consistency Test Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        daily_prod = DailyProduction.objects.create(
            farm=self.farm,
            flock=self.flock,
            production_date=date.today()
        )
        
        consumption = FeedConsumption(
            daily_production=daily_prod,
            farm=other_farm,  # Different farm - should fail
            flock=self.flock,
            feed_type=feed_type,
            date=date.today(),
            quantity_consumed_kg=Decimal('100.00'),
            cost_per_kg=Decimal('2.50'),
            birds_count_at_consumption=950
        )
        
        try:
            consumption.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'farm' in e.message_dict
        
        daily_prod.delete()
        feed_type.delete()
        other_farm.delete()
    
    def test_feed_consumption_excessive_amount(self):
        """Test validation for excessive consumption per bird."""
        feed_type = FeedType.objects.create(
            name='Excessive Consumption Feed',
            category='LAYER',
            form='MASH',
            protein_content=Decimal('16.00')
        )
        
        daily_prod = DailyProduction.objects.create(
            farm=self.farm,
            flock=self.flock,
            production_date=date.today()
        )
        
        consumption = FeedConsumption(
            daily_production=daily_prod,
            farm=self.farm,
            flock=self.flock,
            feed_type=feed_type,
            date=date.today(),
            quantity_consumed_kg=Decimal('400.00'),  # 400kg for 950 birds = 421g/bird (too much)
            cost_per_kg=Decimal('2.50'),
            birds_count_at_consumption=950
        )
        
        try:
            consumption.full_clean()
            assert False, "Should have raised ValidationError for excessive consumption"
        except ValidationError as e:
            assert 'quantity_consumed_kg' in e.message_dict
        
        daily_prod.delete()
        feed_type.delete()
    
    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    
    def run_all_tests(self):
        """Execute all test cases."""
        print("\n" + "="*80)
        print("  FEED INVENTORY MODULE TEST SUITE")
        print("="*80 + "\n")
        
        print("FeedType Tests:")
        print("-" * 80)
        self.run_test("FeedType: Basic Creation", self.test_feed_type_creation)
        self.run_test("FeedType: Age Range Validation", self.test_feed_type_age_validation)
        self.run_test("FeedType: Layer Calcium Validation", self.test_feed_type_layer_calcium)
        
        print("\nFeedSupplier Tests:")
        print("-" * 80)
        self.run_test("FeedSupplier: Basic Creation", self.test_feed_supplier_creation)
        
        print("\nFeedPurchase Tests:")
        print("-" * 80)
        self.run_test("FeedPurchase: Total Cost Calculation", self.test_feed_purchase_total_calculation)
        self.run_test("FeedPurchase: Payment Status Validation", self.test_feed_purchase_payment_status_validation)
        self.run_test("FeedPurchase: Overpayment Validation", self.test_feed_purchase_overpayment_validation)
        
        print("\nFeedInventory Tests:")
        print("-" * 80)
        self.run_test("FeedInventory: Basic Creation", self.test_feed_inventory_creation)
        self.run_test("FeedInventory: Low Stock Alert", self.test_feed_inventory_low_stock_alert)
        self.run_test("FeedInventory: Stock Level Validation", self.test_feed_inventory_stock_validation)
        self.run_test("FeedInventory: Update Stock Method", self.test_feed_inventory_update_stock_method)
        
        print("\nFeedConsumption Tests:")
        print("-" * 80)
        self.run_test("FeedConsumption: Basic Creation", self.test_feed_consumption_creation)
        self.run_test("FeedConsumption: Farm Consistency", self.test_feed_consumption_farm_consistency)
        self.run_test("FeedConsumption: Excessive Amount", self.test_feed_consumption_excessive_amount)
        
        # Print Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test execution summary."""
        print("\n" + "="*80)
        print("  TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for _, status, _ in self.test_results if status == 'PASS')
        failed = sum(1 for _, status, _ in self.test_results if status == 'FAIL')
        errors = sum(1 for _, status, _ in self.test_results if status == 'ERROR')
        total = len(self.test_results)
        
        print(f"\nTotal Tests: {total}")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"⚠ Errors: {errors}")
        print(f"\nSuccess Rate: {(passed/total*100):.1f}%")
        
        if failed > 0 or errors > 0:
            print("\nFailed/Error Tests:")
            for name, status, msg in self.test_results:
                if status in ['FAIL', 'ERROR']:
                    print(f"  {status}: {name}")
                    if msg:
                        print(f"    → {msg}")
        
        print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    tester = TestFeedInventoryModule()
    tester.run_all_tests()
