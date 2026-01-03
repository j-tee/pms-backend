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
    # Admin
    AdminPartnerListView,
    AdminPartnerDetailView,
    AdminOfferListView,
    AdminOfferDetailView,
    AdminLeadListView,
    AdminLeadDetailView,
    AdminOfferAnalyticsView,
)


# Farmer-facing URLs (/api/advertising/)
farmer_urlpatterns = [
    path('offers/', FarmerOffersView.as_view(), name='farmer-offers'),
    path('offers/click/', OfferClickView.as_view(), name='offer-click'),
    path('offers/<uuid:offer_id>/dismiss/', DismissOfferView.as_view(), name='offer-dismiss'),
]

# Public URLs (/api/public/advertise/)
public_urlpatterns = [
    path('', AdvertiseWithUsView.as_view(), name='advertise-with-us'),
]

# Admin URLs (/api/admin/advertising/)
admin_urlpatterns = [
    path('partners/', AdminPartnerListView.as_view(), name='admin-partners'),
    path('partners/<uuid:id>/', AdminPartnerDetailView.as_view(), name='admin-partner-detail'),
    path('offers/', AdminOfferListView.as_view(), name='admin-offers'),
    path('offers/<uuid:id>/', AdminOfferDetailView.as_view(), name='admin-offer-detail'),
    path('leads/', AdminLeadListView.as_view(), name='admin-leads'),
    path('leads/<uuid:id>/', AdminLeadDetailView.as_view(), name='admin-lead-detail'),
    path('analytics/', AdminOfferAnalyticsView.as_view(), name='admin-analytics'),
]
