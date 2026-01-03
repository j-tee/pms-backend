"""
Advertising Serializers
"""

from rest_framework import serializers
from .models import Partner, PartnerOffer, OfferInteraction, AdvertiserLead


class PartnerSerializer(serializers.ModelSerializer):
    """Full partner serializer for admin views"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    has_active_contract = serializers.BooleanField(read_only=True)
    active_offers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Partner
        fields = [
            'id', 'company_name', 'category', 'category_display',
            'logo', 'website', 'description',
            'contact_name', 'contact_email', 'contact_phone',
            'is_verified', 'is_active', 'has_active_contract',
            'contract_start_date', 'contract_end_date', 'monthly_fee',
            'active_offers_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_active_offers_count(self, obj):
        return obj.offers.filter(is_active=True).count()


class PartnerListSerializer(serializers.ModelSerializer):
    """Minimal partner info for list views"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Partner
        fields = ['id', 'company_name', 'category', 'category_display', 'logo', 'is_verified']


class PartnerOfferSerializer(serializers.ModelSerializer):
    """Full offer serializer for admin views"""
    partner_name = serializers.CharField(source='partner.company_name', read_only=True)
    partner_logo = serializers.ImageField(source='partner.logo', read_only=True)
    partner_category = serializers.CharField(source='partner.get_category_display', read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)
    click_through_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    offer_type_display = serializers.CharField(source='get_offer_type_display', read_only=True)
    targeting_display = serializers.CharField(source='get_targeting_display', read_only=True)
    
    class Meta:
        model = PartnerOffer
        fields = [
            'id', 'partner', 'partner_name', 'partner_logo', 'partner_category',
            'title', 'description', 'offer_type', 'offer_type_display',
            'image', 'cta_text', 'cta_url', 'promo_code',
            'targeting', 'targeting_display', 'target_regions',
            'min_flock_size', 'max_flock_size',
            'start_date', 'end_date',
            'is_active', 'is_featured', 'priority', 'is_currently_active',
            'impressions', 'clicks', 'click_through_rate',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'impressions', 'clicks', 'created_at', 'updated_at']


class FarmerOfferSerializer(serializers.ModelSerializer):
    """
    Offer serializer for farmer-facing views.
    Excludes admin-only fields like analytics.
    """
    partner_name = serializers.CharField(source='partner.company_name', read_only=True)
    partner_logo = serializers.ImageField(source='partner.logo', read_only=True)
    partner_category = serializers.CharField(source='partner.get_category_display', read_only=True)
    partner_verified = serializers.BooleanField(source='partner.is_verified', read_only=True)
    offer_type_display = serializers.CharField(source='get_offer_type_display', read_only=True)
    
    class Meta:
        model = PartnerOffer
        fields = [
            'id', 'partner_name', 'partner_logo', 'partner_category', 'partner_verified',
            'title', 'description', 'offer_type', 'offer_type_display',
            'image', 'cta_text', 'cta_url', 'promo_code',
            'is_featured',
        ]


class OfferClickSerializer(serializers.Serializer):
    """Serializer for recording offer clicks"""
    offer_id = serializers.UUIDField()
    source_page = serializers.CharField(max_length=50, required=False, default='dashboard')


class AdvertiserLeadSerializer(serializers.ModelSerializer):
    """Full advertiser lead serializer for admin views"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    budget_display = serializers.CharField(source='get_budget_range_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = AdvertiserLead
        fields = [
            'id', 'company_name', 'category', 'category_display', 'website',
            'contact_name', 'contact_email', 'contact_phone', 'job_title',
            'advertising_interest', 'target_audience', 'budget_range', 'budget_display',
            'status', 'status_display', 'admin_notes',
            'assigned_to', 'assigned_to_name', 'follow_up_date',
            'converted_partner',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdvertiserLeadCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for public lead submission.
    Only includes fields that advertisers should fill out.
    """
    class Meta:
        model = AdvertiserLead
        fields = [
            'company_name', 'category', 'website',
            'contact_name', 'contact_email', 'contact_phone', 'job_title',
            'advertising_interest', 'target_audience', 'budget_range',
        ]
    
    def validate_contact_email(self, value):
        """Ensure email is valid and lowercase"""
        return value.lower().strip()


class PartnerOfferAnalyticsSerializer(serializers.ModelSerializer):
    """Analytics-focused serializer for admin reporting"""
    partner_name = serializers.CharField(source='partner.company_name', read_only=True)
    click_through_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = PartnerOffer
        fields = [
            'id', 'title', 'partner_name',
            'impressions', 'clicks', 'click_through_rate',
            'start_date', 'end_date', 'is_active',
        ]
