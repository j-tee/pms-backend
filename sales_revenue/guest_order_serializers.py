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
    
    SECURITY FEATURES:
    - Cloudflare Turnstile CAPTCHA to prevent bot attacks
    - Idempotency key to prevent duplicate submissions from network retries
    - select_for_update() locks to prevent race conditions
    - @transaction.atomic for all-or-nothing operations
    """
    # Security
    captcha_token = serializers.CharField(
        max_length=2048,
        help_text="Cloudflare Turnstile CAPTCHA response token"
    )
    
    # Idempotency key to prevent duplicate submissions
    idempotency_key = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        help_text="Unique key to prevent duplicate submissions (e.g., UUID generated by client)"
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
        
        # Get farm from first item
        items = data.get('items', [])
        if not items:
            return data
            
        farm = items[0]['product_id'].farm
        phone = GuestCustomer.normalize_phone(data.get('phone_number', ''))
        
        # BACKEND-GENERATED DUPLICATE DETECTION
        # Generate content hash from order details
        items_for_hash = [
            {'product_id': item['product_id'].id, 'quantity': item['quantity']}
            for item in items
        ]
        content_hash = GuestOrder.generate_content_hash(phone, str(farm.id), items_for_hash)
        
        # Check for duplicate within time window (10 minutes)
        duplicate_order = GuestOrder.find_duplicate(content_hash)
        if duplicate_order:
            # Store the duplicate for the view to return (idempotent response)
            self.context['duplicate_order'] = duplicate_order
            self.context['content_hash'] = content_hash
            return data  # Don't raise error - let view handle idempotent response
        
        # Store hash for create() method
        self.context['content_hash'] = content_hash
        
        # Also check client-provided idempotency key if present (belt and suspenders)
        idempotency_key = data.get('idempotency_key')
        if idempotency_key:
            existing_order = GuestOrder.objects.filter(
                farm=farm,
                idempotency_key=idempotency_key
            ).first()
            if existing_order:
                self.context['duplicate_order'] = existing_order
                return data  # Let view handle idempotent response
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create guest order with atomicity and race condition protection.
        
        ATOMICITY GUARANTEES:
        1. @transaction.atomic ensures all DB operations succeed or all rollback
        2. select_for_update() locks Product rows to prevent race conditions
        3. Stock validation happens INSIDE the transaction with locks held
        4. Content-based duplicate detection (backend-generated)
        5. Optional client idempotency_key for additional protection
        4. Optional idempotency_key prevents duplicate submissions
        """
        from .marketplace_models import Product
        
        items_data = validated_data.pop('items')
        phone = validated_data.pop('phone_number')
        name = validated_data.pop('name')
        email = validated_data.pop('email', '')
        
        # Get or create guest customer
        guest_customer, _ = GuestCustomer.get_or_create_by_phone(phone, name, email)
        
        # Get farm from first product
        farm = items_data[0]['product_id'].farm
        
        # STEP 1: Collect all product IDs and lock them FIRST (prevents race conditions)
        product_ids = [item['product_id'].id for item in items_data]
        
        # Lock all product rows in a consistent order (by ID) to prevent deadlocks
        locked_products = {
            p.id: p for p in Product.objects.filter(
                id__in=sorted(set(product_ids))
            ).select_for_update(nowait=False).order_by('id')
        }
        
        # STEP 2: Re-validate stock levels with locks held (prevents TOCTOU race condition)
        for item_data in items_data:
            original_product = item_data['product_id']
            quantity = item_data['quantity']
            locked_product = locked_products.get(original_product.id)
            
            if not locked_product:
                raise serializers.ValidationError({
                    'items': f"Could not lock product '{original_product.name}'."
                })
            
            if locked_product.track_inventory and locked_product.stock_quantity < quantity:
                raise serializers.ValidationError({
                    'items': f"Insufficient stock for '{locked_product.name}'. "
                             f"Available: {locked_product.stock_quantity}, Requested: {quantity}."
                })
        
        # STEP 3: Create order with content hash and optional idempotency key
        idempotency_key = validated_data.pop('idempotency_key', None)
        content_hash = self.context.get('content_hash')
        
        order = GuestOrder.objects.create(
            farm=farm,
            guest_customer=guest_customer,
            content_hash=content_hash,
            idempotency_key=idempotency_key or None,
            status='pending_verification',
            delivery_method=validated_data.get('delivery_method', 'pickup'),
            delivery_address=validated_data.get('delivery_address', ''),
            delivery_gps=validated_data.get('delivery_gps', ''),
            preferred_date=validated_data.get('preferred_date'),
            preferred_time=validated_data.get('preferred_time', ''),
            customer_notes=validated_data.get('customer_notes', ''),
        )
        
        # STEP 4: Create order items and reduce stock from locked products with audit trail
        subtotal = 0
        for item_data in items_data:
            original_product = item_data['product_id']
            quantity = item_data['quantity']
            locked_product = locked_products[original_product.id]
            line_total = locked_product.price * quantity
            subtotal += line_total
            
            order_item = GuestOrderItem.objects.create(
                order=order,
                product=locked_product,
                product_name=locked_product.name,
                product_sku=locked_product.sku or '',
                unit=locked_product.unit,
                unit_price=locked_product.price,
                quantity=quantity,
                line_total=line_total
            )
            
            # Reserve stock from locked product with full audit trail
            locked_product.reduce_stock(
                quantity=quantity,
                reference_record=order_item,
                unit_price=locked_product.price,
                notes=f"Guest order {order.order_number} - {locked_product.name}",
                recorded_by=None  # Guest order - no authenticated user
            )
        
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
        """
        Validate product for POS sale.
        
        BUSINESS RULE: The flow must be Production → Inventory → Sales
        
        Products can only be sold if:
        1. They exist and belong to the farmer's farm
        2. They are linked to a FarmInventory record (moved to inventory)
        3. The inventory has available stock (quantity_available > 0)
        4. Product status is 'active' (not discontinued, draft, or out_of_stock)
        
        This ensures:
        - All sales data comes from a single source (inventory)
        - Reconciliation is straightforward
        - Stock tracking is accurate
        """
        request = self.context.get('request')
        if not request or not hasattr(request.user, 'farm'):
            raise serializers.ValidationError("Unable to verify product ownership.")
        
        farm = request.user.farm
        
        try:
            # Get product belonging to this farm
            product = Product.objects.get(id=value, farm=farm)
            
            # Check product status - must be active
            if product.status != 'active':
                status_messages = {
                    'draft': "Product is still in draft. Publish it first before selling.",
                    'out_of_stock': "Product is out of stock. Add inventory first.",
                    'discontinued': "Product is discontinued and cannot be sold.",
                }
                raise serializers.ValidationError(
                    status_messages.get(product.status, f"Product status '{product.status}' does not allow sales.")
                )
            
            # Check if product is linked to inventory
            if not hasattr(product, 'inventory_record') or product.inventory_record is None:
                raise serializers.ValidationError(
                    "Product is not in inventory. Move products to inventory before selling."
                )
            
            # Check inventory has stock available
            inventory = product.inventory_record
            if inventory.quantity_available <= 0:
                raise serializers.ValidationError(
                    f"No stock available in inventory. Current stock: {inventory.quantity_available} {inventory.unit}."
                )
            
            return product
        except Product.DoesNotExist:
            raise serializers.ValidationError(
                "Product not found or does not belong to your farm."
            )
    
    def validate(self, data):
        """Validate quantity against available inventory."""
        product = data.get('product_id')
        quantity = data.get('quantity')
        
        if product and hasattr(product, 'inventory_record') and product.inventory_record:
            available = product.inventory_record.quantity_available
            if quantity > available:
                raise serializers.ValidationError({
                    'quantity': f"Requested quantity ({quantity}) exceeds available stock ({available})."
                })
        
        return data


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
    """
    Create a POS sale (quick sale entry for farmers).
    
    ATOMICITY & IDEMPOTENCY:
    - Uses @transaction.atomic to ensure all-or-nothing
    - Uses select_for_update() to lock inventory rows and prevent race conditions
    - Supports optional idempotency_key to prevent duplicate submissions
    - All stock checks are done inside the transaction with locks held
    """
    
    # Idempotency key to prevent duplicate submissions
    idempotency_key = serializers.CharField(
        max_length=64, required=False, allow_blank=True,
        help_text="Unique key to prevent duplicate submissions (e.g., UUID)"
    )
    
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
    
    def __init__(self, *args, **kwargs):
        """Ensure context is passed to nested serializers."""
        super().__init__(*args, **kwargs)
        # Pass the context to nested items serializer
        if 'items' in self.fields:
            self.fields['items'].context.update(self.context)
    
    def validate(self, data):
        # Require due date for credit sales
        if data['payment_method'] == 'credit' and not data.get('credit_due_date'):
            raise serializers.ValidationError({
                'credit_due_date': "Due date is required for credit sales."
            })
        
        # Check idempotency key for duplicate prevention
        idempotency_key = data.get('idempotency_key')
        if idempotency_key:
            request = self.context.get('request')
            if request and hasattr(request.user, 'farm'):
                # Check if a sale with this idempotency key already exists
                existing_sale = POSSale.objects.filter(
                    farm=request.user.farm,
                    idempotency_key=idempotency_key
                ).first()
                if existing_sale:
                    raise serializers.ValidationError({
                        'idempotency_key': f"A sale with this key already exists: {existing_sale.sale_number}"
                    })
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create POS sale and deduct from inventory.
        
        FLOW: Production → Inventory → Sales
        All sales must deduct from FarmInventory to maintain single source of truth.
        
        ATOMICITY GUARANTEES:
        1. @transaction.atomic ensures all DB operations succeed or all rollback
        2. select_for_update() locks inventory rows to prevent race conditions
        3. Stock validation happens INSIDE the transaction with locks held
        4. Optional idempotency_key prevents duplicate submissions
        """
        from sales_revenue.inventory_models import FarmInventory, StockMovementType
        from django.db import IntegrityError
        
        request = self.context['request']
        items_data = validated_data.pop('items')
        idempotency_key = validated_data.pop('idempotency_key', None)
        
        # STEP 1: Collect all inventory IDs and lock them FIRST (prevents deadlocks by consistent ordering)
        inventory_ids = []
        for item_data in items_data:
            product = item_data['product_id']
            if hasattr(product, 'inventory_record') and product.inventory_record:
                inventory_ids.append(product.inventory_record_id)
        
        # Lock all inventory rows in a consistent order (by ID) to prevent deadlocks
        inventory_ids = sorted(set(inventory_ids))
        locked_inventories = {
            inv.id: inv for inv in FarmInventory.objects.filter(
                id__in=inventory_ids
            ).select_for_update(nowait=False).order_by('id')
        }
        
        # STEP 2: Re-validate stock levels with locks held (prevents TOCTOU race condition)
        for item_data in items_data:
            product = item_data['product_id']
            quantity = item_data['quantity']
            
            if not hasattr(product, 'inventory_record') or product.inventory_record is None:
                raise serializers.ValidationError({
                    'items': f"Product '{product.name}' is not linked to inventory."
                })
            
            inventory = locked_inventories.get(product.inventory_record_id)
            if not inventory:
                raise serializers.ValidationError({
                    'items': f"Could not lock inventory for product '{product.name}'."
                })
            
            if inventory.quantity_available < quantity:
                raise serializers.ValidationError({
                    'items': f"Insufficient stock for '{product.name}'. "
                             f"Available: {inventory.quantity_available}, Requested: {quantity}."
                })
        
        # STEP 3: Create sale with idempotency key
        sale = POSSale.objects.create(
            farm=request.user.farm,
            recorded_by=request.user,
            idempotency_key=idempotency_key or None,
            payment_method=validated_data.get('payment_method', 'cash'),
            payment_reference=validated_data.get('payment_reference', ''),
            customer_name=validated_data.get('customer_name', ''),
            customer_phone=validated_data.get('customer_phone', ''),
            customer_id=validated_data.get('customer_id'),
            discount_amount=validated_data.get('discount_amount', 0),
            credit_due_date=validated_data.get('credit_due_date'),
            notes=validated_data.get('notes', ''),
        )
        
        # STEP 4: Create items and deduct from locked inventory
        subtotal = 0
        for item_data in items_data:
            product = item_data['product_id']
            quantity = item_data['quantity']
            unit_price = item_data.get('unit_price', product.price)
            line_total = unit_price * quantity
            subtotal += line_total
            
            # Create sale item
            POSSaleItem.objects.create(
                sale=sale,
                product=product,
                product_name=product.name,
                unit=product.unit,
                unit_price=unit_price,
                quantity=quantity,
                line_total=line_total
            )
            
            # Deduct from locked inventory (the single source of truth)
            inventory = locked_inventories[product.inventory_record_id]
            inventory.remove_stock(
                quantity=quantity,
                movement_type=StockMovementType.SALE,
                unit_price=unit_price,
                notes=f"POS Sale {sale.sale_number}",
                recorded_by=request.user
            )
        
        # STEP 5: Update totals
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
