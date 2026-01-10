"""
Guest Order and POS Serializers

Serializers for guest checkout (public marketplace) and POS sales (farm-gate).
"""

from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .guest_order_models import (
    GuestCustomer,
    GuestOrder,
    GuestOrderItem,
    GuestOrderOTP,
    GuestOrderRateLimit,
    POSSale,
    POSSaleItem,
)
from .marketplace_models import Product


# =============================================================================
# GUEST CHECKOUT SERIALIZERS (Public - No Auth Required)
# =============================================================================

class GuestCustomerSerializer(serializers.ModelSerializer):
    """Serializer for guest customer info."""
    
    class Meta:
        model = GuestCustomer
        fields = [
            'id', 'name', 'phone_number', 'email', 'location',
            'phone_verified', 'total_orders', 'completed_orders'
        ]
        read_only_fields = ['id', 'phone_verified', 'total_orders', 'completed_orders']


class RequestOTPSerializer(serializers.Serializer):
    """Request OTP for phone verification."""
    phone_number = serializers.CharField(max_length=15)
    
    def validate_phone_number(self, value):
        """Normalize and validate phone number."""
        phone = GuestCustomer.normalize_phone(value)
        
        # Check if phone is blocked
        try:
            customer = GuestCustomer.objects.get(phone_number=phone)
            if customer.is_blocked:
                raise serializers.ValidationError(
                    "This phone number has been blocked. Please contact support."
                )
        except GuestCustomer.DoesNotExist:
            pass
        
        # Check rate limit (max 5 OTP requests per day)
        allowed, remaining = GuestOrderRateLimit.check_limit(phone, 'otp', max_count=5)
        if not allowed:
            raise serializers.ValidationError(
                "Too many OTP requests today. Please try again tomorrow."
            )
        
        return phone


class VerifyOTPSerializer(serializers.Serializer):
    """
    Verify OTP code.
    
    Code is optional if phone number was already verified in a previous transaction.
    """
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6, required=False, allow_blank=True)
    
    def validate_phone_number(self, value):
        return GuestCustomer.normalize_phone(value)
    
    def validate(self, data):
        phone = data['phone_number']
        code = data.get('code', '')
        
        # Skip OTP verification if phone already verified
        try:
            customer = GuestCustomer.objects.get(phone_number=phone)
            if customer.phone_verified:
                return data  # Already verified - no need to check code
        except GuestCustomer.DoesNotExist:
            pass
        
        # For new/unverified numbers, code is required
        if not code:
            raise serializers.ValidationError({
                'code': 'Verification code is required for new phone numbers.'
            })
        
        # Verify OTP
        success, message = GuestOrderOTP.verify(phone, code)
        if not success:
            raise serializers.ValidationError({'code': message})
        
        return data


class GuestOrderItemCreateSerializer(serializers.Serializer):
    """Serializer for creating order items."""
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    
    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value, status='active')
            return product
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or unavailable.")
    
    def validate(self, data):
        product = data['product_id']
        quantity = data['quantity']
        
        # Check stock
        if product.track_inventory and product.stock_quantity < quantity:
            raise serializers.ValidationError({
                'quantity': f"Only {product.stock_quantity} available in stock."
            })
        
        # Check min/max order quantity
        if quantity < product.min_order_quantity:
            raise serializers.ValidationError({
                'quantity': f"Minimum order quantity is {product.min_order_quantity}."
            })
        
        if product.max_order_quantity and quantity > product.max_order_quantity:
            raise serializers.ValidationError({
                'quantity': f"Maximum order quantity is {product.max_order_quantity}."
            })
        
        return data


