"""
Test script to verify data integrity validations in production tracking models.
Tests the enhanced clean() methods that prevent denormalized field mismatches.
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.exceptions import ValidationError
from farms.models import Farm, FarmLocation, PoultryHouse
from flock_management.models import Flock, DailyProduction, MortalityRecord
from accounts.models import User

print('')
print('═' * 80)
print('  DATA INTEGRITY VALIDATION TESTS')
print('═' * 80)
print('')

# Test counters
tests_run = 0
tests_passed = 0
tests_failed = 0

def test_validation(test_name, test_func):
    """Helper function to run validation tests"""
    global tests_run, tests_passed, tests_failed
    tests_run += 1
    
    try:
        test_func()
        tests_passed += 1
        print(f'  ✅ {test_name}')
        return True
    except AssertionError as e:
        tests_failed += 1
        print(f'  ❌ {test_name}')
        print(f'     Error: {e}')
        return False
    except Exception as e:
        tests_failed += 1
        print(f'  ❌ {test_name} (Unexpected error)')
        print(f'     Error: {e}')
        return False


# ============================================================================
# TEST 1: DailyProduction farm_id consistency validation
# ============================================================================

print('🧪 TEST GROUP 1: DailyProduction Validations')
print('─' * 80)

def test_daily_production_farm_mismatch():
    """Should reject when farm_id doesn't match flock.farm_id"""
    # Create test data (not saved to DB)
    user1 = User(email='farmer1@test.com', first_name='John', last_name='Doe')
    user2 = User(email='farmer2@test.com', first_name='Jane', last_name='Smith')
    
    farm1 = Farm(user=user1, first_name='John', last_name='Doe', 
                 ghana_card_number='GHA-123456789-1', primary_phone='+233201234567',
                 date_of_birth=date(1980, 1, 1), residential_address='Test Address',
                 education_level='SHS/Technical', nok_full_name='Test NOK',
                 nok_relationship='Spouse', nok_phone='+233201234568')
    
    farm2 = Farm(user=user2, first_name='Jane', last_name='Smith',
                 ghana_card_number='GHA-987654321-1', primary_phone='+233207654321',
                 date_of_birth=date(1985, 1, 1), residential_address='Test Address 2',
                 education_level='SHS/Technical', nok_full_name='Test NOK 2',
                 nok_relationship='Spouse', nok_phone='+233207654322')
    
    flock = Flock(
        farm=farm1,
        flock_number='TEST-001',
        flock_type='Layers',
        breed='Isa Brown',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=1000
    )
    
    # Create DailyProduction with WRONG farm
    daily = DailyProduction(
        farm=farm2,  # MISMATCH! Should be farm1
        flock=flock,
        production_date=date(2025, 1, 15),
        eggs_collected=0,
        good_eggs=0
    )
    
    # Should raise ValidationError
    try:
        daily.clean()
        raise AssertionError('Expected ValidationError for farm mismatch, but validation passed')
    except ValidationError as e:
        assert 'farm' in e.message_dict, 'Should have farm error'
        assert 'mismatch' in str(e).lower(), 'Error should mention mismatch'

test_validation(
    'DailyProduction rejects farm_id mismatch',
    test_daily_production_farm_mismatch
)


def test_daily_production_egg_breakdown():
    """Should reject when egg breakdown doesn't match total"""
    user = User(email='test@test.com', first_name='Test', last_name='User')
    farm = Farm(user=user, first_name='Test', last_name='User',
                ghana_card_number='GHA-111111111-1', primary_phone='+233200000000',
                date_of_birth=date(1980, 1, 1), residential_address='Test',
                education_level='SHS/Technical', nok_full_name='NOK',
                nok_relationship='Spouse', nok_phone='+233200000001')
    
    flock = Flock(
        farm=farm,
        flock_number='TEST-002',
        flock_type='Layers',
        breed='Isa Brown',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=1000
    )
    
    daily = DailyProduction(
        farm=farm,
        flock=flock,
        production_date=date(2025, 1, 15),
        eggs_collected=100,  # Total
        good_eggs=80,
        broken_eggs=10,
        dirty_eggs=5,
        small_eggs=3,  # Sum = 98, not 100!
        soft_shell_eggs=0
    )
    
    try:
        daily.clean()
        raise AssertionError('Expected ValidationError for egg breakdown mismatch')
    except ValidationError as e:
        assert 'eggs_collected' in e.message_dict

test_validation(
    'DailyProduction validates egg breakdown sum',
    test_daily_production_egg_breakdown
)


