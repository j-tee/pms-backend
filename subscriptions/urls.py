"""
Subscription URL Routes

Endpoints for marketplace subscription payments via Paystack
"""

from django.urls import path
from .views import (
    MarketplaceAccessInfoView,
    SubscriptionPlansView,
    CurrentSubscriptionView,
    InitiateSubscriptionPaymentView,
    VerifyPaymentView,
    PaymentHistoryView,
    CancelSubscriptionView,
    ReactivateSubscriptionView,
    PaystackWebhookView,
    MoMoProvidersView,
    PaymentMethodsView,
    AdminVerifyPaymentView,
)

app_name = 'subscriptions'

# Farmer-facing endpoints (require authentication)
urlpatterns = [
    # Marketplace access info
    path('marketplace-access/', MarketplaceAccessInfoView.as_view(), name='marketplace-access'),
    
    # Subscription plans
    path('plans/', SubscriptionPlansView.as_view(), name='plans'),
    
    # Current subscription status
    path('current/', CurrentSubscriptionView.as_view(), name='current'),
    
    # Initiate payment
    path('pay/', InitiateSubscriptionPaymentView.as_view(), name='pay'),
    
    # Verify payment
    path('verify/<str:reference>/', VerifyPaymentView.as_view(), name='verify'),
    
    # Payment history
    path('payments/', PaymentHistoryView.as_view(), name='payment-history'),
    
    # Cancel subscription
    path('cancel/', CancelSubscriptionView.as_view(), name='cancel'),
    
    # Reactivate subscription
    path('reactivate/', ReactivateSubscriptionView.as_view(), name='reactivate'),
    
    # Payment methods (recommended)
    path('payment-methods/', PaymentMethodsView.as_view(), name='payment-methods'),
    
    # MoMo providers list (deprecated, use payment-methods instead)
    path('momo-providers/', MoMoProvidersView.as_view(), name='momo-providers'),
]

# Webhook endpoints (no authentication, signature verified)
webhook_urlpatterns = [
    path('paystack/', PaystackWebhookView.as_view(), name='paystack-webhook'),
]

# Admin endpoints
admin_urlpatterns = [
    path('verify-payment/', AdminVerifyPaymentView.as_view(), name='admin-verify-payment'),
]
