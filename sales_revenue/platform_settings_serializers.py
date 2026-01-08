"""
Platform Settings Serializers

Serializers for super admin platform configuration management.
"""

from rest_framework import serializers
from .models import PlatformSettings


class PlatformSettingsSerializer(serializers.ModelSerializer):
    """
    Full serializer for platform settings (Super Admin only).
    """
    last_modified_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PlatformSettings
        fields = [
            'id',
            # Commission Structure
            'commission_tier_1_percentage',
            'commission_tier_1_threshold',
            'commission_tier_2_percentage',
            'commission_tier_2_threshold',
            'commission_tier_3_percentage',
            'commission_minimum_amount',
            # Paystack Configuration
            'paystack_fee_bearer',
            'paystack_settlement_schedule',
            # Payment Retry
            'payment_retry_max_attempts',
            'payment_retry_delay_seconds',
            # Refund Configuration
            'refund_eligibility_hours',
            'payment_auto_refund_hours',
            'enable_refunds',
            'enable_auto_refunds',
            'enable_instant_settlements',
            # Marketplace Activation (Monetization)
            'marketplace_activation_fee',
            'marketplace_trial_days',
            'marketplace_grace_period_days',
            # Government Subsidy
            'enable_government_subsidy',
            'government_subsidy_percentage',
            # Transaction Commission (SUSPENDED)
            'enable_transaction_commission',
            # Advertising & Free Tier
            'enable_ads',
            'free_tier_can_view_marketplace',
            'free_tier_can_view_prices',
            'free_tier_can_access_education',
            # Metadata
            'notes',
            'last_modified_by',
            'last_modified_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_modified_by', 'last_modified_by_name']
    
    def get_last_modified_by_name(self, obj):
        if obj.last_modified_by:
            return obj.last_modified_by.get_full_name() or obj.last_modified_by.username
        return None


class MarketplaceMonetizationSerializer(serializers.ModelSerializer):
    """
    Subset serializer focused on marketplace monetization settings.
    For quick access to monetization config without full settings.
    """
    class Meta:
        model = PlatformSettings
        fields = [
            # Marketplace Activation
            'marketplace_activation_fee',
            'marketplace_trial_days',
            'marketplace_grace_period_days',
            # Government Subsidy
            'enable_government_subsidy',
            'government_subsidy_percentage',
            # Transaction Commission (SUSPENDED)
            'enable_transaction_commission',
            # Commission Tiers (for transaction commission if ever enabled)
            'commission_tier_1_percentage',
            'commission_tier_2_percentage',
            'commission_tier_3_percentage',
            'commission_minimum_amount',
            # Advertising & Free Tier
            'enable_ads',
            'free_tier_can_view_marketplace',
            'free_tier_can_view_prices',
            'free_tier_can_access_education',
            # Metadata
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class PublicPlatformSettingsSerializer(serializers.ModelSerializer):
    """
    Public-facing settings (non-sensitive info for frontend).
    """
    class Meta:
        model = PlatformSettings
        fields = [
            'marketplace_activation_fee',
            'marketplace_trial_days',
            'free_tier_can_view_marketplace',
            'free_tier_can_view_prices',
            'free_tier_can_access_education',
        ]
