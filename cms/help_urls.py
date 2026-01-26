"""
Help Files Public URLs

Public endpoints for the help center / knowledge base.
All endpoints are accessible without authentication.
"""
from django.urls import path
from . import help_views

urlpatterns = [
    # Help Center Overview (main entry point)
    path('', help_views.HelpOverviewView.as_view(), name='help-overview'),
    
    # Categories
    path('categories/', help_views.HelpCategoryListView.as_view(), name='help-categories'),
    path('categories/<slug:slug>/', help_views.HelpCategoryDetailView.as_view(), name='help-category-detail'),
    
    # Articles
    path('articles/', help_views.HelpArticleListView.as_view(), name='help-articles'),
    path('articles/<slug:slug>/', help_views.HelpArticleDetailView.as_view(), name='help-article-detail'),
    
    # Search
    path('search/', help_views.HelpSearchView.as_view(), name='help-search'),
    
    # Popular content
    path('popular/', help_views.PopularArticlesView.as_view(), name='help-popular'),
    path('popular-searches/', help_views.PopularSearchesView.as_view(), name='help-popular-searches'),
    
    # Feedback
    path('feedback/', help_views.HelpFeedbackView.as_view(), name='help-feedback'),
]
