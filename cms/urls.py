"""
CMS Public URLs

Public endpoints for legal and informational pages.
All endpoints are accessible without authentication for AdSense compliance.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Public content pages (no auth required)
    path('pages/<slug:slug>/', views.PublicContentPageView.as_view(), name='public-page'),
    
    # Dedicated endpoints for common pages (AdSense compliance)
    path('about-us/', views.AboutUsView.as_view(), name='about-us'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy-policy'),
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms-of-service'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('contact/', views.ContactInfoView.as_view(), name='contact-info'),
    path('contact-us/', views.ContactInfoView.as_view(), name='contact-us'),  # Alias for contact
    
    # List all published public pages
    path('pages/', views.PublicPageListView.as_view(), name='public-page-list'),
]