"""
Subscription URL Routes

Endpoints for marketplace subscription payments via MoMo
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
    
    # MoMo providers list
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
