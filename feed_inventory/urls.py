"""
Feed Inventory URL Configuration
"""

from django.urls import path

from .views import FeedStockView, FeedPurchaseView
from .consumption_views import AvailableFeedStockView, FeedConsumptionView

urlpatterns = [
    # Feed Purchases/Stock
    path('purchases/', FeedPurchaseView.as_view(), name='feed-purchase-create'),
    path('create/', FeedStockView.as_view(), name='feed-purchase-create-legacy'),
    path('stock/', FeedStockView.as_view(), name='feed-inventory-list'),
    path('stock/available/', AvailableFeedStockView.as_view(), name='available-feed-stock'),
    
    # Feed Consumption
    path('consumption/', FeedConsumptionView.as_view(), name='feed-consumption'),
]
