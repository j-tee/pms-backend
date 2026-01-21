"""
Tests for Health Record Auto-Sync to Detailed Records.

Tests the automatic creation of MedicationRecord, VaccinationRecord, and VetVisit
when a HealthRecord is created. This ensures the unified data entry flow works
correctly and prevents double-counting of health costs.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
import uuid

pytestmark = pytest.mark.django_db


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def farmer_user(django_user_model):
    """Create a farmer user."""
    user = django_user_model.objects.create_user(
        username='health_test_farmer',
        email='health_farmer@test.com',
        password='testpass123',
        role='FARMER',
        phone='+233501234999'
    )
    return user


@pytest.fixture
def farm(farmer_user):
    """Create a farm for testing."""
    from farms.models import Farm
    
    unique_id = uuid.uuid4().hex[:8]
    
    farm = Farm.objects.create(
        user=farmer_user,
        first_name='Health',
        last_name='Tester',
        date_of_birth='1985-06-15',
        gender='Male',
        ghana_card_number=f'GHA-{unique_id.upper()}-H',
        primary_phone='+233501234999',
        residential_address='Health Farm, Accra',
        primary_constituency='Ablekuma South',
        nok_full_name='Test NOK',
        nok_relationship='Spouse',
        nok_phone='+233241000001',
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=5,
        farm_name='Health Test Farm',
        ownership_type='Sole Proprietorship',
        tin=f'H{unique_id.upper()}',
        number_of_poultry_houses=2,
        total_bird_capacity=5000,
        current_bird_count=2000,
        housing_type='Deep Litter',
        total_infrastructure_value_ghs=Decimal('50000.00'),
        primary_production_type='Layers',
        layer_breed='Isa Brown',
        planned_monthly_egg_production=30000,
        planned_production_start_date=timezone.now().date() + timedelta(days=30),
        initial_investment_amount=Decimal('50000.00'),
        funding_source=['Personal Savings'],
        monthly_operating_budget=Decimal('10000.00'),
        expected_monthly_revenue=Decimal('15000.00'),
        application_status='Approved',
        farm_status='Active',
    )
    farmer_user.farm = farm
    farmer_user.save()
    return farm


@pytest.fixture
def flock(farm):
    """Create a flock for testing."""
    from flock_management.models import Flock
    
    return Flock.objects.create(
        farm=farm,
        flock_number='FLOCK-HEALTH-001',
        flock_type='Layers',
        breed='Isa Brown',
        source='Purchased',
        arrival_date=date.today() - timedelta(days=30),
        initial_count=1000,
        current_count=980,
        age_at_arrival_weeks=Decimal('8'),
        purchase_price_per_bird=Decimal('5.00'),
        status='Active'
    )


# =============================================================================
# VACCINATION RECORD AUTO-CREATION TESTS
# =============================================================================

class TestVaccinationRecordAutoCreation:
    """Tests for automatic VaccinationRecord creation from HealthRecord."""
    
    def test_vaccination_health_record_creates_vaccination_record(self, flock):
        """When HealthRecord with record_type='Vaccination' is created, a VaccinationRecord should be auto-created."""
        from flock_management.models import HealthRecord
        from medication_management.models import VaccinationRecord
        
        # Count before
        initial_count = VaccinationRecord.objects.filter(flock=flock).count()
        
        # Create a vaccination health record
        health_record = HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Vaccination',
            treatment_name='Newcastle Disease Vaccine',
            dosage='1 drop per eye',
            treatment_method='Eye Drop',
            birds_affected=980,
            cost_ghs=Decimal('150.00'),
            administering_person='Farm Manager',
            vet_name='Dr. Kwame',
            vet_license='VET-GH-12345',
            notes='Routine vaccination',
        )
        
        # Refresh to get updated FK links
        health_record.refresh_from_db()
        
        # Should have created a VaccinationRecord
        new_count = VaccinationRecord.objects.filter(flock=flock).count()
        assert new_count == initial_count + 1, "VaccinationRecord should be auto-created"
        
        # Should be linked to health record
        assert health_record.vaccination_record is not None
        
        # Verify the data was mapped correctly
        vacc_record = health_record.vaccination_record
        assert vacc_record.flock == flock
        assert vacc_record.farm == flock.farm
        assert vacc_record.vaccination_date == health_record.record_date
        assert vacc_record.total_cost == Decimal('150.00')
        assert vacc_record.birds_vaccinated == 980
        
    def test_vaccination_record_medication_type_created(self, flock):
        """A MedicationType should be created if it doesn't exist."""
        from flock_management.models import HealthRecord
        from medication_management.models import MedicationType
        
        unique_vaccine_name = f'Test Vaccine {uuid.uuid4().hex[:6]}'
        
        # Ensure it doesn't exist
        assert not MedicationType.objects.filter(name=unique_vaccine_name).exists()
        
        # Create health record
        HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Vaccination',
            treatment_name=unique_vaccine_name,
            dosage='1ml per bird',
            birds_affected=100,
            cost_ghs=Decimal('50.00'),
        )
        
        # MedicationType should now exist
        assert MedicationType.objects.filter(name=unique_vaccine_name).exists()
        med_type = MedicationType.objects.get(name=unique_vaccine_name)
        assert med_type.category == 'VACCINE'


