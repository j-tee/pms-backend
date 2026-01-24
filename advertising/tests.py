"""
Advertising Module Tests

Comprehensive tests for:
- Partner management
- Offer targeting and display
- A/B testing
- Lead capture
- Conversion tracking
- Partner payments
- Webhook API

Uses pytest with Django fixtures for cleaner test setup.
"""

import pytest
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User
from farms.models import Farm
from advertising.models import (
    Partner, PartnerOffer, OfferVariant, OfferInteraction,
    AdvertiserLead, PartnerPayment, ConversionWebhookKey,
    PartnerCategory, TargetingCriteria
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    """Return API client"""
    return APIClient()


@pytest.fixture
def super_admin(db):
    """Create super admin user"""
    return User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        first_name='Admin',
        last_name='User',
        phone='+233200000001',
        role='SUPER_ADMIN'
    )


@pytest.fixture
def yea_official(db):
    """Create YEA official user"""
    return User.objects.create_user(
        username='yeaofficial',
        email='yea@test.com',
        password='testpass123',
        first_name='YEA',
        last_name='Official',
        phone='+233200000002',
        role='YEA_OFFICIAL'
    )


@pytest.fixture
def farmer_user(db):
    """Create farmer user"""
    return User.objects.create_user(
        username='farmer',
        email='farmer@test.com',
        password='testpass123',
        first_name='Test',
        last_name='Farmer',
        phone='+233200000003',
        role='FARMER'
    )


@pytest.fixture
def farmer_with_farm(farmer_user, db):
    """Create farmer with associated farm"""
    farm = Farm.objects.create(
        user=farmer_user,
        farm_name='Test Advert Farm',
        primary_constituency='Ablekuma South',
        farm_status='OPERATIONAL',
        total_bird_capacity=2000,
        current_bird_count=500,
        subscription_type='standard',
        marketplace_enabled=True,
        ghana_card_number='GHA-999888777-0',
        tin='C0099888771',
        primary_phone='+233244888777',
        date_of_birth='1990-01-01',
        years_in_poultry=2,
        number_of_poultry_houses=2,
        total_infrastructure_value_ghs=25000,
        planned_production_start_date='2025-01-01',
        initial_investment_amount=30000,
        funding_source=['government_grant'],
        monthly_operating_budget=5000,
        expected_monthly_revenue=15000
    )
    return farmer_user, farm


@pytest.fixture
def partner(super_admin, db):
    """Create test partner"""
    return Partner.objects.create(
        company_name='Test Feed Company',
        category=PartnerCategory.FEED_SUPPLIER,
        contact_email='contact@testfeed.com',
        is_verified=True,
        is_active=True,
        contract_start_date=timezone.now().date() - timedelta(days=30),
        contract_end_date=timezone.now().date() + timedelta(days=335),
        monthly_fee=Decimal('5000.00'),
        created_by=super_admin
    )


@pytest.fixture
def active_offer(partner, super_admin, db):
    """Create active partner offer"""
    return PartnerOffer.objects.create(
        partner=partner,
        title='10% Off Starter Feed',
        description='Get 10% off all starter feed this month',
        offer_type='discount',
        cta_text='Shop Now',
        cta_url='https://testfeed.com/promo',
        promo_code='YEA10',
        targeting=TargetingCriteria.ALL_FARMERS,
        start_date=timezone.now() - timedelta(days=1),
        end_date=timezone.now() + timedelta(days=30),
        is_active=True,
        created_by=super_admin
    )


@pytest.fixture
def webhook_key(partner, db):
    """Create conversion webhook key"""
    return ConversionWebhookKey.objects.create(partner=partner)


