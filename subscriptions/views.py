"""
Subscription Payment Views

API endpoints for:
- Marketplace subscription/activation fee payments via MoMo
- Payment verification
- Subscription status
- Payment history
- Paystack webhook handling
"""

import logging
from decimal import Decimal
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.db import transaction

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes

from .models import Subscription, SubscriptionPlan, SubscriptionPayment, SubscriptionInvoice
from .serializers import (
    InitiatePaymentSerializer,
    PaymentInitiatedResponseSerializer,
    VerifyPaymentSerializer,
    PaymentVerificationResponseSerializer,
    SubscriptionStatusSerializer,
    SubscriptionPaymentSerializer,
    SubscriptionPlanSerializer,
    SubscriptionActivationSerializer,
    MarketplaceAccessInfoSerializer,
    CancelSubscriptionSerializer,
    PaymentHistorySerializer,
)
from sales_revenue.models import PlatformSettings
from core.paystack_service import PaystackService, PaystackError

logger = logging.getLogger(__name__)


class MarketplaceAccessInfoView(APIView):
    """
    GET /api/subscriptions/marketplace-access/
    
    Get current marketplace access status and pricing information
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check if user has a farm
        if not hasattr(user, 'farm'):
            return Response({
                'error': 'No farm associated with this account',
                'code': 'NO_FARM'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        farm = user.farm
        settings = PlatformSettings.get_settings()
        
        # Get subscription if exists
        subscription = getattr(farm, 'subscription', None)
        
        # Build response
        data = {
            'has_marketplace_access': farm.has_marketplace_access,
            'subscription_type': farm.subscription_type,
            'subscription_status': subscription.status if subscription else None,
            'current_period_end': subscription.current_period_end if subscription else None,
            'next_billing_date': subscription.next_billing_date if subscription else None,
            'monthly_fee': settings.marketplace_activation_fee,
            'trial_days': settings.marketplace_trial_days,
            'is_government_subsidized': farm.government_subsidy_active,
            'features': [
                'List products on public marketplace',
                'Up to 20 product images',
                'Sales tracking and analytics',
                'Customer messaging',
                'Order management',
            ]
        }
        
        serializer = MarketplaceAccessInfoSerializer(data)
        return Response(serializer.data)


class SubscriptionPlansView(generics.ListAPIView):
    """
    GET /api/subscriptions/plans/
    
    List available subscription/activation plans
    """
    permission_classes = [AllowAny]
    serializer_class = SubscriptionPlanSerializer
    
    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True).order_by('display_order')


class CurrentSubscriptionView(APIView):
    """
    GET /api/subscriptions/current/
    
    Get current subscription status for the authenticated farmer
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if not hasattr(user, 'farm'):
            return Response({
                'error': 'No farm associated with this account',
                'code': 'NO_FARM'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        farm = user.farm
        
        try:
            subscription = farm.subscription
            serializer = SubscriptionStatusSerializer(subscription)
            return Response(serializer.data)
        except Subscription.DoesNotExist:
            return Response({
                'status': 'none',
                'message': 'No active marketplace subscription. Activate to sell on the marketplace.',
                'monthly_fee': PlatformSettings.get_settings().marketplace_activation_fee
            })


class InitiateSubscriptionPaymentView(APIView):
    """
    POST /api/subscriptions/pay/
    
    Initiate MoMo payment for marketplace subscription fee
    
    Request body:
    {
        "phone": "0241234567",
        "provider": "mtn"  // mtn, vodafone, airteltigo, telecel
    }
    
    Response:
    {
        "status": "success",
        "message": "Payment initialized. Please authorize on your phone.",
        "reference": "SUB-20260105-A3B4C5D6",
        "amount": 50.00,
        "display_text": "Dial *170# to approve payment"
    }
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        user = request.user
        
        # Validate user has a farm
        if not hasattr(user, 'farm'):
            return Response({
                'error': 'No farm associated with this account',
                'code': 'NO_FARM'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        farm = user.farm
        
        # Check if farm is approved
        if farm.application_status != 'Approved':
            return Response({
                'error': 'Farm must be approved before activating marketplace',
                'code': 'FARM_NOT_APPROVED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate request data
        serializer = InitiatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone = serializer.validated_data['phone']
        provider = serializer.validated_data['provider']
        callback_url = serializer.validated_data.get('callback_url')
        
        # Get or create subscription
        settings = PlatformSettings.get_settings()
        amount = settings.marketplace_activation_fee
        
        # Get or create default plan
        plan, _ = SubscriptionPlan.objects.get_or_create(
            name='Marketplace Access',
            defaults={
                'description': 'Monthly marketplace access for selling on the platform',
                'price_monthly': amount,
            }
        )
        
        # Get or create subscription record
        subscription, created = Subscription.objects.get_or_create(
            farm=farm,
            defaults={
                'plan': plan,
                'status': 'pending' if created else 'past_due',
                'start_date': timezone.now().date(),
                'current_period_start': timezone.now().date(),
                'current_period_end': timezone.now().date() + relativedelta(months=1),
                'next_billing_date': timezone.now().date() + relativedelta(months=1),
            }
        )
        
        # Generate payment reference
        reference = SubscriptionPayment.generate_reference()
        
        # Calculate billing period
        period_start = timezone.now().date()
        period_end = period_start + relativedelta(months=1)
        
        # Create pending payment record
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount=amount,
            payment_method='mobile_money',
            payment_reference=reference,
            momo_phone=phone,
            momo_provider=provider,
            status='pending',
            period_start=period_start,
            period_end=period_end,
            gateway_provider='paystack',
            payment_date=timezone.now().date(),
        )
        
        # Initialize Paystack payment
        try:
            # Use email from user, fallback to farm email
            email = user.email or farm.email or f"{phone}@farmer.yea.gov.gh"
            
            # Convert GHS to pesewas
            amount_pesewas = PaystackService.convert_to_pesewas(amount)
            
            result = PaystackService.initialize_momo_payment(
                amount=amount_pesewas,
                email=email,
                phone=phone,
                provider=provider,
                reference=reference,
                metadata={
                    'payment_id': str(payment.id),
                    'subscription_id': str(subscription.id),
                    'farm_id': str(farm.id),
                    'farm_name': farm.farm_name,
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                    'payment_type': 'marketplace_subscription',
                },
                callback_url=callback_url
            )
            
            # Update payment with gateway response
            payment.status = 'processing'
            payment.gateway_access_code = result.get('access_code', '')
            payment.gateway_authorization_url = result.get('authorization_url', '')
            payment.save()
            
            logger.info(f"Payment initiated: {reference} for farm {farm.farm_name}")
            
            return Response({
                'status': 'success',
                'message': result.get('message', 'Payment initialized. Please authorize on your phone.'),
                'reference': reference,
                'authorization_url': result.get('authorization_url'),
                'access_code': result.get('access_code'),
                'amount': amount,
                'display_text': f'A payment request of GHS {amount} has been sent to {phone}. Please approve on your phone.',
            })
            
        except PaystackError as e:
            # Mark payment as failed
            payment.status = 'failed'
            payment.failure_reason = str(e.message)
            payment.save()
            
            logger.error(f"Payment initialization failed: {e.message}", extra={
                'reference': reference,
                'farm_id': str(farm.id),
                'error_code': e.code
            })
            
            return Response({
                'error': e.message,
                'code': e.code
            }, status=status.HTTP_502_BAD_GATEWAY)


class VerifyPaymentView(APIView):
    """
    GET /api/subscriptions/verify/<reference>/
    
    Verify payment status by reference
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, reference):
        user = request.user
        
        # Get payment record
        try:
            payment = SubscriptionPayment.objects.select_related(
                'subscription__farm'
            ).get(payment_reference=reference)
        except SubscriptionPayment.DoesNotExist:
            return Response({
                'error': 'Payment not found',
                'code': 'PAYMENT_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify ownership
        if payment.subscription.farm.user != user:
            return Response({
                'error': 'Access denied',
                'code': 'ACCESS_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # If already completed, return cached status
        if payment.status == 'completed':
            return Response({
                'status': 'success',
                'reference': reference,
                'amount': payment.amount,
                'paid_at': payment.paid_at,
                'channel': 'mobile_money',
                'subscription_status': payment.subscription.status,
                'next_billing_date': payment.subscription.next_billing_date,
            })
        
        # Verify with Paystack
        try:
            result = PaystackService.verify_transaction(reference)
            
            if result['status'] == 'success':
                # Mark payment as completed
                payment.mark_as_completed(gateway_response=result)
                
                logger.info(f"Payment verified successfully: {reference}")
                
                return Response({
                    'status': 'success',
                    'reference': reference,
                    'amount': payment.amount,
                    'paid_at': result.get('paid_at'),
                    'channel': result.get('channel'),
                    'gateway_response': result.get('gateway_response'),
                    'subscription_status': payment.subscription.status,
                    'next_billing_date': payment.subscription.next_billing_date,
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
            logger.error(f"Payment verification failed: {e.message}", extra={
                'reference': reference,
                'error_code': e.code
            })
            
            return Response({
                'error': e.message,
                'code': e.code
            }, status=status.HTTP_502_BAD_GATEWAY)


class PaymentHistoryView(generics.ListAPIView):
    """
    GET /api/subscriptions/payments/
    
    Get payment history for the authenticated farmer
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionPaymentSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if not hasattr(user, 'farm'):
            return SubscriptionPayment.objects.none()
        
        farm = user.farm
        
        try:
            subscription = farm.subscription
            return SubscriptionPayment.objects.filter(
                subscription=subscription
            ).order_by('-created_at')
        except Subscription.DoesNotExist:
            return SubscriptionPayment.objects.none()


class CancelSubscriptionView(APIView):
    """
    POST /api/subscriptions/cancel/
    
    Cancel marketplace subscription
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if not hasattr(user, 'farm'):
            return Response({
                'error': 'No farm associated with this account',
                'code': 'NO_FARM'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        farm = user.farm
        
        try:
            subscription = farm.subscription
        except Subscription.DoesNotExist:
            return Response({
                'error': 'No active subscription to cancel',
                'code': 'NO_SUBSCRIPTION'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CancelSubscriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        reason = serializer.validated_data['reason']
        other_reason = serializer.validated_data.get('other_reason', '')
        
        # Build cancellation reason
        full_reason = reason
        if other_reason:
            full_reason = f"{reason}: {other_reason}"
        
        # Cancel subscription
        subscription.status = 'cancelled'
        subscription.cancelled_at = timezone.now()
        subscription.cancellation_reason = full_reason
        subscription.cancelled_by = user
        subscription.auto_renew = False
        subscription.save()
        
        # Disable marketplace on farm
        farm.marketplace_enabled = False
        farm.save(update_fields=['marketplace_enabled', 'updated_at'])
        
        logger.info(f"Subscription cancelled: farm={farm.farm_name}, reason={reason}")
        
        return Response({
            'status': 'cancelled',
            'message': 'Marketplace subscription has been cancelled.',
            'access_until': subscription.current_period_end,
        })


class ReactivateSubscriptionView(APIView):
    """
    POST /api/subscriptions/reactivate/
    
    Reactivate a cancelled or suspended subscription by initiating payment
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Reuse InitiateSubscriptionPaymentView logic
        view = InitiateSubscriptionPaymentView()
        view.request = request
        return view.post(request)


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(APIView):
    """
    POST /api/subscriptions/webhooks/paystack/
    
    Handle Paystack webhook events
    
    Events handled:
    - charge.success: Payment was successful
    - charge.failed: Payment failed
    - transfer.success: Transfer to farmer was successful
    - transfer.failed: Transfer failed
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Get webhook signature
        signature = request.headers.get('X-Paystack-Signature', '')
        
        # Verify signature
        if not PaystackService.verify_webhook_signature(request.body, signature):
            logger.warning("Invalid Paystack webhook signature")
            return HttpResponse(status=401)
        
        try:
            payload = request.data
            event = payload.get('event')
            data = payload.get('data', {})
            
            logger.info(f"Paystack webhook received: {event}", extra={
                'reference': data.get('reference'),
                'event': event
            })
            
            if event == 'charge.success':
                return self._handle_charge_success(data)
            
            elif event == 'charge.failed':
                return self._handle_charge_failed(data)
            
            # Acknowledge other events
            return HttpResponse(status=200)
            
        except Exception as e:
            logger.exception(f"Webhook processing error: {e}")
            return HttpResponse(status=500)
    
    def _handle_charge_success(self, data):
        """Handle successful payment"""
        reference = data.get('reference')
        
        if not reference:
            return HttpResponse(status=400)
        
        try:
            payment = SubscriptionPayment.objects.get(payment_reference=reference)
            
            # Skip if already processed
            if payment.status == 'completed':
                return HttpResponse(status=200)
            
            # Mark as completed
            payment.mark_as_completed(gateway_response=data)
            
            logger.info(f"Webhook: Payment completed for {reference}")
            
            # TODO: Send SMS confirmation to farmer
            # from core.sms_service import SMSService
            # SMSService.send_sms(
            #     phone=payment.momo_phone,
            #     message=f"Your YEA marketplace subscription of GHS {payment.amount} was successful. Your marketplace access is now active until {payment.period_end}."
            # )
            
        except SubscriptionPayment.DoesNotExist:
            logger.warning(f"Webhook: Payment not found for reference {reference}")
        
        return HttpResponse(status=200)
    
    def _handle_charge_failed(self, data):
        """Handle failed payment"""
        reference = data.get('reference')
        
        if not reference:
            return HttpResponse(status=400)
        
        try:
            payment = SubscriptionPayment.objects.get(payment_reference=reference)
            
            # Skip if already processed
            if payment.status in ['completed', 'failed']:
                return HttpResponse(status=200)
            
            payment.mark_as_failed(
                reason=data.get('gateway_response', 'Payment failed'),
                gateway_response=data
            )
            
            logger.info(f"Webhook: Payment failed for {reference}")
            
        except SubscriptionPayment.DoesNotExist:
            logger.warning(f"Webhook: Payment not found for reference {reference}")
        
        return HttpResponse(status=200)


class MoMoProvidersView(APIView):
    """
    GET /api/subscriptions/momo-providers/
    
    Get list of supported mobile money providers
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        providers = [
            {'code': 'mtn', 'name': 'MTN Mobile Money', 'prefixes': ['024', '054', '055', '059']},
            {'code': 'vodafone', 'name': 'Vodafone Cash', 'prefixes': ['020', '050']},
            {'code': 'airteltigo', 'name': 'AirtelTigo Money', 'prefixes': ['026', '027', '056', '057']},
            {'code': 'telecel', 'name': 'Telecel Cash', 'prefixes': ['027']},
        ]
        return Response(providers)


# Admin views for manual payment verification

class AdminVerifyPaymentView(APIView):
    """
    POST /api/admin/subscriptions/verify-payment/
    
    Manually verify a payment (for admin use with cash/bank transfer payments)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from accounts.policies import UserPolicy
        
        user = request.user
        
        # Check admin permission
        policy = UserPolicy(user)
        if not policy.is_admin():
            return Response({
                'error': 'Admin access required',
                'code': 'ACCESS_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)
        
        payment_id = request.data.get('payment_id')
        if not payment_id:
            return Response({
                'error': 'payment_id is required',
                'code': 'MISSING_PAYMENT_ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = SubscriptionPayment.objects.get(id=payment_id)
        except SubscriptionPayment.DoesNotExist:
            return Response({
                'error': 'Payment not found',
                'code': 'PAYMENT_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if payment.status == 'completed':
            return Response({
                'error': 'Payment already completed',
                'code': 'ALREADY_COMPLETED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark as verified
        payment.verified_by = user
        payment.verified_at = timezone.now()
        payment.mark_as_completed()
        
        logger.info(f"Payment manually verified by {user.email}: {payment.payment_reference}")
        
        return Response({
            'status': 'success',
            'message': 'Payment verified and subscription activated',
            'payment_id': str(payment.id),
            'reference': payment.payment_reference,
        })
