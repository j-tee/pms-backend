"""
CMS App Configuration
Content Management System for platform pages (About Us, Privacy Policy, etc.)
"""
from django.apps import AppConfig


class CmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cms'
    verbose_name = 'Content Management System'
