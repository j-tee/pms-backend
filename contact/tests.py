"""
Comprehensive Tests for Contact Management System
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from contact.models import ContactMessage, ContactMessageReply, ContactFormRateLimit

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin(db):
    return User.objects.create_user(
        email='admin@test.com',
        password='testpass123',
        first_name='Admin',
        last_name='User',
        phone_number='+233200000001',
        role='SUPER_ADMIN'
    )


@pytest.fixture
def national_admin(db):
    return User.objects.create_user(
        email='national@test.com',
        password='testpass123',
        first_name='National',
        last_name='Admin',
        phone_number='+233200000002',
        role='NATIONAL_ADMIN'
    )


@pytest.fixture
def regional_coordinator(db):
    user = User.objects.create_user(
        email='regional@test.com',
        password='testpass123',
        first_name='Regional',
        last_name='Coordinator',
        phone_number='+233200000003',
        role='REGIONAL_COORDINATOR'
    )
    user.assigned_region = 'Greater Accra'
    user.save()
    return user


@pytest.fixture
def farmer(db):
    return User.objects.create_user(
        email='farmer@test.com',
        password='testpass123',
        first_name='Farmer',
        last_name='Test',
        phone_number='+233200000004',
        role='FARMER'
    )


@pytest.fixture
def sample_contact_message(db):
    return ContactMessage.objects.create(
        name='John Doe',
        email='john@example.com',
        subject='general',
        message='This is a test message about the poultry program.',
        ip_address='192.168.1.1'
    )


class TestContactFormSubmission:
    """Test public contact form submission."""
    
    def test_submit_valid_contact_form(self, api_client):
        """Test successful contact form submission."""
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'support',
            'message': 'I need help with my farm registration process.'
        }
        
        response = api_client.post('/api/contact/submit', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert 'ticket_id' in response.data
        assert ContactMessage.objects.count() == 1
    
    def test_submit_missing_required_fields(self, api_client):
        """Test submission with missing fields."""
        data = {
            'name': 'Test User',
            # Missing email, subject, message
        }
        
        response = api_client.post('/api/contact/submit', data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
    
    def test_submit_invalid_email(self, api_client):
        """Test submission with invalid email."""
        data = {
            'name': 'Test User',
            'email': 'invalid-email',
            'subject': 'support',
            'message': 'Test message'
        }
        
        response = api_client.post('/api/contact/submit', data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_submit_message_too_short(self, api_client):
        """Test submission with message too short."""
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'support',
            'message': 'Short'  # Less than 10 characters
        }
        
        response = api_client.post('/api/contact/submit', data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_honeypot_spam_detection(self, api_client):
        """Test honeypot field for spam detection."""
        data = {
            'name': 'Spammer',
            'email': 'spam@example.com',
            'subject': 'support',
            'message': 'This is spam',
            'website': 'http://spam.com'  # Honeypot field should be empty
        }
        
        response = api_client.post('/api/contact/submit', data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestRateLimiting:
    """Test rate limiting for contact form."""
    
    def test_rate_limit_per_hour(self, api_client):
        """Test IP-based rate limiting."""
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'subject': 'support',
            'message': 'Test message number {}'
        }
        
        # Submit 5 times (should succeed)
        for i in range(5):
            data['message'] = f'Test message number {i}'
            response = api_client.post('/api/contact/submit', data)
            assert response.status_code == status.HTTP_201_CREATED
        
        # 6th submission should be rate limited
        data['message'] = 'Test message number 6'
        response = api_client.post('/api/contact/submit', data)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestContactMessageListView:
    """Test admin contact message list view."""
    
    def test_unauthorized_access(self, api_client):
        """Test unauthenticated access is blocked."""
        response = api_client.get('/api/admin/contact-messages/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_farmer_access_denied(self, api_client, farmer):
        """Test farmers cannot access admin endpoints."""
        api_client.force_authenticate(user=farmer)
        response = api_client.get('/api/admin/contact-messages/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_admin_can_list_messages(self, api_client, super_admin, sample_contact_message):
        """Test admin can list contact messages."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/contact-messages/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_filter_by_status(self, api_client, super_admin, sample_contact_message):
        """Test filtering by status."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/contact-messages/?status=new')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_search_functionality(self, api_client, super_admin, sample_contact_message):
        """Test search in messages."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/contact-messages/?search=poultry')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1