# =============================================================================
# MEDICATION RECORD AUTO-CREATION TESTS
# =============================================================================

class TestMedicationRecordAutoCreation:
    """Tests for automatic MedicationRecord creation from HealthRecord."""
    
    def test_medication_health_record_creates_medication_record(self, flock):
        """When HealthRecord with record_type='Medication' is created, a MedicationRecord should be auto-created."""
        from flock_management.models import HealthRecord
        from medication_management.models import MedicationRecord
        
        # Count before
        initial_count = MedicationRecord.objects.filter(flock=flock).count()
        
        # Create a medication health record
        health_record = HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Medication',
            treatment_name='Amoxicillin',
            dosage='5g per liter of water',
            treatment_method='Oral',
            disease='Respiratory Infection',
            symptoms='Sneezing, nasal discharge',
            birds_affected=50,
            cost_ghs=Decimal('75.00'),
            vet_name='Dr. Ama',
            notes='Treatment for CRD',
        )
        
        # Refresh to get updated FK links
        health_record.refresh_from_db()
        
        # Should have created a MedicationRecord
        new_count = MedicationRecord.objects.filter(flock=flock).count()
        assert new_count == initial_count + 1, "MedicationRecord should be auto-created"
        
        # Should be linked to health record
        assert health_record.medication_record is not None
        
        # Verify the data was mapped correctly
        med_record = health_record.medication_record
        assert med_record.flock == flock
        assert med_record.farm == flock.farm
        assert med_record.administered_date == health_record.record_date
        assert med_record.total_cost == Decimal('75.00')
        assert med_record.birds_treated == 50
        assert 'Respiratory Infection' in med_record.notes
        
    def test_medication_category_inferred_from_disease(self, flock):
        """MedicationType category should be inferred from disease description."""
        from flock_management.models import HealthRecord
        from medication_management.models import MedicationType
        
        # Create health record for worm treatment
        health_record = HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Medication',
            treatment_name='Dewormer Treatment',
            disease='Internal worms/parasites',
            birds_affected=100,
            cost_ghs=Decimal('30.00'),
        )
        
        health_record.refresh_from_db()
        
        # Should have created/linked to a DEWORMER type
        med_type = health_record.medication_record.medication_type
        assert med_type.category == 'DEWORMER'


# =============================================================================
# VET VISIT AUTO-CREATION TESTS
# =============================================================================

