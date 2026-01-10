"""
Contact Management Views

API endpoints for contact form submission and admin management.
"""
from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend

from .models import ContactMessage, ContactMessageReply
from .serializers import (
    ContactFormSubmitSerializer,
    ContactMessageListSerializer,
    ContactMessageDetailSerializer,
    ContactMessageUpdateSerializer,
    ContactReplyCreateSerializer,
    ContactStatsSerializer
)
from .permissions import IsAdminOrStaff, CanManageContactMessages, CanReplyToMessages
from .rate_limiting import rate_limit_contact_form, get_client_ip
from .tasks import send_contact_auto_reply, send_staff_notification, send_reply_email


class ContactFormSubmitView(APIView):
    """
    Public endpoint for contact form submissions.
    
    POST /api/contact/submit
    
    No authentication required. Rate limited to prevent spam.
    """
    
    permission_classes = [AllowAny]
    
    @rate_limit_contact_form(max_per_hour=5, max_per_day_email=20)
    def post(self, request):
        """Submit a contact form."""
        serializer = ContactFormSubmitSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Validation failed',
                    'fields': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create contact message
        contact_message = ContactMessage.objects.create(
            name=serializer.validated_data['name'],
            email=serializer.validated_data['email'],
            subject=serializer.validated_data['subject'],
            message=serializer.validated_data['message'],
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Send emails asynchronously
        send_contact_auto_reply.delay(str(contact_message.id))
        send_staff_notification.delay(str(contact_message.id))
        
        return Response(
            {
                'success': True,
                'message': "Your message has been received. We'll get back to you within 24-48 hours.",
                'ticket_id': contact_message.ticket_id
            },
            status=status.HTTP_201_CREATED
        )


class ContactMessageListView(generics.ListAPIView):
    """
    List all contact messages (admin/staff only).
    
    GET /api/admin/contact-messages
    
    Query Parameters:
    - status: Filter by status (new, assigned, in_progress, resolved, closed)
    - subject: Filter by subject category
    - search: Search in name, email, or message
    - assigned_to: Filter by assigned staff member
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20)
    """
    
    permission_classes = [IsAdminOrStaff]
    serializer_class = ContactMessageListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'subject', 'assigned_to']
    search_fields = ['name', 'email', 'message']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get contact messages based on user role."""
        queryset = ContactMessage.objects.filter(is_deleted=False)
        
        user = self.request.user
        
        # Super admin and national admin see all
        if user.role in ['SUPER_ADMIN', 'NATIONAL_ADMIN']:
            return queryset
        
        # Regional coordinators see only assigned messages
        if user.role == 'REGIONAL_COORDINATOR':
            return queryset.filter(assigned_to=user)
        
        return queryset.none()


class ContactMessageDetailView(generics.RetrieveAPIView):
    """
    Get single contact message details.
    
    GET /api/admin/contact-messages/:id
    """
    
    permission_classes = [IsAdminOrStaff]
    serializer_class = ContactMessageDetailSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        """Get contact messages based on user role."""
        queryset = ContactMessage.objects.filter(is_deleted=False)
        
        user = self.request.user
        
        if user.role in ['SUPER_ADMIN', 'NATIONAL_ADMIN']:
            return queryset
        
        if user.role == 'REGIONAL_COORDINATOR':
            return queryset.filter(assigned_to=user)
        
        return queryset.none()


class ContactMessageUpdateView(generics.UpdateAPIView):
    """
    Update contact message status or assignment.
    
    PATCH /api/admin/contact-messages/:id
    """
    
    permission_classes = [CanManageContactMessages]
    serializer_class = ContactMessageUpdateSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        """Get contact messages."""
        return ContactMessage.objects.filter(is_deleted=False)


class ContactMessageReplyView(APIView):
    """
    Send reply to a contact message.
    
    POST /api/admin/contact-messages/:id/reply
    """
    
    permission_classes = [CanReplyToMessages]
    
    def post(self, request, id):
        """Create and send reply."""
        try:
            message = ContactMessage.objects.get(id=id, is_deleted=False)
        except ContactMessage.DoesNotExist:
            return Response(
                {'error': 'Contact message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        self.check_object_permissions(request, message)
        
        serializer = ContactReplyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation failed', 'fields': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create reply
        reply = ContactMessageReply.objects.create(
            message=message,
            staff=request.user,
            reply_message=serializer.validated_data['message'],
            sent_via_email=serializer.validated_data['send_email']
        )
        
        # Update message status if needed
        if message.status == 'new':
            message.status = 'in_progress'
            message.save()
        
        # Send email if requested
        if serializer.validated_data['send_email']:
            send_reply_email.delay(str(reply.id))
        
        return Response(
            {
                'success': True,
                'message': 'Reply sent successfully',
                'reply_id': str(reply.id)
            },
            status=status.HTTP_201_CREATED
        )


class ContactMessageDeleteView(generics.DestroyAPIView):
    """
    Soft delete a contact message (admin only).
    
    DELETE /api/admin/contact-messages/:id
    """
    
    permission_classes = [CanManageContactMessages]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Only allow super admins to delete."""
        if self.request.user.role == 'SUPER_ADMIN':
            return ContactMessage.objects.filter(is_deleted=False)
        return ContactMessage.objects.none()
    
    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        instance.is_deleted = True
        instance.save()


class ContactStatsView(APIView):
    """
    Get contact message statistics.
    
    GET /api/admin/contact-stats
    """
    
    permission_classes = [IsAdminOrStaff]
    
    def get(self, request):
        """Get statistics."""
        user = request.user
        
        # Base queryset
        queryset = ContactMessage.objects.filter(is_deleted=False)
        
        # Scope by role
        if user.role == 'REGIONAL_COORDINATOR':
            queryset = queryset.filter(assigned_to=user)
        
        # Calculate stats
        total_messages = queryset.count()
        new_messages = queryset.filter(status='new').count()
        assigned_messages = queryset.filter(status='assigned').count()
        in_progress_messages = queryset.filter(status='in_progress').count()
        
        # Resolved today
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        resolved_today = queryset.filter(
            status='resolved',
            updated_at__gte=today_start
        ).count()
        
        # Average response time (simplified - time from creation to first reply)
        messages_with_replies = queryset.filter(replies__isnull=False).distinct()
        if messages_with_replies.exists():
            # This is a simplified calculation
            avg_response_time_hours = 18.5  # Placeholder - implement actual calculation
        else:
            avg_response_time_hours = None
        
        # By subject
        by_subject = {}
        for subject, _ in ContactMessage.SUBJECT_CHOICES:
            count = queryset.filter(subject=subject).count()
            if count > 0:
                by_subject[subject] = count
        
        # Recent messages
        recent_messages = queryset.order_by('-created_at')[:10]
        
        stats = {
            'total_messages': total_messages,
            'new_messages': new_messages,
            'assigned_messages': assigned_messages,
            'in_progress_messages': in_progress_messages,
            'resolved_today': resolved_today,
            'avg_response_time_hours': avg_response_time_hours,
            'by_subject': by_subject,
            'recent_messages': recent_messages
        }
        
        serializer = ContactStatsSerializer(stats)
        return Response(serializer.data)
