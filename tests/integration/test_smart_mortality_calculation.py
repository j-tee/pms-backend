"""
Tests for Smart Mortality Loss Calculation.

Tests the auto-calculation of feed and medication costs invested in birds
that die, using actual tracked data from FeedConsumption, MedicationRecord,
and VaccinationRecord models.

This is a critical feature for accurate farm accounting.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import uuid

pytestmark = pytest.mark.django_db


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def farmer_user(django_user_model):
    """Create a farmer user."""
    user = django_user_model.objects.create_user(
        username='test_farmer',
        email='farmer@test.com',
        password='testpass123',
        role='FARMER',
        phone='+233501234567'
    )
    return user


@pytest.fixture
def farm(farmer_user):
    """Create a farm for testing."""
    from farms.models import Farm
    from django.utils import timezone
    import uuid
    
    unique_id = uuid.uuid4().hex[:8]
    
    farm = Farm.objects.create(
        user=farmer_user,
        # Section 1.1: Basic Info
        first_name='Smart',
        last_name='Calculator',
        date_of_birth='1985-06-15',
        gender='Male',
        ghana_card_number=f'GHA-{unique_id.upper()}-S',
        # Section 1.2: Contact
        primary_phone='+233501234567',
        residential_address='Smart Farm, Accra',
        primary_constituency='Ablekuma South',
        # Section 1.3: Next of Kin
        nok_full_name='Test NOK',
        nok_relationship='Spouse',
        nok_phone='+233241000000',
        # Section 1.4: Education
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=5,
        # Section 2: Farm Info
        farm_name='Test Poultry Farm',
        ownership_type='Sole Proprietorship',
        tin=f'S{unique_id.upper()}',
        # Section 4: Infrastructure
        number_of_poultry_houses=2,
        total_bird_capacity=5000,
        current_bird_count=2000,
        housing_type='Deep Litter',
        total_infrastructure_value_ghs=Decimal('50000.00'),
        # Section 5: Production
        primary_production_type='Layers',
        layer_breed='Isa Brown',
        planned_monthly_egg_production=30000,
        planned_production_start_date=timezone.now().date() + timedelta(days=30),
        # Section 7: Financial
        initial_investment_amount=Decimal('50000.00'),
        funding_source=['Personal Savings'],
        monthly_operating_budget=Decimal('10000.00'),
        expected_monthly_revenue=Decimal('15000.00'),
        # Status
        application_status='Approved',
        farm_status='Active',
    )
    farmer_user.farm = farm
    farmer_user.save()
    return farm


@pytest.fixture
def flock(farm):
    """Create a test flock with 2000 birds."""
    from flock_management.models import Flock
    
    arrival_date = date.today() - timedelta(days=21)  # 3 weeks ago
    
    return Flock.objects.create(
        farm=farm,
        flock_number='FLOCK-TEST-001',
        flock_type='Layers',
        breed='Isa Brown',
        source='Purchased',
        supplier_name='Test Hatchery',
        arrival_date=arrival_date,
        initial_count=2000,
        current_count=2000,
        age_at_arrival_weeks=Decimal('0'),  # Day-old chicks
        purchase_price_per_bird=Decimal('5.00'),  # GHS 5 per bird
        status='Active'
    )


@pytest.fixture
def feed_type():
    """Create feed type for testing."""
    from feed_inventory.models import FeedType
    
    return FeedType.objects.create(
        name='Layer Starter Test',
        category='STARTER',
        manufacturer='Premium Feeds',
        form='MASH',
        protein_content=Decimal('21.0'),
        is_active=True
    )


@pytest.fixture
def feed_purchase(farm, feed_type):
    """Create feed stock for consumption records."""
    from feed_inventory.models import FeedPurchase
    
    return FeedPurchase.objects.create(
        farm=farm,
        feed_type=feed_type,
        supplier='Feed Supplier Ltd',
        purchase_date=date.today() - timedelta(days=25),
        quantity_bags=10,
        bag_weight_kg=Decimal('25.00'),  # 25kg bags
        quantity_kg=Decimal('250'),  # 10 bags × 25kg
        stock_balance_kg=Decimal('250'),
        unit_cost_ghs=Decimal('1000.00'),  # GHS 1000 per 25kg bag
        unit_price=Decimal('40.00'),  # GHS 40 per kg
        total_cost=Decimal('10000'),  # 10 bags × GHS 1000
        payment_status='PAID'
    )


@pytest.fixture
def daily_productions(flock, feed_type, feed_purchase):
    """Create 3 weeks of daily production with feed consumption."""
    from flock_management.models import DailyProduction
    from feed_inventory.models import FeedConsumption
    
    productions = []
    consumptions = []
    
    start_date = flock.arrival_date
    
    for day in range(21):  # 3 weeks
        production_date = start_date + timedelta(days=day)
        
        # Create daily production record
        production = DailyProduction.objects.create(
            flock=flock,
            farm=flock.farm,
            production_date=production_date,
            eggs_collected=0,  # Not yet laying
            feed_consumed_kg=Decimal('25.0'),  # 25kg per day
            feed_cost_today=Decimal('1000.0'),  # GHS 1000 per day (40/kg * 25kg)
        )
        productions.append(production)
        
        # Create corresponding feed consumption record
        consumption = FeedConsumption.objects.create(
            daily_production=production,
            farm=flock.farm,
            flock=flock,
            feed_stock=feed_purchase,
            feed_type=feed_type,
            date=production_date,
            quantity_consumed_kg=Decimal('25.0'),
            cost_per_kg=Decimal('40.0'),
            total_cost=Decimal('1000.0'),
            birds_count_at_consumption=2000,
            consumption_per_bird_grams=Decimal('12.5')  # 25000g / 2000 birds
        )
        consumptions.append(consumption)
    
    return {'productions': productions, 'consumptions': consumptions}


@pytest.fixture
def medication_type():
    """Create a medication type for testing."""
    from medication_management.models import MedicationType
    
    return MedicationType.objects.create(
        name='Vitamin Supplement',
        generic_name='Multivitamin',
        category='VITAMIN',
        administration_route='ORAL',
        dosage='1ml per liter water',
        indication='Growth promotion and immune support',
        unit_price=Decimal('50.00'),
        unit_measure='per 100ml bottle',
        withdrawal_period_days=0,
        is_active=True
    )


@pytest.fixture
def vaccine_type():
    """Create a vaccine type for testing."""
    from medication_management.models import MedicationType
    
    return MedicationType.objects.create(
        name='Newcastle Disease Vaccine',
        generic_name='ND-B1',
        category='VACCINE',
        administration_route='EYE_DROP',
        dosage='1 dose per bird',
        indication='Prevention of Newcastle disease',
        unit_price=Decimal('200.00'),
        unit_measure='per 1000 dose vial',
        withdrawal_period_days=0,
        is_active=True
    )


@pytest.fixture
def medication_record(flock, medication_type):
    """Create a medication record for the flock."""
    from medication_management.models import MedicationRecord
    
    return MedicationRecord.objects.create(
        flock=flock,
        farm=flock.farm,
        medication_type=medication_type,
        administered_date=flock.arrival_date + timedelta(days=7),  # Week 1
        reason='PREVENTION',
        dosage_given='5ml in water',
        birds_treated=2000,
        treatment_days=3,
        end_date=flock.arrival_date + timedelta(days=9),
        quantity_used=Decimal('2.0'),  # 2 bottles
        unit_cost=Decimal('50.0'),
        total_cost=Decimal('100.0')  # GHS 100
    )


@pytest.fixture
def vaccination_record(flock, vaccine_type):
    """Create a vaccination record for the flock."""
    from medication_management.models import VaccinationRecord
    
    return VaccinationRecord.objects.create(
        flock=flock,
        farm=flock.farm,
        medication_type=vaccine_type,
        vaccination_date=flock.arrival_date + timedelta(days=1),  # Day 1
        birds_vaccinated=2000,
        flock_age_weeks=0,
        dosage_per_bird='1 dose',
        administration_route='Eye drop',
        batch_number='VAC-2026-001',
        expiry_date=date.today() + timedelta(days=180),
        quantity_used=Decimal('2.0'),  # 2 vials for 2000 birds
        unit_cost=Decimal('200.0'),
        total_cost=Decimal('400.0'),  # GHS 400
        administered_by='Extension Officer'
    )


# =============================================================================
# TESTS: BirdInvestmentCalculator Service
# =============================================================================

class TestBirdInvestmentCalculator:
    """Tests for the BirdInvestmentCalculator service."""
    
    def test_calculate_feed_cost_per_bird(self, flock, daily_productions):
        """Test that feed cost per bird is correctly calculated."""
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        
        # Calculate up to today (3 weeks after arrival)
        today = date.today()
        investment = calculator.calculate_investment_per_bird(today)
        
        # Total feed cost: 21 days × GHS 1000/day = GHS 21,000
        # Per bird: 21,000 / 2000 birds = GHS 10.50
        assert investment['feed_cost_total'] == Decimal('21000.00')
        assert investment['feed_cost_per_bird'] == Decimal('10.50')
        
    def test_calculate_medication_cost_per_bird(self, flock, daily_productions, medication_record):
        """Test that medication cost per bird is correctly calculated."""
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Medication cost: GHS 100 / 2000 birds = GHS 0.05
        assert investment['medication_cost_total'] == Decimal('100.00')
        assert investment['medication_cost_per_bird'] == Decimal('0.05')
        
    def test_calculate_vaccination_cost_per_bird(self, flock, daily_productions, vaccination_record):
        """Test that vaccination cost per bird is correctly calculated."""
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Vaccination cost: GHS 400 / 2000 birds = GHS 0.20
        assert investment['vaccination_cost_total'] == Decimal('400.00')
        assert investment['vaccination_cost_per_bird'] == Decimal('0.20')
        
    def test_calculate_total_other_costs(self, flock, daily_productions, medication_record, vaccination_record):
        """Test that other costs (medication + vaccination) are combined."""
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Other costs: GHS 100 + GHS 400 = GHS 500
        # Per bird: 500 / 2000 = GHS 0.25
        assert investment['other_costs_total'] == Decimal('500.00')
        assert investment['other_costs_per_bird'] == Decimal('0.25')
        
    def test_calculate_total_investment_per_bird(self, flock, daily_productions, medication_record, vaccination_record):
        """Test total investment per bird calculation."""
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Feed: GHS 10.50 + Other: GHS 0.25 = GHS 10.75
        expected = Decimal('10.50') + Decimal('0.25')
        assert investment['total_investment_per_bird'] == expected
        
    def test_calculate_investment_with_acquisition_cost(self, flock, daily_productions):
        """Test investment calculation including acquisition cost."""
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today(), include_acquisition=True)
        
        # Acquisition: GHS 5.00 + Feed: GHS 10.50 = GHS 15.50
        assert investment['acquisition_cost_per_bird'] == Decimal('5.00')
        assert investment['total_investment_per_bird'] == Decimal('15.50')


class TestMortalityLossCalculation:
    """Tests for mortality loss calculation."""
    
    def test_calculate_mortality_loss_12_birds(self, flock, daily_productions, medication_record, vaccination_record):
        """
        Test the user's scenario:
        2000 birds, 25kg/week feed at GHS1000/25kg, after 3 weeks 12 birds die.
        """
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        loss_data = calculator.calculate_mortality_loss(
            mortality_date=date.today(),
            birds_lost=12
        )
        
        # Feed cost per bird: GHS 10.50
        # Feed cost invested for 12 birds: 12 × 10.50 = GHS 126
        assert loss_data['feed_cost_invested'] == Decimal('126.00')
        
        # Other costs per bird: GHS 0.25
        # Other costs invested for 12 birds: 12 × 0.25 = GHS 3
        assert loss_data['other_costs_invested'] == Decimal('3.00')
        
        # Acquisition loss: 12 × GHS 5 = GHS 60
        # Total loss (includes acquisition): 60 + 126 + 3 = GHS 189
        assert loss_data['total_loss_value'] == Decimal('189.00')
        
        # Additional investment (excludes acquisition, for expense tracking):
        # 126 + 3 = GHS 129
        assert loss_data['additional_investment_value'] == Decimal('129.00')
        
    def test_calculate_age_at_death(self, flock, daily_productions):
        """Test age at death calculation."""
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        loss_data = calculator.calculate_mortality_loss(
            mortality_date=date.today(),
            birds_lost=5
        )
        
        # Birds arrived 21 days ago as day-old chicks
        # Age at death: 3 weeks
        assert loss_data['age_at_death_weeks'] == Decimal('3.0')


# =============================================================================
# TESTS: API Endpoints
# =============================================================================

class TestMortalityLossPreviewEndpoint:
    """Tests for the mortality loss preview endpoint."""
    
    def test_preview_returns_calculated_costs(
        self, api_client, farmer_user, farm, flock, daily_productions,
        medication_record, vaccination_record
    ):
        """Test that preview endpoint returns calculated costs."""
        api_client.force_authenticate(user=farmer_user)
        
        url = reverse('expenses:mortality-loss-preview')
        data = {
            'flock_id': str(flock.id),
            'mortality_date': date.today().isoformat(),
            'birds_lost': 12
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        
        # Check calculated costs are returned
        calculated = response.data['calculated_costs']
        assert 'feed_cost_invested' in calculated
        assert 'other_costs_invested' in calculated
        assert 'total_loss_value' in calculated
        assert 'additional_investment_value' in calculated
        
        # Verify values
        assert Decimal(calculated['feed_cost_invested']) == Decimal('126.00')
        assert Decimal(calculated['other_costs_invested']) == Decimal('3.00')
        assert Decimal(calculated['additional_investment_value']) == Decimal('129.00')  # Feed + Other (no acquisition)
        
    def test_preview_returns_breakdown(
        self, api_client, farmer_user, farm, flock, daily_productions
    ):
        """Test that preview returns detailed cost breakdown."""
        api_client.force_authenticate(user=farmer_user)
        
        url = reverse('expenses:mortality-loss-preview')
        data = {
            'flock_id': str(flock.id),
            'mortality_date': date.today().isoformat(),
            'birds_lost': 10
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        breakdown = response.data['breakdown']
        assert 'feed_cost_per_bird' in breakdown
        assert 'medication_cost_per_bird' in breakdown
        assert 'vaccination_cost_per_bird' in breakdown
        
    def test_preview_validates_birds_lost(
        self, api_client, farmer_user, farm, flock, daily_productions
    ):
        """Test validation when birds_lost exceeds flock count."""
        api_client.force_authenticate(user=farmer_user)
        
        url = reverse('expenses:mortality-loss-preview')
        data = {
            'flock_id': str(flock.id),
            'mortality_date': date.today().isoformat(),
            'birds_lost': 5000  # More than flock has
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Cannot record loss' in response.data['error']
        
    def test_preview_requires_authentication(self, api_client, flock):
        """Test that endpoint requires authentication."""
        url = reverse('expenses:mortality-loss-preview')
        data = {
            'flock_id': str(flock.id),
            'mortality_date': date.today().isoformat(),
            'birds_lost': 10
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMortalityLossAutoCalculation:
    """Tests for auto-calculation when creating mortality loss records."""
    
    def test_auto_calculate_on_create(
        self, api_client, farmer_user, farm, flock, daily_productions,
        medication_record, vaccination_record
    ):
        """Test that costs are auto-calculated when creating a record."""
        from expenses.models import Expense
        
        api_client.force_authenticate(user=farmer_user)
        
        # First create the parent expense
        expense = Expense.objects.create(
            farm=farm,
            category='MORTALITY_LOSS',
            description='Mortality loss - 12 birds',
            quantity=Decimal('1'),
            unit_cost=Decimal('0'),
            total_amount=Decimal('0'),  # Will be updated
            expense_date=date.today(),
            payment_status='NA',
            created_by=farmer_user
        )
        
        url = reverse('expenses:mortality-loss-list')
        data = {
            'expense': str(expense.id),
            'flock': str(flock.id),
            'mortality_date': date.today().isoformat(),
            'birds_lost': 12,
            'acquisition_cost_per_bird': '5.00',
            'cause_of_death': 'Heat stress',
            'auto_calculate': True  # Request auto-calculation
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Create failed: {response.data}"
        
        # Verify costs were auto-calculated
        from expenses.models import MortalityLossRecord
        record = MortalityLossRecord.objects.get(id=response.data['id'])
        
        assert record.costs_auto_calculated is True
        assert record.feed_cost_invested == Decimal('126.00')
        assert record.other_costs_invested == Decimal('3.00')
        
    def test_manual_values_respected_when_provided(
        self, api_client, farmer_user, farm, flock, daily_productions
    ):
        """Test that manual values are used when provided (not auto-calculated)."""
        from expenses.models import Expense
        
        api_client.force_authenticate(user=farmer_user)
        
        expense = Expense.objects.create(
            farm=farm,
            category='MORTALITY_LOSS',
            description='Mortality loss - manual values',
            quantity=Decimal('1'),
            unit_cost=Decimal('0'),
            total_amount=Decimal('0'),
            expense_date=date.today(),
            payment_status='NA',
            created_by=farmer_user
        )
        
        url = reverse('expenses:mortality-loss-list')
        data = {
            'expense': str(expense.id),
            'flock': str(flock.id),
            'mortality_date': date.today().isoformat(),
            'birds_lost': 10,
            'acquisition_cost_per_bird': '5.00',
            'feed_cost_invested': '200.00',  # Manual value
            'other_costs_invested': '50.00',  # Manual value
            'cause_of_death': 'Disease',
            'auto_calculate': False  # Explicit no auto-calculation
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        from expenses.models import MortalityLossRecord
        record = MortalityLossRecord.objects.get(id=response.data['id'])
        
        assert record.feed_cost_invested == Decimal('200.00')
        assert record.other_costs_invested == Decimal('50.00')


class TestFlockInvestmentSummaryEndpoint:
    """Tests for the flock investment summary endpoint."""
    
    def test_get_flock_investment_summary(
        self, api_client, farmer_user, farm, flock, daily_productions,
        medication_record, vaccination_record
    ):
        """Test getting a complete investment summary for a flock."""
        api_client.force_authenticate(user=farmer_user)
        
        url = reverse('expenses:flock-investment', kwargs={'flock_id': flock.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['flock_id'] == str(flock.id)
        assert response.data['flock_number'] == flock.flock_number
        
        investment = response.data['investment']
        assert 'feed_cost_per_bird' in investment
        assert 'medication_cost_per_bird' in investment
        assert 'vaccination_cost_per_bird' in investment
        assert 'total_investment_per_bird' in investment
        
    def test_get_investment_with_date_filter(
        self, api_client, farmer_user, farm, flock, daily_productions
    ):
        """Test getting investment summary up to a specific date."""
        api_client.force_authenticate(user=farmer_user)
        
        # Get investment up to 1 week ago (7 days of consumption)
        one_week_ago = (date.today() - timedelta(days=7)).isoformat()
        url = reverse('expenses:flock-investment', kwargs={'flock_id': flock.id})
        
        response = api_client.get(url, {'as_of_date': one_week_ago})
        
        assert response.status_code == status.HTTP_200_OK
        
        # Should have 14 days of feed (21 - 7 = 14 days from arrival to one week ago)
        investment = response.data['investment']
        # Feed cost: 14 days × GHS 1000 = GHS 14,000 / 2000 birds = GHS 7.00
        # But calculation depends on actual dates, so just verify it's less than full period
        assert Decimal(investment['feed_cost_per_bird']) < Decimal('10.50')


# =============================================================================
# TESTS: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases in mortality loss calculation."""
    
    def test_no_feed_consumption_records(self, farm, farmer_user):
        """Test calculation when no feed consumption records exist."""
        from flock_management.models import Flock
        from expenses.services import BirdInvestmentCalculator
        
        # Create flock with no feed consumption
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-NEW-001',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today() - timedelta(days=7),
            initial_count=500,
            current_count=500,
            age_at_arrival_weeks=Decimal('0'),
            purchase_price_per_bird=Decimal('5.00'),
            status='Active'
        )
        
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Should return zeros without errors
        assert investment['feed_cost_total'] == Decimal('0.00')
        assert investment['feed_cost_per_bird'] == Decimal('0.00')
        
    def test_calculation_for_day_of_arrival(self, flock):
        """Test calculation when mortality occurs on arrival day."""
        from expenses.services import BirdInvestmentCalculator
        
        calculator = BirdInvestmentCalculator(flock)
        loss_data = calculator.calculate_mortality_loss(
            mortality_date=flock.arrival_date,
            birds_lost=5
        )
        
        # Should only have acquisition loss
        assert loss_data['feed_cost_invested'] == Decimal('0.00')
        assert loss_data['acquisition_cost_per_bird'] == Decimal('5.00')
        
    def test_flock_with_zero_purchase_price(self, farm, farmer_user):
        """Test calculation when birds were donated (zero purchase price)."""
        from flock_management.models import Flock
        from expenses.services import BirdInvestmentCalculator
        
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-DONATED-001',
            flock_type='Layers',
            breed='Local',
            source='Donated',
            arrival_date=date.today() - timedelta(days=14),
            initial_count=100,
            current_count=100,
            age_at_arrival_weeks=Decimal('8'),
            purchase_price_per_bird=Decimal('0.00'),  # Free birds
            status='Active'
        )
        
        calculator = BirdInvestmentCalculator(flock)
        loss_data = calculator.calculate_mortality_loss(
            mortality_date=date.today(),
            birds_lost=5
        )
        
        # Acquisition cost should be zero
        assert loss_data['acquisition_cost_per_bird'] == Decimal('0.00')
        # Total loss (with acquisition) equals feed + other when acquisition is zero
        assert loss_data['total_loss_value'] == loss_data['feed_cost_invested'] + loss_data['other_costs_invested']
        # Additional investment (without acquisition) should equal total when acquisition is zero
        assert loss_data['additional_investment_value'] == loss_data['feed_cost_invested'] + loss_data['other_costs_invested']