class TestVetVisitAutoCreation:
    """Tests for automatic VetVisit creation from HealthRecord."""
    
    def test_health_check_creates_vet_visit(self, flock):
        """When HealthRecord with record_type='Health Check' is created, a VetVisit should be auto-created."""
        from flock_management.models import HealthRecord
        from medication_management.models import VetVisit
        
        # Count before
        initial_count = VetVisit.objects.filter(flock=flock).count()
        
        # Create a health check record
        health_record = HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Health Check',
            vet_name='Dr. Kofi',
            vet_license='VET-GH-99999',
            diagnosis='Healthy flock',
            outcome='No issues found',
            cost_ghs=Decimal('200.00'),
            follow_up_date=date.today() + timedelta(days=30),
            notes='Routine monthly inspection',
        )
        
        # Refresh to get updated FK links
        health_record.refresh_from_db()
        
        # Should have created a VetVisit
        new_count = VetVisit.objects.filter(flock=flock).count()
        assert new_count == initial_count + 1, "VetVisit should be auto-created"
        
        # Should be linked to health record
        assert health_record.vet_visit is not None
        
        # Verify the data was mapped correctly
        vet_visit = health_record.vet_visit
        assert vet_visit.farm == flock.farm
        assert vet_visit.flock == flock
        assert vet_visit.visit_date == health_record.record_date
        assert vet_visit.visit_fee == Decimal('200.00')
        assert vet_visit.veterinarian_name == 'Dr. Kofi'
        assert vet_visit.vet_license_number == 'VET-GH-99999'
        assert vet_visit.status == 'COMPLETED'
        assert vet_visit.follow_up_required is True
        assert vet_visit.follow_up_date == health_record.follow_up_date
        
    def test_vet_visit_type_creates_vet_visit(self, flock):
        """HealthRecord with record_type='Vet Visit' should also create VetVisit."""
        from flock_management.models import HealthRecord
        from medication_management.models import VetVisit
        
        health_record = HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Vet Visit',
            vet_name='Dr. Yaa',
            cost_ghs=Decimal('150.00'),
            disease='Suspected Gumboro',
            notes='Emergency call',
        )
        
        health_record.refresh_from_db()
        
        assert health_record.vet_visit is not None
        assert health_record.vet_visit.visit_type == 'DISEASE_INVESTIGATION'


# =============================================================================
# EDGE CASES AND PREVENTION TESTS
# =============================================================================

class TestHealthRecordSyncEdgeCases:
    """Tests for edge cases and double-counting prevention."""
    
    def test_zero_cost_does_not_create_detailed_record(self, flock):
        """HealthRecord with zero cost should NOT create detailed records (nothing to track financially)."""
        from flock_management.models import HealthRecord
        from medication_management.models import VaccinationRecord
        
        initial_count = VaccinationRecord.objects.filter(flock=flock).count()
        
        # Create health record with zero cost
        health_record = HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Vaccination',
            treatment_name='Free Government Vaccine',
            birds_affected=1000,
            cost_ghs=Decimal('0.00'),  # Zero cost
        )
        
        health_record.refresh_from_db()
        
        # Should NOT have created a detailed record
        new_count = VaccinationRecord.objects.filter(flock=flock).count()
        assert new_count == initial_count, "Zero-cost records should not create detailed records"
        assert health_record.vaccination_record is None
        
    def test_update_does_not_create_duplicate(self, flock):
        """Updating a HealthRecord should NOT create another detailed record."""
        from flock_management.models import HealthRecord
        from medication_management.models import VaccinationRecord
        
        # Create health record
        health_record = HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Vaccination',
            treatment_name='Test Vaccine',
            birds_affected=100,
            cost_ghs=Decimal('50.00'),
        )
        
        health_record.refresh_from_db()
        count_after_create = VaccinationRecord.objects.filter(flock=flock).count()
        original_vacc_id = health_record.vaccination_record_id
        
        # Update the health record
        health_record.notes = 'Updated notes'
        health_record.save()
        
        # Should still have same count (no duplicate)
        count_after_update = VaccinationRecord.objects.filter(flock=flock).count()
        assert count_after_update == count_after_create
        
        # Should still point to same vaccination record
        health_record.refresh_from_db()
        assert health_record.vaccination_record_id == original_vacc_id
        
    def test_already_linked_record_not_duplicated(self, flock):
        """If HealthRecord already has a linked detailed record, don't create another."""
        from flock_management.models import HealthRecord
        from medication_management.models import VaccinationRecord, MedicationType
        
        # Pre-create a vaccination record
        med_type = MedicationType.objects.create(
            name='Pre-existing Vaccine',
            category='VACCINE',
            administration_route='INJECTION_SC',
            dosage='0.5ml per bird',
            indication='Prevention',
        )
        
        pre_existing_vacc = VaccinationRecord.objects.create(
            flock=flock,
            farm=flock.farm,
            medication_type=med_type,
            vaccination_date=date.today(),
            birds_vaccinated=100,
            flock_age_weeks=10,
            dosage_per_bird='0.5ml',
            administration_route='Injection',
            batch_number='BATCH-001',
            expiry_date=date.today() + timedelta(days=365),
            quantity_used=Decimal('100'),
            unit_cost=Decimal('1.00'),
            total_cost=Decimal('100.00'),
            administered_by='Test',
        )
        
        count_before = VaccinationRecord.objects.filter(flock=flock).count()
        
        # Create health record already linked to the vaccination record
        health_record = HealthRecord(
            farm=flock.farm,
            flock=flock,
            record_date=date.today(),
            record_type='Vaccination',
            treatment_name='Pre-existing Vaccine',
            birds_affected=100,
            cost_ghs=Decimal('100.00'),
            vaccination_record=pre_existing_vacc,  # Already linked!
        )
        health_record.save()
        
        # Should NOT have created another record
        count_after = VaccinationRecord.objects.filter(flock=flock).count()
        assert count_after == count_before


