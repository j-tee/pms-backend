"""
Marketplace Views

API views for marketplace functionality with farm-scoped data access.
Each farmer can only view and manage their own marketplace data.

SECURITY FEATURES:
1. All querysets are filtered by request.user.farm
2. Create operations auto-populate farm from authenticated user
3. Permission checks ensure only farm owners can access their data
4. No cross-farm data access is possible
"""

from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .marketplace_models import (
    ProductCategory,
    Product,
    ProductImage,
    MarketplaceOrder,
    OrderItem,
    MarketplaceStatistics
)
from .models import Customer
from .marketplace_serializers import (
    ProductCategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    CustomerSerializer,
    MarketplaceOrderListSerializer,
    MarketplaceOrderDetailSerializer,
    OrderCreateSerializer,
    MarketplaceStatisticsSerializer,
    MarketplaceDashboardSerializer
)


class IsFarmer(permissions.BasePermission):
    """
    Permission check for farmer access.
    Ensures the user has a farm associated with their account.
    """
    message = "You must have a registered farm to access the marketplace."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            hasattr(request.user, 'farm') and
            request.user.farm is not None
        )


class FarmScopedMixin:
    """
    Mixin that filters querysets to only include data belonging to the farmer's farm.
    
    SECURITY: This is the core security mechanism that prevents data breaches.
    All marketplace views must inherit from this mixin.
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    
    def get_farm(self):
        """Get the authenticated farmer's farm."""
        return self.request.user.farm
    
    def get_queryset(self):
        """
        SECURITY: Filter queryset to only include records from the farmer's farm.
        This prevents farmers from seeing other farmers' data.
        """
        queryset = super().get_queryset()
        return queryset.filter(farm=self.get_farm())


# =============================================================================
# PRODUCT CATEGORY VIEWS (Read-only for farmers)
# =============================================================================

class ProductCategoryListView(generics.ListAPIView):
    """
    List all active product categories.
    Categories are system-wide and managed by admins.
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.filter(is_active=True)


# =============================================================================
# PRODUCT VIEWS
# =============================================================================

class ProductListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    List farmer's products or create a new product.
    
    GET: Returns only products belonging to the authenticated farmer's farm.
    POST: Creates a new product with farm auto-populated from the authenticated user.
    
    SECURITY: Farmers can only see and create products for their own farm.
    """
    queryset = Product.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductDetailSerializer
        return ProductListSerializer
    
    def get_queryset(self):
        """Get products filtered by farm with optional query parameters."""
        queryset = super().get_queryset()
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by stock status
        stock_status = self.request.query_params.get('stock_status')
        if stock_status == 'in_stock':
            queryset = queryset.filter(
                Q(track_inventory=False) | Q(stock_quantity__gt=0)
            )
        elif stock_status == 'out_of_stock':
            queryset = queryset.filter(
                track_inventory=True,
                stock_quantity=0
            )
        elif stock_status == 'low_stock':
            queryset = queryset.filter(
                track_inventory=True,
                stock_quantity__gt=0,
                stock_quantity__lte=F('low_stock_threshold')
            )
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Sorting
        sort_by = self.request.query_params.get('sort_by', '-created_at')
        valid_sorts = ['name', '-name', 'price', '-price', 'stock_quantity', '-stock_quantity',
                       'created_at', '-created_at', 'total_sold', '-total_sold']
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by)
        
        return queryset


