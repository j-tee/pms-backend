"""
Serializers for Returns and Refunds functionality.
Provides API serialization for customer return requests, refund processing, and related operations.
"""

from rest_framework import serializers
from django.db import models
from decimal import Decimal
from .returns_refunds_models import (
    ReturnRequest, ReturnItem, RefundTransaction, ReturnReason
)
from .marketplace_models import MarketplaceOrder, OrderItem
from accounts.serializers import UserSerializer


class ReturnItemSerializer(serializers.ModelSerializer):
    """Serializer for individual return items."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.product_code', read_only=True)
    order_item_quantity = serializers.IntegerField(source='order_item.quantity', read_only=True)
    max_returnable_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = ReturnItem
        fields = [
            'id', 'return_request', 'order_item', 'product', 'product_name', 'product_code',
            'quantity', 'order_item_quantity', 'max_returnable_quantity',
            'reason', 'refund_amount', 'restocking_fee', 'condition_on_arrival',
            'quality_notes', 'stock_restored', 'stock_movement', 'created_at'
        ]
        read_only_fields = ['id', 'return_request', 'stock_restored', 'stock_movement', 'created_at']
    
    def get_max_returnable_quantity(self, obj):
        """Calculate maximum quantity that can be returned for this item."""
        if obj.order_item:
            # Quantity from order minus any already returned
            already_returned = ReturnItem.objects.filter(
                order_item=obj.order_item,
                return_request__status__in=['approved', 'items_received', 'refund_issued', 'completed']
            ).exclude(id=obj.id).aggregate(total=models.Sum('quantity'))['total'] or 0
            return obj.order_item.quantity - already_returned
        return 0
    
    def validate_quantity(self, value):
        """Ensure return quantity doesn't exceed order quantity."""
        if value <= 0:
            raise serializers.ValidationError("Return quantity must be greater than zero.")
        return value
    
    def validate(self, attrs):
        """Validate return item data."""
        order_item = attrs.get('order_item')
        quantity = attrs.get('quantity')
        
        if order_item and quantity:
            # Check if quantity exceeds what was ordered
            if quantity > order_item.quantity:
                raise serializers.ValidationError({
                    'quantity': f"Cannot return {quantity} items. Order only contains {order_item.quantity} units."
                })
            
            # Check for duplicate returns
            already_returned = ReturnItem.objects.filter(
                order_item=order_item,
                return_request__status__in=['approved', 'items_received', 'refund_issued', 'completed']
            ).aggregate(total=models.Sum('quantity'))['total'] or 0
            
            if already_returned + quantity > order_item.quantity:
                available = order_item.quantity - already_returned
                raise serializers.ValidationError({
                    'quantity': f"Only {available} units available for return ({already_returned} already returned)."
                })
        
        return attrs


class ReturnItemCreateSerializer(serializers.Serializer):
    """Simplified serializer for creating return items in a return request."""
    
    order_item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(choices=ReturnReason.choices)
    
    def validate_order_item_id(self, value):
        """Ensure order item exists."""
        if not OrderItem.objects.filter(id=value).exists():
            raise serializers.ValidationError("Order item not found.")
        return value


