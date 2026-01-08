"""
Subscription Serializers

Handles serialization for:
- Marketplace subscription/activation payments
- MoMo payment initialization
- Payment verification
- Invoice generation
"""

from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone
from .models import Subscription, SubscriptionPlan, SubscriptionPayment, SubscriptionInvoice
from sales_revenue.models import PlatformSettings


class MoMoProviderSerializer(serializers.Serializer):
    """Serializer for MoMo provider selection"""
    PROVIDER_CHOICES = [
        ('mtn', 'MTN Mobile Money'),
        ('vodafone', 'Vodafone Cash'),
        ('airteltigo', 'AirtelTigo Money'),
        ('telecel', 'Telecel Cash'),
    ]
    
    provider = serializers.ChoiceField(choices=PROVIDER_CHOICES)
    name = serializers.CharField(read_only=True)


class InitiatePaymentSerializer(serializers.Serializer):
    """
    Serializer for initiating Paystack payment for marketplace activation.
    
    Farmer is redirected to Paystack hosted checkout page where they
    can choose their preferred payment method (MoMo, Card, Bank, USSD).
    """
    callback_url = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="Optional URL to redirect after payment completion"
    )


class PaymentInitiatedResponseSerializer(serializers.Serializer):
    """Response after payment initialization"""
    status = serializers.CharField()
    message = serializers.CharField()
    reference = serializers.CharField()
    authorization_url = serializers.URLField(required=False, allow_null=True)
    access_code = serializers.CharField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    display_text = serializers.CharField(required=False)


class VerifyPaymentSerializer(serializers.Serializer):
    """Serializer for payment verification request"""
    reference = serializers.CharField(
        max_length=100,
        help_text="Payment reference from initialization"
    )


class PaymentVerificationResponseSerializer(serializers.Serializer):
    """Response from payment verification"""
    status = serializers.CharField()  # success, failed, pending, abandoned
    reference = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_at = serializers.DateTimeField(required=False, allow_null=True)
    channel = serializers.CharField(required=False)
    gateway_response = serializers.CharField(required=False)
    subscription_status = serializers.CharField(required=False)
    next_billing_date = serializers.DateField(required=False)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plan details"""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'price_monthly',
            'max_product_images', 'max_image_size_mb',
            'marketplace_listing', 'sales_tracking', 'analytics_dashboard',
            'api_access', 'trial_period_days', 'is_active', 'display_order'
        ]
        read_only_fields = fields


class SubscriptionStatusSerializer(serializers.ModelSerializer):
    """Serializer for current subscription status"""
    plan = SubscriptionPlanSerializer(read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_in_grace_period = serializers.BooleanField(read_only=True)
    days_until_suspension = serializers.IntegerField(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    amount_due = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'farm_name', 'status', 'start_date',
            'current_period_start', 'current_period_end', 'next_billing_date',
            'trial_start', 'trial_end', 'last_payment_date', 'last_payment_amount',
            'is_active', 'is_in_grace_period', 'days_until_suspension',
            'days_remaining', 'amount_due', 'auto_renew', 'reminder_count'
        ]
        read_only_fields = fields
    
    def get_days_remaining(self, obj):
        """Calculate days remaining in current period"""
        if obj.current_period_end:
            delta = obj.current_period_end - timezone.now().date()
            return max(0, delta.days)
        return None
    
    def get_amount_due(self, obj):
        """Get amount due for next billing"""
        if obj.status in ['past_due', 'suspended']:
            return obj.plan.price_monthly
        return None


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    """Serializer for subscription payment records"""
    subscription_farm = serializers.CharField(
        source='subscription.farm.farm_name', 
        read_only=True
    )
    
    class Meta:
        model = SubscriptionPayment
        fields = [
            'id', 'subscription_farm', 'amount', 'payment_method',
            'payment_reference', 'status', 'period_start', 'period_end',
            'gateway_provider', 'gateway_transaction_id', 'payment_date',
            'verified_at', 'created_at', 'notes'
        ]
        read_only_fields = fields


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for subscription invoices"""
    farm_name = serializers.CharField(
        source='subscription.farm.farm_name',
        read_only=True
    )
    
    class Meta:
        model = SubscriptionInvoice
        fields = [
            'id', 'invoice_number', 'farm_name', 'amount', 'description',
            'billing_period_start', 'billing_period_end', 'issue_date',
            'due_date', 'paid_date', 'status', 'created_at'
        ]
        read_only_fields = fields


