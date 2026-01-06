"""
Contact Management Admin URL Configuration

Separate admin URLs for contact message management.
"""
from django.urls import path
from .views import (
    ContactMessageListView,
    ContactMessageDetailView,
    ContactMessageUpdateView,
    ContactMessageReplyView,
    ContactMessageDeleteView,
    ContactStatsView
)

app_name = 'contact_admin'

urlpatterns = [
    path('contact-messages/', ContactMessageListView.as_view(), name='message-list'),
    path('contact-messages/<uuid:id>/', ContactMessageDetailView.as_view(), name='message-detail'),
    path('contact-messages/<uuid:id>/update/', ContactMessageUpdateView.as_view(), name='message-update'),
    path('contact-messages/<uuid:id>/reply/', ContactMessageReplyView.as_view(), name='message-reply'),
    path('contact-messages/<uuid:id>/delete/', ContactMessageDeleteView.as_view(), name='message-delete'),
    path('contact-stats/', ContactStatsView.as_view(), name='stats'),
]