class RefundTransactionSerializer(serializers.ModelSerializer):
    """Serializer for refund transaction records."""
    
    return_number = serializers.CharField(source='return_request.return_number', read_only=True)
    
    class Meta:
        model = RefundTransaction
        fields = [
            'id', 'return_request', 'return_number', 'transaction_id', 'amount',
            'payment_method', 'payment_provider', 'status', 'initiated_by',
            'processed_at', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReturnRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing return requests."""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(source='items.count', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ReturnRequest
        fields = [
            'id', 'return_number', 'order', 'order_number', 'customer',
            'customer_name', 'status', 'status_display', 'items_count',
            'total_refund_amount', 'requested_at', 'processed_at'
        ]
        read_only_fields = ['id', 'return_number', 'requested_at', 'processed_at']
    
    def get_customer_name(self, obj):
        """Get customer display name."""
        if obj.customer and obj.customer.user:
            return obj.customer.user.get_full_name() or obj.customer.user.email
        return "Unknown Customer"


class ReturnRequestDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for return request with all related data."""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    order_date = serializers.DateTimeField(source='order.created_at', read_only=True)
    customer_details = serializers.SerializerMethodField()
    items = ReturnItemSerializer(many=True, read_only=True)
    refund_transactions = RefundTransactionSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_details = UserSerializer(source='approved_by', read_only=True)
    rejected_by_details = UserSerializer(source='rejected_by', read_only=True)
    
    class Meta:
        model = ReturnRequest
        fields = [
            'id', 'return_number', 'order', 'order_number', 'order_date',
            'customer', 'customer_details', 'status', 'status_display',
            'requested_at', 'approved_at', 'approved_by', 'approved_by_details',
            'rejected_at', 'rejected_by', 'rejected_by_details', 'rejection_reason',
            'items_received_at', 'refund_issued_at', 'completed_at',
            'total_refund_amount', 'total_restocking_fee', 'items', 'refund_transactions',
            'return_shipping_address', 'return_shipping_carrier', 'return_tracking_number',
            'customer_notes', 'admin_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'return_number', 'requested_at', 'approved_at', 'approved_by',
            'rejected_at', 'rejected_by', 'items_received_at', 'refund_issued_at',
            'completed_at', 'created_at', 'updated_at'
        ]
    
    def get_customer_details(self, obj):
        """Get detailed customer information."""
        if obj.customer and obj.customer.user:
            user = obj.customer.user
            return {
                'id': obj.customer.id,
                'name': user.get_full_name() or user.email,
                'email': user.email,
                'phone': str(user.phone) if user.phone else None,
            }
        return None


class ReturnRequestCreateSerializer(serializers.Serializer):
    """Serializer for creating a new return request."""
    
    order_id = serializers.UUIDField()
    items = ReturnItemCreateSerializer(many=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    return_shipping_address = serializers.CharField(required=False, allow_blank=True)
    
    def validate_order_id(self, value):
        """Ensure order exists and belongs to the requesting customer."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context required.")
        
        try:
            order = MarketplaceOrder.objects.get(id=value)
        except MarketplaceOrder.DoesNotExist:
            raise serializers.ValidationError("Order not found.")
        
        # Verify customer owns this order
        if hasattr(request.user, 'customer_profile'):
            if order.customer != request.user.customer_profile:
                raise serializers.ValidationError("You can only request returns for your own orders.")
        
        # Check if order is eligible for returns (not too old, already delivered, etc.)
        if order.status not in ['delivered', 'completed']:
            raise serializers.ValidationError("Only delivered orders can be returned.")
        
        return value
    
    def validate_items(self, value):
        """Ensure at least one item is being returned."""
        if not value:
            raise serializers.ValidationError("At least one item must be selected for return.")
        return value
    
    def validate(self, attrs):
        """Cross-validate order and items."""
        order_id = attrs.get('order_id')
        items = attrs.get('items', [])
        
        if order_id and items:
            # Verify all order items belong to the specified order
            order_item_ids = [item['order_item_id'] for item in items]
            valid_order_items = OrderItem.objects.filter(
                id__in=order_item_ids,
                order_id=order_id
            ).values_list('id', flat=True)
            
            if len(valid_order_items) != len(order_item_ids):
                raise serializers.ValidationError({
                    'items': "Some items do not belong to the specified order."
                })
        
        return attrs
    
    def create(self, validated_data):
        """Create return request with items."""
        from django.db import transaction
        
        items_data = validated_data.pop('items')
        order = MarketplaceOrder.objects.get(id=validated_data['order_id'])
        
        request = self.context.get('request')
        customer = request.user.customer_profile if hasattr(request.user, 'customer_profile') else None
        
        with transaction.atomic():
            # Create return request
            return_request = ReturnRequest.objects.create(
                order=order,
                customer=customer,
                customer_notes=validated_data.get('customer_notes', ''),
                return_shipping_address=validated_data.get('return_shipping_address', ''),
                status='pending'
            )
            
            # Create return items
            for item_data in items_data:
                order_item = OrderItem.objects.get(id=item_data['order_item_id'])
                
                # Calculate refund amount (proportional to quantity returned)
                refund_amount = (order_item.unit_price * item_data['quantity'])
                
                ReturnItem.objects.create(
                    return_request=return_request,
                    order_item=order_item,
                    product=order_item.product,
                    quantity=item_data['quantity'],
                    reason=item_data['reason'],
                    refund_amount=refund_amount
                )
            
            # Calculate total refund amount
            return_request.total_refund_amount = sum(
                item.refund_amount for item in return_request.items.all()
            )
            return_request.save(update_fields=['total_refund_amount'])
        
        return return_request


class ReturnApprovalSerializer(serializers.Serializer):
    """Serializer for approving a return request."""
    
    approved = serializers.BooleanField()
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        """Ensure rejection reason is provided if not approved."""
        if not attrs.get('approved') and not attrs.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': "Rejection reason is required when denying a return."
            })
        return attrs


class ItemsReceivedSerializer(serializers.Serializer):
    """Serializer for marking items as received and assessing quality."""
    
    items = serializers.ListField(
        child=serializers.DictField()
    )
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        """Validate items received data structure."""
        for item in value:
            if 'id' not in item:
                raise serializers.ValidationError("Each item must have an 'id' field.")
            if 'condition_on_arrival' not in item:
                raise serializers.ValidationError("Each item must have a 'condition_on_arrival' field.")
            if item['condition_on_arrival'] not in ['good', 'damaged', 'defective']:
                raise serializers.ValidationError("Invalid condition value. Must be 'good', 'damaged', or 'defective'.")
        return value


class IssueRefundSerializer(serializers.Serializer):
    """Serializer for issuing refund to customer."""
    
    payment_method = serializers.CharField(max_length=50)
    payment_provider = serializers.CharField(max_length=100, required=False, allow_blank=True)
    transaction_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_payment_method(self, value):
        """Ensure payment method is valid."""
        valid_methods = ['mobile_money', 'bank_transfer', 'cash', 'store_credit']
        if value not in valid_methods:
            raise serializers.ValidationError(f"Payment method must be one of: {', '.join(valid_methods)}")
        return value
