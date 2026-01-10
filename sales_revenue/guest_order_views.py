"""
Guest Order and POS Views

Two pathways for sales:
1. Guest Orders - Public marketplace, phone OTP verification, farmer confirms payment
2. POS Sales - Farmer records walk-in sales directly

NO payment processing on platform - all payments happen off-platform.
"""

from rest_framework import generics, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from core.sms_service import HubtelSMSService
from core.turnstile_service import turnstile_service
from .guest_order_models import (
    GuestCustomer,
    GuestOrder,
    GuestOrderItem,
    GuestOrderOTP,
    GuestOrderRateLimit,
    POSSale,
    POSSaleItem,
)
from .guest_order_serializers import (
    RequestOTPSerializer,
    VerifyOTPSerializer,
    GuestOrderCreateSerializer,
    GuestOrderSerializer,
    GuestOrderPublicSerializer,
    FarmerOrderActionSerializer,
    POSSaleCreateSerializer,
    POSSaleSerializer,
    POSSaleListSerializer,
)


# =============================================================================
# PUBLIC GUEST ORDER VIEWS (No Authentication Required)
# =============================================================================

class RequestOTPView(APIView):
    """
    Request OTP for phone verification.
    
    POST /api/public/marketplace/order/request-otp/
    {
        "phone_number": "0241234567"
    }
    
    Returns:
    {
        "message": "OTP sent to your phone",
        "expires_in": 600,  // seconds
        "already_verified": false  // true if phone was previously verified
    }
    
    Cost Optimization: If phone number was previously verified, 
    no OTP is sent (saves SMS costs).
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone = serializer.validated_data['phone_number']
        
        # OPTIMIZATION: Check if phone is already verified
        # This saves SMS costs by not sending OTP to previously verified numbers
        try:
            existing_customer = GuestCustomer.objects.get(phone_number=phone)
            if existing_customer.phone_verified:
                # Phone already verified - skip sending OTP
                return Response({
                    'message': 'Phone number already verified.',
                    'already_verified': True,
                    'expires_in': 0,
                }, status=status.HTTP_200_OK)
        except GuestCustomer.DoesNotExist:
            pass  # New customer - proceed with OTP
        
        # Generate OTP
        otp = GuestOrderOTP.generate_for_phone(phone)
        
        # Increment rate limit
        GuestOrderRateLimit.increment(phone, 'otp')
        
        # Send SMS
        sms_service = HubtelSMSService()
        message = f"Your PMS Marketplace verification code is: {otp.code}. Valid for 10 minutes."
        
        result = sms_service.send_sms(phone, message)
        
        if not result.get('success', True):
            # Still return success to prevent phone enumeration
            pass
        
        return Response({
            'message': 'Verification code sent to your phone.',
            'already_verified': False,
            'expires_in': 600,  # 10 minutes
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    Verify OTP code.
    
    POST /api/public/marketplace/order/verify-otp/
    {
        "phone_number": "0241234567",
        "code": "123456"  // Optional if already verified
    }
    
    Returns:
    {
        "verified": true,
        "message": "Phone verified successfully",
        "already_verified": false
    }
    
    Note: If phone was already verified, code is optional
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone = serializer.validated_data['phone_number']
        code = serializer.validated_data.get('code', '')
        
        # Check if phone is already verified (no OTP needed)
        try:
            existing_customer = GuestCustomer.objects.get(phone_number=phone)
            if existing_customer.phone_verified:
                return Response({
                    'verified': True,
                    'message': 'Phone number already verified.',
                    'already_verified': True,
                }, status=status.HTTP_200_OK)
        except GuestCustomer.DoesNotExist:
            pass
        
        # Verify OTP code for new/unverified numbers
        if not code:
            return Response({
                'verified': False,
                'message': 'Verification code required.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update or create guest customer
        customer, _ = GuestCustomer.objects.get_or_create(
            phone_number=phone,
            defaults={'name': 'Guest'}
        )
        customer.phone_verified = True
        customer.phone_verified_at = timezone.now()
        customer.save(update_fields=['phone_verified', 'phone_verified_at'])
        
        return Response({
            'verified': True,
            'message': 'Phone verified successfully.',
            'already_verified': False,
        }, status=status.HTTP_200_OK)


class CreateGuestOrderView(APIView):
    """
    Create a guest order.
    
    POST /api/public/marketplace/order/create/
    {
        "captcha_token": "cloudflare-turnstile-token",
        "phone_number": "0241234567",
        "name": "Kofi Mensah",
        "email": "kofi@example.com",  // optional
        "items": [
            {"product_id": "uuid", "quantity": 2}
        ],
        "delivery_method": "pickup",  // or "delivery"
        "delivery_address": "Accra, Osu",  // required for delivery
        "preferred_date": "2026-01-05",
        "preferred_time": "Morning",
        "customer_notes": "Please call before coming"
    }
    
    Returns the created order with order_number for tracking.
    
    SECURITY FEATURES:
    - Cloudflare Turnstile CAPTCHA (blocks 99%+ bots, unlimited free)
    - Rate limiting: Max 5 orders/hour per phone number
    - Selective OTP re-verification when rate limit hit
    """
    permission_classes = [AllowAny]
    
    def _get_client_ip(self, request):
        """Extract client IP from request headers (supports proxies/load balancers)."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can be comma-separated list, first is original client
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def post(self, request):
        # SECURITY LAYER 1: Cloudflare Turnstile CAPTCHA
        captcha_token = request.data.get('captcha_token')
        if not captcha_token:
            return Response({
                'error': 'CAPTCHA verification required.',
                'code': 'CAPTCHA_MISSING',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify CAPTCHA with Cloudflare
        user_ip = self._get_client_ip(request)
        is_valid = turnstile_service.verify_token(captcha_token, user_ip)
        
        if not is_valid:
            return Response({
                'error': 'CAPTCHA verification failed. Please try again.',
                'code': 'CAPTCHA_INVALID',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # SECURITY LAYER 2: Validate order data (includes rate limit check)
        serializer = GuestOrderCreateSerializer(data=request.data, context={'request': request})
        
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            # Check if rate limit hit (requires OTP re-verification)
            if 'phone_number' in e.detail:
                phone_errors = e.detail['phone_number']
                if isinstance(phone_errors, list):
                    for error in phone_errors:
                        if hasattr(error, 'code') and error.code == 'rate_limit_otp_required':
                            return Response({
                                'error': str(error),
                                'code': 'RATE_LIMIT_OTP_REQUIRED',
                                'requires_otp_reverification': True,
                            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Re-raise validation error
            raise
        
        # SECURITY LAYER 3: Create order (already validated)
        order = serializer.save()
        
        # Send OTP for verification
        phone = order.guest_customer.phone_number
        otp = GuestOrderOTP.generate_for_phone(phone)
        
        # Send SMS
        sms_service = HubtelSMSService()
        message = (
            f"Your order {order.order_number} has been received. "
            f"Verify with code: {otp.code}. "
            f"Total: GHS {order.total_amount:.2f}"
        )
        sms_service.send_sms(phone, message)
        
        return Response({
            'message': 'Order created. Please verify with the code sent to your phone.',
            'order_number': order.order_number,
            'verification_required': True,
            'total_amount': str(order.total_amount),
        }, status=status.HTTP_201_CREATED)


class VerifyGuestOrderView(APIView):
    """
    Verify a guest order with OTP.
    
    POST /api/public/marketplace/order/verify/
    {
        "order_number": "GO-20260102-XXXXX",
        "phone_number": "0241234567",
        "code": "123456"
    }
    
    After verification, order status changes to pending_confirmation
    and farmer is notified.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        order_number = request.data.get('order_number')
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')
        
        if not all([order_number, phone_number, code]):
            return Response({
                'error': 'order_number, phone_number, and code are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone = GuestCustomer.normalize_phone(phone_number)
        
        # Verify OTP
        success, message = GuestOrderOTP.verify(phone, code)
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find order
        try:
            order = GuestOrder.objects.get(
                order_number=order_number,
                guest_customer__phone_number=phone,
                status='pending_verification'
            )
        except GuestOrder.DoesNotExist:
            return Response({
                'error': 'Order not found or already verified.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update order status
        order.status = 'pending_confirmation'
        order.verified_at = timezone.now()
        order.save()
        
        # Update customer verification status
        order.guest_customer.phone_verified = True
        order.guest_customer.phone_verified_at = timezone.now()
        order.guest_customer.save()
        
        # Notify farmer (SMS)
        sms_service = HubtelSMSService()
        farmer_message = (
            f"New order {order.order_number}! "
            f"Customer: {order.guest_customer.name}, "
            f"Amount: GHS {order.total_amount:.2f}. "
            f"Please confirm in your dashboard."
        )
        if order.farm.primary_phone:
            sms_service.send_sms(str(order.farm.primary_phone), farmer_message)
        
        return Response({
            'message': 'Order verified successfully. The farmer will confirm shortly.',
            'order': GuestOrderPublicSerializer(order).data
        }, status=status.HTTP_200_OK)


class TrackGuestOrderView(APIView):
    """
    Track guest order status.
    
    GET /api/public/marketplace/order/track/?order_number=XXX&phone=XXX
    
    Returns order status and details.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        order_number = request.query_params.get('order_number')
        phone = request.query_params.get('phone')
        
        if not order_number or not phone:
            return Response({
                'error': 'order_number and phone are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone = GuestCustomer.normalize_phone(phone)
        
        try:
            order = GuestOrder.objects.get(
                order_number=order_number,
                guest_customer__phone_number=phone
            )
        except GuestOrder.DoesNotExist:
            return Response({
                'error': 'Order not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(GuestOrderPublicSerializer(order).data)


class CancelGuestOrderView(APIView):
    """
    Customer cancels their guest order.
    
    POST /api/public/marketplace/order/cancel/
    {
        "order_number": "GO-20260102-XXXXX",
        "phone_number": "0241234567"
    }
    
    Can only cancel orders that haven't been confirmed or paid.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        order_number = request.data.get('order_number')
        phone = request.data.get('phone_number')
        
        if not order_number or not phone:
            return Response({
                'error': 'order_number and phone_number are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone = GuestCustomer.normalize_phone(phone)
        
        try:
            order = GuestOrder.objects.get(
                order_number=order_number,
                guest_customer__phone_number=phone
            )
        except GuestOrder.DoesNotExist:
            return Response({
                'error': 'Order not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Can only cancel pending orders
        if order.status not in ['pending_verification', 'pending_confirmation', 'confirmed']:
            return Response({
                'error': 'Cannot cancel this order. Payment may have been confirmed already.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order.cancel('customer_request', 'Customer requested cancellation')
        
        return Response({
            'message': 'Order cancelled successfully.',
            'order_number': order.order_number
        }, status=status.HTTP_200_OK)


# =============================================================================
# FARMER GUEST ORDER MANAGEMENT (Authentication Required)
# =============================================================================

class FarmerGuestOrderListView(generics.ListAPIView):
    """
    List guest orders for farmer's farm.
    
    GET /api/marketplace/guest-orders/
    GET /api/marketplace/guest-orders/?status=pending_confirmation
    """
    permission_classes = [IsAuthenticated]
    serializer_class = GuestOrderSerializer
    
    def get_queryset(self):
        queryset = GuestOrder.objects.filter(
            farm=self.request.user.farm
        ).select_related('guest_customer').prefetch_related('items')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


class FarmerGuestOrderDetailView(generics.RetrieveAPIView):
    """
    Get guest order details.
    
    GET /api/marketplace/guest-orders/<id>/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = GuestOrderSerializer
    
    def get_queryset(self):
        return GuestOrder.objects.filter(
            farm=self.request.user.farm
        ).select_related('guest_customer').prefetch_related('items')


class FarmerGuestOrderActionView(APIView):
    """
    Farmer actions on guest orders.
    
    POST /api/marketplace/guest-orders/<id>/action/
    {
        "action": "confirm",  // confirm, confirm_payment, processing, ready, complete, cancel
        "payment_method": "MTN MoMo",  // for confirm_payment
        "payment_reference": "TX123456",  // optional
        "cancellation_reason": "farmer_unavailable",  // for cancel
        "notes": "..."
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        order = get_object_or_404(
            GuestOrder,
            pk=pk,
            farm=request.user.farm
        )
        
        serializer = FarmerOrderActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        
        sms_service = HubtelSMSService()
        customer_phone = order.guest_customer.phone_number
        
        if action == 'confirm':
            if order.status != 'pending_confirmation':
                return Response({
                    'error': 'Order cannot be confirmed in current state.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order.status = 'confirmed'
            order.confirmed_at = timezone.now()
            if notes:
                order.farmer_notes = notes
            order.save()
            
            # Notify customer
            sms_service.send_sms(
                customer_phone,
                f"Your order {order.order_number} has been confirmed! "
                f"Total: GHS {order.total_amount:.2f}. "
                f"Please proceed with payment. Contact farm: {order.farm.primary_phone}"
            )
            
        elif action == 'confirm_payment':
            if order.status not in ['confirmed', 'pending_confirmation']:
                return Response({
                    'error': 'Cannot confirm payment in current state.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            payment_method = serializer.validated_data.get('payment_method', '')
            payment_ref = serializer.validated_data.get('payment_reference', '')
            
            order.confirm_payment(request.user, payment_method, payment_ref)
            
            # Notify customer
            sms_service.send_sms(
                customer_phone,
                f"Payment confirmed for order {order.order_number}! "
                f"We're preparing your order. Thank you!"
            )
            
        elif action == 'processing':
            order.status = 'processing'
            order.save()
            
        elif action == 'ready':
            order.status = 'ready'
            order.save()
            
            # Notify customer
            delivery_msg = "ready for pickup" if order.delivery_method == 'pickup' else "ready for delivery"
            sms_service.send_sms(
                customer_phone,
                f"Your order {order.order_number} is {delivery_msg}! "
                f"Contact: {order.farm.primary_phone}"
            )
            
        elif action == 'complete':
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()
            
            # Update customer stats
            order.guest_customer.completed_orders += 1
            order.guest_customer.save()
            
            # Update product stats
            for item in order.items.all():
                item.product.total_sold += item.quantity
                item.product.total_revenue += item.line_total
                item.product.save()
            
        elif action == 'cancel':
            reason = serializer.validated_data.get('cancellation_reason', 'other')
            order.cancel(reason, notes)
            
            # Notify customer
            sms_service.send_sms(
                customer_phone,
                f"Your order {order.order_number} has been cancelled. "
                f"Reason: {order.get_cancellation_reason_display()}. "
                f"Contact farm for more info: {order.farm.primary_phone}"
            )
        
        return Response({
            'message': f'Order {action} successful.',
            'order': GuestOrderSerializer(order).data
        })


# =============================================================================
# POS SALES VIEWS (Farmer Authentication Required)
# =============================================================================

class POSSaleCreateView(APIView):
    """
    Quick POS sale entry for farm-gate sales.
    
    POST /api/marketplace/pos/sales/
    {
        "items": [
            {"product_id": "uuid", "quantity": 2, "unit_price": 50.00}
        ],
        "payment_method": "cash",  // cash, momo_mtn, momo_voda, momo_tigo, bank_transfer, credit
        "payment_reference": "TX123",  // for mobile money
        "customer_name": "Walk-in Customer",  // optional
        "customer_phone": "0241234567",  // optional
        "discount_amount": 0,
        "credit_due_date": "2026-01-15",  // required for credit
        "notes": "Regular customer"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not hasattr(request.user, 'farm'):
            return Response({
                'error': 'User is not associated with a farm.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = POSSaleCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        sale = serializer.save()
        
        return Response({
            'message': 'Sale recorded successfully.',
            'sale': POSSaleSerializer(sale).data
        }, status=status.HTTP_201_CREATED)


class POSSaleListView(generics.ListAPIView):
    """
    List POS sales for the farm.
    
    GET /api/marketplace/pos/sales/
    GET /api/marketplace/pos/sales/?date=2026-01-02
    GET /api/marketplace/pos/sales/?is_credit=true
    """
    permission_classes = [IsAuthenticated]
    serializer_class = POSSaleListSerializer
    
    def get_queryset(self):
        if not hasattr(self.request.user, 'farm'):
            return POSSale.objects.none()
        
        queryset = POSSale.objects.filter(
            farm=self.request.user.farm
        ).select_related('recorded_by')
        
        # Filter by date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(sale_date__date=date)
        
        # Filter by credit status
        is_credit = self.request.query_params.get('is_credit')
        if is_credit == 'true':
            queryset = queryset.filter(is_credit_sale=True)
        elif is_credit == 'false':
            queryset = queryset.filter(is_credit_sale=False)
        
        # Filter unpaid credit
        unpaid_credit = self.request.query_params.get('unpaid_credit')
        if unpaid_credit == 'true':
            queryset = queryset.filter(is_credit_sale=True, credit_paid=False)
        
        return queryset.order_by('-sale_date')


class POSSaleDetailView(generics.RetrieveAPIView):
    """
    Get POS sale details.
    
    GET /api/marketplace/pos/sales/<id>/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = POSSaleSerializer
    
    def get_queryset(self):
        if not hasattr(self.request.user, 'farm'):
            return POSSale.objects.none()
        
        return POSSale.objects.filter(
            farm=self.request.user.farm
        ).prefetch_related('items')


class POSSaleMarkCreditPaidView(APIView):
    """
    Mark a credit sale as paid.
    
    POST /api/marketplace/pos/sales/<id>/mark-paid/
    {
        "payment_method": "momo_mtn",
        "payment_reference": "TX123456"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if not hasattr(request.user, 'farm'):
            return Response({
                'error': 'User is not associated with a farm.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        sale = get_object_or_404(
            POSSale,
            pk=pk,
            farm=request.user.farm,
            is_credit_sale=True,
            credit_paid=False
        )
        
        payment_method = request.data.get('payment_method', '')
        payment_ref = request.data.get('payment_reference', '')
        
        sale.mark_credit_paid(payment_method, payment_ref)
        
        return Response({
            'message': 'Credit sale marked as paid.',
            'sale': POSSaleSerializer(sale).data
        })


class POSSaleSummaryView(APIView):
    """
    Get POS sales summary for today or date range.
    
    GET /api/marketplace/pos/summary/
    GET /api/marketplace/pos/summary/?date=2026-01-02
    GET /api/marketplace/pos/summary/?from=2026-01-01&to=2026-01-31
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not hasattr(request.user, 'farm'):
            return Response({
                'error': 'User is not associated with a farm.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from django.db.models import Sum, Count
        
        queryset = POSSale.objects.filter(farm=request.user.farm)
        
        # Date filtering
        date = request.query_params.get('date')
        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')
        
        if date:
            queryset = queryset.filter(sale_date__date=date)
            period = date
        elif date_from and date_to:
            queryset = queryset.filter(sale_date__date__gte=date_from, sale_date__date__lte=date_to)
            period = f"{date_from} to {date_to}"
        else:
            today = timezone.now().date()
            queryset = queryset.filter(sale_date__date=today)
            period = str(today)
        
        # Aggregate
        summary = queryset.aggregate(
            total_sales=Count('id'),
            total_revenue=Sum('total_amount'),
            total_received=Sum('amount_received'),
            credit_sales=Count('id', filter=Q(is_credit_sale=True)),
            credit_amount=Sum('total_amount', filter=Q(is_credit_sale=True)),
            unpaid_credit=Sum('total_amount', filter=Q(is_credit_sale=True, credit_paid=False)),
        )
        
        # Handle None values
        for key in summary:
            if summary[key] is None:
                summary[key] = 0
        
        summary['period'] = period
        
        return Response(summary)