class PaymentHistorySerializer(serializers.Serializer):
    """Serializer for payment history listing"""
    payments = SubscriptionPaymentSerializer(many=True)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_count = serializers.IntegerField()


class SubscriptionActivationSerializer(serializers.Serializer):
    """
    Serializer for activating/subscribing to marketplace access
    
    Used when a farmer first activates marketplace access
    """
    phone = serializers.CharField(
        max_length=15,
        help_text="Mobile money phone number for payment"
    )
    provider = serializers.ChoiceField(
        choices=[
            ('mtn', 'MTN Mobile Money'),
            ('vodafone', 'Vodafone Cash'),
            ('airteltigo', 'AirtelTigo Money'),
            ('telecel', 'Telecel Cash'),
        ],
        help_text="Mobile money provider"
    )
    accept_terms = serializers.BooleanField(
        help_text="Confirm acceptance of marketplace terms and conditions"
    )
    enable_auto_renew = serializers.BooleanField(
        default=True,
        help_text="Automatically renew subscription each month"
    )
    
    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must accept the terms and conditions to proceed"
            )
        return value
    
    def validate_phone(self, value):
        """Reuse phone validation from InitiatePaymentSerializer"""
        serializer = InitiatePaymentSerializer(data={'phone': value, 'provider': 'mtn'})
        if not serializer.is_valid():
            raise serializers.ValidationError(serializer.errors.get('phone', 'Invalid phone'))
        return serializer.validated_data['phone']


class MarketplaceAccessInfoSerializer(serializers.Serializer):
    """
    Serializer for marketplace access information
    
    Returns current status and pricing info
    """
    has_marketplace_access = serializers.BooleanField()
    subscription_type = serializers.CharField()
    subscription_status = serializers.CharField(required=False)
    current_period_end = serializers.DateField(required=False)
    next_billing_date = serializers.DateField(required=False)
    monthly_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    trial_days = serializers.IntegerField()
    is_government_subsidized = serializers.BooleanField()
    features = serializers.ListField(child=serializers.CharField())


class CancelSubscriptionSerializer(serializers.Serializer):
    """Serializer for subscription cancellation"""
    reason = serializers.ChoiceField(
        choices=[
            ('too_expensive', 'Too expensive'),
            ('not_using', 'Not using the marketplace'),
            ('found_alternative', 'Found an alternative'),
            ('seasonal_break', 'Taking a seasonal break'),
            ('closing_farm', 'Closing the farm'),
            ('other', 'Other'),
        ],
        help_text="Reason for cancellation"
    )
    other_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Additional details if 'other' selected"
    )
    confirm_cancellation = serializers.BooleanField(
        help_text="Confirm you want to cancel marketplace access"
    )
    
    def validate(self, data):
        if not data.get('confirm_cancellation'):
            raise serializers.ValidationError({
                'confirm_cancellation': 'Please confirm cancellation'
            })
        if data.get('reason') == 'other' and not data.get('other_reason'):
            raise serializers.ValidationError({
                'other_reason': 'Please provide a reason'
            })
        return data


class WebhookEventSerializer(serializers.Serializer):
    """Serializer for Paystack webhook events"""
    event = serializers.CharField()
    data = serializers.DictField()


class PaymentReminderSerializer(serializers.Serializer):
    """Response for payment reminder status"""
    subscription_id = serializers.UUIDField()
    farm_name = serializers.CharField()
    status = serializers.CharField()
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_date = serializers.DateField()
    days_overdue = serializers.IntegerField()
    reminder_count = serializers.IntegerField()
