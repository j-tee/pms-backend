"""
Contact Management URL Configuration
"""
from django.urls import path
from .views import (
    ContactFormSubmitView,
    ContactMessageListView,
    ContactMessageDetailView,
    ContactMessageUpdateView,
    ContactMessageReplyView,
    ContactMessageDeleteView,
    ContactStatsView
)

app_name = 'contact'

# Public URLs (no auth required)
public_urlpatterns = [
    path('submit', ContactFormSubmitView.as_view(), name='submit'),
]

# Admin URLs (auth required)
admin_urlpatterns = [
    path('', ContactMessageListView.as_view(), name='list'),
    path('stats', ContactStatsView.as_view(), name='stats'),
    path('<uuid:id>', ContactMessageDetailView.as_view(), name='detail'),
    path('<uuid:id>/update', ContactMessageUpdateView.as_view(), name='update'),
    path('<uuid:id>/reply', ContactMessageReplyView.as_view(), name='reply'),
    path('<uuid:id>/delete', ContactMessageDeleteView.as_view(), name='delete'),
]

urlpatterns = public_urlpatterns
