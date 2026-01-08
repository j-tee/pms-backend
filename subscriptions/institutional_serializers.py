"""
Serializers for Institutional Data Subscriptions.
"""

from rest_framework import serializers
from django.utils import timezone

from .institutional_models import (
    InstitutionalPlan,
    InstitutionalSubscriber,
    InstitutionalAPIKey,
    InstitutionalAPIUsage,
    InstitutionalPayment,
    InstitutionalInquiry,
)


# =============================================================================
# PUBLIC SERIALIZERS (No Auth Required)
# =============================================================================

class InstitutionalPlanPublicSerializer(serializers.ModelSerializer):
    """
    Public view of institutional plans (for landing page).
    """
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = InstitutionalPlan
        fields = [
            'id', 'name', 'tier', 'tier_display', 'description',
            'price_monthly', 'price_annually',
            'requests_per_day', 'requests_per_month',
            'features', 'support_level',
        ]
    
    def get_features(self, obj):
        """Return list of features included in this plan"""
        features = []
        
        if obj.access_regional_aggregates:
            features.append('Regional production aggregates')
        if obj.access_constituency_data:
            features.append('Constituency-level breakdown')
        if obj.access_production_trends:
            features.append('Historical production trends')
        if obj.access_market_prices:
            features.append('Average market prices')
        if obj.access_mortality_data:
            features.append('Mortality & health statistics')
        if obj.access_supply_forecasts:
            features.append('Supply forecasting')
        if obj.access_individual_farm_data:
            features.append('Anonymized farm performance data')
        
        features.append(f"Up to {obj.requests_per_day} API calls/day")
        features.append(f"Max {obj.max_export_records} records per export")
        
        if obj.export_formats:
            features.append(f"Export formats: {', '.join(obj.export_formats)}")
        
        return features


class InstitutionalInquiryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for submitting institutional data subscription inquiries.
    """
    class Meta:
        model = InstitutionalInquiry
        fields = [
            'organization_name', 'organization_category', 'website',
            'contact_name', 'contact_email', 'contact_phone', 'contact_position',
            'interested_plan', 'data_use_purpose', 'message', 'source',
        ]
    
    def validate_contact_email(self, value):
        """Validate email format and check for duplicates"""
        # Check for recent duplicate submissions
        recent = InstitutionalInquiry.objects.filter(
            contact_email__iexact=value,
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).exists()
        
        if recent:
            raise serializers.ValidationError(
                "An inquiry from this email was submitted recently. "
                "Please allow 7 days between submissions."
            )
        
        return value.lower()


# =============================================================================
# SUBSCRIBER SERIALIZERS
# =============================================================================

class InstitutionalPlanDetailSerializer(serializers.ModelSerializer):
    """
    Detailed plan info for subscribers.
    """
    class Meta:
        model = InstitutionalPlan
        fields = '__all__'


class InstitutionalAPIKeySerializer(serializers.ModelSerializer):
    """
    API key serializer (excludes hash for security).
    """
    class Meta:
        model = InstitutionalAPIKey
        fields = [
            'id', 'name', 'key_prefix', 'is_active', 'is_readonly',
            'allowed_ips', 'last_used_at', 'total_requests',
            'expires_at', 'created_at',
        ]
        read_only_fields = ['key_prefix', 'last_used_at', 'total_requests', 'created_at']


class InstitutionalAPIKeyCreateSerializer(serializers.Serializer):
    """
    Serializer for creating new API keys.
    """
    name = serializers.CharField(max_length=100)
    allowed_ips = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
        help_text="List of allowed IP addresses"
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class InstitutionalSubscriberSerializer(serializers.ModelSerializer):
    """
    Subscriber profile serializer.
    """
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_tier = serializers.CharField(source='plan.tier', read_only=True)
    category_display = serializers.CharField(
        source='get_organization_category_display', 
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    api_keys = InstitutionalAPIKeySerializer(many=True, read_only=True)
    
    class Meta:
        model = InstitutionalSubscriber
        fields = [
            'id', 'organization_name', 'organization_category', 'category_display',
            'registration_number', 'website',
            'contact_name', 'contact_email', 'contact_phone', 'contact_position',
            'tech_contact_name', 'tech_contact_email',
            'address', 'city', 'region',
            'plan', 'plan_name', 'plan_tier', 'status', 'status_display',
            'billing_cycle', 'subscription_start',
            'current_period_start', 'current_period_end', 'next_billing_date',
            'trial_start', 'trial_end',
            'preferred_regions', 'data_use_purpose',
            'is_verified', 'api_keys',
            'created_at',
        ]
        read_only_fields = [
            'id', 'status', 'subscription_start', 'current_period_start',
            'current_period_end', 'next_billing_date', 'trial_start', 'trial_end',
            'is_verified', 'created_at',
        ]


class InstitutionalSubscriberUpdateSerializer(serializers.ModelSerializer):
    """
    Subscriber can update contact info and preferences.
    """
    class Meta:
        model = InstitutionalSubscriber
        fields = [
            'contact_name', 'contact_email', 'contact_phone', 'contact_position',
            'tech_contact_name', 'tech_contact_email',
            'address', 'city', 'region', 'preferred_regions',
        ]


# =============================================================================
# USAGE & BILLING SERIALIZERS
# =============================================================================

class InstitutionalAPIUsageSerializer(serializers.ModelSerializer):
    """
    API usage record serializer.
    """
    class Meta:
        model = InstitutionalAPIUsage
        fields = [
            'id', 'endpoint', 'method', 'status_code', 
            'response_time_ms', 'date', 'timestamp',
        ]


class InstitutionalAPIUsageSummarySerializer(serializers.Serializer):
    """
    Usage summary for dashboard.
    """
    period = serializers.CharField()
    total_requests = serializers.IntegerField()
    successful_requests = serializers.IntegerField()
    failed_requests = serializers.IntegerField()
    average_response_time_ms = serializers.FloatField()
    quota_used_percent = serializers.FloatField()
    requests_remaining = serializers.IntegerField()
    top_endpoints = serializers.ListField()


class InstitutionalPaymentSerializer(serializers.ModelSerializer):
    """
    Payment record serializer.
    """
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', 
        read_only=True
    )
    payment_status_display = serializers.CharField(
        source='get_payment_status_display', 
        read_only=True
    )
    
    class Meta:
        model = InstitutionalPayment
        fields = [
            'id', 'amount', 'currency',
            'period_start', 'period_end',
            'payment_method', 'payment_method_display',
            'payment_status', 'payment_status_display',
            'invoice_number', 'invoice_date', 'invoice_due_date',
            'paid_at', 'created_at',
        ]


# =============================================================================
# ADMIN SERIALIZERS
# =============================================================================

class InstitutionalInquiryListSerializer(serializers.ModelSerializer):
    """
    List view of inquiries for admin.
    """
    category_display = serializers.CharField(
        source='get_organization_category_display', 
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    plan_name = serializers.CharField(source='interested_plan.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = InstitutionalInquiry
        fields = [
            'id', 'organization_name', 'organization_category', 'category_display',
            'contact_name', 'contact_email', 'contact_phone',
            'interested_plan', 'plan_name',
            'status', 'status_display',
            'assigned_to', 'assigned_to_name', 'next_follow_up',
            'created_at',
        ]


class InstitutionalInquiryDetailSerializer(serializers.ModelSerializer):
    """
    Detailed inquiry view for admin.
    """
    category_display = serializers.CharField(
        source='get_organization_category_display', 
        read_only=True
    )
    
    class Meta:
        model = InstitutionalInquiry
        fields = '__all__'


class InstitutionalSubscriberAdminSerializer(serializers.ModelSerializer):
    """
    Admin view of subscriber with all fields.
    """
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    category_display = serializers.CharField(
        source='get_organization_category_display', 
        read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    api_keys_count = serializers.IntegerField(source='api_keys.count', read_only=True)
    total_api_requests = serializers.SerializerMethodField()
    
    class Meta:
        model = InstitutionalSubscriber
        fields = '__all__'
    
    def get_total_api_requests(self, obj):
        return sum(key.total_requests for key in obj.api_keys.all())


class InstitutionalSubscriberCreateSerializer(serializers.ModelSerializer):
    """
    Admin creating a new subscriber (from inquiry or directly).
    """
    class Meta:
        model = InstitutionalSubscriber
        fields = [
            'organization_name', 'organization_category',
            'registration_number', 'website',
            'contact_name', 'contact_email', 'contact_phone', 'contact_position',
            'tech_contact_name', 'tech_contact_email',
            'address', 'city', 'region',
            'plan', 'billing_cycle', 'trial_days',
            'preferred_regions', 'data_use_purpose',
            'admin_notes',
        ]


class InstitutionalPlanAdminSerializer(serializers.ModelSerializer):
    """
    Admin serializer for managing plans.
    """
    subscribers_count = serializers.IntegerField(
        source='subscribers.count', 
        read_only=True
    )
    
    class Meta:
        model = InstitutionalPlan
        fields = '__all__'
