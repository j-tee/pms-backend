"""
Comprehensive Test Suite for Medication Management Module

Tests all medication management models with focus on:
- Withdrawal period calculations
- Vaccination schedule compliance
- Batch tracking
- Cross-module integrations
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
from farms.models import Farm
from flock_management.models import Flock
from medication_management.models import (
    MedicationType, VaccinationSchedule, MedicationRecord,
    VaccinationRecord, VetVisit
)
from accounts.models import User


class TestMedicationManagementModule:
    """Test suite for Medication Management module."""
    
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
        self.farm = Farm.objects.filter(farm_name='Test Farm Med').first()
        if not self.farm:
            self.farm = Farm.objects.create(
                user=self.user,
                farm_name='Test Farm Med',
                first_name='Test',
                last_name='Farmer',
                date_of_birth=date(1990, 1, 1),
                gender='Male',
                ghana_card_number='GHA-987654321-0',
                marital_status='Single',
                primary_phone='+233207654321',
                preferred_contact_method='Phone Call',
                residential_address='Test Address Med',
                nok_full_name='Test Kin',
                nok_relationship='Sibling',
                nok_phone='+233207111111',
                nok_residential_address='Kin Address',
                education_level='Secondary',
                literacy_level='Can Read & Write',
                ownership_type='Sole Proprietorship',
                tin='9876543210',
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
        self.flock = Flock.objects.filter(flock_number='TEST-MED-001').first()
        if not self.flock:
            self.flock = Flock.objects.create(
                farm=self.farm,
                flock_number='TEST-MED-001',
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
    # MEDICATION TYPE TESTS
    # =========================================================================
    
    def test_medication_type_creation(self):
        """Test basic MedicationType creation."""
        med = MedicationType.objects.create(
            name='Test Antibiotic',
            category='ANTIBIOTIC',
            administration_route='ORAL',
            dosage='1ml per liter water',
            indication='Bacterial infections',
            withdrawal_period_days=7
        )
        assert med.is_active is True
        assert med.requires_prescription is False
        med.delete()
    
    def test_medication_type_withdrawal_validation(self):
        """Test withdrawal period requirements for antibiotics."""
        med = MedicationType(
            name='Zero Withdrawal Antibiotic',
            category='ANTIBIOTIC',
            administration_route='ORAL',
            dosage='1ml per liter',
            indication='Test',
            withdrawal_period_days=0,  # Should trigger warning
            egg_withdrawal_days=None,
            meat_withdrawal_days=None
        )
        try:
            med.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'withdrawal_period_days' in e.message_dict
    
    def test_vaccine_no_withdrawal(self):
        """Test that vaccines don't have withdrawal periods."""
        vaccine = MedicationType(
            name='Test Vaccine',
            category='VACCINE',
            administration_route='INJECTION_IM',
            dosage='0.3ml per bird',
            indication='Disease prevention',
            withdrawal_period_days=7  # Vaccines shouldn't have withdrawal
        )
        try:
            vaccine.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'withdrawal_period_days' in e.message_dict
    
    # =========================================================================
    # VACCINATION SCHEDULE TESTS
    # =========================================================================
    
    def test_vaccination_schedule_creation(self):
        """Test VaccinationSchedule creation."""
        vaccine = MedicationType.objects.create(
            name='Schedule Test Vaccine',
            category='VACCINE',
            administration_route='INJECTION_IM',
            dosage='0.3ml per bird',
            indication='Disease prevention'
        )
        
        schedule = VaccinationSchedule.objects.create(
            medication_type=vaccine,
            flock_type='LAYER',
            age_in_weeks=1,
            dosage_per_bird='0.3ml',
            disease_prevented='Newcastle Disease',
            is_mandatory=True,
            priority=9
        )
        
        assert schedule.is_active is True
        assert schedule.frequency == 'ONCE'
        
        schedule.delete()
        vaccine.delete()
    
    def test_vaccination_schedule_vaccine_only(self):
        """Test that only vaccines can be in schedules."""
        antibiotic = MedicationType.objects.create(
            name='Schedule Antibiotic Test',
            category='ANTIBIOTIC',
            administration_route='ORAL',
            dosage='1ml per liter',
            indication='Test',
            withdrawal_period_days=7
        )
        
        schedule = VaccinationSchedule(
            medication_type=antibiotic,  # Not a vaccine
            flock_type='LAYER',
            age_in_weeks=1,
            dosage_per_bird='1ml',
            disease_prevented='Test'
        )
        
        try:
            schedule.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'medication_type' in e.message_dict
        
        antibiotic.delete()
    
    # =========================================================================
    # MEDICATION RECORD TESTS
    # =========================================================================
    
    def test_medication_record_creation(self):
        """Test MedicationRecord creation with auto-calculations."""
        antibiotic = MedicationType.objects.create(
            name='Record Test Antibiotic',
            category='ANTIBIOTIC',
            administration_route='ORAL',
            dosage='1ml per liter',
            indication='Test',
            withdrawal_period_days=7
        )
        
        record = MedicationRecord.objects.create(
            flock=self.flock,
            farm=self.farm,
            medication_type=antibiotic,
            administered_date=date.today(),
            reason='TREATMENT',
            dosage_given='10ml',
            birds_treated=950,
            treatment_days=5,
            quantity_used=Decimal('50.00'),
            unit_cost=Decimal('5.00')
        )
        
        # Test auto-calculated fields
        assert record.total_cost == Decimal('250.00')
        assert record.end_date == date.today() + timedelta(days=4)
        assert record.withdrawal_end_date == date.today() + timedelta(days=11)  # end + 7
        assert record.farm == self.flock.farm
        
        record.delete()
        antibiotic.delete()
    
    def test_medication_record_bird_count_validation(self):
        """Test bird count validation."""
        antibiotic = MedicationType.objects.create(
            name='Bird Count Test',
            category='ANTIBIOTIC',
            administration_route='ORAL',
            dosage='1ml per liter',
            indication='Test',
            withdrawal_period_days=7
        )
        
        record = MedicationRecord(
            flock=self.flock,
            farm=self.farm,
            medication_type=antibiotic,
            administered_date=date.today(),
            reason='TREATMENT',
            dosage_given='10ml',
            birds_treated=1500,  # More than flock count (950)
            treatment_days=5,
            quantity_used=Decimal('50.00'),
            unit_cost=Decimal('5.00')
        )
        
        try:
            record.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'birds_treated' in e.message_dict
        
        antibiotic.delete()
    
    def test_medication_record_vaccine_rejection(self):
        """Test that vaccines cannot be in MedicationRecord."""
        vaccine = MedicationType.objects.create(
            name='Vaccine Rejection Test',
            category='VACCINE',
            administration_route='INJECTION_IM',
            dosage='0.3ml',
            indication='Test'
        )
        
        record = MedicationRecord(
            flock=self.flock,
            farm=self.farm,
            medication_type=vaccine,
            administered_date=date.today(),
            reason='PREVENTION',
            dosage_given='0.3ml',
            birds_treated=950,
            treatment_days=1,
            quantity_used=Decimal('300.00'),
            unit_cost=Decimal('1.00')
        )
        
        try:
            record.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'medication_type' in e.message_dict
        
        vaccine.delete()
    
    # =========================================================================
    # VACCINATION RECORD TESTS
    # =========================================================================
    
    def test_vaccination_record_creation(self):
        """Test VaccinationRecord creation."""
        vaccine = MedicationType.objects.create(
            name='Vacc Record Test',
            category='VACCINE',
            administration_route='INJECTION_IM',
            dosage='0.3ml',
            indication='Test'
        )
        
        record = VaccinationRecord.objects.create(
            flock=self.flock,
            farm=self.farm,
            medication_type=vaccine,
            vaccination_date=date.today(),
            birds_vaccinated=950,
            flock_age_weeks=20,
            dosage_per_bird='0.3ml',
            administration_route='IM Injection',
            batch_number='BATCH-2025-001',
            expiry_date=date.today() + timedelta(days=365),
            quantity_used=Decimal('950.00'),
            unit_cost=Decimal('0.50'),
            administered_by='Dr. Test'
        )
        
        assert record.total_cost == Decimal('475.00')
        assert record.farm == self.flock.farm
        
        record.delete()
        vaccine.delete()
    
    def test_vaccination_record_expired_vaccine(self):
        """Test expired vaccine validation."""
        vaccine = MedicationType.objects.create(
            name='Expired Vaccine Test',
            category='VACCINE',
            administration_route='INJECTION_IM',
            dosage='0.3ml',
            indication='Test'
        )
        
        record = VaccinationRecord(
            flock=self.flock,
            farm=self.farm,
            medication_type=vaccine,
            vaccination_date=date.today(),
            birds_vaccinated=950,
            flock_age_weeks=20,
            dosage_per_bird='0.3ml',
            administration_route='IM',
            batch_number='BATCH-EXPIRED',
            expiry_date=date.today() - timedelta(days=30),  # Expired
            quantity_used=Decimal('950.00'),
            unit_cost=Decimal('0.50'),
            administered_by='Dr. Test'
        )
        
        try:
            record.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'expiry_date' in e.message_dict
        
        vaccine.delete()
    
    def test_vaccination_record_mortality_validation(self):
        """Test mortality validation."""
        vaccine = MedicationType.objects.create(
            name='Mortality Test Vaccine',
            category='VACCINE',
            administration_route='INJECTION_IM',
            dosage='0.3ml',
            indication='Test'
        )
        
        record = VaccinationRecord(
            flock=self.flock,
            farm=self.farm,
            medication_type=vaccine,
            vaccination_date=date.today(),
            birds_vaccinated=950,
            flock_age_weeks=20,
            dosage_per_bird='0.3ml',
            administration_route='IM',
            batch_number='BATCH-001',
            expiry_date=date.today() + timedelta(days=365),
            quantity_used=Decimal('950.00'),
            unit_cost=Decimal('0.50'),
            administered_by='Dr. Test',
            mortality_within_24hrs=1000  # More than vaccinated
        )
        
        try:
            record.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'mortality_within_24hrs' in e.message_dict
        
        vaccine.delete()
    
    # =========================================================================
    # VET VISIT TESTS
    # =========================================================================
    
    def test_vet_visit_creation(self):
        """Test VetVisit creation."""
        visit = VetVisit.objects.create(
            farm=self.farm,
            flock=self.flock,
            visit_date=date.today(),
            visit_type='ROUTINE',
            status='COMPLETED',
            veterinarian_name='Dr. Test Vet',
            vet_license_number='VET-2025-001',
            purpose='Routine health inspection',
            findings='All birds healthy',
            compliance_status='COMPLIANT',
            visit_fee=Decimal('200.00')
        )
        
        assert visit.follow_up_required is False
        assert visit.certificate_issued is False
        
        visit.delete()
    
    def test_vet_visit_follow_up_validation(self):
        """Test follow-up date validation."""
        visit = VetVisit(
            farm=self.farm,
            visit_date=date.today(),
            visit_type='DISEASE_INVESTIGATION',
            status='COMPLETED',
            veterinarian_name='Dr. Test',
            vet_license_number='VET-001',
            purpose='Disease check',
            findings='Disease detected',
            follow_up_required=True
            # Missing follow_up_date
        )
        
        try:
            visit.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'follow_up_date' in e.message_dict
    
    def test_vet_visit_certificate_validation(self):
        """Test certificate number requirement."""
        visit = VetVisit(
            farm=self.farm,
            visit_date=date.today(),
            visit_type='COMPLIANCE_CHECK',
            status='COMPLETED',
            veterinarian_name='Dr. Test',
            vet_license_number='VET-001',
            purpose='Compliance check',
            findings='Compliant',
            certificate_issued=True
            # Missing certificate_number
        )
        
        try:
            visit.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'certificate_number' in e.message_dict
    
    def test_vet_visit_completed_validation(self):
        """Test that completed visits require findings."""
        visit = VetVisit(
            farm=self.farm,
            visit_date=date.today(),
            visit_type='ROUTINE',
            status='COMPLETED',
            veterinarian_name='Dr. Test',
            vet_license_number='VET-001',
            purpose='Check',
            findings=''  # Empty findings for completed visit
        )
        
        try:
            visit.full_clean()
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert 'findings' in e.message_dict
    
    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    
    def run_all_tests(self):
        """Execute all test cases."""
        print("\n" + "="*80)
        print("  MEDICATION MANAGEMENT MODULE TEST SUITE")
        print("="*80 + "\n")
        
        print("MedicationType Tests:")
        print("-" * 80)
        self.run_test("MedicationType: Basic Creation", self.test_medication_type_creation)
        self.run_test("MedicationType: Withdrawal Validation", self.test_medication_type_withdrawal_validation)
        self.run_test("MedicationType: Vaccine No Withdrawal", self.test_vaccine_no_withdrawal)
        
        print("\nVaccinationSchedule Tests:")
        print("-" * 80)
        self.run_test("VaccinationSchedule: Basic Creation", self.test_vaccination_schedule_creation)
        self.run_test("VaccinationSchedule: Vaccine Only", self.test_vaccination_schedule_vaccine_only)
        
        print("\nMedicationRecord Tests:")
        print("-" * 80)
        self.run_test("MedicationRecord: Basic Creation", self.test_medication_record_creation)
        self.run_test("MedicationRecord: Bird Count Validation", self.test_medication_record_bird_count_validation)
        self.run_test("MedicationRecord: Vaccine Rejection", self.test_medication_record_vaccine_rejection)
        
        print("\nVaccinationRecord Tests:")
        print("-" * 80)
        self.run_test("VaccinationRecord: Basic Creation", self.test_vaccination_record_creation)
        self.run_test("VaccinationRecord: Expired Vaccine", self.test_vaccination_record_expired_vaccine)
        self.run_test("VaccinationRecord: Mortality Validation", self.test_vaccination_record_mortality_validation)
        
        print("\nVetVisit Tests:")
        print("-" * 80)
        self.run_test("VetVisit: Basic Creation", self.test_vet_visit_creation)
        self.run_test("VetVisit: Follow-up Validation", self.test_vet_visit_follow_up_validation)
        self.run_test("VetVisit: Certificate Validation", self.test_vet_visit_certificate_validation)
        self.run_test("VetVisit: Completed Validation", self.test_vet_visit_completed_validation)
        
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
    tester = TestMedicationManagementModule()
    tester.run_all_tests()