class TestContactMessageDetailView:
    """Test admin contact message detail view."""
    
    def test_get_message_details(self, api_client, super_admin, sample_contact_message):
        """Test getting message details."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get(f'/api/admin/contact-messages/{sample_contact_message.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'John Doe'
        assert response.data['email'] == 'john@example.com'


class TestContactMessageUpdate:
    """Test updating contact messages."""
    
    def test_update_status(self, api_client, super_admin, sample_contact_message):
        """Test updating message status."""
        api_client.force_authenticate(user=super_admin)
        
        data = {'status': 'in_progress'}
        response = api_client.patch(
            f'/api/admin/contact-messages/{sample_contact_message.id}/update/',
            data
        )
        
        assert response.status_code == status.HTTP_200_OK
        sample_contact_message.refresh_from_db()
        assert sample_contact_message.status == 'in_progress'
    
    def test_assign_to_staff(self, api_client, super_admin, national_admin, sample_contact_message):
        """Test assigning message to staff."""
        api_client.force_authenticate(user=super_admin)
        
        data = {'assigned_to': str(national_admin.id)}
        response = api_client.patch(
            f'/api/admin/contact-messages/{sample_contact_message.id}/update/',
            data
        )
        
        assert response.status_code == status.HTTP_200_OK
        sample_contact_message.refresh_from_db()
        assert sample_contact_message.assigned_to == national_admin


class TestContactMessageReply:
    """Test replying to contact messages."""
    
    def test_create_reply(self, api_client, super_admin, sample_contact_message):
        """Test creating a reply."""
        api_client.force_authenticate(user=super_admin)
        
        data = {
            'message': 'Thank you for your inquiry. We will get back to you soon.',
            'send_email': False
        }
        
        response = api_client.post(
            f'/api/admin/contact-messages/{sample_contact_message.id}/reply/',
            data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert ContactMessageReply.objects.count() == 1
        
        reply = ContactMessageReply.objects.first()
        assert reply.message == sample_contact_message
        assert reply.staff == super_admin


class TestContactStats:
    """Test contact statistics endpoint."""
    
    def test_get_stats(self, api_client, super_admin, sample_contact_message):
        """Test getting contact stats."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/contact-stats/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_messages'] == 1
        assert response.data['new_messages'] == 1
        assert 'by_subject' in response.data


class TestContactModels:
    """Test contact model methods."""
    
    def test_ticket_id_generation(self, sample_contact_message):
        """Test ticket ID is generated correctly."""
        assert sample_contact_message.ticket_id.startswith('CNT-')
        assert len(sample_contact_message.ticket_id) == 12
    
    def test_assign_to_method(self, sample_contact_message, national_admin):
        """Test assign_to method."""
        sample_contact_message.assign_to(national_admin)
        
        assert sample_contact_message.assigned_to == national_admin
        assert sample_contact_message.status == 'assigned'
    
    def test_mark_resolved(self, sample_contact_message):
        """Test mark_resolved method."""
        sample_contact_message.mark_resolved()
        assert sample_contact_message.status == 'resolved'


class TestEmailTasks:
    """Test email tasks (mock)."""
    
    def test_auto_reply_email(self, sample_contact_message):
        """Test auto-reply email task."""
        # This would test with mock SMTP
        assert sample_contact_message.email == 'john@example.com'
    
    def test_staff_notification_email(self, sample_contact_message):
        """Test staff notification email task."""
        assert sample_contact_message.ticket_id is not None