# =============================================================================
# PARTNER MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestPartnerModel:
    """Tests for Partner model"""
    
    def test_partner_creation(self, partner):
        """Test partner model creation"""
        assert partner.company_name == 'Test Feed Company'
        assert partner.is_verified
        assert partner.has_active_contract
    
    def test_partner_expired_contract(self, super_admin):
        """Test partner with expired contract"""
        expired_partner = Partner.objects.create(
            company_name='Expired Partner',
            category=PartnerCategory.EQUIPMENT,
            contract_start_date=timezone.now().date() - timedelta(days=400),
            contract_end_date=timezone.now().date() - timedelta(days=30),
            created_by=super_admin
        )
        assert not expired_partner.has_active_contract
    
    def test_partner_str(self, partner):
        """Test partner string representation"""
        assert 'Test Feed Company' in str(partner)


# =============================================================================
# OFFER MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestOfferModel:
    """Tests for PartnerOffer model"""
    
    def test_offer_creation(self, active_offer):
        """Test partner offer creation"""
        assert active_offer.title == '10% Off Starter Feed'
        assert active_offer.is_currently_active
        assert active_offer.impressions == 0
        assert active_offer.clicks == 0
    
    def test_offer_click_through_rate(self, partner, super_admin):
        """Test CTR calculation"""
        offer = PartnerOffer.objects.create(
            partner=partner,
            title='CTR Test Offer',
            cta_url='https://test.com',
            targeting=TargetingCriteria.ALL_FARMERS,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True,
            impressions=1000,
            clicks=50,
            created_by=super_admin
        )
        assert offer.click_through_rate == Decimal('5.00')
    
    def test_offer_inactive_not_currently_active(self, partner, super_admin):
        """Test inactive offer reports not currently active"""
        offer = PartnerOffer.objects.create(
            partner=partner,
            title='Inactive Offer',
            cta_url='https://test.com',
            targeting=TargetingCriteria.ALL_FARMERS,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            is_active=False,  # Inactive
            created_by=super_admin
        )
        assert not offer.is_currently_active
    
    def test_offer_expired_not_currently_active(self, partner, super_admin):
        """Test expired offer reports not currently active"""
        offer = PartnerOffer.objects.create(
            partner=partner,
            title='Expired Offer',
            cta_url='https://test.com',
            targeting=TargetingCriteria.ALL_FARMERS,
            start_date=timezone.now() - timedelta(days=60),
            end_date=timezone.now() - timedelta(days=1),  # Expired
            is_active=True,
            created_by=super_admin
        )
        assert not offer.is_currently_active


# =============================================================================
# A/B TESTING MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestOfferVariant:
    """Tests for A/B testing variants"""
    
    def test_variant_creation(self, active_offer):
        """Test variant creation"""
        variant = OfferVariant.objects.create(
            offer=active_offer,
            name='Variant A - Bold CTA',
            title='Special Discount!',
            cta_text='Claim Now!',
            traffic_percentage=50,
            is_active=True
        )
        assert variant.offer == active_offer
        assert variant.name == 'Variant A - Bold CTA'
        assert variant.traffic_percentage == 50
    
    def test_variant_ctr_calculation(self, active_offer):
        """Test CTR calculated correctly for variants"""
        variant = OfferVariant.objects.create(
            offer=active_offer,
            name='CTR Test Variant',
            traffic_percentage=100,
            impressions=250,
            clicks=20,
            is_active=True
        )
        # 20/250 = 8%
        assert variant.click_through_rate == Decimal('8.00')
    
    def test_variant_cvr_calculation(self, active_offer):
        """Test CVR calculated correctly for variants"""
        variant = OfferVariant.objects.create(
            offer=active_offer,
            name='CVR Test Variant',
            traffic_percentage=100,
            impressions=100,
            clicks=20,
            conversions=5,
            is_active=True
        )
        # 5/20 = 25%
        assert variant.conversion_rate == Decimal('25.00')


# =============================================================================
# ADVERTISER LEAD TESTS
# =============================================================================

