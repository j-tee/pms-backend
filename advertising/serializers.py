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


# =============================================================================
# A/B TESTING SERIALIZERS
# =============================================================================

class OfferVariantSerializer(serializers.ModelSerializer):
    """Full variant serializer for admin views"""
    click_through_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    display_title = serializers.CharField(source='get_display_title', read_only=True)
    display_description = serializers.CharField(source='get_display_description', read_only=True)
    display_cta = serializers.CharField(source='get_display_cta', read_only=True)
    
    class Meta:
        from .models import OfferVariant
        model = OfferVariant
        fields = [
            'id', 'offer', 'name',
            'title', 'description', 'image', 'cta_text',
            'display_title', 'display_description', 'display_cta',
            'traffic_percentage',
            'impressions', 'clicks', 'conversions',
            'click_through_rate', 'conversion_rate',
            'is_active', 'is_winner',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'impressions', 'clicks', 'conversions', 'created_at', 'updated_at']


class OfferVariantListSerializer(serializers.ModelSerializer):
    """Minimal variant serializer for list views"""
    click_through_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        from .models import OfferVariant
        model = OfferVariant
        fields = [
            'id', 'name', 'traffic_percentage',
            'impressions', 'clicks', 'conversions',
            'click_through_rate', 'conversion_rate',
            'is_active', 'is_winner',
        ]


# =============================================================================
# CONVERSION TRACKING SERIALIZERS
# =============================================================================

class ConversionEventSerializer(serializers.ModelSerializer):
    """Full conversion event serializer"""
    offer_title = serializers.CharField(source='offer.title', read_only=True)
    partner_name = serializers.CharField(source='offer.partner.company_name', read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    conversion_type_display = serializers.CharField(source='get_conversion_type_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        from .models import ConversionEvent
        model = ConversionEvent
        fields = [
            'id', 'offer', 'offer_title', 'partner_name',
            'variant', 'variant_name',
            'farm', 'farm_name',
            'conversion_type', 'conversion_type_display',
            'conversion_value', 'promo_code_used', 'external_reference',
            'click_interaction', 'attribution_window_hours',
            'source', 'source_display',
            'is_verified', 'verified_by', 'verified_at',
            'notes', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ConversionEventCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating conversion events (webhook/manual)"""
    farm_id = serializers.UUIDField(required=False, allow_null=True)
    
    class Meta:
        from .models import ConversionEvent
        model = ConversionEvent
        fields = [
            'offer', 'variant', 'farm_id',
            'conversion_type', 'conversion_value',
            'promo_code_used', 'external_reference', 'notes',
        ]
    
    def create(self, validated_data):
        from .models import ConversionEvent
        farm_id = validated_data.pop('farm_id', None)
        if farm_id:
            from farms.models import Farm
            validated_data['farm'] = Farm.objects.get(id=farm_id)
        return ConversionEvent.objects.create(**validated_data)


class WebhookConversionSerializer(serializers.Serializer):
    """Serializer for partner webhook conversion data"""
    offer_id = serializers.UUIDField()
    conversion_type = serializers.ChoiceField(choices=[
        'signup', 'purchase', 'application', 'registration',
        'quote_request', 'contact', 'download', 'other'
    ])
    conversion_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    promo_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    external_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    farmer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    farmer_email = serializers.EmailField(required=False, allow_blank=True)


# =============================================================================
# PARTNER PAYMENT SERIALIZERS
# =============================================================================

class PartnerPaymentSerializer(serializers.ModelSerializer):
    """Full partner payment serializer"""
    partner_name = serializers.CharField(source='partner.company_name', read_only=True)
    partner_category = serializers.CharField(source='partner.get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    class Meta:
        from .models import PartnerPayment
        model = PartnerPayment
        fields = [
            'id', 'partner', 'partner_name', 'partner_category',
            'amount', 'currency',
            'payment_type', 'payment_type_display',
            'period_start', 'period_end',
            'status', 'status_display',
            'payment_method', 'payment_method_display',
            'transaction_reference', 'invoice_number',
            'invoice_date', 'due_date', 'paid_at',
            'notes', 'recorded_by', 'recorded_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PartnerPaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating partner payments"""
    
    class Meta:
        from .models import PartnerPayment
        model = PartnerPayment
        fields = [
            'partner', 'amount', 'currency',
            'payment_type', 'period_start', 'period_end',
            'status', 'payment_method',
            'transaction_reference', 'invoice_number',
            'invoice_date', 'due_date', 'paid_at', 'notes',
        ]


class WebhookKeySerializer(serializers.ModelSerializer):
    """Webhook key serializer for admin"""
    partner_name = serializers.CharField(source='partner.company_name', read_only=True)
    
    class Meta:
        from .models import ConversionWebhookKey
        model = ConversionWebhookKey
        fields = [
            'id', 'partner', 'partner_name',
            'api_key', 'is_active',
            'daily_limit', 'last_used_at', 'total_requests',
            'created_at',
        ]
        read_only_fields = ['id', 'api_key', 'last_used_at', 'total_requests', 'created_at']
