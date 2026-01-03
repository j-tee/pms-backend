"""
Guest Order and POS URLs

Public endpoints for guest checkout (no auth required):
- /api/public/marketplace/order/...

Farmer endpoints for managing orders and POS (auth required):
- /api/marketplace/guest-orders/...
- /api/marketplace/pos/...
"""

from django.urls import path
from .guest_order_views import (
    # Public guest order endpoints
    RequestOTPView,
    VerifyOTPView,
    CreateGuestOrderView,
    VerifyGuestOrderView,
    TrackGuestOrderView,
    CancelGuestOrderView,
    # Farmer guest order management
    FarmerGuestOrderListView,
    FarmerGuestOrderDetailView,
    FarmerGuestOrderActionView,
    # POS endpoints
    POSSaleCreateView,
    POSSaleListView,
    POSSaleDetailView,
    POSSaleMarkCreditPaidView,
    POSSaleSummaryView,
)


# Public guest order endpoints (add to public_marketplace_urls.py)
public_guest_order_patterns = [
    path('order/request-otp/', RequestOTPView.as_view(), name='guest-order-request-otp'),
    path('order/verify-otp/', VerifyOTPView.as_view(), name='guest-order-verify-otp'),
    path('order/create/', CreateGuestOrderView.as_view(), name='guest-order-create'),
    path('order/verify/', VerifyGuestOrderView.as_view(), name='guest-order-verify'),
    path('order/track/', TrackGuestOrderView.as_view(), name='guest-order-track'),
    path('order/cancel/', CancelGuestOrderView.as_view(), name='guest-order-cancel'),
]


# Farmer guest order management (auth required)
farmer_guest_order_patterns = [
    path('guest-orders/', FarmerGuestOrderListView.as_view(), name='farmer-guest-order-list'),
    path('guest-orders/<uuid:pk>/', FarmerGuestOrderDetailView.as_view(), name='farmer-guest-order-detail'),
    path('guest-orders/<uuid:pk>/action/', FarmerGuestOrderActionView.as_view(), name='farmer-guest-order-action'),
]


# POS endpoints (auth required)
pos_patterns = [
    path('pos/sales/', POSSaleCreateView.as_view(), name='pos-sale-create'),
    path('pos/sales/list/', POSSaleListView.as_view(), name='pos-sale-list'),
    path('pos/sales/<uuid:pk>/', POSSaleDetailView.as_view(), name='pos-sale-detail'),
    path('pos/sales/<uuid:pk>/mark-paid/', POSSaleMarkCreditPaidView.as_view(), name='pos-sale-mark-paid'),
    path('pos/summary/', POSSaleSummaryView.as_view(), name='pos-summary'),
]