@pytest.mark.django_db
class TestAdvertiserLead:
    """Tests for advertiser lead model"""
    
    def test_lead_creation(self):
        """Test lead creation"""
        lead = AdvertiserLead.objects.create(
            company_name='New Advertiser',
            category=PartnerCategory.VETERINARY,
            contact_name='John Doe',
            contact_email='john@newadvertiser.com',
            contact_phone='+233244123456',
            advertising_interest='We want to promote our veterinary services',
            budget_range='5000_plus'
        )
        assert lead.status == 'new'
        assert lead.company_name == 'New Advertiser'
    
    def test_lead_status_workflow(self):
        """Test lead status transitions"""
        lead = AdvertiserLead.objects.create(
            company_name='Workflow Test',
            category=PartnerCategory.EQUIPMENT,
            contact_name='Jane Doe',
            contact_email='jane@test.com',
            advertising_interest='Equipment promotion'
        )
        
        assert lead.status == 'new'
        
        lead.status = 'contacted'
        lead.save()
        assert lead.status == 'contacted'
        
        lead.status = 'demo_scheduled'
        lead.save()
        assert lead.status == 'demo_scheduled'


# =============================================================================
# WEBHOOK KEY TESTS
# =============================================================================

@pytest.mark.django_db
class TestWebhookKey:
    """Tests for conversion webhook keys"""
    
    def test_webhook_key_generation(self, webhook_key):
        """Test webhook key auto-generation"""
        # API key is generated using secrets.token_urlsafe(48)
        assert len(webhook_key.api_key) == 64  # token_urlsafe(48) produces 64 chars
        assert webhook_key.is_active
    
    def test_webhook_key_regeneration(self, webhook_key):
        """Test API key regeneration"""
        old_key = webhook_key.api_key
        new_key = webhook_key.regenerate_key()
        
        assert old_key != new_key
        assert webhook_key.api_key == new_key


# =============================================================================
# PARTNER PAYMENT TESTS
# =============================================================================

@pytest.mark.django_db
class TestPartnerPayment:
    """Tests for partner payment model"""
    
    def test_payment_creation(self, partner):
        """Test payment record creation"""
        payment = PartnerPayment.objects.create(
            partner=partner,
            amount=Decimal('5000.00'),
            payment_type='monthly_fee',
            period_start=timezone.now().date(),
            period_end=timezone.now().date() + timedelta(days=30),
            status='pending',
            invoice_number='INV-2026-001'
        )
        assert payment.status == 'pending'
        assert payment.paid_at is None
    
    def test_mark_as_paid(self, partner, super_admin):
        """Test marking payment as paid"""
        payment = PartnerPayment.objects.create(
            partner=partner,
            amount=Decimal('5000.00'),
            payment_type='monthly_fee',
            period_start=timezone.now().date(),
            period_end=timezone.now().date() + timedelta(days=30),
            status='pending'
        )
        
        payment.mark_as_paid(user=super_admin, reference='TXN123456')
        
        assert payment.status == 'paid'
        assert payment.paid_at is not None
        assert payment.transaction_reference == 'TXN123456'


# =============================================================================
# FREQUENCY CAPPING TESTS
# =============================================================================

@pytest.mark.django_db
class TestFrequencyCapping:
    """Tests for frequency capping feature"""
    
    def test_can_show_to_farm_within_cap(self, active_offer, farmer_with_farm):
        """Test offer can be shown when under frequency cap"""
        farmer, farm = farmer_with_farm
        active_offer.max_impressions_per_user = 3
        active_offer.save()
        
        # Record 2 impressions
        for _ in range(2):
            OfferInteraction.objects.create(
                offer=active_offer,
                farm=farm,
                interaction_type='impression'
            )
        
        can_show, reason = active_offer.can_show_to_farm(farm)
        assert can_show
        assert reason is None
    
    def test_cannot_show_to_farm_at_cap(self, active_offer, farmer_with_farm):
        """Test offer is hidden when at frequency cap"""
        farmer, farm = farmer_with_farm
        active_offer.max_impressions_per_user = 3
        active_offer.save()
        
        # Record 3 impressions (at cap)
        for _ in range(3):
            OfferInteraction.objects.create(
                offer=active_offer,
                farm=farm,
                interaction_type='impression'
            )
        
        can_show, reason = active_offer.can_show_to_farm(farm)
        assert not can_show
        assert reason == 'max_impressions_reached'
    
    def test_cooldown_after_click(self, active_offer, farmer_with_farm):
        """Test cooldown period after click"""
        farmer, farm = farmer_with_farm
        active_offer.cooldown_hours = 24
        active_offer.save()
        
        # Record a click
        OfferInteraction.objects.create(
            offer=active_offer,
            farm=farm,
            interaction_type='click'
        )
        
        can_show, reason = active_offer.can_show_to_farm(farm)
        assert not can_show
        assert reason == 'in_cooldown'


