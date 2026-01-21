"""
Expense Tracking Integration Tests

Tests the comprehensive expense tracking system including:
- Expense creation and categorization
- Labor records with overtime calculations
- Utility records with meter readings
- Mortality loss valuation
- Recurring expense templates
- Flock cost accumulation (auto-update via signals)
- Expense summaries and analytics

SCENARIO:
=========
A broiler farmer tracks all operational costs for a flock of 500 birds:
- Labor: Caretaker wages (GHS 50/day × 42 days = GHS 2,100)
- Utilities: Electricity and water (GHS 840 over 6 weeks)
- Bedding: Wood shavings (GHS 400 initial + GHS 100 top-up = GHS 500)
- Transport: Feed delivery trips (4 × GHS 75 = GHS 300)
- Maintenance: Equipment repairs (GHS 150)
- Overhead: Pro-rata insurance and admin (GHS 250)
- Mortality Loss: 35 birds × GHS 35 invested = GHS 1,225
- Miscellaneous: Cleaning supplies (GHS 75)

Total Operational Costs: GHS 5,440
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
import uuid

User = get_user_model()

pytestmark = pytest.mark.django_db


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def expense_test_setup():
    """Create farm and flock for expense testing."""
    from farms.models import Farm
    from flock_management.models import Flock
    
    unique_id = uuid.uuid4().hex[:8]
    
    # Create farmer user
    farmer_user = User.objects.create_user(
        username=f'expense_farmer_{unique_id}',
        email=f'expense_farmer_{unique_id}@test.com',
        phone=f'+23324555{unique_id[:4]}',
        first_name='Expense',
        last_name='Tester',
        role='FARMER',
        password='testpass123'
    )
    
    # Create farm with all required fields
    farm = Farm.objects.create(
        user=farmer_user,
        # Section 1.1: Basic Info
        first_name='Expense',
        last_name='Tester',
        date_of_birth='1985-06-15',
        gender='Male',
        ghana_card_number=f'GHA-{unique_id[:9].upper()}-E',
        # Section 1.2: Contact
        primary_phone=f'+23324555{unique_id[:4]}',
        residential_address='Expense Test Farm, Tema',
        primary_constituency='Tema West',
        # Section 1.3: Next of Kin
        nok_full_name='Test NOK',
        nok_relationship='Spouse',
        nok_phone='+233241000000',
        # Section 1.4: Education
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=5,
        # Section 2: Farm Info
        farm_name='Expense Test Poultry',
        ownership_type='Sole Proprietorship',
        tin=f'E{unique_id[:10].upper()}',
        # Section 4: Infrastructure
        number_of_poultry_houses=1,
        total_bird_capacity=600,
        current_bird_count=500,
        housing_type='Deep Litter',
        total_infrastructure_value_ghs=Decimal('15000.00'),
        # Section 5: Production
        primary_production_type='Broilers',
        broiler_breed='Cobb 500',
        planned_monthly_bird_sales=150,
        planned_production_start_date='2025-01-01',
        # Section 7: Financial
        initial_investment_amount=Decimal('30000.00'),
        funding_source=['Personal Savings'],
        monthly_operating_budget=Decimal('5000.00'),
        expected_monthly_revenue=Decimal('8000.00'),
        # Status
        application_status='Approved',
        farm_status='Active',
    )
    
    # Create flock for expense tracking
    flock = Flock.objects.create(
        farm=farm,
        flock_number=f'FLOCK-EXP-{unique_id[:4]}',
        flock_type='Broilers',
        breed='Cobb 500',
        source='YEA Program',
        supplier_name='National Hatchery',
        arrival_date=timezone.now().date() - timedelta(days=42),  # 6 weeks ago
        initial_count=500,
        current_count=465,  # After 35 mortality
        age_at_arrival_weeks=Decimal('0'),
        purchase_price_per_bird=Decimal('15.00'),
        status='Active',
    )
    
    return {
        'farmer': farmer_user,
        'farm': farm,
        'flock': flock,
    }


@pytest.fixture
def authenticated_farmer_client(expense_test_setup):
    """API client authenticated as farmer."""
    client = APIClient()
    client.force_authenticate(user=expense_test_setup['farmer'])
    return client


# =============================================================================
# EXPENSE CREATION TESTS
# =============================================================================

class TestExpenseCreation:
    """Test creating expenses across all categories."""
    
    def test_create_labor_expense(self, expense_test_setup):
        """Create a labor expense for caretaker wages."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        user = expense_test_setup['farmer']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.LABOR,
            description='Daily caretaker wage - Kofi',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='day',
            unit_cost=Decimal('50.00'),
            payee_name='Kofi Mensah',
            payment_status='PAID',
            created_by=user,
        )
        
        # Verify total amount auto-calculated
        assert expense.total_amount == Decimal('50.00')
        assert expense.category == ExpenseCategory.LABOR
        
    def test_create_utilities_expense(self, expense_test_setup):
        """Create a utilities expense for electricity."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=None,  # Farm-level expense
            category=ExpenseCategory.UTILITIES,
            description='December electricity bill - ECG',
            expense_date=timezone.now().date(),
            quantity=Decimal('450'),
            unit='kWh',
            unit_cost=Decimal('0.85'),
            payee_name='ECG',
            payment_status='PAID',
        )
        
        # 450 kWh × GHS 0.85 = GHS 382.50
        assert expense.total_amount == Decimal('382.50')
        assert expense.flock is None  # Farm-level
        
    def test_create_bedding_expense(self, expense_test_setup):
        """Create a bedding expense for wood shavings."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Wood shavings for brooder',
            expense_date=flock.arrival_date,
            quantity=Decimal('16'),
            unit='bags',
            unit_cost=Decimal('25.00'),
            payee_name='Timber Supplies',
            payment_status='PAID',
        )
        
        # 16 bags × GHS 25 = GHS 400
        assert expense.total_amount == Decimal('400.00')
        
    def test_create_transport_expense(self, expense_test_setup):
        """Create a transport expense for feed delivery."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.TRANSPORT,
            description='Feed delivery from supplier',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='trip',
            unit_cost=Decimal('75.00'),
            payment_status='PAID',
        )
        
        assert expense.total_amount == Decimal('75.00')
        
    def test_create_maintenance_expense(self, expense_test_setup):
        """Create a maintenance expense for repairs."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=None,  # Farm-level
            category=ExpenseCategory.MAINTENANCE,
            description='Feeder repair',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='repair',
            unit_cost=Decimal('150.00'),
            payment_status='PAID',
        )
        
        assert expense.total_amount == Decimal('150.00')
        
    def test_create_overhead_expense(self, expense_test_setup):
        """Create an overhead expense for insurance."""
        from expenses.models import Expense, ExpenseCategory, ExpenseFrequency
        
        farm = expense_test_setup['farm']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=None,  # Farm-level
            category=ExpenseCategory.OVERHEAD,
            description='Monthly pro-rata insurance',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='month',
            unit_cost=Decimal('250.00'),
            frequency=ExpenseFrequency.MONTHLY,
            is_recurring=True,
            payment_status='PAID',
        )
        
        assert expense.total_amount == Decimal('250.00')
        assert expense.is_recurring == True
        
    def test_create_miscellaneous_expense(self, expense_test_setup):
        """Create a miscellaneous expense."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MISCELLANEOUS,
            description='Cleaning supplies (disinfectant)',
            expense_date=timezone.now().date(),
            quantity=Decimal('3'),
            unit='bottles',
            unit_cost=Decimal('25.00'),
            payment_status='PAID',
        )
        
        assert expense.total_amount == Decimal('75.00')


# =============================================================================
# FLOCK COST ACCUMULATION TESTS
# =============================================================================

class TestFlockCostAccumulation:
    """Test that expenses linked to flocks auto-update flock cost fields."""
    
    def test_expense_updates_flock_labor_cost(self, expense_test_setup):
        """Verify labor expenses update flock.total_labor_cost."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        # Initial labor cost should be 0
        assert flock.total_labor_cost == Decimal('0.00')
        
        # Create first labor expense
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.LABOR,
            description='Week 1 caretaker wage',
            expense_date=timezone.now().date() - timedelta(days=35),
            quantity=Decimal('7'),
            unit='days',
            unit_cost=Decimal('50.00'),
            payment_status='PAID',
        )
        
        # Refresh flock and check
        flock.refresh_from_db()
        assert flock.total_labor_cost == Decimal('350.00')
        
        # Create second labor expense
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.LABOR,
            description='Week 2 caretaker wage',
            expense_date=timezone.now().date() - timedelta(days=28),
            quantity=Decimal('7'),
            unit='days',
            unit_cost=Decimal('50.00'),
            payment_status='PAID',
        )
        
        # Should accumulate
        flock.refresh_from_db()
        assert flock.total_labor_cost == Decimal('700.00')
        
    def test_expense_updates_flock_utilities_cost(self, expense_test_setup):
        """Verify utility expenses update flock.total_utilities_cost."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        assert flock.total_utilities_cost == Decimal('0.00')
        
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.UTILITIES,
            description='Electricity for brooder heating',
            expense_date=timezone.now().date(),
            quantity=Decimal('200'),
            unit='kWh',
            unit_cost=Decimal('0.85'),
            payment_status='PAID',
        )
        
        flock.refresh_from_db()
        assert flock.total_utilities_cost == Decimal('170.00')
        
    def test_expense_updates_flock_bedding_cost(self, expense_test_setup):
        """Verify bedding expenses update flock.total_bedding_cost."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Initial bedding',
            expense_date=flock.arrival_date,
            quantity=Decimal('16'),
            unit='bags',
            unit_cost=Decimal('25.00'),
        )
        
        flock.refresh_from_db()
        assert flock.total_bedding_cost == Decimal('400.00')
        
    def test_farm_level_expense_does_not_update_flock(self, expense_test_setup):
        """Farm-level expenses (no flock) should not update any flock."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        initial_overhead = flock.total_overhead_cost
        
        # Create farm-level expense (no flock)
        Expense.objects.create(
            farm=farm,
            flock=None,  # Farm-level
            category=ExpenseCategory.OVERHEAD,
            description='Farm insurance',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='policy',
            unit_cost=Decimal('500.00'),
        )
        
        # Flock cost should not change
        flock.refresh_from_db()
        assert flock.total_overhead_cost == initial_overhead


# =============================================================================
# LABOR RECORD TESTS
# =============================================================================

class TestLaborRecords:
    """Test detailed labor tracking with overtime."""
    
    def test_create_labor_record_with_overtime(self, expense_test_setup):
        """Create labor record with overtime calculation."""
        from expenses.models import Expense, LaborRecord, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        # First create the expense
        expense = Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.LABOR,
            description='Vaccination day - extended hours',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='day',
            unit_cost=Decimal('110.00'),  # Will be updated by labor record
            payment_status='PAID',
        )
        
        # Create detailed labor record
        labor = LaborRecord.objects.create(
            expense=expense,
            farm=farm,
            flock=flock,
            worker_name='Kwame Boateng',
            worker_type='CASUAL',
            work_date=timezone.now().date(),
            task_type='VACCINATION',
            hours_worked=Decimal('8.00'),
            hourly_rate=Decimal('10.00'),
            overtime_hours=Decimal('2.00'),
            overtime_rate=Decimal('15.00'),
        )
        
        # Verify calculations
        assert labor.base_pay == Decimal('80.00')  # 8 × 10
        assert labor.overtime_pay == Decimal('30.00')  # 2 × 15
        assert labor.total_pay == Decimal('110.00')  # 80 + 30
        
    def test_labor_record_worker_types(self, expense_test_setup):
        """Test different worker types."""
        from expenses.models import Expense, LaborRecord, ExpenseCategory
        
        farm = expense_test_setup['farm']
        
        worker_types = [
            ('PERMANENT', 'Permanent Staff'),
            ('CASUAL', 'Casual Worker'),
            ('CONTRACT', 'Contract Worker'),
            ('FAMILY', 'Family Labor'),
        ]
        
        for code, display in worker_types:
            expense = Expense.objects.create(
                farm=farm,
                category=ExpenseCategory.LABOR,
                description=f'{display} wage',
                expense_date=timezone.now().date(),
                quantity=Decimal('1'),
                unit='day',
                unit_cost=Decimal('50.00'),
            )
            
            labor = LaborRecord.objects.create(
                expense=expense,
                farm=farm,
                worker_name=f'Worker {code}',
                worker_type=code,
                work_date=timezone.now().date(),
                task_type='GENERAL',
                hours_worked=Decimal('8.00'),
                hourly_rate=Decimal('6.25'),
            )
            
            assert labor.worker_type == code
            assert labor.get_worker_type_display() == display


# =============================================================================
# UTILITY RECORD TESTS
# =============================================================================

class TestUtilityRecords:
    """Test utility tracking with meter readings."""
    
    def test_create_utility_record_with_readings(self, expense_test_setup):
        """Create utility record and verify consumption calculation."""
        from expenses.models import Expense, UtilityRecord, ExpenseCategory
        
        farm = expense_test_setup['farm']
        
        expense = Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.UTILITIES,
            description='January electricity',
            expense_date=timezone.now().date(),
            quantity=Decimal('450'),
            unit='kWh',
            unit_cost=Decimal('0.85'),
        )
        
        utility = UtilityRecord.objects.create(
            expense=expense,
            farm=farm,
            utility_type='ELECTRICITY',
            provider='ECG',
            account_number='ACC-12345',
            billing_period_start=date(2026, 1, 1),
            billing_period_end=date(2026, 1, 31),
            previous_reading=Decimal('12500.00'),
            current_reading=Decimal('12950.00'),
            unit_of_measure='kWh',
            rate_per_unit=Decimal('0.85'),
        )
        
        # Verify units consumed auto-calculated
        assert utility.units_consumed == Decimal('450.00')
        
    def test_utility_types(self, expense_test_setup):
        """Test all utility types."""
        from expenses.models import Expense, UtilityRecord, ExpenseCategory
        
        farm = expense_test_setup['farm']
        
        utility_types = ['ELECTRICITY', 'WATER', 'GAS', 'FUEL', 'INTERNET', 'OTHER']
        
        for util_type in utility_types:
            expense = Expense.objects.create(
                farm=farm,
                category=ExpenseCategory.UTILITIES,
                description=f'{util_type} expense',
                expense_date=timezone.now().date(),
                quantity=Decimal('100'),
                unit='unit',
                unit_cost=Decimal('1.00'),
            )
            
            utility = UtilityRecord.objects.create(
                expense=expense,
                farm=farm,
                utility_type=util_type,
            )
            
            assert utility.utility_type == util_type


# =============================================================================
# MORTALITY LOSS RECORD TESTS
# =============================================================================

class TestMortalityLossRecords:
    """Test mortality loss valuation."""
    
    def test_create_mortality_loss_record(self, expense_test_setup):
        """Create mortality loss and verify value calculation."""
        from expenses.models import Expense, MortalityLossRecord, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MORTALITY_LOSS,
            description='Week 1 mortality - heat stress',
            expense_date=flock.arrival_date + timedelta(days=7),
            quantity=Decimal('10'),
            unit='birds',
            unit_cost=Decimal('17.50'),  # Acquisition + feed invested per bird
        )
        
        loss_record = MortalityLossRecord.objects.create(
            expense=expense,
            farm=farm,
            flock=flock,
            mortality_date=flock.arrival_date + timedelta(days=7),
            birds_lost=10,
            cause_of_death='Heat Stress',
            age_at_death_weeks=Decimal('1'),
            acquisition_cost_per_bird=Decimal('15.00'),
            feed_cost_invested=Decimal('25.00'),  # Total feed for 10 birds
            other_costs_invested=Decimal('0.00'),
        )
        
        # Total loss = (15 × 10) + 25 + 0 = GHS 175
        assert loss_record.total_loss_value == Decimal('175.00')
        
    def test_mortality_loss_comprehensive(self, expense_test_setup):
        """Test mortality with all cost components."""
        from expenses.models import Expense, MortalityLossRecord, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        expense = Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MORTALITY_LOSS,
            description='Disease outbreak mortality',
            expense_date=timezone.now().date() - timedelta(days=21),
            quantity=Decimal('8'),
            unit='birds',
            unit_cost=Decimal('35.00'),
        )
        
        loss_record = MortalityLossRecord.objects.create(
            expense=expense,
            farm=farm,
            flock=flock,
            mortality_date=timezone.now().date() - timedelta(days=21),
            birds_lost=8,
            cause_of_death='Coccidiosis',
            age_at_death_weeks=Decimal('3'),
            acquisition_cost_per_bird=Decimal('15.00'),
            feed_cost_invested=Decimal('80.00'),  # 3 weeks of feed for 8 birds
            other_costs_invested=Decimal('20.00'),  # Vaccination already administered
            potential_revenue_lost=Decimal('680.00'),  # 8 × GHS 85 (if sold as live)
        )
        
        # Total loss = (15 × 8) + 80 + 20 = GHS 220
        assert loss_record.total_loss_value == Decimal('220.00')
        
        # Verify flock mortality cost updated
        flock.refresh_from_db()
        assert flock.total_mortality_loss_value >= Decimal('220.00')


# =============================================================================
# RECURRING EXPENSE TEMPLATE TESTS
# =============================================================================

class TestRecurringExpenseTemplates:
    """Test recurring expense automation."""
    
    def test_create_monthly_salary_template(self, expense_test_setup):
        """Create recurring monthly salary template."""
        from expenses.models import RecurringExpenseTemplate, ExpenseCategory, ExpenseFrequency
        
        farm = expense_test_setup['farm']
        user = expense_test_setup['farmer']
        
        template = RecurringExpenseTemplate.objects.create(
            farm=farm,
            name='Monthly Caretaker Salary',
            category=ExpenseCategory.LABOR,
            description='Kofi monthly salary',
            quantity=Decimal('1'),
            unit='month',
            unit_cost=Decimal('1500.00'),
            frequency=ExpenseFrequency.MONTHLY,
            start_date=date(2026, 1, 1),
            payee_name='Kofi Mensah',
            is_active=True,
            created_by=user,
        )
        
        # Verify estimated amount
        assert template.estimated_amount == Decimal('1500.00')
        assert template.next_due_date == date(2026, 1, 1)
        
    def test_generate_expense_from_template(self, expense_test_setup):
        """Generate actual expense from template."""
        from expenses.models import (
            RecurringExpenseTemplate, Expense, 
            ExpenseCategory, ExpenseFrequency
        )
        
        farm = expense_test_setup['farm']
        user = expense_test_setup['farmer']
        
        template = RecurringExpenseTemplate.objects.create(
            farm=farm,
            name='Weekly Water Bill',
            category=ExpenseCategory.UTILITIES,
            description='Weekly water usage',
            quantity=Decimal('500'),
            unit='gallons',
            unit_cost=Decimal('0.20'),
            frequency=ExpenseFrequency.WEEKLY,
            start_date=timezone.now().date(),
            is_active=True,
        )
        
        # Generate expense
        expense = template.generate_expense(user=user)
        
        assert expense is not None
        assert expense.category == ExpenseCategory.UTILITIES
        assert expense.total_amount == Decimal('100.00')  # 500 × 0.20
        assert expense.is_recurring == True
        
        # Template should be updated
        template.refresh_from_db()
        assert template.last_generated_date == expense.expense_date
        # Next due date should be 1 week later
        assert template.next_due_date == expense.expense_date + timedelta(days=7)


# =============================================================================
# EXPENSE SUMMARY TESTS
# =============================================================================

class TestExpenseSummaries:
    """Test expense summary calculations."""
    
    def test_summary_recalculation(self, expense_test_setup):
        """Test summary recalculates correctly."""
        from expenses.models import Expense, ExpenseSummary, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        today = timezone.now().date()
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # Create expenses
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.LABOR,
            description='Labor 1',
            expense_date=today,
            quantity=Decimal('1'),
            unit='day',
            unit_cost=Decimal('100.00'),
        )
        
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.UTILITIES,
            description='Utilities 1',
            expense_date=today,
            quantity=Decimal('1'),
            unit='bill',
            unit_cost=Decimal('200.00'),
        )
        
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Bedding 1',
            expense_date=today,
            quantity=Decimal('1'),
            unit='order',
            unit_cost=Decimal('150.00'),
        )
        
        # Create/update summary
        summary, _ = ExpenseSummary.objects.get_or_create(
            farm=farm,
            flock=flock,
            period_type='MONTHLY',
            period_start=month_start,
            period_end=month_end,
        )
        
        summary.recalculate()
        
        assert summary.labor_total == Decimal('100.00')
        assert summary.utilities_total == Decimal('200.00')
        assert summary.bedding_total == Decimal('150.00')
        assert summary.grand_total == Decimal('450.00')
        assert summary.expense_count == 3


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

class TestExpenseAPIEndpoints:
    """Test expense API endpoints."""
    
    def test_dashboard_endpoint(self, authenticated_farmer_client, expense_test_setup):
        """Test expense dashboard returns correct data."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        
        # Create some expenses
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.LABOR,
            description='Test labor',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='day',
            unit_cost=Decimal('100.00'),
        )
        
        response = authenticated_farmer_client.get('/api/expenses/dashboard/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'total_expenses' in response.data
        assert 'breakdown' in response.data
        
    def test_list_expenses_endpoint(self, authenticated_farmer_client, expense_test_setup):
        """Test listing expenses."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        
        # Create expenses
        for i in range(3):
            Expense.objects.create(
                farm=farm,
                category=ExpenseCategory.LABOR,
                description=f'Labor expense {i}',
                expense_date=timezone.now().date(),
                quantity=Decimal('1'),
                unit='day',
                unit_cost=Decimal('50.00'),
            )
        
        response = authenticated_farmer_client.get('/api/expenses/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3
        
    def test_create_expense_via_api(self, authenticated_farmer_client, expense_test_setup):
        """Test creating expense via API."""
        flock = expense_test_setup['flock']
        
        data = {
            'category': 'BEDDING',
            'description': 'Wood shavings via API',
            'expense_date': timezone.now().date().isoformat(),
            'quantity': '10',
            'unit': 'bags',
            'unit_cost': '25.00',
            'flock': str(flock.id),
            'payment_status': 'PAID',
        }
        
        response = authenticated_farmer_client.post('/api/expenses/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['total_amount'] == '250.00'
        
    def test_filter_expenses_by_category(self, authenticated_farmer_client, expense_test_setup):
        """Test filtering expenses by category."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        
        # Create different category expenses
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Labor',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='day',
            unit_cost=Decimal('50.00'),
        )
        
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.UTILITIES,
            description='Utilities',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='bill',
            unit_cost=Decimal('100.00'),
        )
        
        # Filter by LABOR only
        response = authenticated_farmer_client.get('/api/expenses/?category=LABOR')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['category'] == 'LABOR'
        
    def test_expense_analytics_endpoint(self, authenticated_farmer_client, expense_test_setup):
        """Test analytics endpoint."""
        from expenses.models import Expense, ExpenseCategory
        
        farm = expense_test_setup['farm']
        
        Expense.objects.create(
            farm=farm,
            category=ExpenseCategory.LABOR,
            description='Labor expense',
            expense_date=timezone.now().date(),
            quantity=Decimal('1'),
            unit='day',
            unit_cost=Decimal('100.00'),
        )
        
        response = authenticated_farmer_client.get('/api/expenses/analytics/?period=MONTH')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'summary' in response.data
        assert 'by_category' in response.data


