"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.views.generic import RedirectView
from core.admin_site import yea_admin_site

# Import platform settings URL patterns
from sales_revenue.platform_settings_urls import admin_urlpatterns as platform_settings_admin_urls
from sales_revenue.platform_settings_urls import public_urlpatterns as platform_settings_public_urls

# Import advertising URL patterns
from advertising.urls import farmer_urlpatterns as advertising_farmer_urls
from advertising.urls import public_urlpatterns as advertising_public_urls
from advertising.urls import admin_urlpatterns as advertising_admin_urls

# Import subscription URL patterns
from subscriptions.urls import urlpatterns as subscription_urls
from subscriptions.urls import webhook_urlpatterns as subscription_webhook_urls
from subscriptions.urls import admin_urlpatterns as subscription_admin_urls

# Import institutional data subscription URL patterns
from subscriptions.institutional_urls import (
    public_urlpatterns as institutional_public_urls,
    institutional_urlpatterns as institutional_api_urls,
    admin_urlpatterns as institutional_admin_urls,
)

# Import farmer analytics URL patterns
from dashboards.farmer_analytics_urls import urlpatterns as farmer_analytics_urls

# Import National Admin reports URL patterns
from dashboards.national_admin_urls import urlpatterns as national_admin_reports_urls

# Import contact management URL patterns
from contact.urls import urlpatterns as contact_public_urls
from contact.admin_urls import urlpatterns as contact_admin_urls

# Import CMS URL patterns
from cms.urls import urlpatterns as cms_public_urls
from cms.admin_urls import urlpatterns as cms_admin_urls

# Import Procurement URL patterns
from procurement.urls import farmer_urlpatterns as procurement_farmer_urls
from procurement.admin_urls import urlpatterns as procurement_admin_urls

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    path('admin/', yea_admin_site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/dashboards/', include('dashboards.urls')),
    path('api/farms/analytics/', include((farmer_analytics_urls, 'farmer_analytics'))),  # Farmer analytics
    path('api/admin/', include('accounts.admin_urls')),
    path('api/admin/analytics/', include('dashboards.analytics_urls', namespace='admin-analytics')),  # YEA Admin analytics
    path('api/admin/reports/', include((national_admin_reports_urls, 'national_admin_reports'))),  # National Admin / Minister reports
    path('api/admin/inventory/', include('sales_revenue.inventory_urls', namespace='admin-inventory')),  # Government inventory analytics
    path('api/admin/platform-settings/', include((platform_settings_admin_urls, 'platform_settings'))),  # Platform settings (Super Admin)
    path('api/admin/subscriptions/', include((subscription_admin_urls, 'admin_subscriptions'))),  # Admin subscription management
    path('api/admin/procurement/', include((procurement_admin_urls, 'admin_procurement'))),  # Admin procurement management (orders, invoices, assignments)
    path('api/farms/', include('farms.management_urls')),  # Authenticated farm management
    path('api/extension/', include('farms.extension_urls')),  # Extension officer / field officer endpoints
    path('api/flocks/', include('flock_management.urls')),  # Flock management
    path('api/feed/', include('feed_inventory.urls')),  # Feed inventory management
    path('api/expenses/', include('expenses.urls')),  # Expense tracking (labor, utilities, bedding, transport, etc.)
    path('api/inventory/', include('sales_revenue.inventory_urls')),  # Farmer inventory management
    path('api/marketplace/', include('sales_revenue.marketplace_urls')),  # Marketplace (farmer-scoped)
    path('api/processing/', include('sales_revenue.processing_urls')),  # Processing batches (birds → products)
    path('api/returns/', include('sales_revenue.returns_refunds_urls')),  # Returns and refunds
    path('api/procurement/', include((procurement_farmer_urls, 'farmer_procurement'))),  # Farmer procurement (assignments, deliveries, earnings)
    path('api/subscriptions/', include((subscription_urls, 'subscriptions'))),  # Marketplace subscription payments
    path('api/subscriptions/webhooks/', include((subscription_webhook_urls, 'subscription_webhooks'))),  # Payment webhooks
    path('api/public/marketplace/', include('sales_revenue.public_marketplace_urls')),  # Public marketplace (no auth)
    path('api/public/platform-settings/', include((platform_settings_public_urls, 'public_platform_settings'))),  # Public platform settings
    path('api/public/advertise/', include((advertising_public_urls, 'advertise'))),  # Advertise with us (lead capture)
    path('api/advertising/', include((advertising_farmer_urls, 'advertising'))),  # Partner offers for farmers
    path('api/admin/advertising/', include((advertising_admin_urls, 'admin_advertising'))),  # Admin advertising management
    path('api/contact/', include((contact_public_urls, 'contact'))),  # Public contact form
    path('api/admin/', include((contact_admin_urls, 'contact_admin'))),  # Admin contact management
    path('api/cms/', include((cms_admin_urls, 'cms_admin'))),  # CMS management (SUPER_ADMIN only)
    path('api/public/cms/', include((cms_public_urls, 'cms_public'))),  # Public content pages (About Us, etc.)
    path('api/public/data-subscriptions/', include((institutional_public_urls, 'institutional_public'))),  # Institutional data subscriptions landing
    path('api/institutional/', include((institutional_api_urls, 'institutional'))),  # Institutional data API
    path('api/admin/institutional/', include((institutional_admin_urls, 'institutional_admin'))),  # Admin institutional management
    path('api/', include('farms.urls')),  # Public farm application endpoints
]

