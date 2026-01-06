"""
CMS Public URLs
"""
from django.urls import path
from . import views

urlpatterns = [
    # Public content pages (no auth required)
    path('pages/<slug:slug>/', views.PublicContentPageView.as_view(), name='public-page'),
    
    # Dedicated endpoints for common pages
    path('about-us/', views.AboutUsView.as_view(), name='about-us'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy-policy'),
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms-of-service'),
]
