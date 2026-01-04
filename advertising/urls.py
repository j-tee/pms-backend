"""
Advertising URL Configuration
"""

from django.urls import path
from .views import (
    # Farmer-facing
    FarmerOffersView,
    OfferClickView,
    DismissOfferView,
    # Public
    AdvertiseWithUsView,
    # Public webhook
    ConversionWebhookView,
    # Admin - Partners
    AdminPartnerListView,
    AdminPartnerDetailView,
    # Admin - Offers
    AdminOfferListView,
    AdminOfferDetailView,
    # Admin - A/B Testing
    AdminOfferVariantListView,
    AdminOfferVariantDetailView,
    AdminABTestResultsView,
    # Admin - Leads
    AdminLeadListView,
    AdminLeadDetailView,
    # Admin - Conversions
    AdminConversionListView,
    AdminConversionDetailView,
    AdminVerifyConversionView,
    # Admin - Payments
    AdminPartnerPaymentListView,
    AdminPartnerPaymentDetailView,
    AdminMarkPaymentPaidView,
    # Admin - Webhook Keys
    AdminWebhookKeyListView,
    AdminWebhookKeyDetailView,
    AdminRegenerateWebhookKeyView,
    # Admin - Analytics
    AdminOfferAnalyticsView,
    AdminAdvertisingRevenueView,
)


# Farmer-facing URLs (/api/advertising/)
farmer_urlpatterns = [
    path('offers/', FarmerOffersView.as_view(), name='farmer-offers'),
    path('offers/click/', OfferClickView.as_view(), name='offer-click'),
    path('offers/<uuid:offer_id>/dismiss/', DismissOfferView.as_view(), name='offer-dismiss'),
    # Webhook for partners (no auth, uses API key)
    path('webhook/conversion/', ConversionWebhookView.as_view(), name='conversion-webhook'),
]

# Public URLs (/api/public/advertise/)
public_urlpatterns = [
    path('', AdvertiseWithUsView.as_view(), name='advertise-with-us'),
]

# Admin URLs (/api/admin/advertising/)
admin_urlpatterns = [
    # Partners
    path('partners/', AdminPartnerListView.as_view(), name='admin-partners'),
    path('partners/<uuid:id>/', AdminPartnerDetailView.as_view(), name='admin-partner-detail'),
    
    # Offers
    path('offers/', AdminOfferListView.as_view(), name='admin-offers'),
    path('offers/<uuid:id>/', AdminOfferDetailView.as_view(), name='admin-offer-detail'),
    
    # A/B Testing Variants
    path('offers/<uuid:offer_id>/variants/', AdminOfferVariantListView.as_view(), name='admin-offer-variants'),
    path('offers/<uuid:offer_id>/ab-results/', AdminABTestResultsView.as_view(), name='admin-ab-results'),
    path('variants/<uuid:id>/', AdminOfferVariantDetailView.as_view(), name='admin-variant-detail'),
    
    # Leads
    path('leads/', AdminLeadListView.as_view(), name='admin-leads'),
    path('leads/<uuid:id>/', AdminLeadDetailView.as_view(), name='admin-lead-detail'),
    
    # Conversions
    path('conversions/', AdminConversionListView.as_view(), name='admin-conversions'),
    path('conversions/<uuid:id>/', AdminConversionDetailView.as_view(), name='admin-conversion-detail'),
    path('conversions/<uuid:id>/verify/', AdminVerifyConversionView.as_view(), name='admin-verify-conversion'),
    
    # Partner Payments (Revenue - SUPER_ADMIN only)
    path('payments/', AdminPartnerPaymentListView.as_view(), name='admin-ad-payments'),
    path('payments/<uuid:id>/', AdminPartnerPaymentDetailView.as_view(), name='admin-ad-payment-detail'),
    path('payments/<uuid:id>/mark-paid/', AdminMarkPaymentPaidView.as_view(), name='admin-mark-payment-paid'),
    
    # Webhook Keys
    path('webhook-keys/', AdminWebhookKeyListView.as_view(), name='admin-webhook-keys'),
    path('webhook-keys/<uuid:id>/', AdminWebhookKeyDetailView.as_view(), name='admin-webhook-key-detail'),
    path('webhook-keys/<uuid:id>/regenerate/', AdminRegenerateWebhookKeyView.as_view(), name='admin-regenerate-key'),
    
    # Analytics
    path('analytics/', AdminOfferAnalyticsView.as_view(), name='admin-analytics'),
    path('revenue/', AdminAdvertisingRevenueView.as_view(), name='admin-ad-revenue'),
]