class GuestOrderCreateSerializer(serializers.Serializer):
    """
    Create a guest order.
    
    Requires phone verification first.
    SECURITY: Requires Cloudflare Turnstile CAPTCHA to prevent bot attacks.
    """
    # Security
    captcha_token = serializers.CharField(
        max_length=2048,
        help_text="Cloudflare Turnstile CAPTCHA response token"
    )
    
    # Customer info
    phone_number = serializers.CharField(max_length=15)
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField(required=False, allow_blank=True)
    
    # Order items
    items = GuestOrderItemCreateSerializer(many=True, min_length=1)
    
    # Delivery info
    delivery_method = serializers.ChoiceField(
        choices=GuestOrder.DELIVERY_METHOD_CHOICES,
        default='pickup'
    )
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    delivery_gps = serializers.CharField(required=False, allow_blank=True, max_length=50)
    preferred_date = serializers.DateField(required=False, allow_null=True)
    preferred_time = serializers.CharField(required=False, allow_blank=True, max_length=50)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_phone_number(self, value):
        phone = GuestCustomer.normalize_phone(value)
        
        # Check if blocked
        try:
            customer = GuestCustomer.objects.get(phone_number=phone)
            if customer.is_blocked:
                raise serializers.ValidationError(
                    "This phone number has been blocked."
                )
        except GuestCustomer.DoesNotExist:
            pass
        
        # Check order rate limit (max 5 orders per hour)
        # This prevents abuse even with verified phone numbers
        from datetime import timedelta
        from django.utils import timezone
        
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_orders = GuestOrder.objects.filter(
            guest_customer__phone_number=phone,
            created_at__gte=one_hour_ago
        ).count()
        
        if recent_orders >= 5:
            # Store in context for view to trigger OTP re-verification
            self.context['requires_otp_reverification'] = True
            raise serializers.ValidationError(
                "Too many orders in the last hour. Please verify your phone number again.",
                code='rate_limit_otp_required'
            )
        
        return phone
    
    def validate_items(self, items):
        """Ensure all items are from the same farm."""
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        
        farms = set()
        for item in items:
            product = item['product_id']  # Already validated to Product instance
            farms.add(product.farm_id)
        
        if len(farms) > 1:
            raise serializers.ValidationError(
                "All items must be from the same farm. Please place separate orders for different farms."
            )
        
        return items
    
    def validate(self, data):
        # Require address for delivery
        if data['delivery_method'] == 'delivery' and not data.get('delivery_address'):
            raise serializers.ValidationError({
                'delivery_address': "Delivery address is required for delivery orders."
            })
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        phone = validated_data.pop('phone_number')
        name = validated_data.pop('name')
        email = validated_data.pop('email', '')
        
        # Get or create guest customer
        guest_customer, _ = GuestCustomer.get_or_create_by_phone(phone, name, email)
        
        # Get farm from first product
        farm = items_data[0]['product_id'].farm
        
        # Create order
        order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            status='pending_verification',
            delivery_method=validated_data.get('delivery_method', 'pickup'),
            delivery_address=validated_data.get('delivery_address', ''),
            delivery_gps=validated_data.get('delivery_gps', ''),
            preferred_date=validated_data.get('preferred_date'),
            preferred_time=validated_data.get('preferred_time', ''),
            customer_notes=validated_data.get('customer_notes', ''),
        )
        
        # Create order items
        subtotal = 0
        for item_data in items_data:
            product = item_data['product_id']
            quantity = item_data['quantity']
            line_total = product.price * quantity
            subtotal += line_total
            
            GuestOrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                product_sku=product.sku or '',
                unit=product.unit,
                unit_price=product.price,
                quantity=quantity,
                line_total=line_total
            )
            
            # Reserve stock
            product.reduce_stock(quantity)
        
        # Update totals
        order.subtotal = subtotal
        order.total_amount = subtotal + order.delivery_fee
        order.save()
        
        # Update rate limit
        GuestOrderRateLimit.increment(phone, 'order')
        
        # Update guest customer stats
        guest_customer.total_orders += 1
        guest_customer.last_order_at = timezone.now()
        guest_customer.save(update_fields=['total_orders', 'last_order_at'])
        
        return order


class GuestOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order item details."""
    
    class Meta:
        model = GuestOrderItem
        fields = [
            'id', 'product_id', 'product_name', 'product_sku',
            'unit', 'unit_price', 'quantity', 'line_total'
        ]
        read_only_fields = fields


class GuestOrderSerializer(serializers.ModelSerializer):
    """Full guest order serializer."""
    items = GuestOrderItemSerializer(many=True, read_only=True)
    guest_customer = GuestCustomerSerializer(read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = GuestOrder
        fields = [
            'id', 'order_number', 'farm', 'farm_name',
            'guest_customer', 'status', 'status_display',
            'delivery_method', 'delivery_address', 'delivery_gps',
            'preferred_date', 'preferred_time', 'customer_notes',
            'subtotal', 'delivery_fee', 'total_amount',
            'payment_method_used', 'payment_confirmed_at',
            'items', 'created_at', 'verified_at', 'confirmed_at'
        ]
        read_only_fields = fields


class GuestOrderPublicSerializer(serializers.ModelSerializer):
    """
    Limited order info for public access (order tracking).
    Customer can check order status with order number + phone.
    """
    items = GuestOrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    farm_phone = serializers.SerializerMethodField()
    
    class Meta:
        model = GuestOrder
        fields = [
            'order_number', 'status', 'status_display', 'farm_name', 'farm_phone',
            'delivery_method', 'preferred_date', 'preferred_time',
            'subtotal', 'delivery_fee', 'total_amount',
            'items', 'created_at', 'confirmed_at'
        ]
    
    def get_farm_phone(self, obj):
        """Return farm contact phone for order inquiries."""
        return str(obj.farm.primary_phone) if obj.farm.primary_phone else None


class ConfirmPaymentSerializer(serializers.Serializer):
    """Farmer confirms payment received."""
    payment_method = serializers.CharField(max_length=50, required=False)
    payment_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)


class FarmerOrderActionSerializer(serializers.Serializer):
    """Farmer actions on guest orders."""
    action = serializers.ChoiceField(choices=[
        ('confirm', 'Confirm Order'),
        ('confirm_payment', 'Confirm Payment Received'),
        ('processing', 'Mark as Processing'),
        ('ready', 'Mark as Ready'),
        ('complete', 'Mark as Completed'),
        ('cancel', 'Cancel Order'),
    ])
    payment_method = serializers.CharField(max_length=50, required=False, allow_blank=True)
    payment_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    cancellation_reason = serializers.ChoiceField(
        choices=GuestOrder.CANCELLATION_REASON_CHOICES,
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)


# =============================================================================
# POS SALES SERIALIZERS (Farmer Auth Required)
# =============================================================================

class POSSaleItemCreateSerializer(serializers.Serializer):
    """Create POS sale item."""
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        help_text="Override price if needed (e.g., for discounts)"
    )
    
    def validate_product_id(self, value):
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'farm'):
            raise serializers.ValidationError("Unable to verify product ownership.")
        
        try:
            product = Product.objects.get(id=value, farm=request.user.farm, status='active')
            return product
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or unavailable.")


class POSSaleItemSerializer(serializers.ModelSerializer):
    """POS sale item details."""
    
    class Meta:
        model = POSSaleItem
        fields = [
            'id', 'product_id', 'product_name', 'unit',
            'unit_price', 'quantity', 'line_total'
        ]
        read_only_fields = fields


class POSSaleCreateSerializer(serializers.Serializer):
    """Create a POS sale (quick sale entry for farmers)."""
    
    # Items
    items = POSSaleItemCreateSerializer(many=True, min_length=1)
    
    # Payment
    payment_method = serializers.ChoiceField(
        choices=POSSale.PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    payment_reference = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    
    # Optional customer info
    customer_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    customer_phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    
    # Discount
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )
    
    # Credit sale
    credit_due_date = serializers.DateField(required=False, allow_null=True)
    
    # Notes
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        # Require due date for credit sales
        if data['payment_method'] == 'credit' and not data.get('credit_due_date'):
            raise serializers.ValidationError({
                'credit_due_date': "Due date is required for credit sales."
            })
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        items_data = validated_data.pop('items')
        
        # Create sale
        sale = POSSale.objects.create(
            farm=request.user.farm,
            recorded_by=request.user,
            payment_method=validated_data.get('payment_method', 'cash'),
            payment_reference=validated_data.get('payment_reference', ''),
            customer_name=validated_data.get('customer_name', ''),
            customer_phone=validated_data.get('customer_phone', ''),
            customer_id=validated_data.get('customer_id'),
            discount_amount=validated_data.get('discount_amount', 0),
            credit_due_date=validated_data.get('credit_due_date'),
            notes=validated_data.get('notes', ''),
        )
        
        # Create items
        subtotal = 0
        for item_data in items_data:
            product = item_data['product_id']
            quantity = item_data['quantity']
            unit_price = item_data.get('unit_price', product.price)
            line_total = unit_price * quantity
            subtotal += line_total
            
            POSSaleItem.objects.create(
                sale=sale,
                product=product,
                product_name=product.name,
                unit=product.unit,
                unit_price=unit_price,
                quantity=quantity,
                line_total=line_total
            )
        
        # Update totals
        sale.subtotal = subtotal
        sale.total_amount = subtotal - sale.discount_amount
        
        if sale.payment_method != 'credit':
            sale.amount_received = sale.total_amount
        else:
            sale.is_credit_sale = True
            sale.amount_received = 0
        
        sale.save()
        
        return sale


class POSSaleSerializer(serializers.ModelSerializer):
    """Full POS sale serializer."""
    items = POSSaleItemSerializer(many=True, read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = POSSale
        fields = [
            'id', 'sale_number', 'farm', 'recorded_by', 'recorded_by_name',
            'customer_name', 'customer_phone', 'customer',
            'payment_method', 'payment_method_display', 'payment_reference',
            'subtotal', 'discount_amount', 'total_amount', 'amount_received',
            'is_credit_sale', 'credit_due_date', 'credit_paid', 'credit_paid_at',
            'notes', 'items', 'sale_date', 'created_at'
        ]
        read_only_fields = fields


class POSSaleListSerializer(serializers.ModelSerializer):
    """Compact POS sale list serializer."""
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = POSSale
        fields = [
            'id', 'sale_number', 'customer_name', 'payment_method',
            'total_amount', 'is_credit_sale', 'credit_paid',
            'recorded_by_name', 'item_count', 'sale_date'
        ]
    
    def get_item_count(self, obj):
        return obj.items.count()