# =============================================================================
# COMPREHENSIVE LIFECYCLE TEST
# =============================================================================

class TestExpenseLifecycle:
    """
    Complete expense lifecycle for a flock.
    
    Simulates 6 weeks of operational expenses for 500 broilers:
    - Labor: GHS 2,100 (42 days × GHS 50/day)
    - Utilities: GHS 840 (6 weeks × GHS 140/week)
    - Bedding: GHS 500 (GHS 400 initial + GHS 100 top-up)
    - Transport: GHS 300 (4 trips × GHS 75)
    - Maintenance: GHS 150
    - Overhead: GHS 250
    - Mortality Loss: GHS 1,225 (35 birds × GHS 35 invested)
    - Miscellaneous: GHS 75
    
    TOTAL: GHS 5,440
    """
    
    def test_complete_flock_expense_tracking(self, expense_test_setup):
        """Track all operational expenses for a flock lifecycle."""
        from expenses.models import Expense, ExpenseCategory
        from flock_management.models import Flock
        
        farm = expense_test_setup['farm']
        flock = expense_test_setup['flock']
        arrival = flock.arrival_date
        
        # ===== LABOR COSTS =====
        # 42 days of caretaker wages at GHS 50/day
        for week in range(6):
            Expense.objects.create(
                farm=farm,
                flock=flock,
                category=ExpenseCategory.LABOR,
                description=f'Caretaker wage - Week {week + 1}',
                expense_date=arrival + timedelta(days=week * 7),
                quantity=Decimal('7'),
                unit='days',
                unit_cost=Decimal('50.00'),
                payment_status='PAID',
            )
        
        # ===== UTILITIES COSTS =====
        # 6 weeks at GHS 140/week
        for week in range(6):
            Expense.objects.create(
                farm=farm,
                flock=flock,
                category=ExpenseCategory.UTILITIES,
                description=f'Electricity/water - Week {week + 1}',
                expense_date=arrival + timedelta(days=week * 7),
                quantity=Decimal('1'),
                unit='week',
                unit_cost=Decimal('140.00'),
            )
        
        # ===== BEDDING COSTS =====
        # Initial: GHS 400, Top-up: GHS 100
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Initial bedding - wood shavings',
            expense_date=arrival,
            quantity=Decimal('16'),
            unit='bags',
            unit_cost=Decimal('25.00'),
        )
        
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.BEDDING,
            description='Bedding top-up',
            expense_date=arrival + timedelta(days=21),
            quantity=Decimal('4'),
            unit='bags',
            unit_cost=Decimal('25.00'),
        )
        
        # ===== TRANSPORT COSTS =====
        # 4 feed delivery trips at GHS 75 each
        for trip in range(4):
            Expense.objects.create(
                farm=farm,
                flock=flock,
                category=ExpenseCategory.TRANSPORT,
                description=f'Feed delivery trip {trip + 1}',
                expense_date=arrival + timedelta(days=trip * 10),
                quantity=Decimal('1'),
                unit='trip',
                unit_cost=Decimal('75.00'),
            )
        
        # ===== MAINTENANCE COSTS =====
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MAINTENANCE,
            description='Feeder repair',
            expense_date=arrival + timedelta(days=14),
            quantity=Decimal('1'),
            unit='repair',
            unit_cost=Decimal('150.00'),
        )
        
        # ===== OVERHEAD COSTS =====
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.OVERHEAD,
            description='Pro-rata insurance and admin',
            expense_date=arrival,
            quantity=Decimal('1'),
            unit='month',
            unit_cost=Decimal('250.00'),
        )
        
        # ===== MORTALITY LOSS =====
        # 35 birds lost × GHS 35 invested per bird
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MORTALITY_LOSS,
            description='Mortality economic loss',
            expense_date=arrival + timedelta(days=21),
            quantity=Decimal('35'),
            unit='birds',
            unit_cost=Decimal('35.00'),  # Acquisition + feed invested
        )
        
        # ===== MISCELLANEOUS =====
        Expense.objects.create(
            farm=farm,
            flock=flock,
            category=ExpenseCategory.MISCELLANEOUS,
            description='Cleaning supplies',
            expense_date=arrival,
            quantity=Decimal('3'),
            unit='items',
            unit_cost=Decimal('25.00'),
        )
        
        # ===== VERIFY FLOCK ACCUMULATED COSTS =====
        flock.refresh_from_db()
        
        assert flock.total_labor_cost == Decimal('2100.00')
        assert flock.total_utilities_cost == Decimal('840.00')
        assert flock.total_bedding_cost == Decimal('500.00')
        assert flock.total_transport_cost == Decimal('300.00')
        assert flock.total_maintenance_cost == Decimal('150.00')
        assert flock.total_overhead_cost == Decimal('250.00')
        assert flock.total_mortality_loss_value == Decimal('1225.00')
        assert flock.total_miscellaneous_cost == Decimal('75.00')
        
        # ===== VERIFY TOTAL OPERATIONAL COST =====
        # Note: total_operational_cost excludes mortality loss (tracked separately)
        # Labor + Utilities + Bedding + Transport + Maintenance + Overhead + Misc
        # 2100 + 840 + 500 + 300 + 150 + 250 + 75 = 4215
        expected_operational = Decimal('4215.00')
        assert flock.total_operational_cost == expected_operational
        
        # Total including mortality loss
        expected_total_with_mortality = Decimal('5440.00')
        actual_total_with_mortality = flock.total_operational_cost + flock.total_mortality_loss_value
        assert actual_total_with_mortality == expected_total_with_mortality
        
        # ===== VERIFY PER-BIRD COST =====
        # Total operational / current birds (465)
        per_bird_cost = flock.total_operational_cost / flock.current_count
        assert per_bird_cost == Decimal('4215.00') / Decimal('465')
        
        # ===== VERIFY COST BREAKDOWN =====
        breakdown = flock.get_cost_breakdown()
        
        assert 'breakdown' in breakdown
        assert 'labor' in breakdown['breakdown']
        assert breakdown['breakdown']['labor']['amount'] == Decimal('2100.00')
        
        # Labor should be ~49.8% of operational costs (2100/4215)
        labor_percentage = (Decimal('2100.00') / expected_operational) * 100
        assert abs(breakdown['breakdown']['labor']['percentage'] - labor_percentage) < Decimal('0.1')
        
        print(f"\n{'='*60}")
        print("FLOCK OPERATIONAL EXPENSE SUMMARY")
        print(f"{'='*60}")
        print(f"Labor:           GHS {flock.total_labor_cost:>10,.2f}")
        print(f"Utilities:       GHS {flock.total_utilities_cost:>10,.2f}")
        print(f"Bedding:         GHS {flock.total_bedding_cost:>10,.2f}")
        print(f"Transport:       GHS {flock.total_transport_cost:>10,.2f}")
        print(f"Maintenance:     GHS {flock.total_maintenance_cost:>10,.2f}")
        print(f"Overhead:        GHS {flock.total_overhead_cost:>10,.2f}")
        print(f"Miscellaneous:   GHS {flock.total_miscellaneous_cost:>10,.2f}")
        print(f"{'-'*60}")
        print(f"OPERATIONAL:     GHS {flock.total_operational_cost:>10,.2f}")
        print(f"Mortality Loss:  GHS {flock.total_mortality_loss_value:>10,.2f}")
        print(f"{'-'*60}")
        print(f"TOTAL w/LOSS:    GHS {actual_total_with_mortality:>10,.2f}")
        print(f"{'='*60}")
        print(f"Per-bird cost:   GHS {per_bird_cost:>10,.2f}")
        print(f"{'='*60}")
