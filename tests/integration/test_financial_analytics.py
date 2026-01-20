"""
Integration Tests for Financial Analytics Service

Tests the updated financial analytics that includes ALL expense categories:
- Feed, Medication, Vaccination, Vet Visits
- Labor, Utilities, Bedding, Transport
- Maintenance, Overhead, Mortality Loss, Miscellaneous

These tests verify the fix that ensures Total Expenses accurately reflects
all costs, not just feed/medication/vaccination.

Author: AI-assisted development
Date: January 2026
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from accounts.models import User
from farms.models import Farm
from flock_management.models import Flock
from feed_inventory.models import FeedPurchase, FeedType
from medication_management.models import (
    MedicationRecord, VaccinationRecord, VetVisit, MedicationType
)
from expenses.models import Expense, ExpenseCategory
from dashboards.services.farmer_analytics import FarmerAnalyticsService


@pytest.fixture
def farmer_user(db):
    """Create a farmer user for testing."""
    return User.objects.create_user(
        username='test_financial_farmer',
        email='financial_farmer@test.com',
        password='testpass123',
        phone='+233240000099',
        role='FARMER',
        is_active=True
    )


@pytest.fixture
def farm(db, farmer_user):
    """Create a farm for testing."""
    import uuid
    from decimal import Decimal
    unique_id = str(uuid.uuid4().hex)[:6]
    return Farm.objects.create(
        user=farmer_user,
        # Section 1.1: Basic Info
        first_name='Financial',
        last_name='Test',
        date_of_birth='1985-06-15',
        gender='Male',
        ghana_card_number=f'GHA-{unique_id.upper()}-FIN',
        # Section 1.2: Contact
        primary_phone=f'+23324555{unique_id[:4]}',
        residential_address='Financial Test Farm, Accra',
        primary_constituency='Ayawaso West',
        # Section 1.3: Next of Kin
        nok_full_name='Test NOK',
        nok_relationship='Spouse',
        nok_phone='+233241000000',
        # Section 1.4: Education
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=5,
        # Section 2: Farm Info
        farm_name='Financial Test Poultry',
        ownership_type='Sole Proprietorship',
        tin=f'F{unique_id[:10].upper()}',
        # Section 4: Infrastructure
        number_of_poultry_houses=2,
        total_bird_capacity=5000,
        current_bird_count=2000,
        housing_type='Deep Litter',
        total_infrastructure_value_ghs=Decimal('50000.00'),
        # Section 5: Production
        primary_production_type='Layers',
        layer_breed='Isa Brown',
        planned_production_start_date='2025-01-01',
        # Section 7: Financial
        initial_investment_amount=Decimal('100000.00'),
        funding_source=['Personal Savings'],
        monthly_operating_budget=Decimal('15000.00'),
        expected_monthly_revenue=Decimal('25000.00'),
        # Status
        application_status='Approved',
        farm_status='Active',
    )


@pytest.fixture
def flock(db, farm):
    """Create a flock for testing."""
    return Flock.objects.create(
        farm=farm,
        flock_number='FLOCK-FIN-001',
        flock_type='Layers',
        breed='Isa Brown',
        source='YEA Program',
        initial_count=2000,
        current_count=1950,
        arrival_date=date.today() - timedelta(days=60),
        status='Active',
        is_currently_producing=True
    )


@pytest.fixture
def feed_type(db):
    """Create a feed type for testing."""
    return FeedType.objects.create(
        name='Layer Mash Test',
        category='LAYER',
        form='MASH',
        protein_content=Decimal('16.0')
    )


@pytest.fixture
def medication_type(db):
    """Create an antibiotic medication type for testing."""
    return MedicationType.objects.create(
        name='Test Antibiotic',
        category='ANTIBIOTIC',
        administration_route='ORAL',
        dosage='1ml per liter water',
        indication='Respiratory infections'
    )


@pytest.fixture
def vaccine_type(db):
    """Create a vaccine medication type for testing."""
    return MedicationType.objects.create(
        name='Newcastle Disease Vaccine',
        category='VACCINE',
        administration_route='EYE_DROP',
        dosage='1 drop per bird',
        indication='Newcastle Disease prevention'
    )


@pytest.fixture
def analytics_service(farmer_user, farm):
    """Create analytics service instance. Depends on farm to ensure it's created first."""
    return FarmerAnalyticsService(farmer_user)


