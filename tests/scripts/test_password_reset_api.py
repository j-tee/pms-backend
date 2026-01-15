import os
import sys
import django

# Setup Django environment FIRST before importing anything from Django/DRF
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Now import after Django is set up
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

def test_password_reset_api():
    print("Starting Password Reset API Test...")
    
    client = APIClient()
    
    # Create a test user
    email = "api_test@example.com"
    User.objects.filter(email=email).delete()
    User.objects.create_user(
        username="api_test",
        email=email,
        password="password123",
        phone="+233244123456"  # Add phone to avoid unique constraint error
    )
    
    url = '/api/auth/password-reset/request/'
    data = {'email': email}
    
    print(f"Testing POST to {url}")
    response = client.post(url, data, format='json')
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.data}")
    
    if response.status_code == status.HTTP_200_OK:
        print("SUCCESS: Endpoint is reachable and returned 200.")
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        print("FAILURE: Endpoint returned 404.")
    else:
        print(f"FAILURE: Unexpected status code {response.status_code}")

if __name__ == "__main__":
    test_password_reset_api()
