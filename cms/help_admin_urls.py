"""
Help Files Admin URLs

Admin endpoints for managing help center content.
Only accessible by SUPER_ADMIN.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import help_admin_views

router = DefaultRouter()
router.register('categories', help_admin_views.HelpCategoryAdminViewSet, basename='help-category-admin')
router.register('articles', help_admin_views.HelpArticleAdminViewSet, basename='help-article-admin')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),
    
    # Analytics
    path('analytics/', help_admin_views.HelpAnalyticsView.as_view(), name='help-analytics'),
]
