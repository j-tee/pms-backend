"""
Views for Institutional Data Subscriptions.

- Public views for landing page and inquiries
- Admin views for managing subscribers
- Subscriber views for self-service
- Payment views for MoMo payments via Paystack
"""

import logging
from dateutil.relativedelta import relativedelta

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404

from dashboards.permissions import IsExecutive, IsSuperAdmin
from core.paystack_service import PaystackService, PaystackError
from .institutional_models import (
    InstitutionalPlan,
    InstitutionalSubscriber,
    InstitutionalAPIKey,
    InstitutionalAPIUsage,
    InstitutionalPayment,
    InstitutionalInquiry,
)
from .institutional_serializers import (
    InstitutionalPlanPublicSerializer,
    InstitutionalInquiryCreateSerializer,
    InstitutionalPlanDetailSerializer,
    InstitutionalAPIKeySerializer,
    InstitutionalAPIKeyCreateSerializer,
    InstitutionalSubscriberSerializer,
    InstitutionalSubscriberUpdateSerializer,
    InstitutionalAPIUsageSummarySerializer,
    InstitutionalPaymentSerializer,
    InstitutionalInquiryListSerializer,
    InstitutionalInquiryDetailSerializer,
    InstitutionalSubscriberAdminSerializer,
    InstitutionalSubscriberCreateSerializer,
    InstitutionalPlanAdminSerializer,
    InstitutionalInitiatePaymentSerializer,
)
from .institutional_auth import (
    InstitutionalAPIKeyAuthentication,
    IsInstitutionalSubscriber,
    InstitutionalRateLimiter,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PUBLIC VIEWS (No Auth Required)
# =============================================================================

class InstitutionalPlansPublicView(APIView):
    """
    GET /api/public/data-subscriptions/plans/
    
    List available institutional subscription plans.
    For the "Data Subscriptions" landing page.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        plans = InstitutionalPlan.objects.filter(is_active=True).order_by('display_order')
        serializer = InstitutionalPlanPublicSerializer(plans, many=True)
        
        return Response({
            'title': 'YEA Poultry Data Subscriptions',
            'description': (
                'Access aggregated poultry sector data for Ghana. '
                'Ideal for financial institutions, insurers, agribusinesses, and researchers.'
            ),
            'use_cases': [
                {
                    'category': 'Banks & Financial Institutions',
                    'description': 'Assess farm creditworthiness based on production data',
                },
                {
                    'category': 'Insurance Providers',
                    'description': 'Price livestock insurance using mortality and health data',
                },
                {
                    'category': 'Agribusinesses',
                    'description': 'Plan procurement and logistics based on regional supply',
                },
                {
                    'category': 'Feed Companies',
                    'description': 'Target sales based on flock sizes and feed consumption',
                },
                {
                    'category': 'Researchers & NGOs',
                    'description': 'Analyze food security trends and sector development',
                },
            ],
            'plans': serializer.data,
            'contact': {
                'email': 'data@yeapoultry.gov.gh',
                'phone': '+233-XXX-XXX-XXX',
            },
        })


class InstitutionalInquiryCreateView(APIView):
    """
    POST /api/public/data-subscriptions/inquire/
    
    Submit an inquiry for institutional data subscription.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = InstitutionalInquiryCreateSerializer(data=request.data)
        if serializer.is_valid():
            inquiry = serializer.save()
            
            # TODO: Send notification to sales team
            # send_institutional_inquiry_notification.delay(inquiry.id)
            
            return Response({
                'message': 'Thank you for your inquiry. Our team will contact you within 2 business days.',
                'inquiry_id': str(inquiry.id),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# SUBSCRIBER SELF-SERVICE VIEWS
# =============================================================================

class SubscriberProfileView(APIView):
    """
    GET /api/institutional/profile/
    PATCH /api/institutional/profile/
    
    View and update subscriber profile.
    """
    authentication_classes = [InstitutionalAPIKeyAuthentication]
    permission_classes = [IsInstitutionalSubscriber]
    
    def get(self, request):
        subscriber = request.institutional_subscriber
        serializer = InstitutionalSubscriberSerializer(subscriber)
        return Response(serializer.data)
    
    def patch(self, request):
        subscriber = request.institutional_subscriber
        serializer = InstitutionalSubscriberUpdateSerializer(
            subscriber, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(InstitutionalSubscriberSerializer(subscriber).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubscriberAPIKeysView(APIView):
    """
    GET /api/institutional/api-keys/
    POST /api/institutional/api-keys/
    
    List and create API keys for subscriber.
    """
    authentication_classes = [InstitutionalAPIKeyAuthentication]
    permission_classes = [IsInstitutionalSubscriber]
    
    def get(self, request):
        subscriber = request.institutional_subscriber
        keys = subscriber.api_keys.all()
        serializer = InstitutionalAPIKeySerializer(keys, many=True)
        return Response({'api_keys': serializer.data})
    
    def post(self, request):
        subscriber = request.institutional_subscriber
        
        # Limit number of API keys per subscriber
        if subscriber.api_keys.count() >= 5:
            return Response(
                {'error': 'Maximum 5 API keys per subscriber'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = InstitutionalAPIKeyCreateSerializer(data=request.data)
        if serializer.is_valid():
            api_key_obj, full_key = InstitutionalAPIKey.generate_key(
                subscriber=subscriber,
                name=serializer.validated_data['name'],
                expires_at=serializer.validated_data.get('expires_at'),
            )
            
            # Update allowed IPs if provided
            if serializer.validated_data.get('allowed_ips'):
                api_key_obj.allowed_ips = serializer.validated_data['allowed_ips']
                api_key_obj.save()
            
            return Response({
                'message': 'API key created successfully. Save this key - it will not be shown again.',
                'api_key': full_key,
                'key_id': str(api_key_obj.id),
                'key_prefix': api_key_obj.key_prefix,
                'name': api_key_obj.name,
                'expires_at': api_key_obj.expires_at,
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubscriberAPIKeyDetailView(APIView):
    """
    DELETE /api/institutional/api-keys/<key_id>/
    
    Revoke an API key.
    """
    authentication_classes = [InstitutionalAPIKeyAuthentication]
    permission_classes = [IsInstitutionalSubscriber]
    
    def delete(self, request, key_id):
        subscriber = request.institutional_subscriber
        api_key = get_object_or_404(
            InstitutionalAPIKey,
            id=key_id,
            subscriber=subscriber
        )
        
        api_key.is_active = False
        api_key.save()
        
        return Response({
            'message': f'API key "{api_key.name}" has been revoked.',
        })


class SubscriberUsageView(APIView):
    """
    GET /api/institutional/usage/history/
    
    Get API usage history and statistics.
    """
    authentication_classes = [InstitutionalAPIKeyAuthentication]
    permission_classes = [IsInstitutionalSubscriber]
    
    def get(self, request):
        subscriber = request.institutional_subscriber
        days = min(int(request.query_params.get('days', 30)), 90)
        start_date = timezone.now().date() - timezone.timedelta(days=days)
        
        # Usage records
        usage = InstitutionalAPIUsage.objects.filter(
            subscriber=subscriber,
            date__gte=start_date
        )
        
        # Summary stats
        stats = usage.aggregate(
            total_requests=Count('id'),
            successful_requests=Count('id', filter=Q(status_code__lt=400)),
            failed_requests=Count('id', filter=Q(status_code__gte=400)),
            avg_response_time=models.Avg('response_time_ms'),
        )
        
        # Top endpoints
        top_endpoints = usage.values('endpoint').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Daily breakdown
        daily_usage = usage.values('date').annotate(
            requests=Count('id')
        ).order_by('date')
        
        # Current quota
        quota = InstitutionalRateLimiter.get_usage(subscriber)
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().date().isoformat(),
                'days': days,
            },
            'summary': {
                'total_requests': stats['total_requests'] or 0,
                'successful_requests': stats['successful_requests'] or 0,
                'failed_requests': stats['failed_requests'] or 0,
                'average_response_time_ms': round(stats['avg_response_time'] or 0, 0),
            },
            'quota': quota,
            'top_endpoints': list(top_endpoints),
            'daily_usage': list(daily_usage),
        })


class SubscriberPaymentsView(APIView):
    """
    GET /api/institutional/payments/
    
    Get payment history.
    """
    authentication_classes = [InstitutionalAPIKeyAuthentication]
    permission_classes = [IsInstitutionalSubscriber]
    
    def get(self, request):
        subscriber = request.institutional_subscriber
        payments = InstitutionalPayment.objects.filter(subscriber=subscriber)
        serializer = InstitutionalPaymentSerializer(payments, many=True)
        return Response({'payments': serializer.data})


class InitiateInstitutionalPaymentView(APIView):
    """
    POST /api/institutional/pay/
    
    Initiate Paystack payment for institutional subscription fee.
    
    Subscriber is redirected to Paystack's hosted checkout page where they
    can choose their preferred payment method (MoMo, Card, Bank Transfer, USSD).
    
    Request body:
    {
        "billing_cycle": "monthly",  // or "annually"
        "callback_url": "https://yourapp.com/payment/callback"  // optional
    }
    
    Response:
    {
        "status": "success",
        "message": "Payment initialized. Complete payment on the checkout page.",
        "authorization_url": "https://checkout.paystack.com/xxx",
        "reference": "INST-20260108-A3B4C5D6",
        "amount": 1500.00,
        "billing_cycle": "monthly",
        "period_start": "2026-01-08",
        "period_end": "2026-02-07"
    }
    """
    authentication_classes = [InstitutionalAPIKeyAuthentication]
    permission_classes = [IsInstitutionalSubscriber]
    
    @transaction.atomic
    def post(self, request):
        subscriber = request.institutional_subscriber
        
        # Validate request data
        serializer = InstitutionalInitiatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        billing_cycle = serializer.validated_data.get('billing_cycle', 'monthly')
        callback_url = serializer.validated_data.get('callback_url')
        
        # Get plan and determine amount
        plan = subscriber.plan
        if billing_cycle == 'annually':
            amount = plan.price_annually
        else:
            amount = plan.price_monthly
        
        # Calculate billing period
        period_start = timezone.now().date()
        if billing_cycle == 'annually':
            period_end = period_start + relativedelta(years=1)
        else:
            period_end = period_start + relativedelta(months=1)
        
        # IDEMPOTENCY: Check for existing pending/processing payment for this period
        existing_payment = InstitutionalPayment.objects.filter(
            subscriber=subscriber,
            period_start=period_start,
            period_end=period_end,
            payment_status__in=['pending', 'processing']
        ).first()
        
        if existing_payment:
            # Return existing payment details (idempotent)
            logger.info(f"Idempotent payment request (institutional): returning existing payment {existing_payment.payment_reference}")
            return Response({
                'status': 'success',
                'message': 'Payment already initialized. Complete payment on the checkout page.',
                'reference': existing_payment.payment_reference,
                'authorization_url': existing_payment.gateway_authorization_url,
                'access_code': existing_payment.gateway_access_code,
                'amount': str(amount),
                'billing_cycle': billing_cycle,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
            })
        
        # Generate payment reference
        reference = InstitutionalPayment.generate_reference()
        
        # Create pending payment record
        payment = InstitutionalPayment.objects.create(
            subscriber=subscriber,
            amount=amount,
            currency='GHS',
            period_start=period_start,
            period_end=period_end,
            payment_method='paystack',
            payment_status='pending',
            payment_reference=reference,
            gateway_provider='paystack',
        )
        
        # Initialize Paystack transaction
        try:
            # Use contact email from subscriber
            email = subscriber.contact_email
            
            # Convert GHS to pesewas
            amount_pesewas = PaystackService.convert_to_pesewas(amount)
            
            result = PaystackService.initialize_transaction(
                amount=amount_pesewas,
                email=email,
                reference=reference,
                metadata={
                    'payment_id': str(payment.id),
                    'subscriber_id': str(subscriber.id),
                    'organization_name': subscriber.organization_name,
                    'plan_name': plan.name,
                    'billing_cycle': billing_cycle,
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                    'payment_type': 'institutional_subscription',
                },
                callback_url=callback_url
            )
            
            # Update payment with gateway response
            payment.payment_status = 'processing'
            payment.gateway_access_code = result.get('access_code', '')
            payment.gateway_authorization_url = result.get('authorization_url', '')
            payment.save()
            
            logger.info(f"Institutional payment initiated: {reference} for {subscriber.organization_name}")
            
            return Response({
                'status': 'success',
                'message': result.get('message', 'Payment initialized. Complete payment on the checkout page.'),
                'reference': reference,
                'authorization_url': result.get('authorization_url'),
                'access_code': result.get('access_code'),
                'amount': amount,
                'billing_cycle': billing_cycle,
                'period_start': period_start,
                'period_end': period_end,
            })
            
        except PaystackError as e:
            # Mark payment as failed
            payment.payment_status = 'failed'
            payment.failure_reason = str(e.message)
            payment.save()
            
            logger.error(f"Institutional payment initialization failed: {e.message}", extra={
                'reference': reference,
                'subscriber_id': str(subscriber.id),
                'error_code': e.code
            })
            
            return Response({
                'error': e.message,
                'code': e.code
            }, status=status.HTTP_502_BAD_GATEWAY)


class VerifyInstitutionalPaymentView(APIView):
    """
    GET /api/institutional/pay/verify/<reference>/
    
    Verify payment status by reference.
    """
    authentication_classes = [InstitutionalAPIKeyAuthentication]
    permission_classes = [IsInstitutionalSubscriber]
    
    def get(self, request, reference):
        subscriber = request.institutional_subscriber
        
        # Get payment record
        try:
            payment = InstitutionalPayment.objects.get(
                payment_reference=reference,
                subscriber=subscriber
            )
        except InstitutionalPayment.DoesNotExist:
            return Response({
                'error': 'Payment not found',
                'code': 'PAYMENT_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # If already completed, return cached status
        if payment.payment_status == 'completed':
            return Response({
                'status': 'success',
                'reference': reference,
                'amount': payment.amount,
                'paid_at': payment.paid_at,
                'payment_method': payment.payment_method,
                'period_start': payment.period_start,
                'period_end': payment.period_end,
                'subscriber_status': subscriber.status,
            })
        
        # Verify with Paystack
        try:
            result = PaystackService.verify_transaction(reference)
            
            if result['status'] == 'success':
                # Mark payment as completed
                payment.mark_as_completed(gateway_response=result)
                
                logger.info(f"Institutional payment verified successfully: {reference}")
                
                return Response({
                    'status': 'success',
                    'reference': reference,
                    'amount': payment.amount,
                    'paid_at': result.get('paid_at'),
                    'channel': result.get('channel'),
                    'gateway_response': result.get('gateway_response'),
                    'period_start': payment.period_start,
                    'period_end': payment.period_end,
                    'subscriber_status': subscriber.status,
                })
            
            elif result['status'] == 'failed':
                payment.mark_as_failed(
                    reason=result.get('gateway_response', 'Payment failed'),
                    gateway_response=result
                )
                
                return Response({
                    'status': 'failed',
                    'reference': reference,
                    'message': result.get('gateway_response', 'Payment was not successful'),
                })
            
            else:  # pending, abandoned, etc.
                return Response({
                    'status': result['status'],
                    'reference': reference,
                    'message': 'Payment is still being processed. Please check again shortly.',
                })
                
        except PaystackError as e:
            logger.error(f"Institutional payment verification failed: {e.message}", extra={
                'reference': reference,
                'error_code': e.code
            })
            
            return Response({
                'error': e.message,
                'code': e.code
            }, status=status.HTTP_502_BAD_GATEWAY)


class PaymentMethodsView(APIView):
    """
    GET /api/institutional/payment-methods/
    
    Get list of supported payment methods via Paystack.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        methods = [
            {
                'code': 'mobile_money',
                'name': 'Mobile Money',
                'description': 'Pay with MTN MoMo, Vodafone Cash, AirtelTigo Money, or Telecel Cash',
                'providers': ['MTN', 'Vodafone', 'AirtelTigo', 'Telecel']
            },
            {
                'code': 'card',
                'name': 'Card Payment',
                'description': 'Pay with Visa, Mastercard, or Verve cards',
                'providers': ['Visa', 'Mastercard', 'Verve']
            },
            {
                'code': 'bank_transfer',
                'name': 'Bank Transfer',
                'description': 'Pay via bank transfer',
                'providers': []
            },
            {
                'code': 'ussd',
                'name': 'USSD',
                'description': 'Pay using USSD banking',
                'providers': []
            },
        ]
        return Response({
            'payment_gateway': 'Paystack',
            'methods': methods,
            'note': 'Payment method is selected on the Paystack checkout page'
        })


# =============================================================================
# ADMIN VIEWS
# =============================================================================

class AdminInstitutionalDashboardView(APIView):
    """
    GET /api/admin/institutional/dashboard/
    
    Dashboard overview of institutional subscriptions.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def get(self, request):
        # Subscriber stats
        subscribers = InstitutionalSubscriber.objects.all()
        
        subscriber_stats = {
            'total': subscribers.count(),
            'active': subscribers.filter(status='active').count(),
            'trial': subscribers.filter(status='trial').count(),
            'pending': subscribers.filter(status='pending').count(),
            'suspended': subscribers.filter(status='suspended').count(),
        }
        
        # By category
        by_category = subscribers.values('organization_category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Inquiry stats
        inquiries = InstitutionalInquiry.objects.all()
        inquiry_stats = {
            'total': inquiries.count(),
            'new': inquiries.filter(status='new').count(),
            'converted': inquiries.filter(status='converted').count(),
            'conversion_rate': round(
                inquiries.filter(status='converted').count() / 
                max(inquiries.count(), 1) * 100, 1
            ),
        }
        
        # Revenue (last 12 months)
        year_ago = timezone.now().date() - timezone.timedelta(days=365)
        revenue = InstitutionalPayment.objects.filter(
            payment_status='completed',
            paid_at__date__gte=year_ago
        ).aggregate(
            total=Sum('amount'),
            count=Count('id'),
        )
        
        # API usage (last 30 days)
        month_ago = timezone.now().date() - timezone.timedelta(days=30)
        api_usage = InstitutionalAPIUsage.objects.filter(
            date__gte=month_ago
        ).aggregate(
            total_requests=Count('id'),
            avg_response_time=models.Avg('response_time_ms'),
        )
        
        return Response({
            'subscribers': subscriber_stats,
            'by_category': list(by_category),
            'inquiries': inquiry_stats,
            'revenue': {
                'total_12_months': float(revenue['total'] or 0),
                'transactions': revenue['count'] or 0,
            },
            'api_usage_30_days': {
                'total_requests': api_usage['total_requests'] or 0,
                'avg_response_time_ms': round(api_usage['avg_response_time'] or 0, 0),
            },
        })


class AdminInquiryListView(generics.ListAPIView):
    """
    GET /api/admin/institutional/inquiries/
    
    List institutional inquiries.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    serializer_class = InstitutionalInquiryListSerializer
    
    def get_queryset(self):
        queryset = InstitutionalInquiry.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(organization_category=category)
        
        return queryset.order_by('-created_at')


class AdminInquiryDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/admin/institutional/inquiries/<id>/
    PATCH /api/admin/institutional/inquiries/<id>/
    
    View and update inquiry details.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    serializer_class = InstitutionalInquiryDetailSerializer
    queryset = InstitutionalInquiry.objects.all()


class AdminInquiryConvertView(APIView):
    """
    POST /api/admin/institutional/inquiries/<id>/convert/
    
    Convert inquiry to subscriber.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def post(self, request, pk):
        inquiry = get_object_or_404(InstitutionalInquiry, pk=pk)
        
        if inquiry.status == 'converted':
            return Response(
                {'error': 'Inquiry already converted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get plan from request or inquiry
        plan_id = request.data.get('plan_id', inquiry.interested_plan_id)
        if not plan_id:
            return Response(
                {'error': 'Plan ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        plan = get_object_or_404(InstitutionalPlan, pk=plan_id)
        
        # Create subscriber
        subscriber = InstitutionalSubscriber.objects.create(
            organization_name=inquiry.organization_name,
            organization_category=inquiry.organization_category,
            website=inquiry.website,
            contact_name=inquiry.contact_name,
            contact_email=inquiry.contact_email,
            contact_phone=inquiry.contact_phone,
            contact_position=inquiry.contact_position,
            plan=plan,
            data_use_purpose=inquiry.data_use_purpose,
            status='pending',
        )
        
        # Update inquiry
        inquiry.status = 'converted'
        inquiry.converted_subscriber = subscriber
        inquiry.converted_at = timezone.now()
        inquiry.save()
        
        return Response({
            'message': f'Inquiry converted to subscriber: {subscriber.organization_name}',
            'subscriber_id': str(subscriber.id),
        }, status=status.HTTP_201_CREATED)


class AdminSubscriberListView(generics.ListCreateAPIView):
    """
    GET /api/admin/institutional/subscribers/
    POST /api/admin/institutional/subscribers/
    
    List and create subscribers.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InstitutionalSubscriberCreateSerializer
        return InstitutionalSubscriberAdminSerializer
    
    def get_queryset(self):
        queryset = InstitutionalSubscriber.objects.all()
        
        # Filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(organization_category=category)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(organization_name__icontains=search) |
                Q(contact_name__icontains=search) |
                Q(contact_email__icontains=search)
            )
        
        return queryset.order_by('-created_at')


class AdminSubscriberDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/admin/institutional/subscribers/<id>/
    PATCH /api/admin/institutional/subscribers/<id>/
    
    View and update subscriber.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    serializer_class = InstitutionalSubscriberAdminSerializer
    queryset = InstitutionalSubscriber.objects.all()


class AdminSubscriberVerifyView(APIView):
    """
    POST /api/admin/institutional/subscribers/<id>/verify/
    
    Verify subscriber organization.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def post(self, request, pk):
        subscriber = get_object_or_404(InstitutionalSubscriber, pk=pk)
        
        subscriber.is_verified = True
        subscriber.verified_by = request.user
        subscriber.verified_at = timezone.now()
        subscriber.save()
        
        return Response({
            'message': f'{subscriber.organization_name} has been verified.',
        })


class AdminSubscriberActivateView(APIView):
    """
    POST /api/admin/institutional/subscribers/<id>/activate/
    
    Activate subscriber (start trial or paid subscription).
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def post(self, request, pk):
        subscriber = get_object_or_404(InstitutionalSubscriber, pk=pk)
        
        action = request.data.get('action', 'trial')  # trial or activate
        
        if action == 'trial':
            subscriber.start_trial()
            message = f'{subscriber.organization_name} trial started for {subscriber.trial_days} days.'
        else:
            subscriber.activate()
            message = f'{subscriber.organization_name} subscription activated.'
        
        # Generate initial API key
        if not subscriber.api_keys.exists():
            api_key_obj, full_key = InstitutionalAPIKey.generate_key(
                subscriber=subscriber,
                name='Primary',
                created_by=request.user,
            )
            
            return Response({
                'message': message,
                'api_key': full_key,
                'note': 'Save this API key - it will not be shown again.',
            })
        
        return Response({'message': message})


class AdminPlansListView(generics.ListCreateAPIView):
    """
    GET /api/admin/institutional/plans/
    POST /api/admin/institutional/plans/
    
    List and create institutional plans.
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = InstitutionalPlanAdminSerializer
    queryset = InstitutionalPlan.objects.all().order_by('display_order')


class AdminPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/admin/institutional/plans/<id>/
    PATCH /api/admin/institutional/plans/<id>/
    DELETE /api/admin/institutional/plans/<id>/
    
    Manage institutional plans.
    """
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = InstitutionalPlanAdminSerializer
    queryset = InstitutionalPlan.objects.all()


# Need to import models for aggregation
from django.db import models