# =============================================================================
# BIRD INVESTMENT CALCULATOR INTEGRATION TEST
# =============================================================================

class TestBirdInvestmentCalculatorIntegration:
    """Test that auto-created records work with BirdInvestmentCalculator."""
    
    def test_auto_created_vaccination_included_in_calculator(self, flock):
        """Auto-created VaccinationRecord should be included in BirdInvestmentCalculator."""
        from flock_management.models import HealthRecord
        from expenses.services import BirdInvestmentCalculator
        
        # Create vaccination via HealthRecord
        HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today() - timedelta(days=5),
            record_type='Vaccination',
            treatment_name='NCD Vaccine',
            birds_affected=980,
            cost_ghs=Decimal('200.00'),
        )
        
        # Calculate investment using BirdInvestmentCalculator
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Vaccination cost should be included
        assert investment['vaccination_cost_total'] >= Decimal('200.00')
        assert investment['vaccination_records_count'] >= 1
        
    def test_auto_created_medication_included_in_calculator(self, flock):
        """Auto-created MedicationRecord should be included in BirdInvestmentCalculator."""
        from flock_management.models import HealthRecord
        from expenses.services import BirdInvestmentCalculator
        
        # Create medication via HealthRecord
        HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today() - timedelta(days=3),
            record_type='Medication',
            treatment_name='Antibiotic Treatment',
            birds_affected=50,
            cost_ghs=Decimal('75.00'),
        )
        
        # Calculate investment
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Medication cost should be included
        assert investment['medication_cost_total'] >= Decimal('75.00')
        assert investment['medication_records_count'] >= 1
    
    def test_auto_created_vet_visit_included_in_calculator(self, flock):
        """Auto-created VetVisit should be included in BirdInvestmentCalculator."""
        from flock_management.models import HealthRecord
        from expenses.services import BirdInvestmentCalculator
        
        # Create health check via HealthRecord (triggers VetVisit creation)
        HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today() - timedelta(days=2),
            record_type='Health Check',
            notes='Routine inspection by vet',
            cost_ghs=Decimal('150.00'),
        )
        
        # Calculate investment
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Vet visit cost should be included
        assert investment['vet_visit_cost_total'] >= Decimal('150.00')
        assert investment['vet_visit_records_count'] >= 1
        # Should also be included in other_costs_total
        assert investment['other_costs_total'] >= Decimal('150.00')
    
    def test_vet_visit_from_vet_visit_record_type_included(self, flock):
        """VetVisit created from 'Vet Visit' record_type should be included in calculator."""
        from flock_management.models import HealthRecord
        from expenses.services import BirdInvestmentCalculator
        
        # Create vet visit via HealthRecord with explicit 'Vet Visit' type
        HealthRecord.objects.create(
            farm=flock.farm,
            flock=flock,
            record_date=date.today() - timedelta(days=1),
            record_type='Vet Visit',
            notes='Emergency consultation for respiratory issues',
            cost_ghs=Decimal('200.00'),
        )
        
        # Calculate investment
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(date.today())
        
        # Vet visit cost should be included
        assert investment['vet_visit_cost_total'] >= Decimal('200.00')
        assert investment['vet_visit_records_count'] >= 1