@pytest.fixture
def customer(db, farm):
    """Create a customer for marketplace orders."""
    from sales_revenue.models import Customer
    return Customer.objects.create(
        farm=farm,
        customer_type='individual',
        first_name='Test',
        last_name='Customer',
        phone_number='+233240111222',
        mobile_money_number='+233240111222',
        mobile_money_provider='mtn',
        mobile_money_account_name='Test Customer'
    )


class TestFinancialAnalyticsExpenseBreakdown:
    """Test that financial analytics includes all expense categories."""
    
    def test_expense_breakdown_has_all_fields(self, analytics_service, farm, flock):
        """Test that expenses_breakdown returns all 12 expected fields."""
        result = analytics_service.get_financial_analytics(days=30)
        
        assert 'expenses_breakdown' in result
        breakdown = result['expenses_breakdown']
        
        # Check all expected fields exist
        expected_fields = [
            'feed', 'medication', 'vaccination', 'vet_visits',
            'labor', 'utilities', 'bedding', 'transport',
            'maintenance', 'overhead', 'mortality_loss', 'miscellaneous'
        ]
        
        for field in expected_fields:
            assert field in breakdown, f"Missing field: {field}"
            # All values should be numeric (float)
            assert isinstance(breakdown[field], (int, float)), f"{field} should be numeric"
    
    def test_feed_expense_from_feed_purchase(self, analytics_service, farm, flock, feed_type):
        """Test that feed costs come from FeedPurchase model."""
        # Create a feed purchase
        FeedPurchase.objects.create(
            farm=farm,
            feed_type=feed_type,
            quantity_bags=10,
            bag_weight_kg=Decimal('50.00'),
            quantity_kg=Decimal('500.00'),
            unit_cost_ghs=Decimal('175.00'),
            unit_price=Decimal('3.50'),
            total_cost=Decimal('1750.00'),
            purchase_date=date.today() - timedelta(days=5),
            supplier='Test Feed Supplier'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['feed'] == 1750.00
    
    def test_medication_expense_from_medication_records(self, analytics_service, farm, flock, medication_type):
        """Test that medication costs come from MedicationRecord model."""
        # Create medication record using the medication_type fixture
        MedicationRecord.objects.create(
            flock=flock,
            farm=farm,
            medication_type=medication_type,
            administered_date=date.today() - timedelta(days=3),
            reason='TREATMENT',
            dosage_given='100ml',
            birds_treated=100,
            treatment_days=3,
            end_date=date.today(),
            quantity_used=Decimal('100.00'),
            unit_cost=Decimal('2.50'),
            total_cost=Decimal('250.00'),
            administered_by='Test Vet'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['medication'] == 250.00
    
    def test_vaccination_expense_from_vaccination_records(self, analytics_service, farm, flock, vaccine_type):
        """Test that vaccination costs come from VaccinationRecord model."""
        # Create vaccination record using the vaccine_type fixture
        VaccinationRecord.objects.create(
            flock=flock,
            farm=farm,
            medication_type=vaccine_type,
            vaccination_date=date.today() - timedelta(days=7),
            birds_vaccinated=1950,
            flock_age_weeks=8,
            dosage_per_bird='1 drop',
            administration_route='Eye drop',
            batch_number='VAC-2026-001',
            expiry_date=date.today() + timedelta(days=180),
            quantity_used=Decimal('1950.00'),
            unit_cost=Decimal('0.30'),
            total_cost=Decimal('585.00'),
            administered_by='Test Vet',
            vet_license_number='VET-001'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['vaccination'] == 585.00
    
    def test_vet_visit_expense_from_vet_visits(self, analytics_service, farm, flock):
        """Test that vet visit costs come from VetVisit model (status=COMPLETED)."""
        # Create completed vet visit
        VetVisit.objects.create(
            farm=farm,
            flock=flock,
            visit_date=date.today() - timedelta(days=10),
            veterinarian_name='Dr. Test Vet',
            vet_license_number='VET-001',
            visit_type='ROUTINE',
            purpose='Routine health check',
            visit_fee=Decimal('150.00'),
            status='COMPLETED',
            findings='Flock in good health',
            recommendations='Continue current feeding regime'
        )
        
        # Create pending vet visit (should NOT be counted)
        VetVisit.objects.create(
            farm=farm,
            flock=flock,
            visit_date=date.today() - timedelta(days=2),
            veterinarian_name='Dr. Another Vet',
            vet_license_number='VET-002',
            visit_type='EMERGENCY',
            purpose='Emergency consultation',
            visit_fee=Decimal('300.00'),
            status='SCHEDULED',  # Not completed
            findings='',
            recommendations=''
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        # Only completed visit should be counted
        assert breakdown['vet_visits'] == 150.00
    
    def test_labor_expense_from_expense_model(self, analytics_service, farm, flock):
        """Test that labor costs come from Expense model with category=LABOR."""
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.LABOR,
            description='Weekly caretaker wage',
            expense_date=date.today() - timedelta(days=7),
            quantity=Decimal('1.00'),
            unit='week',
            unit_cost=Decimal('350.00'),
            total_amount=Decimal('350.00'),
            payment_status='PAID'
        )
        
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Vaccination labor',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('4.00'),
            unit='hours',
            unit_cost=Decimal('25.00'),
            total_amount=Decimal('100.00'),
            payment_status='PAID'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['labor'] == 450.00
    
    def test_utilities_expense_from_expense_model(self, analytics_service, farm):
        """Test that utilities costs come from Expense model with category=UTILITIES."""
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.UTILITIES,
            description='Electricity bill',
            expense_date=date.today() - timedelta(days=15),
            quantity=Decimal('1.00'),
            unit='bill',
            unit_cost=Decimal('450.00'),
            total_amount=Decimal('450.00'),
            payment_status='PAID'
        )
        
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.UTILITIES,
            description='Water bill',
            expense_date=date.today() - timedelta(days=15),
            quantity=Decimal('1.00'),
            unit='bill',
            unit_cost=Decimal('120.00'),
            total_amount=Decimal('120.00'),
            payment_status='PAID'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['utilities'] == 570.00
    
    def test_bedding_expense_from_expense_model(self, analytics_service, farm, flock):
        """Test that bedding costs come from Expense model with category=BEDDING."""
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Wood shavings',
            expense_date=date.today() - timedelta(days=20),
            quantity=Decimal('10.00'),
            unit='bags',
            unit_cost=Decimal('25.00'),
            total_amount=Decimal('250.00'),
            payment_status='PAID'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['bedding'] == 250.00
    
    def test_transport_expense_from_expense_model(self, analytics_service, farm):
        """Test that transport costs come from Expense model with category=TRANSPORT."""
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.TRANSPORT,
            description='Feed delivery',
            expense_date=date.today() - timedelta(days=10),
            quantity=Decimal('1.00'),
            unit='trip',
            unit_cost=Decimal('80.00'),
            total_amount=Decimal('80.00'),
            payment_status='PAID'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['transport'] == 80.00
    
    def test_maintenance_expense_from_expense_model(self, analytics_service, farm):
        """Test that maintenance costs come from Expense model with category=MAINTENANCE."""
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.MAINTENANCE,
            description='Feeder repair',
            expense_date=date.today() - timedelta(days=8),
            quantity=Decimal('1.00'),
            unit='job',
            unit_cost=Decimal('120.00'),
            total_amount=Decimal('120.00'),
            payment_status='PAID'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['maintenance'] == 120.00
    
    def test_overhead_expense_from_expense_model(self, analytics_service, farm):
        """Test that overhead costs come from Expense model with category=OVERHEAD."""
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.OVERHEAD,
            description='Monthly insurance',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='month',
            unit_cost=Decimal('200.00'),
            total_amount=Decimal('200.00'),
            payment_status='PAID'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['overhead'] == 200.00
    
    def test_mortality_loss_expense_from_expense_model(self, analytics_service, farm, flock):
        """Test that mortality loss costs come from Expense model with category=MORTALITY_LOSS."""
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MORTALITY_LOSS,
            description='Mortality loss - disease outbreak',
            expense_date=date.today() - timedelta(days=12),
            quantity=Decimal('15.00'),
            unit='birds',
            unit_cost=Decimal('35.00'),
            total_amount=Decimal('525.00'),
            payment_status='PAID'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['mortality_loss'] == 525.00
    
    def test_miscellaneous_expense_from_expense_model(self, analytics_service, farm):
        """Test that miscellaneous costs come from Expense model with category=MISCELLANEOUS."""
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.MISCELLANEOUS,
            description='Cleaning supplies',
            expense_date=date.today() - timedelta(days=6),
            quantity=Decimal('1.00'),
            unit='lot',
            unit_cost=Decimal('75.00'),
            total_amount=Decimal('75.00'),
            payment_status='PAID'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        breakdown = result['expenses_breakdown']
        
        assert breakdown['miscellaneous'] == 75.00


class TestFinancialAnalyticsTotalExpenses:
    """Test that total_expenses correctly sums ALL expense categories."""
    
    def test_total_expenses_includes_all_categories(
        self, analytics_service, farm, flock, feed_type, medication_type, vaccine_type
    ):
        """Test that total_expenses is the sum of all expense categories."""
        # Create expenses in multiple categories
        
        # Feed
        FeedPurchase.objects.create(
            farm=farm,
            feed_type=feed_type,
            quantity_bags=6,
            bag_weight_kg=Decimal('50.00'),
            quantity_kg=Decimal('300.00'),
            unit_cost_ghs=Decimal('50.00'),
            unit_price=Decimal('1.00'),
            total_cost=Decimal('300.00'),
            purchase_date=date.today() - timedelta(days=5),
            supplier='Feed Supplier'
        )
        
        # Medication
        MedicationRecord.objects.create(
            flock=flock,
            farm=farm,
            medication_type=medication_type,
            administered_date=date.today() - timedelta(days=3),
            reason='TREATMENT',
            dosage_given='50ml',
            birds_treated=50,
            treatment_days=3,
            end_date=date.today(),
            quantity_used=Decimal('50.00'),
            unit_cost=Decimal('2.00'),
            total_cost=Decimal('100.00'),
            administered_by='Vet'
        )
        
        # Vaccination
        VaccinationRecord.objects.create(
            flock=flock,
            farm=farm,
            medication_type=vaccine_type,
            vaccination_date=date.today() - timedelta(days=7),
            birds_vaccinated=1950,
            flock_age_weeks=8,
            dosage_per_bird='0.5ml',
            administration_route='Injection',
            batch_number='VAC-2026-002',
            expiry_date=date.today() + timedelta(days=180),
            quantity_used=Decimal('1000.00'),
            unit_cost=Decimal('0.20'),
            total_cost=Decimal('200.00'),
            administered_by='Vet',
            vet_license_number='VET-001'
        )
        
        # Vet Visit
        VetVisit.objects.create(
            farm=farm,
            flock=flock,
            visit_date=date.today() - timedelta(days=10),
            veterinarian_name='Dr. Vet',
            vet_license_number='VET-001',
            visit_type='ROUTINE',
            purpose='Routine check',
            visit_fee=Decimal('150.00'),
            status='COMPLETED'
        )
        
        # Labor
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Labor',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='week',
            unit_cost=Decimal('400.00'),
            total_amount=Decimal('400.00')
        )
        
        # Utilities
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.UTILITIES,
            description='Utilities',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='bill',
            unit_cost=Decimal('250.00'),
            total_amount=Decimal('250.00')
        )
        
        # Bedding
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Bedding',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('5.00'),
            unit='bags',
            unit_cost=Decimal('20.00'),
            total_amount=Decimal('100.00')
        )
        
        # Transport
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.TRANSPORT,
            description='Transport',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='trip',
            unit_cost=Decimal('50.00'),
            total_amount=Decimal('50.00')
        )
        
        # Maintenance
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.MAINTENANCE,
            description='Maintenance',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='job',
            unit_cost=Decimal('80.00'),
            total_amount=Decimal('80.00')
        )
        
        # Overhead
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.OVERHEAD,
            description='Overhead',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='month',
            unit_cost=Decimal('120.00'),
            total_amount=Decimal('120.00')
        )
        
        # Mortality Loss
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MORTALITY_LOSS,
            description='Mortality',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('5.00'),
            unit='birds',
            unit_cost=Decimal('30.00'),
            total_amount=Decimal('150.00')
        )
        
        # Miscellaneous
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.MISCELLANEOUS,
            description='Misc',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='lot',
            unit_cost=Decimal('100.00'),
            total_amount=Decimal('100.00')
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        
        # Calculate expected total
        expected_total = (
            300.00 +   # Feed
            100.00 +   # Medication
            200.00 +   # Vaccination
            150.00 +   # Vet Visit
            400.00 +   # Labor
            250.00 +   # Utilities
            100.00 +   # Bedding
            50.00 +    # Transport
            80.00 +    # Maintenance
            120.00 +   # Overhead
            150.00 +   # Mortality Loss
            100.00     # Miscellaneous
        )
        
        assert result['summary']['total_expenses'] == expected_total
        
        # Verify breakdown matches total
        breakdown = result['expenses_breakdown']
        breakdown_sum = sum(breakdown.values())
        assert abs(breakdown_sum - expected_total) < 0.01  # Allow small floating point variance


