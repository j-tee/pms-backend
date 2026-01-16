import os
import sys
import django
from django.urls import reverse, resolve
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

print(f"ROOT_URLCONF: {settings.ROOT_URLCONF}")

try:
    url = reverse('accounts:password_reset_request')
    print(f"Resolved URL for 'accounts:password_reset_request': {url}")
except Exception as e:
    print(f"Error reversing URL: {e}")

path = '/api/auth/password-reset/request/'
print(f"\nResolving path: {path}")
try:
    match = resolve(path)
    print(f"Match found: {match.view_name}")
except Exception as e:
    print(f"Error resolving path: {e}")