def test_daily_production_mortality_exceeds_count():
    """Should reject when birds_died exceeds current_count"""
    user = User(email='test3@test.com', first_name='Test', last_name='User')
    farm = Farm(user=user, first_name='Test', last_name='User',
                ghana_card_number='GHA-222222222-2', primary_phone='+233201111111',
                date_of_birth=date(1980, 1, 1), residential_address='Test',
                education_level='SHS/Technical', nok_full_name='NOK',
                nok_relationship='Spouse', nok_phone='+233201111112')
    
    flock = Flock(
        farm=farm,
        flock_number='TEST-003',
        flock_type='Layers',
        breed='Isa Brown',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=50  # Only 50 birds left
    )
    
    daily = DailyProduction(
        farm=farm,
        flock=flock,
        production_date=date(2025, 1, 15),
        eggs_collected=0,
        good_eggs=0,
        birds_died=100  # Can't lose 100 when only 50 exist!
    )
    
    try:
        daily.clean()
        raise AssertionError('Expected ValidationError for mortality exceeding count')
    except ValidationError as e:
        assert 'birds_died' in e.message_dict

test_validation(
    'DailyProduction rejects mortality > current_count',
    test_daily_production_mortality_exceeds_count
)


def test_daily_production_combined_removal():
    """Should reject when (birds_died + birds_sold) exceeds current_count"""
    user = User(email='test4@test.com', first_name='Test', last_name='User')
    farm = Farm(user=user, first_name='Test', last_name='User',
                ghana_card_number='GHA-333333333-3', primary_phone='+233202222222',
                date_of_birth=date(1980, 1, 1), residential_address='Test',
                education_level='SHS/Technical', nok_full_name='NOK',
                nok_relationship='Spouse', nok_phone='+233202222223')
    
    flock = Flock(
        farm=farm,
        flock_number='TEST-004',
        flock_type='Layers',
        breed='Isa Brown',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=100
    )
    
    daily = DailyProduction(
        farm=farm,
        flock=flock,
        production_date=date(2025, 1, 15),
        eggs_collected=0,
        good_eggs=0,
        birds_died=60,
        birds_sold=50  # 60 + 50 = 110 > 100 current_count
    )
    
    try:
        daily.clean()
        raise AssertionError('Expected ValidationError for combined removal')
    except ValidationError as e:
        assert 'birds_died' in e.message_dict

test_validation(
    'DailyProduction validates combined mortality + sales',
    test_daily_production_combined_removal
)

print('')

# ============================================================================
# TEST 2: MortalityRecord validations
# ============================================================================

print('🧪 TEST GROUP 2: MortalityRecord Validations')
print('─' * 80)

def test_mortality_record_farm_mismatch():
    """Should reject when farm doesn't match flock.farm"""
    user1 = User(email='farmer5@test.com', first_name='John', last_name='Doe')
    user2 = User(email='farmer6@test.com', first_name='Jane', last_name='Smith')
    
    farm1 = Farm(user=user1, first_name='John', last_name='Doe',
                 ghana_card_number='GHA-444444444-4', primary_phone='+233203333333',
                 date_of_birth=date(1980, 1, 1), residential_address='Test',
                 education_level='SHS/Technical', nok_full_name='NOK',
                 nok_relationship='Spouse', nok_phone='+233203333334')
    
    farm2 = Farm(user=user2, first_name='Jane', last_name='Smith',
                 ghana_card_number='GHA-555555555-5', primary_phone='+233204444444',
                 date_of_birth=date(1985, 1, 1), residential_address='Test',
                 education_level='SHS/Technical', nok_full_name='NOK',
                 nok_relationship='Spouse', nok_phone='+233204444445')
    
    flock = Flock(
        farm=farm1,
        flock_number='TEST-005',
        flock_type='Layers',
        breed='Isa Brown',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=1000
    )
    
    mortality = MortalityRecord(
        farm=farm2,  # MISMATCH!
        flock=flock,
        date_discovered=date(2025, 1, 15),
        number_of_birds=10,
        probable_cause='Disease - Viral'
    )
    
    try:
        mortality.clean()
        raise AssertionError('Expected ValidationError for farm mismatch')
    except ValidationError as e:
        assert 'farm' in e.message_dict

test_validation(
    'MortalityRecord rejects farm_id mismatch',
    test_mortality_record_farm_mismatch
)


def test_mortality_record_flock_mismatch_via_daily():
    """Should reject when flock doesn't match daily_production.flock"""
    user = User(email='farmer7@test.com', first_name='Test', last_name='User')
    farm = Farm(user=user, first_name='Test', last_name='User',
                ghana_card_number='GHA-666666666-6', primary_phone='+233205555555',
                date_of_birth=date(1980, 1, 1), residential_address='Test',
                education_level='SHS/Technical', nok_full_name='NOK',
                nok_relationship='Spouse', nok_phone='+233205555556')
    
    flock1 = Flock(
        farm=farm,
        flock_number='TEST-006',
        flock_type='Layers',
        breed='Isa Brown',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=1000
    )
    
    flock2 = Flock(
        farm=farm,
        flock_number='TEST-007',
        flock_type='Broilers',
        breed='Cobb 500',
        arrival_date=date(2025, 1, 1),
        initial_count=500,
        current_count=500
    )
    
    daily = DailyProduction(
        farm=farm,
        flock=flock1,
        production_date=date(2025, 1, 15),
        eggs_collected=0,
        good_eggs=0
    )
    
    mortality = MortalityRecord(
        farm=farm,
        flock=flock2,  # Different flock!
        daily_production=daily,  # Links to flock1
        date_discovered=date(2025, 1, 15),
        number_of_birds=10,
        probable_cause='Disease - Viral'
    )
    
    try:
        mortality.clean()
        raise AssertionError('Expected ValidationError for flock mismatch')
    except ValidationError as e:
        assert 'flock' in e.message_dict

