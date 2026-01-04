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

urlpatterns = [
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    path('admin/', yea_admin_site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/dashboards/', include('dashboards.urls')),
    path('api/admin/', include('accounts.admin_urls')),
    path('api/admin/inventory/', include('sales_revenue.inventory_urls', namespace='admin-inventory')),  # Government inventory analytics
    path('api/admin/platform-settings/', include((platform_settings_admin_urls, 'platform_settings'))),  # Platform settings (Super Admin)
    path('api/farms/', include('farms.management_urls')),  # Authenticated farm management
    path('api/extension/', include('farms.extension_urls')),  # Extension officer / field officer endpoints
    path('api/flocks/', include('flock_management.urls')),  # Flock management
    path('api/feed/', include('feed_inventory.urls')),  # Feed inventory management
    path('api/inventory/', include('sales_revenue.inventory_urls')),  # Farmer inventory management
    path('api/marketplace/', include('sales_revenue.marketplace_urls')),  # Marketplace (farmer-scoped)
    path('api/processing/', include('sales_revenue.processing_urls')),  # Processing batches (birds → products)
    path('api/public/marketplace/', include('sales_revenue.public_marketplace_urls')),  # Public marketplace (no auth)
    path('api/public/platform-settings/', include((platform_settings_public_urls, 'public_platform_settings'))),  # Public platform settings
    path('api/public/advertise/', include((advertising_public_urls, 'advertise'))),  # Advertise with us (lead capture)
    path('api/advertising/', include((advertising_farmer_urls, 'advertising'))),  # Partner offers for farmers
    path('api/admin/advertising/', include((advertising_admin_urls, 'admin_advertising'))),  # Admin advertising management
    path('api/', include('farms.urls')),  # Public farm application endpoints
]