class ProductDetailView(FarmScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a product.
    
    SECURITY: Farmers can only access products belonging to their farm.
    The FarmScopedMixin ensures the queryset is filtered by farm.
    """
    queryset = Product.objects.all()
    serializer_class = ProductDetailSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'pk'


class ProductStockUpdateView(FarmScopedMixin, APIView):
    """
    Update product stock quantity.
    
    SECURITY: Only the product's farm owner can update stock.
    """
    
    def patch(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, farm=self.get_farm())
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_quantity = request.data.get('stock_quantity')
        if new_quantity is None:
            return Response(
                {'error': 'stock_quantity is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product.stock_quantity = int(new_quantity)
            if product.stock_quantity > 0 and product.status == 'out_of_stock':
                product.status = 'active'
            elif product.stock_quantity == 0 and product.track_inventory:
                product.status = 'out_of_stock'
            product.save(update_fields=['stock_quantity', 'status', 'updated_at'])
            
            return Response({
                'message': 'Stock updated successfully',
                'stock_quantity': product.stock_quantity,
                'status': product.status
            })
        except ValueError:
            return Response(
                {'error': 'stock_quantity must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProductImageUploadView(FarmScopedMixin, generics.CreateAPIView):
    """
    Upload additional images for a product.
    
    SECURITY: Only the product's farm owner can upload images.
    """
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ProductImageSerializer
    
    def get_queryset(self):
        return ProductImage.objects.filter(product__farm=self.get_farm())
    
    def perform_create(self, serializer):
        product_pk = self.kwargs.get('product_pk')
        product = Product.objects.get(pk=product_pk, farm=self.get_farm())
        serializer.save(product=product)


class ProductBatchTraceabilityView(FarmScopedMixin, APIView):
    """
    Get processing batch and source flock information for a product.
    
    This endpoint bridges the gap between marketplace products and their
    source processing batches, enabling full traceability:
    
    Product -> ProcessingOutput -> ProcessingBatch -> Flock
    
    SECURITY: Only the product's farm owner can view traceability info.
    """
    
    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, farm=self.get_farm())
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if this is a processed product
        if not product.has_processing_source:
            return Response({
                'product_id': str(product.id),
                'product_name': product.name,
                'has_processing_source': False,
                'message': 'This product is not linked to any processing batches',
                'batches': [],
                'source_flocks': []
            })
        
        # Get batch summary
        batch_summary = product.get_batch_summary()
        
        # Get source flocks
        source_flocks = []
        for flock in product.source_flocks:
            source_flocks.append({
                'id': str(flock.id),
                'name': flock.name,
                'breed': flock.breed if hasattr(flock, 'breed') else None,
                'flock_type': flock.flock_type if hasattr(flock, 'flock_type') else None,
                'date_acquired': flock.date_acquired.isoformat() if hasattr(flock, 'date_acquired') and flock.date_acquired else None,
            })
        
        # Get inventory info if linked
        inventory_info = None
        if hasattr(product, 'inventory_record') and product.inventory_record:
            inv = product.inventory_record
            inventory_info = {
                'id': str(inv.id),
                'product_name': inv.product_name,
                'category': inv.category,
                'quantity_available': str(inv.quantity_available),
                'unit': inv.unit,
                'oldest_stock_date': inv.oldest_stock_date.isoformat() if inv.oldest_stock_date else None,
                'average_age_days': inv.average_age_days,
            }
        
        return Response({
            'product_id': str(product.id),
            'product_name': product.name,
            'has_processing_source': True,
            'inventory': inventory_info,
            'batches': batch_summary,
            'source_flocks': source_flocks,
            'total_batches': len(batch_summary),
            'total_source_flocks': len(source_flocks),
        })


# =============================================================================
# CUSTOMER VIEWS
# =============================================================================

class CustomerListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    List farmer's customers or create a new customer.
    
    SECURITY: Farmers can only see and create customers for their own farm.
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by customer type
        customer_type = self.request.query_params.get('customer_type')
        if customer_type:
            queryset = queryset.filter(customer_type=customer_type)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(business_name__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset.order_by('-created_at')


class CustomerDetailView(FarmScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a customer.
    
    SECURITY: Farmers can only access customers belonging to their farm.
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    lookup_field = 'pk'


# =============================================================================
# ORDER VIEWS
# =============================================================================

class OrderListCreateView(FarmScopedMixin, generics.ListCreateAPIView):
    """
    List farmer's orders or create a new order.
    
    SECURITY: Farmers can only see and create orders for their own farm.
    All product and customer validation ensures farm ownership.
    """
    queryset = MarketplaceOrder.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return MarketplaceOrderListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filter by payment status
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Filter by customer
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Search by order number
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(customer__phone_number__icontains=search)
            )
        
        return queryset.select_related('customer').order_by('-created_at')


class OrderDetailView(FarmScopedMixin, generics.RetrieveUpdateAPIView):
    """
    Retrieve or update an order.
    
    SECURITY: Farmers can only access orders belonging to their farm.
    """
    queryset = MarketplaceOrder.objects.all()
    serializer_class = MarketplaceOrderDetailSerializer
    lookup_field = 'pk'
    
    def get_queryset(self):
        return super().get_queryset().select_related('customer').prefetch_related('items')


class OrderStatusUpdateView(FarmScopedMixin, APIView):
    """
    Update order status.
    
    SECURITY: Only the order's farm owner can update status.
    """
    
    def patch(self, request, pk):
        from django.db import transaction
        from sales_revenue.marketplace_models import Product
        
        try:
            order = MarketplaceOrder.objects.get(pk=pk, farm=self.get_farm())
        except MarketplaceOrder.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {'error': 'status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_statuses = [choice[0] for choice in MarketplaceOrder.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Handle status-specific logic with atomic operations
        old_status = order.status
        
        with transaction.atomic():
            order.status = new_status
            
            if new_status == 'confirmed' and not order.confirmed_at:
                order.confirmed_at = timezone.now()
            elif new_status == 'completed' and not order.completed_at:
                order.completed_at = timezone.now()
                # Update customer stats when order is completed
                customer = order.customer
                customer.total_orders = (customer.total_orders or 0) + 1
                customer.total_purchases = (customer.total_purchases or Decimal('0')) + order.total_amount
                customer.save(update_fields=['total_orders', 'total_purchases'])
                # Update product stats when order is completed
                for item in order.items.all():
                    product = item.product
                    product.total_sold = (product.total_sold or 0) + item.quantity
                    product.total_revenue = (product.total_revenue or Decimal('0')) + item.line_total
                    product.save(update_fields=['total_sold', 'total_revenue'])
            elif new_status == 'cancelled':
                order.cancelled_at = timezone.now()
                order.cancellation_reason = request.data.get('reason', '')
                # Restore stock for cancelled orders with audit trail
                for item in order.items.all():
                    # Lock product for atomic operation
                    locked_product = Product.objects.select_for_update().get(pk=item.product_id)
                    locked_product.restore_stock(
                        quantity=item.quantity,
                        reference_record=item,
                        notes=f"Order {order.order_number} cancelled - restoring stock",
                        recorded_by=request.user
                    )
            
            order.save()
        
        return Response({
            'message': f'Order status updated from {old_status} to {new_status}',
            'order_number': order.order_number,
            'status': order.status
        })


class OrderCancelView(FarmScopedMixin, APIView):
    """
    Cancel an order and restore stock.
    
    SECURITY: Only the order's farm owner can cancel.
    """
    
    def post(self, request, pk):
        from django.db import transaction
        from sales_revenue.marketplace_models import Product
        
        try:
            order = MarketplaceOrder.objects.get(pk=pk, farm=self.get_farm())
        except MarketplaceOrder.DoesNotExist:
            return Response(
                {'error': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if order.status in ['completed', 'cancelled', 'refunded']:
            return Response(
                {'error': f'Cannot cancel order with status: {order.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Cancel order
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.cancellation_reason = request.data.get('reason', 'Cancelled by farmer')
            order.save()
            
            # Restore stock with audit trail
            for item in order.items.all():
                # Lock product for atomic operation
                locked_product = Product.objects.select_for_update().get(pk=item.product_id)
                locked_product.restore_stock(
                    quantity=item.quantity,
                    reference_record=item,
                    notes=f"Order {order.order_number} cancelled by farmer",
                    recorded_by=request.user
                )
        
        return Response({
            'message': 'Order cancelled successfully',
            'order_number': order.order_number
        })


# =============================================================================
# STATISTICS & DASHBOARD VIEWS
# =============================================================================

class MarketplaceDashboardView(FarmScopedMixin, APIView):
    """
    Get marketplace dashboard overview.
    
    SECURITY: Only returns statistics for the farmer's own farm.
    
    NOTE: Includes visibility status. All farmers can access marketplace,
    but only those with active subscriptions appear in public searches.
    """
    
    def get(self, request):
        farm = self.get_farm()
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # =================================================================
        # VISIBILITY STATUS - Let farmers know if their products are visible
        # =================================================================
        has_subscription = hasattr(farm, 'subscription') and farm.subscription is not None
        subscription_status = farm.subscription.status if has_subscription else None
        is_visible_in_search = (
            farm.marketplace_enabled and
            has_subscription and
            subscription_status in ['trial', 'active']
        )
        
        # Build visibility info
        visibility_info = {
            'is_visible_in_public_search': is_visible_in_search,
            'marketplace_enabled': farm.marketplace_enabled,
            'subscription_status': subscription_status,
            'visibility_message': self._get_visibility_message(is_visible_in_search, subscription_status),
        }
        
        # Get subscription details if exists
        if has_subscription:
            sub = farm.subscription
            visibility_info['subscription'] = {
                'status': sub.status,
                'current_period_end': sub.current_period_end.isoformat() if sub.current_period_end else None,
                'next_billing_date': sub.next_billing_date.isoformat() if sub.next_billing_date else None,
                'trial_end': sub.trial_end.isoformat() if sub.trial_end else None,
            }
        
        # Product statistics
        products = Product.objects.filter(farm=farm)
        total_products = products.count()
        active_products = products.filter(status='active').count()
        out_of_stock = products.filter(status='out_of_stock').count()
        low_stock = products.filter(
            track_inventory=True,
            stock_quantity__gt=0,
            stock_quantity__lte=F('low_stock_threshold')
        ).count()
        
        # Order statistics
        orders = MarketplaceOrder.objects.filter(farm=farm)
        total_orders = orders.count()
        pending_orders = orders.filter(
            status__in=['pending', 'confirmed', 'processing', 'ready']
        ).count()
        completed_orders = orders.filter(status='completed').count()
        
        # Customer statistics
        customers = Customer.objects.filter(farm=farm)
        total_customers = customers.count()
        active_customers = customers.filter(is_active=True).count()
        
        # Revenue statistics
        completed_revenue = orders.filter(
            status='completed'
        ).aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0'))
        )['total']
        
        month_revenue = orders.filter(
            status='completed',
            completed_at__date__gte=month_start
        ).aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0'))
        )['total']
        
        # Top selling products
        top_products = products.filter(
            total_sold__gt=0
        ).order_by('-total_sold')[:5]
        
        # Recent orders
        recent_orders = orders.select_related('customer').order_by('-created_at')[:5]
        
        data = {
            # Visibility status (most important - show at top)
            'visibility': visibility_info,
            # Product stats
            'total_products': total_products,
            'active_products': active_products,
            'out_of_stock_products': out_of_stock,
            'low_stock_products': low_stock,
            # Order stats
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            # Customer stats
            'total_customers': total_customers,
            'active_customers': active_customers,
            # Revenue stats
            'total_revenue': completed_revenue,
            'revenue_this_month': month_revenue,
            # Lists
            'top_selling_products': ProductListSerializer(top_products, many=True).data,
            'recent_orders': MarketplaceOrderListSerializer(recent_orders, many=True).data
        }
        
        return Response(data)
    
    def _get_visibility_message(self, is_visible, subscription_status):
        """
        Get user-friendly visibility message based on subscription status.
        
        This helps farmers understand why their products may or may not appear
        in public searches, and what action they can take.
        """
        if is_visible:
            if subscription_status == 'trial':
                return "Your products are visible in public searches (trial period)"
            return "Your products are visible in public searches"
        
        # Not visible - explain why
        if not subscription_status:
            return (
                "Your products are NOT visible in public searches. "
                "Activate marketplace subscription to appear in buyer searches and increase sales."
            )
        
        if subscription_status == 'past_due':
            return (
                "Your products are NOT visible in public searches. "
                "Your payment is overdue. Please renew to restore visibility."
            )
        
        if subscription_status == 'suspended':
            return (
                "Your products are NOT visible in public searches. "
                "Your subscription is suspended. Please contact support or renew."
            )
        
        if subscription_status == 'cancelled':
            return (
                "Your products are NOT visible in public searches. "
                "Your subscription was cancelled. Reactivate to appear in buyer searches."
            )
        
        return (
            "Your products are NOT visible in public searches. "
            "Activate marketplace subscription to appear in buyer searches."
        )


class MarketplaceStatisticsView(FarmScopedMixin, generics.ListAPIView):
    """
    Get daily marketplace statistics.
    
    SECURITY: Only returns statistics for the farmer's own farm.
    """
    queryset = MarketplaceStatistics.objects.all()
    serializer_class = MarketplaceStatisticsSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date')


class MarketplaceAnalyticsView(FarmScopedMixin, APIView):
    """
    Get marketplace analytics for charts and reports.
    
    SECURITY: Only returns analytics for the farmer's own farm.
    """
    
    def get(self, request):
        farm = self.get_farm()
        period = request.query_params.get('period', 'MONTH')
        
        # Determine date range
        today = timezone.now().date()
        if period == 'WEEK':
            start_date = today - timedelta(days=7)
        elif period == 'MONTH':
            start_date = today - timedelta(days=30)
        elif period == 'QUARTER':
            start_date = today - timedelta(days=90)
        elif period == 'YEAR':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)
        
        # Get orders in date range
        orders = MarketplaceOrder.objects.filter(
            farm=farm,
            created_at__date__gte=start_date
        )
        
        # Sales by status
        sales_by_status = orders.values('status').annotate(
            count=Count('id'),
            total=Coalesce(Sum('total_amount'), Decimal('0'))
        )
        
        # Top products by revenue - calculate dynamically from completed order items
        top_products = Product.objects.filter(farm=farm).annotate(
            calculated_total_sold=Coalesce(
                Sum(
                    'order_items__quantity',
                    filter=Q(order_items__order__status='completed')
                ),
                0
            ),
            calculated_total_revenue=Coalesce(
                Sum(
                    'order_items__line_total',
                    filter=Q(order_items__order__status='completed')
                ),
                Decimal('0')
            )
        ).order_by('-calculated_total_revenue')[:10]
        
        # Top customers - calculate totals from all sales sources dynamically
        # Includes: MarketplaceOrders (completed), EggSales, and BirdSales
        top_customers = Customer.objects.filter(farm=farm).annotate(
            # Count orders from all sources
            marketplace_order_count=Count(
                'marketplace_orders',
                filter=Q(marketplace_orders__status='completed')
            ),
            egg_sale_count=Count('egg_purchases'),
            bird_sale_count=Count('bird_purchases'),
            calculated_total_orders=F('marketplace_order_count') + F('egg_sale_count') + F('bird_sale_count'),
            # Sum purchases from all sources
            marketplace_total=Coalesce(
                Sum(
                    'marketplace_orders__total_amount',
                    filter=Q(marketplace_orders__status='completed')
                ),
                Decimal('0')
            ),
            egg_sales_total=Coalesce(Sum('egg_purchases__subtotal'), Decimal('0')),
            bird_sales_total=Coalesce(Sum('bird_purchases__subtotal'), Decimal('0')),
            calculated_total_purchases=F('marketplace_total') + F('egg_sales_total') + F('bird_sales_total')
        ).order_by('-calculated_total_purchases')[:10]
        
        # Daily order counts (for chart)
        from django.db.models.functions import TruncDate
        daily_orders = orders.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id'),
            revenue=Coalesce(Sum('total_amount'), Decimal('0'))
        ).order_by('date')
        
        return Response({
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': today.isoformat(),
            'summary': {
                'total_orders': orders.count(),
                'total_revenue': orders.filter(status='completed').aggregate(
                    total=Coalesce(Sum('total_amount'), Decimal('0'))
                )['total'],
                'average_order_value': orders.filter(status='completed').aggregate(
                    avg=Coalesce(Sum('total_amount') / Count('id'), Decimal('0'))
                )['avg'] if orders.filter(status='completed').exists() else Decimal('0')
            },
            'sales_by_status': list(sales_by_status),
            'top_products': [
                {
                    'id': str(p.id),
                    'name': p.name,
                    'total_sold': p.calculated_total_sold,
                    'total_revenue': float(p.calculated_total_revenue)
                }
                for p in top_products
            ],
            'top_customers': [
                {
                    'id': str(c.id),
                    'name': c.get_full_name(),
                    'total_orders': c.calculated_total_orders,
                    'total_purchases': float(c.calculated_total_purchases)
                }
                for c in top_customers
            ],
            'daily_orders': [
                {
                    'date': item['date'].isoformat(),
                    'count': item['count'],
                    'revenue': float(item['revenue'])
                }
                for item in daily_orders
            ]
        })