# =============================================================================
# SCHEDULING TESTS
# =============================================================================

@pytest.mark.django_db
class TestScheduling:
    """Tests for offer scheduling"""
    
    def test_is_within_schedule_all_days(self, active_offer):
        """Test offer with no schedule restrictions"""
        active_offer.show_on_days = []
        active_offer.save()
        
        assert active_offer.is_within_schedule()
    
    def test_is_within_budget_no_limit(self, active_offer):
        """Test offer with no budget limit"""
        active_offer.daily_budget = None
        active_offer.save()
        
        assert active_offer.is_within_budget()
    
    def test_is_within_budget_under_limit(self, active_offer):
        """Test offer under budget limit"""
        active_offer.daily_budget = Decimal('100.00')
        active_offer.daily_spend = Decimal('50.00')
        active_offer.save()
        
        assert active_offer.is_within_budget()
    
    def test_is_within_budget_at_limit(self, active_offer):
        """Test offer at budget limit"""
        active_offer.daily_budget = Decimal('100.00')
        active_offer.daily_spend = Decimal('100.00')
        active_offer.save()
        
        assert not active_offer.is_within_budget()


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
class TestPartnerAPIEndpoints:
    """Tests for partner API endpoints"""
    
    def test_admin_can_list_partners(self, api_client, super_admin, partner):
        """Test admin can list all partners"""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/advertising/partners/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_admin_can_create_partner(self, api_client, super_admin):
        """Test admin can create a new partner"""
        api_client.force_authenticate(user=super_admin)
        
        data = {
            'company_name': 'New Partner',
            'category': 'equipment',
            'contact_email': 'contact@newpartner.com',
            'is_active': True
        }
        
        response = api_client.post('/api/admin/advertising/partners/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['company_name'] == 'New Partner'


@pytest.mark.django_db
class TestFarmerOfferEndpoints:
    """Tests for farmer-facing offer endpoints"""
    
    def test_farmer_can_get_offers(self, api_client, farmer_with_farm, active_offer):
        """Test farmer can retrieve targeted offers"""
        farmer, farm = farmer_with_farm
        api_client.force_authenticate(user=farmer)
        
        response = api_client.get('/api/advertising/offers/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'offers' in response.data
    
    def test_farmer_can_click_offer(self, api_client, farmer_with_farm, active_offer):
        """Test farmer can record offer click"""
        farmer, farm = farmer_with_farm
        api_client.force_authenticate(user=farmer)
        
        data = {
            'offer_id': str(active_offer.id),
            'source_page': 'dashboard'
        }
        
        response = api_client.post('/api/advertising/offers/click/', data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'redirect_url' in response.data
        
        # Verify click was recorded
        active_offer.refresh_from_db()
        assert active_offer.clicks == 1
    
    def test_farmer_can_dismiss_offer(self, api_client, farmer_with_farm, active_offer):
        """Test farmer can dismiss an offer"""
        farmer, farm = farmer_with_farm
        api_client.force_authenticate(user=farmer)
        
        response = api_client.post(f'/api/advertising/offers/{active_offer.id}/dismiss/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success']


@pytest.mark.django_db
class TestLeadCaptureEndpoints:
    """Tests for advertiser lead capture endpoints"""
    
    def test_public_can_view_advertising_info(self, api_client):
        """Test unauthenticated users can view advertising info"""
        response = api_client.get('/api/public/advertise/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'categories' in response.data
    
    def test_public_can_submit_lead(self, api_client):
        """Test unauthenticated users can submit lead form"""
        data = {
            'company_name': 'New Advertiser Co',
            'category': 'feed_supplier',
            'contact_name': 'Jane Doe',
            'contact_email': 'jane@advertiser.com',
            'contact_phone': '+233244123456',
            'advertising_interest': 'We want to promote our products to farmers',
            'budget_range': '2000_5000'  # Must match model choices
        }
        
        response = api_client.post('/api/public/advertise/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success']
        assert 'lead_id' in response.data
    
    def test_lead_validation_required_fields(self, api_client):
        """Test lead form validation"""
        data = {
            'company_name': 'Incomplete Lead'
            # Missing required fields
        }
        
        response = api_client.post('/api/public/advertise/', data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestConversionWebhookEndpoints:
    """Tests for partner conversion webhook endpoints"""
    
    def test_webhook_requires_api_key(self, api_client, active_offer):
        """Test webhook rejects requests without API key"""
        data = {
            'offer_id': str(active_offer.id),
            'conversion_type': 'purchase',
            'conversion_value': '150.00'
        }
        
        response = api_client.post('/api/advertising/webhook/conversion/', data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_webhook_rejects_invalid_key(self, api_client, active_offer):
        """Test webhook rejects invalid API key"""
        data = {
            'offer_id': str(active_offer.id),
            'conversion_type': 'purchase'
        }
        
        api_client.credentials(HTTP_X_API_KEY='invalid_key_123')
        response = api_client.post('/api/advertising/webhook/conversion/', data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_webhook_accepts_valid_conversion(self, api_client, active_offer, webhook_key):
        """Test webhook accepts valid conversion with valid key"""
        data = {
            'offer_id': str(active_offer.id),
            'conversion_type': 'purchase',
            'conversion_value': '150.00',
            'promo_code': 'TESTCODE'
        }
        
        api_client.credentials(HTTP_X_API_KEY=webhook_key.api_key)
        response = api_client.post('/api/advertising/webhook/conversion/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success']
        assert 'conversion_id' in response.data


@pytest.mark.django_db
class TestTargeting:
    """Tests for offer targeting system"""
    
    def test_region_targeting_match(self, api_client, super_admin, partner):
        """Test ALL_FARMERS targeting matches all farmers regardless of location"""
        # Create farmer
        farmer = User.objects.create_user(
            username='accra_farmer',
            email='accra@test.com',
            password='testpass123',
            phone='+233200000010',
            role='FARMER'
        )
        farm = Farm.objects.create(
            user=farmer,
            farm_name='Accra Farm',
            primary_constituency='Ayawaso West',
            current_bird_count=500,
            total_bird_capacity=1000,
            subscription_type='standard',
            marketplace_enabled=True,
            ghana_card_number='GHA-999777666-1',
            tin='C0099777661',
            primary_phone='+233244777666',
            date_of_birth='1990-01-01',
            years_in_poultry=2,
            number_of_poultry_houses=1,
            total_infrastructure_value_ghs=15000,
            planned_production_start_date='2025-01-01',
            initial_investment_amount=20000,
            funding_source=['government_grant'],
            monthly_operating_budget=4000,
            expected_monthly_revenue=12000,
        )
        
        # Create offer targeting all farmers
        offer = PartnerOffer.objects.create(
            partner=partner,
            title='All Farmers Offer',
            cta_url='https://test.com',
            targeting=TargetingCriteria.ALL_FARMERS,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True,
            created_by=super_admin
        )
        
        api_client.force_authenticate(user=farmer)
        response = api_client.get('/api/advertising/offers/')
        
        offer_titles = [o['title'] for o in response.data.get('offers', [])]
        assert 'All Farmers Offer' in offer_titles
    
    def test_flock_size_targeting(self, api_client, super_admin, partner):
        """Test flock size targeting"""
        # Create farmer with large flock
        farmer = User.objects.create_user(
            username='large_farmer',
            email='large@test.com',
            password='testpass123',
            phone='+233200000011',
            role='FARMER'
        )
        farm = Farm.objects.create(
            user=farmer,
            farm_name='Large Farm',
            primary_constituency='Kumasi Central',
            current_bird_count=1000,
            total_bird_capacity=2000,
            subscription_type='standard',
            marketplace_enabled=True,
            ghana_card_number='GHA-999666555-2',
            tin='C0099666552',
            primary_phone='+233244666555',
            date_of_birth='1990-01-01',
            years_in_poultry=3,
            number_of_poultry_houses=2,
            total_infrastructure_value_ghs=25000,
            planned_production_start_date='2025-01-01',
            initial_investment_amount=30000,
            funding_source=['personal_savings'],
            monthly_operating_budget=6000,
            expected_monthly_revenue=18000,
        )
        
        # Create offer for large flocks
        offer = PartnerOffer.objects.create(
            partner=partner,
            title='Large Flock Offer',
            cta_url='https://test.com',
            targeting=TargetingCriteria.BY_FLOCK_SIZE,
            min_flock_size=500,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True,
            created_by=super_admin
        )
        
        api_client.force_authenticate(user=farmer)
        response = api_client.get('/api/advertising/offers/')
        
        offer_titles = [o['title'] for o in response.data.get('offers', [])]
        assert 'Large Flock Offer' in offer_titles


@pytest.mark.django_db
class TestABTestingEndpoints:
    """Tests for A/B testing admin endpoints"""
    
    def test_admin_can_view_ab_results(self, api_client, super_admin, active_offer):
        """Test admin can view A/B test results"""
        # Create variants
        OfferVariant.objects.create(
            offer=active_offer,
            name='Variant A',
            traffic_percentage=50,
            impressions=200,
            clicks=20,
            conversions=5,
            is_active=True
        )
        OfferVariant.objects.create(
            offer=active_offer,
            name='Variant B',
            traffic_percentage=50,
            impressions=200,
            clicks=10,
            conversions=2,
            is_active=True
        )
        
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(f'/api/admin/advertising/offers/{active_offer.id}/ab-results/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'variants' in response.data
        assert len(response.data['variants']) == 2


@pytest.mark.django_db
class TestPaymentEndpoints:
    """Tests for partner payment endpoints"""
    
    def test_super_admin_can_view_payments(self, api_client, super_admin, partner):
        """Test super admin can view partner payments"""
        # Create payment
        PartnerPayment.objects.create(
            partner=partner,
            amount=Decimal('5000.00'),
            payment_type='monthly_fee',
            period_start=timezone.now().date(),
            period_end=timezone.now().date() + timedelta(days=30),
            status='pending'
        )
        
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/advertising/payments/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_yea_official_cannot_view_payments(self, api_client, yea_official, partner):
        """Test YEA official cannot view payment revenue data"""
        PartnerPayment.objects.create(
            partner=partner,
            amount=Decimal('5000.00'),
            payment_type='monthly_fee',
            period_start=timezone.now().date(),
            period_end=timezone.now().date() + timedelta(days=30),
            status='pending'
        )
        
        api_client.force_authenticate(user=yea_official)
        response = api_client.get('/api/admin/advertising/payments/')
        
        # Should return empty list (permission filtered)
        if response.status_code == status.HTTP_200_OK:
            assert len(response.data.get('results', [])) == 0


@pytest.mark.django_db
class TestAnalyticsEndpoints:
    """Tests for advertising analytics endpoints"""
    
    def test_admin_can_view_analytics(self, api_client, super_admin, active_offer):
        """Test admin can view offer analytics"""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/advertising/analytics/')
        
        assert response.status_code == status.HTTP_200_OK
        # Check for actual response structure
        assert 'partners' in response.data or 'offers' in response.data or 'leads' in response.data
    
    def test_super_admin_can_view_revenue(self, api_client, super_admin):
        """Test super admin can view revenue dashboard"""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/advertising/revenue/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'total_revenue' in response.data
