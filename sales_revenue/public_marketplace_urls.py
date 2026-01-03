"""
Public Marketplace URLs

These endpoints are publicly accessible without authentication.
They power the public-facing marketplace where anyone can browse
products from all farms.

Base URL: /api/public/marketplace/

Endpoints:
- GET  /                        - Marketplace home (featured, latest, etc.)
- GET  /products/               - Browse all products
- GET  /products/{id}/          - View product details
- GET  /products/search/        - Advanced product search
- GET  /categories/             - List product categories
- GET  /farms/                  - List farms with products
- GET  /farms/{farm_id}/        - View farm profile/storefront
- GET  /farms/{farm_id}/products/ - List products from a farm
- POST /inquiries/              - Submit order inquiry
"""

from django.urls import path
from .public_marketplace_views import (
    PublicMarketplaceHomeView,
    PublicProductListView,
    PublicProductDetailView,
    PublicProductSearchView,
    PublicCategoryListView,
    PublicLocationFiltersView,
    PublicFarmListView,
    PublicFarmProfileView,
    PublicFarmProductsView,
    PublicOrderInquiryView,
)

from .guest_order_urls import public_guest_order_patterns

app_name = 'public_marketplace'

urlpatterns = [
    # Marketplace Home
    path('', PublicMarketplaceHomeView.as_view(), name='home'),
    
    # Products
    path('products/', PublicProductListView.as_view(), name='product-list'),
    path('products/<uuid:id>/', PublicProductDetailView.as_view(), name='product-detail'),
    path('products/search/', PublicProductSearchView.as_view(), name='product-search'),
    
    # Categories
    path('categories/', PublicCategoryListView.as_view(), name='category-list'),
    
    # Location Filters (regions, districts, constituencies)
    path('locations/', PublicLocationFiltersView.as_view(), name='location-filters'),
    
    # Farms
    path('farms/', PublicFarmListView.as_view(), name='farm-list'),
    path('farms/<uuid:farm_id>/', PublicFarmProfileView.as_view(), name='farm-profile'),
    path('farms/<uuid:farm_id>/products/', PublicFarmProductsView.as_view(), name='farm-products'),
    
    # Order Inquiries (legacy)
    path('inquiries/', PublicOrderInquiryView.as_view(), name='order-inquiry'),
] + public_guest_order_patterns  # Add guest order endpoints
