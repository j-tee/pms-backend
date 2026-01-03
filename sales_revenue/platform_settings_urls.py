"""
Platform Settings URL Configuration

Admin and public endpoints for platform settings management.
"""

from django.urls import path
from .platform_settings_views import (
    PlatformSettingsView,
    MarketplaceMonetizationView,
    PublicPlatformSettingsView,
    PlatformSettingsResetView,
)

app_name = 'platform_settings'

# Admin endpoints (require authentication)
admin_urlpatterns = [
    path('', PlatformSettingsView.as_view(), name='platform-settings'),
    path('monetization/', MarketplaceMonetizationView.as_view(), name='monetization-settings'),
    path('reset/', PlatformSettingsResetView.as_view(), name='platform-settings-reset'),
]

# Public endpoint (no auth required)
public_urlpatterns = [
    path('', PublicPlatformSettingsView.as_view(), name='public-platform-settings'),
]