class TestFinancialAnalyticsProfitCalculation:
    """Test that profit calculations are accurate with all expenses included."""
    
    def test_gross_profit_calculation(self, analytics_service, farm, flock, feed_type, customer):
        """Test that gross_profit = total_revenue - total_expenses (with all categories)."""
        from sales_revenue.marketplace_models import MarketplaceOrder
        
        # Create revenue (marketplace order)
        MarketplaceOrder.objects.create(
            farm=farm,
            customer=customer,
            order_number='ORD-TEST-001',
            status='completed',
            total_amount=Decimal('5000.00'),
            subtotal=Decimal('5000.00')
        )
        
        # Create expenses
        FeedPurchase.objects.create(
            farm=farm,
            feed_type=feed_type,
            quantity_bags=4,
            bag_weight_kg=Decimal('50.00'),
            quantity_kg=Decimal('200.00'),
            unit_cost_ghs=Decimal('175.00'),
            unit_price=Decimal('3.50'),
            total_cost=Decimal('700.00'),
            purchase_date=date.today() - timedelta(days=5),
            supplier='Feed Supplier'
        )
        
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Labor',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='week',
            unit_cost=Decimal('300.00'),
            total_amount=Decimal('300.00')
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        
        # Revenue: 5000
        # Expenses: 700 (feed) + 300 (labor) = 1000
        # Gross Profit: 5000 - 1000 = 4000
        
        assert result['summary']['total_revenue'] == 5000.00
        assert result['summary']['total_expenses'] == 1000.00
        assert result['summary']['gross_profit'] == 4000.00
    
    def test_profit_margin_calculation(self, analytics_service, farm, flock, feed_type, customer):
        """Test that profit_margin_percent is calculated correctly."""
        from sales_revenue.marketplace_models import MarketplaceOrder
        
        # Create revenue
        MarketplaceOrder.objects.create(
            farm=farm,
            customer=customer,
            order_number='ORD-TEST-002',
            status='completed',
            total_amount=Decimal('10000.00'),
            subtotal=Decimal('10000.00')
        )
        
        # Create expenses totaling 4000
        FeedPurchase.objects.create(
            farm=farm,
            feed_type=feed_type,
            quantity_bags=10,
            bag_weight_kg=Decimal('50.00'),
            quantity_kg=Decimal('500.00'),
            unit_cost_ghs=Decimal('200.00'),
            unit_price=Decimal('4.00'),
            total_cost=Decimal('2000.00'),
            purchase_date=date.today() - timedelta(days=5),
            supplier='Feed Supplier'
        )
        
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Labor',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='month',
            unit_cost=Decimal('1000.00'),
            total_amount=Decimal('1000.00')
        )
        
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.UTILITIES,
            description='Utilities',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='month',
            unit_cost=Decimal('1000.00'),
            total_amount=Decimal('1000.00')
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        
        # Revenue: 10000
        # Expenses: 2000 + 1000 + 1000 = 4000
        # Profit: 6000
        # Margin: 6000/10000 * 100 = 60%
        
        assert result['summary']['profit_margin_percent'] == 60.0