test_validation(
    'MortalityRecord validates flock consistency with DailyProduction',
    test_mortality_record_flock_mismatch_via_daily
)


def test_mortality_record_compensation_validation():
    """Should reject when compensation_claimed=False but status != 'Not Claimed'"""
    user = User(email='farmer8@test.com', first_name='Test', last_name='User')
    farm = Farm(user=user, first_name='Test', last_name='User',
                ghana_card_number='GHA-777777777-7', primary_phone='+233206666666',
                date_of_birth=date(1980, 1, 1), residential_address='Test',
                education_level='SHS/Technical', nok_full_name='NOK',
                nok_relationship='Spouse', nok_phone='+233206666667')
    
    flock = Flock(
        farm=farm,
        flock_number='TEST-008',
        flock_type='Layers',
        breed='Isa Brown',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=1000
    )
    
    mortality = MortalityRecord(
        farm=farm,
        flock=flock,
        date_discovered=date(2025, 1, 15),
        number_of_birds=20,
        probable_cause='Disease - Viral',
        compensation_claimed=False,  # Not claimed
        compensation_status='Approved'  # But status is Approved??
    )
    
    try:
        mortality.clean()
        raise AssertionError('Expected ValidationError for compensation inconsistency')
    except ValidationError as e:
        assert 'compensation_claimed' in e.message_dict

test_validation(
    'MortalityRecord validates compensation workflow consistency',
    test_mortality_record_compensation_validation
)

print('')

# ============================================================================
# TEST 3: Flock validations
# ============================================================================

print('🧪 TEST GROUP 3: Flock Validations')
print('─' * 80)

def test_flock_current_exceeds_initial():
    """Should reject when current_count > initial_count"""
    user = User(email='farmer9@test.com', first_name='Test', last_name='User')
    farm = Farm(user=user, first_name='Test', last_name='User',
                ghana_card_number='GHA-888888888-8', primary_phone='+233207777777',
                date_of_birth=date(1980, 1, 1), residential_address='Test',
                education_level='SHS/Technical', nok_full_name='NOK',
                nok_relationship='Spouse', nok_phone='+233207777778')
    
    flock = Flock(
        farm=farm,
        flock_number='TEST-009',
        flock_type='Layers',
        breed='Isa Brown',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=1500  # More than initial!
    )
    
    try:
        flock.clean()
        raise AssertionError('Expected ValidationError for current > initial')
    except ValidationError as e:
        assert 'current_count' in e.message_dict

test_validation(
    'Flock rejects current_count > initial_count',
    test_flock_current_exceeds_initial
)


def test_flock_broiler_with_eggs():
    """Should reject when Broiler flock has egg production"""
    user = User(email='farmer10@test.com', first_name='Test', last_name='User')
    farm = Farm(user=user, first_name='Test', last_name='User',
                ghana_card_number='GHA-999999999-9', primary_phone='+233208888888',
                date_of_birth=date(1980, 1, 1), residential_address='Test',
                education_level='SHS/Technical', nok_full_name='NOK',
                nok_relationship='Spouse', nok_phone='+233208888889')
    
    flock = Flock(
        farm=farm,
        flock_number='TEST-010',
        flock_type='Broilers',  # Broilers don't lay eggs!
        breed='Cobb 500',
        arrival_date=date(2025, 1, 1),
        initial_count=1000,
        current_count=1000,
        total_eggs_produced=500  # Invalid!
    )
    
    try:
        flock.clean()
        raise AssertionError('Expected ValidationError for broiler with eggs')
    except ValidationError as e:
        assert 'total_eggs_produced' in e.message_dict

test_validation(
    'Flock rejects egg production for non-layer types',
    test_flock_broiler_with_eggs
)

print('')

# ============================================================================
# SUMMARY
# ============================================================================

print('═' * 80)
print('  TEST RESULTS SUMMARY')
print('═' * 80)
print(f'  Total Tests Run:    {tests_run}')
print(f'  Tests Passed:       {tests_passed} ✅')
print(f'  Tests Failed:       {tests_failed} ❌')
print('')

if tests_failed == 0:
    print('  🎉 ALL VALIDATIONS WORKING CORRECTLY!')
    print('  ✅ Data integrity protection is active')
    print('  ✅ Denormalized fields are protected from mismatches')
    print('  ✅ Business logic validations are enforced')
else:
    print(f'  ⚠️  {tests_failed} validation(s) need attention')

print('═' * 80)
print('')

# Exit with proper code
sys.exit(0 if tests_failed == 0 else 1)
