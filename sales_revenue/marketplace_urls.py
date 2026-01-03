"""
Marketplace URL Configuration

All marketplace endpoints are protected by authentication and farm-scoped access.
Farmers can only access data belonging to their own farm.

Endpoint Structure:
- /api/marketplace/                     - Dashboard overview
- /api/marketplace/products/            - Product list/create
- /api/marketplace/products/<id>/       - Product detail/update/delete
- /api/marketplace/customers/           - Customer list/create
- /api/marketplace/customers/<id>/      - Customer detail/update/delete
- /api/marketplace/orders/              - Order list/create
- /api/marketplace/orders/<id>/         - Order detail/update
- /api/marketplace/statistics/          - Daily statistics
- /api/marketplace/analytics/           - Analytics for charts
"""

from django.urls import path
from .marketplace_views import (
    # Product views
    ProductCategoryListView,
    ProductListCreateView,
    ProductDetailView,
    ProductStockUpdateView,
    ProductImageUploadView,
    ProductBatchTraceabilityView,
    
    # Customer views
    CustomerListCreateView,
    CustomerDetailView,
    
    # Order views
    OrderListCreateView,
    OrderDetailView,
    OrderStatusUpdateView,
    OrderCancelView,
    
    # Dashboard & Analytics
    MarketplaceDashboardView,
    MarketplaceStatisticsView,
    MarketplaceAnalyticsView,
)

app_name = 'marketplace'

urlpatterns = [
    # Dashboard
    path('', MarketplaceDashboardView.as_view(), name='dashboard'),
    
    # Product Categories (read-only)
    path('categories/', ProductCategoryListView.as_view(), name='category-list'),
    
    # Products
    path('products/', ProductListCreateView.as_view(), name='product-list'),
    path('products/<uuid:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<uuid:pk>/stock/', ProductStockUpdateView.as_view(), name='product-stock'),
    path('products/<uuid:pk>/batches/', ProductBatchTraceabilityView.as_view(), name='product-batches'),
    path('products/<uuid:product_pk>/images/', ProductImageUploadView.as_view(), name='product-image-upload'),
    
    # Customers
    path('customers/', CustomerListCreateView.as_view(), name='customer-list'),
    path('customers/<uuid:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    
    # Orders (logged-in customer orders)
    path('orders/', OrderListCreateView.as_view(), name='order-list'),
    path('orders/<uuid:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<uuid:pk>/status/', OrderStatusUpdateView.as_view(), name='order-status'),
    path('orders/<uuid:pk>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
    
    # Statistics & Analytics
    path('statistics/', MarketplaceStatisticsView.as_view(), name='statistics'),
    path('analytics/', MarketplaceAnalyticsView.as_view(), name='analytics'),
]

# Add guest order management and POS endpoints
from .guest_order_urls import farmer_guest_order_patterns, pos_patterns
urlpatterns += farmer_guest_order_patterns
urlpatterns += pos_patterns