class TestFinancialAnalyticsPeriodFiltering:
    """Test that expenses are correctly filtered by the specified period."""
    
    def test_expenses_outside_period_not_included(self, analytics_service, farm, flock):
        """Test that expenses outside the period are not included."""
        # Create expense within period (5 days ago)
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Recent labor',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='week',
            unit_cost=Decimal('200.00'),
            total_amount=Decimal('200.00')
        )
        
        # Create expense outside period (45 days ago, outside 30-day window)
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Old labor',
            expense_date=date.today() - timedelta(days=45),
            quantity=Decimal('1.00'),
            unit='week',
            unit_cost=Decimal('300.00'),
            total_amount=Decimal('300.00')
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        
        # Only the recent expense should be counted
        assert result['expenses_breakdown']['labor'] == 200.00
    
    def test_vet_visits_outside_period_not_included(self, analytics_service, farm, flock):
        """Test that vet visits outside the period are not included."""
        # Create vet visit within period
        VetVisit.objects.create(
            farm=farm,
            flock=flock,
            visit_date=date.today() - timedelta(days=10),
            veterinarian_name='Dr. Recent',
            vet_license_number='VET-001',
            visit_type='ROUTINE',
            purpose='Routine check',
            visit_fee=Decimal('100.00'),
            status='COMPLETED'
        )
        
        # Create vet visit outside period
        VetVisit.objects.create(
            farm=farm,
            flock=flock,
            visit_date=date.today() - timedelta(days=60),
            veterinarian_name='Dr. Old',
            vet_license_number='VET-002',
            visit_type='ROUTINE',
            purpose='Routine check',
            visit_fee=Decimal('200.00'),
            status='COMPLETED'
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        
        # Only the recent visit should be counted
        assert result['expenses_breakdown']['vet_visits'] == 100.00


class TestFinancialAnalyticsNoFarm:
    """Test behavior when user has no farm."""
    
    def test_returns_empty_dict_when_no_farm(self, db):
        """Test that empty dict is returned when user has no farm."""
        user = User.objects.create_user(
            username='no_farm_user',
            email='nofarm@test.com',
            password='testpass123',
            phone='+233240000088',
            role='FARMER',
            is_active=True
        )
        
        service = FarmerAnalyticsService(user)
        result = service.get_financial_analytics(days=30)
        
        assert result == {}


class TestFinancialAnalyticsZeroValues:
    """Test handling of zero values."""
    
    def test_zero_expenses_returns_zero_totals(self, analytics_service, farm, flock):
        """Test that zero expenses result in zero totals."""
        result = analytics_service.get_financial_analytics(days=30)
        
        assert result['summary']['total_expenses'] == 0.0
        assert result['summary']['gross_profit'] == 0.0
        
        # All breakdown values should be 0
        for value in result['expenses_breakdown'].values():
            assert value == 0.0
    
    def test_profit_margin_zero_when_no_revenue(self, analytics_service, farm, flock):
        """Test that profit margin is 0 when there's no revenue."""
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Labor',
            expense_date=date.today() - timedelta(days=5),
            quantity=Decimal('1.00'),
            unit='week',
            unit_cost=Decimal('500.00'),
            total_amount=Decimal('500.00')
        )
        
        result = analytics_service.get_financial_analytics(days=30)
        
        # With expenses but no revenue, profit margin should be 0
        assert result['summary']['profit_margin_percent'] == 0