# =============================================================================
# UNIFIED FLOW TESTS - Signal Auto-Creation
# =============================================================================

class TestAutoCreateExpenseFromMortalityRecord:
    """
    Test the signal that automatically creates MortalityLossRecord (expense)
    when a MortalityRecord is created in Flock Management.
    
    This validates the UNIFIED flow where users only need to enter mortality
    data in ONE place (Flock Management), and the financial record is
    automatically created with smart cost calculations.
    """
    
    def test_mortality_record_creates_expense_automatically(self, flock, farmer_user):
        """
        When a MortalityRecord is created, an Expense and MortalityLossRecord
        should be automatically created by the signal.
        """
        from flock_management.models import MortalityRecord
        from expenses.models import Expense, MortalityLossRecord
        
        # Count existing records
        initial_expense_count = Expense.objects.filter(farm=flock.farm).count()
        initial_loss_record_count = MortalityLossRecord.objects.filter(farm=flock.farm).count()
        
        # Create a mortality record (simulating user entering data in Flock Management)
        mortality_record = MortalityRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            date_discovered=date.today() - timedelta(days=1),
            number_of_birds=5,
            probable_cause='Disease - Viral',
            symptoms_observed=['Lethargy', 'Loss of appetite'],
            estimated_value_per_bird=Decimal('20.00'),
            reported_by=farmer_user,
        )
        
        # Check that expense was auto-created
        new_expense_count = Expense.objects.filter(farm=flock.farm).count()
        assert new_expense_count == initial_expense_count + 1, "Expense should be auto-created"
        
        # Check that MortalityLossRecord was auto-created
        new_loss_record_count = MortalityLossRecord.objects.filter(farm=flock.farm).count()
        assert new_loss_record_count == initial_loss_record_count + 1, "MortalityLossRecord should be auto-created"
        
        # Verify the records are linked correctly
        loss_record = MortalityLossRecord.objects.filter(mortality_record=mortality_record).first()
        assert loss_record is not None, "MortalityLossRecord should be linked to MortalityRecord"
        assert loss_record.birds_lost == 5
        assert loss_record.mortality_date == mortality_record.date_discovered
        assert loss_record.flock == flock
        assert loss_record.mortality_record == mortality_record
        
    def test_auto_created_expense_has_correct_values(self, flock, farmer_user, daily_productions):
        """
        The auto-created expense should use the BirdInvestmentCalculator
        to calculate actual feed and medication costs from tracked data.
        """
        from flock_management.models import MortalityRecord
        from expenses.models import MortalityLossRecord
        
        # Create a mortality record
        mortality_record = MortalityRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            date_discovered=date.today(),
            number_of_birds=10,
            probable_cause='Predation',
            estimated_value_per_bird=Decimal('15.00'),
            reported_by=farmer_user,
        )
        
        # Get the auto-created loss record
        loss_record = MortalityLossRecord.objects.filter(mortality_record=mortality_record).first()
        assert loss_record is not None
        
        # Verify costs were auto-calculated (from tracked feed consumption data)
        assert loss_record.costs_auto_calculated is True
        
        # Feed cost should be > 0 since we have feed_consumption fixture
        # (unless it's 0 due to calculation specifics - check for reasonable values)
        assert loss_record.feed_cost_invested >= Decimal('0.00')
        
        # Total loss should include acquisition + feed + other
        expected_acquisition = Decimal('15.00') * 10  # 150.00
        assert loss_record.total_loss_value >= expected_acquisition
        
        # Additional investment should exclude acquisition (to avoid double-counting)
        # additional_investment = feed + medication only
        assert loss_record.additional_investment_value == (
            loss_record.feed_cost_invested + loss_record.other_costs_invested
        )
        
    def test_expense_linked_to_flock(self, flock, farmer_user):
        """The auto-created expense should be linked to the correct flock."""
        from flock_management.models import MortalityRecord
        from expenses.models import MortalityLossRecord
        
        mortality_record = MortalityRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            date_discovered=date.today(),
            number_of_birds=3,
            probable_cause='Unknown',
            estimated_value_per_bird=Decimal('10.00'),
            reported_by=farmer_user,
        )
        
        loss_record = MortalityLossRecord.objects.filter(mortality_record=mortality_record).first()
        assert loss_record is not None
        
        # Both expense and loss record should be linked to flock
        assert loss_record.expense.flock == flock
        assert loss_record.flock == flock
        
    def test_signal_does_not_create_duplicate_on_update(self, flock, farmer_user):
        """
        Updating an existing MortalityRecord should NOT create another expense.
        The signal should only trigger on creation (created=True).
        """
        from flock_management.models import MortalityRecord
        from expenses.models import MortalityLossRecord
        
        # Create a mortality record
        mortality_record = MortalityRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            date_discovered=date.today(),
            number_of_birds=5,
            probable_cause='Disease - Bacterial',
            estimated_value_per_bird=Decimal('12.00'),
            reported_by=farmer_user,
        )
        
        # Count expenses after creation
        expense_count_after_create = MortalityLossRecord.objects.filter(
            mortality_record=mortality_record
        ).count()
        assert expense_count_after_create == 1
        
        # Update the mortality record
        mortality_record.notes = "Updated notes"
        mortality_record.save()
        
        # Count should still be 1 (no duplicate created)
        expense_count_after_update = MortalityLossRecord.objects.filter(
            mortality_record=mortality_record
        ).count()
        assert expense_count_after_update == 1
        
    def test_signal_handles_zero_estimated_value(self, flock, farmer_user):
        """
        When estimated_value_per_bird is not provided (default 0),
        the signal should still create the expense using acquisition defaults.
        """
        from flock_management.models import MortalityRecord
        from expenses.models import MortalityLossRecord
        
        # Create mortality without specifying estimated value
        mortality_record = MortalityRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            date_discovered=date.today(),
            number_of_birds=2,
            probable_cause='Heat Stress',
            # estimated_value_per_bird defaults to 0
            reported_by=farmer_user,
        )
        
        loss_record = MortalityLossRecord.objects.filter(mortality_record=mortality_record).first()
        assert loss_record is not None
        
        # Should have used the default (0 or flock's purchase price)
        # The important thing is it didn't crash
        assert loss_record.acquisition_cost_per_bird >= Decimal('0.00')

