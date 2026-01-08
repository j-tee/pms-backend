"""
URL Configuration for Institutional Data Subscriptions.

Three URL namespaces:
1. Public - /api/public/data-subscriptions/ - Landing page, inquiries
2. Institutional - /api/institutional/ - Data API for subscribers
3. Admin - /api/admin/institutional/ - Management views
"""

from django.urls import path

from .institutional_views import (
    # Public
    InstitutionalPlansPublicView,
    InstitutionalInquiryCreateView,
    # Subscriber self-service
    SubscriberProfileView,
    SubscriberAPIKeysView,
    SubscriberAPIKeyDetailView,
    SubscriberUsageView,
    SubscriberPaymentsView,
    # Payment
    InitiateInstitutionalPaymentView,
    VerifyInstitutionalPaymentView,
    PaymentMethodsView,
    # Admin
    AdminInstitutionalDashboardView,
    AdminInquiryListView,
    AdminInquiryDetailView,
    AdminInquiryConvertView,
    AdminSubscriberListView,
    AdminSubscriberDetailView,
    AdminSubscriberVerifyView,
    AdminSubscriberActivateView,
    AdminPlansListView,
    AdminPlanDetailView,
)

# Import webhook from subscriptions.views
from .views import InstitutionalPaystackWebhookView

from .institutional_data_views import (
    ProductionOverviewView,
    ProductionTrendsView,
    RegionalBreakdownView,
    ConstituencyBreakdownView,
    MarketPricesView,
    MortalityDataView,
    SupplyForecastView,
    FarmPerformanceView,
    UsageStatusView,
)


# =============================================================================
# PUBLIC ENDPOINTS (No Auth)
# =============================================================================

public_urlpatterns = [
    path('plans/', InstitutionalPlansPublicView.as_view(), name='plans'),
    path('inquire/', InstitutionalInquiryCreateView.as_view(), name='inquire'),
    path('payment-methods/', PaymentMethodsView.as_view(), name='payment-methods'),
]


# =============================================================================
# INSTITUTIONAL DATA API (API Key Auth)
# =============================================================================

institutional_urlpatterns = [
    # Account & Usage
    path('profile/', SubscriberProfileView.as_view(), name='profile'),
    path('api-keys/', SubscriberAPIKeysView.as_view(), name='api-keys'),
    path('api-keys/<uuid:key_id>/', SubscriberAPIKeyDetailView.as_view(), name='api-key-detail'),
    path('usage/', UsageStatusView.as_view(), name='usage'),
    path('usage/history/', SubscriberUsageView.as_view(), name='usage-history'),
    path('payments/', SubscriberPaymentsView.as_view(), name='payments'),
    
    # Payment (Paystack Checkout)
    path('pay/', InitiateInstitutionalPaymentView.as_view(), name='initiate-payment'),
    path('pay/verify/<str:reference>/', VerifyInstitutionalPaymentView.as_view(), name='verify-payment'),
    path('payment-methods/', PaymentMethodsView.as_view(), name='payment-methods'),
    
    # Webhook (no auth - signature verified)
    path('webhooks/paystack/', InstitutionalPaystackWebhookView.as_view(), name='paystack-webhook'),
    
    # Data Endpoints
    path('production/overview/', ProductionOverviewView.as_view(), name='production-overview'),
    path('production/trends/', ProductionTrendsView.as_view(), name='production-trends'),
    path('production/regions/', RegionalBreakdownView.as_view(), name='production-regions'),
    path('production/constituencies/', ConstituencyBreakdownView.as_view(), name='production-constituencies'),
    path('market/prices/', MarketPricesView.as_view(), name='market-prices'),
    path('health/mortality/', MortalityDataView.as_view(), name='health-mortality'),
    path('supply/forecast/', SupplyForecastView.as_view(), name='supply-forecast'),
    path('farms/performance/', FarmPerformanceView.as_view(), name='farms-performance'),
]


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

admin_urlpatterns = [
    # Dashboard
    path('dashboard/', AdminInstitutionalDashboardView.as_view(), name='dashboard'),
    
    # Inquiries
    path('inquiries/', AdminInquiryListView.as_view(), name='inquiries'),
    path('inquiries/<uuid:pk>/', AdminInquiryDetailView.as_view(), name='inquiry-detail'),
    path('inquiries/<uuid:pk>/convert/', AdminInquiryConvertView.as_view(), name='inquiry-convert'),
    
    # Subscribers
    path('subscribers/', AdminSubscriberListView.as_view(), name='subscribers'),
    path('subscribers/<uuid:pk>/', AdminSubscriberDetailView.as_view(), name='subscriber-detail'),
    path('subscribers/<uuid:pk>/verify/', AdminSubscriberVerifyView.as_view(), name='subscriber-verify'),
    path('subscribers/<uuid:pk>/activate/', AdminSubscriberActivateView.as_view(), name='subscriber-activate'),
    
    # Plans
    path('plans/', AdminPlansListView.as_view(), name='plans'),
    path('plans/<uuid:pk>/', AdminPlanDetailView.as_view(), name='plan-detail'),
]
