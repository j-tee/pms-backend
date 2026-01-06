"""
CMS URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Admin router for content management
router = DefaultRouter()
router.register(r'pages', views.ContentPageViewSet, basename='content-page')

# Admin URLs (SUPER_ADMIN only)
admin_urlpatterns = [
    path('', include(router.urls)),
    path('company-profile/', views.CompanyProfileView.as_view(), name='company-profile'),
]

urlpatterns = [
    path('admin/', include(admin_urlpatterns)),
]
