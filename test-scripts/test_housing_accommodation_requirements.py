"""
Test housing-to-accommodation transition and validation
Tests all backend requirements:
1. Field name compatibility (house_name, capacity properties)
2. Validation for Accommodation type
3. Capacity checks
4. Auto-update occupancy
5. Protect deletion of accommodation with active flocks
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from farms.models import Farm, Infrastructure
from flock_management.models import Flock
from accounts.models import User


@pytest.fixture
def user(db):
    """Create test user"""
    return User.objects.create_user(
        username='testfarmer',
        email='farmer@test.com',
        password='testpass123',
        first_name='Test',
        last_name='Farmer',
        phone='+233241234567',
        role='FARMER'
    )


@pytest.fixture
def farm(db, user):
    """Create test farm"""
    return Farm.objects.create(
        user=user,
        first_name='Test',
        last_name='Farmer',
        date_of_birth=date(1990, 1, 1),
        gender='Male',
        ghana_card_number='GHA-123456789-1',
        primary_phone='+233241234567',
        residential_address='Test Address',
        primary_constituency='Test Constituency',
        nok_full_name='Test Next of Kin',
        nok_relationship='Brother',
        nok_phone='+233249999999',
        education_level='SHS/Technical',
        literacy_level='Can Read & Write',
        years_in_poultry=Decimal('2.0'),
        farm_name='Test Farm',
        ownership_type='Sole Proprietorship',
        tin='C1234567890',
        number_of_poultry_houses=2,
        total_bird_capacity=5000,
        housing_type='Battery Cage',
        total_infrastructure_value_ghs=Decimal('10000.00')
    )


@pytest.fixture
def accommodation(db, farm):
    """Create test accommodation infrastructure"""
    return Infrastructure.objects.create(
        farm=farm,
        infrastructure_type='Accommodation',
        infrastructure_name='House H1',
        housing_system='Battery Cage',
        bird_capacity=2000,
        current_occupancy=0,
        status='Operational',
        condition='Good'
    )


@pytest.fixture
def non_accommodation(db, farm):
    """Create non-accommodation infrastructure"""
    return Infrastructure.objects.create(
        farm=farm,
        infrastructure_type='Water System',
        infrastructure_name='Main Borehole',
        status='Operational',
        condition='Good'
    )


@pytest.mark.django_db
class TestBackwardCompatibility:
    """Test house_name and capacity computed properties"""
    
    def test_house_name_property(self, farm, accommodation):
        """Test house_name property returns infrastructure_name"""
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-001',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=500,
            current_count=500,
            housed_in=accommodation
        )
        
        assert flock.house_name == 'House H1'
        assert flock.house_name == accommodation.infrastructure_name
    
    def test_capacity_property(self, farm, accommodation):
        """Test capacity property returns bird_capacity"""
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-002',
            flock_type='Broilers',
            breed='Cobb 500',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=1000,
            current_count=1000,
            housed_in=accommodation
        )
        
        assert flock.capacity == 2000
        assert flock.capacity == accommodation.bird_capacity
    
    def test_properties_with_no_housing(self, farm):
        """Test properties return None when not housed"""
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-003',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=500,
            current_count=500,
            housed_in=None
        )
        
        assert flock.house_name is None
        assert flock.capacity is None


@pytest.mark.django_db
class TestAccommodationTypeValidation:
    """Test flocks can only be housed in Accommodation type"""
    
    def test_valid_accommodation_housing(self, farm, accommodation):
        """Test flock can be housed in Accommodation"""
        flock = Flock(
            farm=farm,
            flock_number='FLOCK-004',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=500,
            current_count=500,
            housed_in=accommodation
        )
        
        # Should not raise ValidationError
        flock.full_clean()
        flock.save()
        assert flock.housed_in.infrastructure_type == 'Accommodation'
    
    def test_invalid_non_accommodation_housing(self, farm, non_accommodation):
        """Test flock cannot be housed in non-Accommodation infrastructure"""
        flock = Flock(
            farm=farm,
            flock_number='FLOCK-005',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=500,
            current_count=500,
            housed_in=non_accommodation
        )
        
        with pytest.raises(ValidationError) as exc_info:
            flock.full_clean()
        
        assert 'housed_in' in exc_info.value.message_dict
        assert 'Accommodation infrastructure' in str(exc_info.value)


@pytest.mark.django_db
class TestCapacityValidation:
    """Test capacity checks prevent exceeding house capacity"""
    
    def test_flock_within_capacity(self, farm, accommodation):
        """Test flock that fits within capacity"""
        flock = Flock(
            farm=farm,
            flock_number='FLOCK-006',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=1500,
            current_count=1500,
            housed_in=accommodation  # Capacity is 2000
        )
        
        # Should not raise ValidationError
        flock.full_clean()
        flock.save()
        assert flock.housed_in.bird_capacity >= flock.current_count
    
    def test_single_flock_exceeds_capacity(self, farm, accommodation):
        """Test single flock exceeding capacity is rejected"""
        flock = Flock(
            farm=farm,
            flock_number='FLOCK-007',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=2500,
            current_count=2500,
            housed_in=accommodation  # Capacity is 2000
        )
        
        with pytest.raises(ValidationError) as exc_info:
            flock.full_clean()
        
        assert 'housed_in' in exc_info.value.message_dict
        assert 'Capacity exceeded' in str(exc_info.value)
    
    def test_multiple_flocks_exceed_capacity(self, farm, accommodation):
        """Test multiple flocks exceeding total capacity"""
        # First flock uses 1500 birds
        flock1 = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-008',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=1500,
            current_count=1500,
            housed_in=accommodation,
            status='Active'
        )
        
        # Second flock tries to add 800 more (total 2300 > 2000 capacity)
        flock2 = Flock(
            farm=farm,
            flock_number='FLOCK-009',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=800,
            current_count=800,
            housed_in=accommodation,
            status='Active'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            flock2.full_clean()
        
        assert 'housed_in' in exc_info.value.message_dict
        assert 'Capacity exceeded' in str(exc_info.value)
        assert '2300' in str(exc_info.value)  # Total occupancy


@pytest.mark.django_db
class TestOccupancyAutoUpdate:
    """Test auto-update of infrastructure current_occupancy"""
    
    def test_occupancy_updates_on_new_flock(self, farm, accommodation):
        """Test occupancy increases when flock is added"""
        assert accommodation.current_occupancy == 0
        
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-010',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=800,
            current_count=800,
            housed_in=accommodation,
            status='Active'
        )
        
        accommodation.refresh_from_db()
        assert accommodation.current_occupancy == 800
    
    def test_occupancy_updates_when_count_changes(self, farm, accommodation):
        """Test occupancy updates when flock count changes"""
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-011',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=1000,
            current_count=1000,
            housed_in=accommodation,
            status='Active'
        )
        
        accommodation.refresh_from_db()
        assert accommodation.current_occupancy == 1000
        
        # Update flock count (mortality)
        flock.current_count = 950
        flock.save()
        
        accommodation.refresh_from_db()
        assert accommodation.current_occupancy == 950
    
    def test_occupancy_updates_when_flock_moves(self, farm, accommodation):
        """Test occupancy updates when flock moves to different housing"""
        # Create second accommodation
        accommodation2 = Infrastructure.objects.create(
            farm=farm,
            infrastructure_type='Accommodation',
            infrastructure_name='House H2',
            housing_system='Deep Litter',
            bird_capacity=1500,
            current_occupancy=0,
            status='Operational'
        )
        
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-012',
            flock_type='Broilers',
            breed='Cobb 500',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=600,
            current_count=600,
            housed_in=accommodation,
            status='Active'
        )
        
        accommodation.refresh_from_db()
        assert accommodation.current_occupancy == 600
        assert accommodation2.current_occupancy == 0
        
        # Move flock to accommodation2
        flock.housed_in = accommodation2
        flock.save()
        
        accommodation.refresh_from_db()
        accommodation2.refresh_from_db()
        assert accommodation.current_occupancy == 0
        assert accommodation2.current_occupancy == 600
    
    def test_occupancy_with_multiple_flocks(self, farm, accommodation):
        """Test occupancy correctly sums multiple active flocks"""
        flock1 = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-013',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=500,
            current_count=500,
            housed_in=accommodation,
            status='Active'
        )
        
        flock2 = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-014',
            flock_type='Layers',
            breed='Lohmann Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=700,
            current_count=700,
            housed_in=accommodation,
            status='Active'
        )
        
        accommodation.refresh_from_db()
        assert accommodation.current_occupancy == 1200
    
    def test_occupancy_ignores_non_active_flocks(self, farm, accommodation):
        """Test occupancy only counts active flocks"""
        active_flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-015',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=500,
            current_count=500,
            housed_in=accommodation,
            status='Active'
        )
        
        sold_flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-016',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today() - timedelta(days=365),
            initial_count=800,
            current_count=0,
            housed_in=accommodation,
            status='Sold'
        )
        
        accommodation.refresh_from_db()
        # Should only count active flock
        assert accommodation.current_occupancy == 500


@pytest.mark.django_db
class TestProtectDeletion:
    """Test PROTECT prevents deletion of accommodation with active flocks"""
    
    def test_cannot_delete_accommodation_with_active_flock(self, farm, accommodation):
        """Test accommodation with active flock cannot be deleted"""
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-017',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=500,
            current_count=500,
            housed_in=accommodation,
            status='Active'
        )
        
        with pytest.raises(IntegrityError):
            accommodation.delete()
        
        # Verify accommodation still exists
        assert Infrastructure.objects.filter(id=accommodation.id).exists()
    
    def test_can_delete_accommodation_without_flocks(self, farm, accommodation):
        """Test accommodation without flocks can be deleted"""
        accommodation_id = accommodation.id
        
        # Should not raise error
        accommodation.delete()
        
        # Verify it's deleted
        assert not Infrastructure.objects.filter(id=accommodation_id).exists()
    
    def test_can_delete_accommodation_after_flock_removed(self, farm, accommodation):
        """Test accommodation can be deleted after flock is moved or sold"""
        flock = Flock.objects.create(
            farm=farm,
            flock_number='FLOCK-018',
            flock_type='Layers',
            breed='Isa Brown',
            source='Purchased',
            arrival_date=date.today(),
            initial_count=500,
            current_count=500,
            housed_in=accommodation,
            status='Active'
        )
        
        # Remove flock association
        flock.housed_in = None
        flock.save()
        
        accommodation_id = accommodation.id
        
        # Should not raise error now
        accommodation.delete()
        
        # Verify it's deleted
        assert not Infrastructure.objects.filter(id=accommodation_id).exists()


@pytest.mark.django_db
class TestInfrastructureValidation:
    """Test Infrastructure model validation for Accommodation"""
    
    def test_accommodation_requires_housing_system(self, farm):
        """Test Accommodation must have housing_system"""
        infra = Infrastructure(
            farm=farm,
            infrastructure_type='Accommodation',
            infrastructure_name='House H3',
            housing_system=None,  # Missing!
            bird_capacity=1000,
            status='Operational'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            infra.full_clean()
        
        assert 'housing_system' in exc_info.value.message_dict
    
    def test_accommodation_requires_bird_capacity(self, farm):
        """Test Accommodation must have bird_capacity"""
        infra = Infrastructure(
            farm=farm,
            infrastructure_type='Accommodation',
            infrastructure_name='House H4',
            housing_system='Battery Cage',
            bird_capacity=None,  # Missing!
            status='Operational'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            infra.full_clean()
        
        assert 'bird_capacity' in exc_info.value.message_dict
    
    def test_occupancy_cannot_exceed_capacity(self, farm, accommodation):
        """Test current_occupancy validation"""
        accommodation.current_occupancy = 2500  # Exceeds capacity of 2000
        
        with pytest.raises(ValidationError) as exc_info:
            accommodation.full_clean()
        
        assert 'current_occupancy' in exc_info.value.message_dict
        assert 'cannot exceed' in str(exc_info.value)
    
    def test_non_accommodation_can_omit_housing_fields(self, farm):
        """Test non-Accommodation infrastructure doesn't require housing fields"""
        infra = Infrastructure(
            farm=farm,
            infrastructure_type='Water System',
            infrastructure_name='Borehole 2',
            housing_system=None,
            bird_capacity=None,
            status='Operational'
        )
        
        # Should not raise ValidationError
        infra.full_clean()
        infra.save()
        assert infra.infrastructure_type != 'Accommodation'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
