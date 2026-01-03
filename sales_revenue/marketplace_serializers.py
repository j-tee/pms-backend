"""
Marketplace Serializers

Serializers for marketplace products, orders, and customers.
Implements farm-scoped data access to prevent data security breaches.
"""

from rest_framework import serializers
from django.utils import timezone
from .marketplace_models import (
    ProductCategory,
    Product,
    ProductImage,
    MarketplaceOrder,
    OrderItem,
    MarketplaceStatistics
)
from .models import Customer


class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories (read-only for farmers)."""
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'is_active', 'display_order'
        ]
        read_only_fields = fields


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images."""
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'display_order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product list views.
    Used when displaying multiple products.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'category_name', 'sku',
            'unit', 'price', 'compare_at_price',
            'stock_quantity', 'status', 'is_featured',
            'is_in_stock', 'is_low_stock',
            'primary_image', 'total_sold', 'average_rating',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_sold', 'average_rating', 'review_count',
            'created_at', 'updated_at'
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for product detail/create/update.
    
    SECURITY: The 'farm' field is read-only and auto-populated from the request user.
    Farmers cannot set or change the farm ownership of a product.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'farm', 'farm_name',
            'category', 'category_name', 'name', 'description', 'sku',
            'unit', 'price', 'compare_at_price',
            'stock_quantity', 'low_stock_threshold', 'track_inventory', 'allow_backorder',
            'status', 'is_featured',
            'min_order_quantity', 'max_order_quantity',
            'primary_image', 'images',
            'tags', 'specifications',
            'total_sold', 'total_revenue', 'average_rating', 'review_count',
            'is_in_stock', 'is_low_stock',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'id', 'farm', 'farm_name',
            'total_sold', 'total_revenue', 'average_rating', 'review_count',
            'created_at', 'updated_at'
        ]
    
    def validate_sku(self, value):
        """Ensure SKU is unique within the farm."""
        if not value:
            return value
        
        farm = self.context['request'].user.farm
        queryset = Product.objects.filter(farm=farm, sku=value)
        
        # Exclude current instance for updates
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError(
                f"A product with SKU '{value}' already exists in your farm."
            )
        return value
    
    def validate(self, data):
        """Additional validation."""
        # Validate max order quantity
        min_qty = data.get('min_order_quantity', 1)
        max_qty = data.get('max_order_quantity')
        
        if max_qty is not None and max_qty < min_qty:
            raise serializers.ValidationError({
                'max_order_quantity': 'Maximum order quantity must be greater than or equal to minimum.'
            })
        
        return data
    
    def create(self, validated_data):
        """Create product with farm from request user."""
        # SECURITY: Auto-populate farm from authenticated user
        validated_data['farm'] = self.context['request'].user.farm
        
        # Set published_at if status is active
        if validated_data.get('status') == 'active' and not validated_data.get('published_at'):
            validated_data['published_at'] = timezone.now()
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update product, setting published_at if newly activated."""
        # Set published_at if transitioning to active
        if (validated_data.get('status') == 'active' and 
            instance.status != 'active' and 
            not instance.published_at):
            validated_data['published_at'] = timezone.now()
        
        return super().update(instance, validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for customers.
    
    SECURITY: Farm is auto-populated and read-only.
    """
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'farm',
            'customer_type', 'first_name', 'last_name', 'full_name',
            'business_name', 'phone_number', 'email',
            'mobile_money_number', 'mobile_money_provider', 'mobile_money_account_name',
            'location', 'delivery_address',
            'total_purchases', 'total_orders', 'is_active', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'farm', 'full_name',
            'total_purchases', 'total_orders',
            'created_at', 'updated_at'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def create(self, validated_data):
        # SECURITY: Auto-populate farm from authenticated user
        validated_data['farm'] = self.context['request'].user.farm
        return super().create(validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order line items."""
    product_id = serializers.UUIDField(write_only=True, source='product.id')
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_id', 'product', 'product_name', 'product_sku',
            'unit', 'unit_price', 'quantity', 'line_total',
            'fulfilled_quantity', 'created_at'
        ]
        read_only_fields = [
            'id', 'product', 'product_name', 'product_sku',
            'unit', 'unit_price', 'line_total',
            'fulfilled_quantity', 'created_at'
        ]


class MarketplaceOrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order list views."""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MarketplaceOrder
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'customer_phone',
            'status', 'payment_status',
            'total_amount', 'delivery_method',
            'item_count', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_item_count(self, obj):
        return obj.items.count()


class MarketplaceOrderDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for order detail/create/update.
    
    SECURITY: Farm is auto-populated from request user.
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    
    class Meta:
        model = MarketplaceOrder
        fields = [
            'id', 'order_number', 'farm', 'farm_name',
            'customer', 'customer_name', 'customer_phone', 'customer_email',
            'status', 'payment_status',
            'subtotal', 'discount_amount', 'delivery_fee', 'total_amount',
            'delivery_method', 'delivery_address', 'delivery_notes',
            'estimated_delivery_date', 'actual_delivery_date',
            'customer_notes', 'internal_notes',
            'items',
            'created_at', 'updated_at', 'confirmed_at',
            'completed_at', 'cancelled_at', 'cancellation_reason'
        ]
        read_only_fields = [
            'id', 'order_number', 'farm', 'farm_name',
            'customer_name', 'customer_phone', 'customer_email',
            'subtotal', 'total_amount', 'items',
            'created_at', 'updated_at', 'confirmed_at',
            'completed_at', 'cancelled_at'
        ]
    
    def validate_customer(self, value):
        """Ensure customer belongs to the farmer's farm."""
        farm = self.context['request'].user.farm
        if value.farm != farm:
            raise serializers.ValidationError(
                "Customer not found. You can only create orders for your own customers."
            )
        return value
    
    def create(self, validated_data):
        # SECURITY: Auto-populate farm from authenticated user
        validated_data['farm'] = self.context['request'].user.farm
        return super().create(validated_data)


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating orders with items.
    
    SECURITY: Validates that customer and products belong to the farmer's farm.
    """
    customer = serializers.UUIDField()
    delivery_method = serializers.ChoiceField(
        choices=MarketplaceOrder.DELIVERY_METHOD_CHOICES,
        default='pickup'
    )
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    delivery_notes = serializers.CharField(required=False, allow_blank=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    estimated_delivery_date = serializers.DateField(required=False, allow_null=True)
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_customer(self, value):
        """Ensure customer belongs to the farmer's farm."""
        farm = self.context['request'].user.farm
        try:
            customer = Customer.objects.get(id=value, farm=farm)
            return customer
        except Customer.DoesNotExist:
            raise serializers.ValidationError(
                "Customer not found. You can only create orders for your own customers."
            )
    
    def validate_items(self, value):
        """Validate order items and check product ownership."""
        farm = self.context['request'].user.farm
        validated_items = []
        
        for item in value:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            
            if not product_id:
                raise serializers.ValidationError("Each item must have a product_id.")
            
            try:
                # SECURITY: Only allow products from the farmer's own farm
                product = Product.objects.get(id=product_id, farm=farm)
            except Product.DoesNotExist:
                raise serializers.ValidationError(
                    f"Product {product_id} not found in your farm's inventory."
                )
            
            # Check stock
            if product.track_inventory and not product.allow_backorder:
                if product.stock_quantity < quantity:
                    raise serializers.ValidationError(
                        f"Insufficient stock for {product.name}. "
                        f"Available: {product.stock_quantity}, Requested: {quantity}"
                    )
            
            # Check min/max order quantity
            if quantity < product.min_order_quantity:
                raise serializers.ValidationError(
                    f"Minimum order quantity for {product.name} is {product.min_order_quantity}."
                )
            
            if product.max_order_quantity and quantity > product.max_order_quantity:
                raise serializers.ValidationError(
                    f"Maximum order quantity for {product.name} is {product.max_order_quantity}."
                )
            
            validated_items.append({
                'product': product,
                'quantity': quantity
            })
        
        return validated_items
    
    def create(self, validated_data):
        """Create order with items."""
        from django.db import transaction
        
        farm = self.context['request'].user.farm
        items_data = validated_data.pop('items')
        
        with transaction.atomic():
            # Create order
            order = MarketplaceOrder.objects.create(
                farm=farm,
                **validated_data
            )
            
            # Create order items and reduce stock
            for item_data in items_data:
                product = item_data['product']
                quantity = item_data['quantity']
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku or '',
                    unit=product.unit,
                    unit_price=product.price,
                    quantity=quantity,
                    line_total=product.price * quantity
                )
                
                # Reduce stock
                product.reduce_stock(quantity)
            
            # Calculate totals
            order.calculate_totals()
        
        return order


class MarketplaceStatisticsSerializer(serializers.ModelSerializer):
    """Serializer for marketplace statistics."""
    
    class Meta:
        model = MarketplaceStatistics
        fields = [
            'id', 'date',
            'total_orders', 'completed_orders', 'cancelled_orders',
            'total_revenue', 'total_items_sold',
            'new_customers', 'returning_customers',
            'products_listed', 'products_out_of_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class MarketplaceDashboardSerializer(serializers.Serializer):
    """Serializer for marketplace dashboard overview."""
    total_products = serializers.IntegerField()
    active_products = serializers.IntegerField()
    out_of_stock_products = serializers.IntegerField()
    low_stock_products = serializers.IntegerField()
    
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    
    total_customers = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    top_selling_products = ProductListSerializer(many=True)
    recent_orders = MarketplaceOrderListSerializer(many=True)


# =============================================================================
# PUBLIC MARKETPLACE SERIALIZERS
# =============================================================================
# These serializers are for the public-facing marketplace browsing.
# They hide sensitive farm data and are accessible without authentication.
# =============================================================================


class PublicFarmSerializer(serializers.Serializer):
    """
    Public farm information for marketplace display.
    Only exposes non-sensitive farm details.
    """
    id = serializers.UUIDField()
    farm_name = serializers.CharField()
    location = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    constituency = serializers.CharField(source='primary_constituency', allow_blank=True)
    description = serializers.CharField(source='farm_description', allow_blank=True, allow_null=True)
    logo = serializers.ImageField(source='farm_logo', allow_null=True)
    cover_image = serializers.ImageField(source='farm_cover_image', allow_null=True)
    rating = serializers.DecimalField(
        max_digits=3, decimal_places=2,
        source='average_rating',
        default=0.00
    )
    total_products = serializers.SerializerMethodField()
    is_verified = serializers.BooleanField(default=False)
    
    def get_location(self, obj):
        """Get primary location community/district from FarmLocation."""
        primary_location = obj.locations.filter(is_primary_location=True).first()
        if primary_location:
            return f"{primary_location.community}, {primary_location.district}"
        # Fall back to first location if no primary set
        first_location = obj.locations.first()
        if first_location:
            return f"{first_location.community}, {first_location.district}"
        return obj.primary_constituency or ""
    
    def get_region(self, obj):
        """Get region from primary FarmLocation."""
        primary_location = obj.locations.filter(is_primary_location=True).first()
        if primary_location:
            return primary_location.region
        first_location = obj.locations.first()
        if first_location:
            return first_location.region
        return ""
    
    def get_total_products(self, obj):
        return Product.objects.filter(farm=obj, status='active').count()


class PublicProductListSerializer(serializers.ModelSerializer):
    """
    Public product listing for marketplace browsing.
    Hides sensitive pricing data like min_price.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    farm = PublicFarmSerializer(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    negotiable = serializers.BooleanField(source='price_negotiable', read_only=True)
    price_info = serializers.CharField(source='price_notes', read_only=True)
    
    # Delivery options available from the farm
    delivery_options = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'category_name',
            'unit', 'price', 'compare_at_price',
            'negotiable', 'price_info',
            'stock_quantity', 'is_in_stock',
            'primary_image', 'average_rating', 'review_count',
            'is_featured',
            'farm', 'delivery_options',
            'created_at'
        ]
    
    def get_delivery_options(self, obj):
        """Return available delivery options for this product's farm."""
        # These would normally come from farm settings
        return ['pickup', 'farmer_delivery', 'third_party']


class PublicProductDetailSerializer(serializers.ModelSerializer):
    """
    Public product detail view.
    Shows full product info without sensitive data.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    farm = PublicFarmSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    negotiable = serializers.BooleanField(source='price_negotiable', read_only=True)
    price_info = serializers.CharField(source='price_notes', read_only=True)
    
    # Related products from same farm
    related_products = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'unit', 'price', 'compare_at_price',
            'negotiable', 'price_info',
            'stock_quantity', 'is_in_stock',
            'min_order_quantity', 'max_order_quantity',
            'primary_image', 'images',
            'tags', 'specifications',
            'average_rating', 'review_count',
            'is_featured', 'total_sold',
            'farm',
            'related_products',
            'created_at', 'published_at'
        ]
    
    def get_related_products(self, obj):
        """Get related products from the same category or farm."""
        related = Product.objects.filter(
            status='active',
            category=obj.category
        ).exclude(id=obj.id).order_by('-total_sold')[:4]
        
        return PublicProductListSerializer(related, many=True, context=self.context).data


class PublicFarmProfileSerializer(serializers.Serializer):
    """
    Full public farm profile for storefront display.
    """
    id = serializers.UUIDField()
    farm_name = serializers.CharField()
    location = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    constituency = serializers.CharField(source='primary_constituency', allow_blank=True)
    description = serializers.CharField(source='farm_description', allow_blank=True, allow_null=True)
    logo = serializers.ImageField(source='farm_logo', allow_null=True)
    cover_image = serializers.ImageField(source='farm_cover_image', allow_null=True)
    rating = serializers.DecimalField(
        max_digits=3, decimal_places=2,
        source='average_rating',
        default=0.00
    )
    total_products = serializers.SerializerMethodField()
    total_reviews = serializers.IntegerField(source='review_count', default=0)
    member_since = serializers.DateTimeField(source='created_at')
    is_verified = serializers.BooleanField(default=False)
    
    # Contact (only if farm allows public contact)
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    
    # Delivery options this farm offers
    delivery_options = serializers.SerializerMethodField()
    
    # Products and categories
    featured_products = serializers.SerializerMethodField()
    product_categories = serializers.SerializerMethodField()
    
    def get_location(self, obj):
        """Get primary location community/district from FarmLocation."""
        primary_location = obj.locations.filter(is_primary_location=True).first()
        if primary_location:
            return f"{primary_location.community}, {primary_location.district}"
        first_location = obj.locations.first()
        if first_location:
            return f"{first_location.community}, {first_location.district}"
        return obj.primary_constituency or ""
    
    def get_region(self, obj):
        """Get region from primary FarmLocation."""
        primary_location = obj.locations.filter(is_primary_location=True).first()
        if primary_location:
            return primary_location.region
        first_location = obj.locations.first()
        if first_location:
            return first_location.region
        return ""
    
    def get_total_products(self, obj):
        return Product.objects.filter(farm=obj, status='active').count()
    
    def get_phone(self, obj):
        # Only show if farm has opted to display contact publicly
        return getattr(obj, 'public_phone', None)
    
    def get_email(self, obj):
        # Only show if farm has opted to display contact publicly
        return getattr(obj, 'public_email', None)
    
    def get_delivery_options(self, obj):
        """Return available delivery methods for this farm."""
        return [
            {'method': 'pickup', 'label': 'Farm Pickup', 'available': True},
            {'method': 'farmer_delivery', 'label': 'Farm Delivery', 'available': True},
            {'method': 'third_party', 'label': 'Third-Party Delivery', 'available': True},
        ]
    
    def get_featured_products(self, obj):
        """Get featured products from this farm."""
        featured = Product.objects.filter(
            farm=obj,
            status='active',
            is_featured=True
        ).order_by('-total_sold')[:6]
        
        return PublicProductListSerializer(featured, many=True, context=self.context).data
    
    def get_product_categories(self, obj):
        """Get categories with products in this farm."""
        from django.db.models import Count
        
        categories = ProductCategory.objects.filter(
            products__farm=obj,
            products__status='active'
        ).annotate(
            product_count=Count('products')
        ).values('id', 'name', 'slug', 'icon', 'product_count')
        
        return list(categories)


class PublicOrderInquirySerializer(serializers.Serializer):
    """
    Serializer for public order inquiries (price negotiation).
    Allows potential customers to contact farmers about products.
    """
    product_id = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1)
    proposed_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    message = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    delivery_preference = serializers.ChoiceField(
        choices=[
            ('pickup', 'Farm Pickup'),
            ('farmer_delivery', 'Farm Delivery'),
            ('third_party', 'Third-Party Delivery'),
        ],
        default='pickup'
    )
    delivery_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate_product_id(self, value):
        """Ensure product exists and is available."""
        try:
            product = Product.objects.get(id=value, status='active')
            return product
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or not available.")
    
    def validate(self, data):
        """Additional validation for inquiry."""
        product = data['product_id']
        
        # Check if price negotiation is allowed
        if data.get('proposed_price') and not product.price_negotiable:
            raise serializers.ValidationError({
                'proposed_price': 'Price negotiation is not available for this product.'
            })
        
        # Validate proposed price against min_price (if set)
        if data.get('proposed_price') and product.min_price:
            if data['proposed_price'] < product.min_price:
                raise serializers.ValidationError({
                    'proposed_price': 'Proposed price is below acceptable range.'
                })
        
        # Validate quantity
        if data['quantity'] < product.min_order_quantity:
            raise serializers.ValidationError({
                'quantity': f'Minimum order quantity is {product.min_order_quantity}.'
            })
        
        if product.max_order_quantity and data['quantity'] > product.max_order_quantity:
            raise serializers.ValidationError({
                'quantity': f'Maximum order quantity is {product.max_order_quantity}.'
            })
        
        return data


class PublicSearchSerializer(serializers.Serializer):
    """Serializer for public product search parameters."""
    q = serializers.CharField(required=False, allow_blank=True, help_text='Search query')
    category = serializers.UUIDField(required=False, help_text='Filter by category ID')
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False,
        help_text='Minimum price filter'
    )
    max_price = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        required=False,
        help_text='Maximum price filter'
    )
    region = serializers.CharField(required=False, help_text='Filter by farm region')
    negotiable = serializers.BooleanField(required=False, help_text='Only negotiable prices')
    in_stock = serializers.BooleanField(required=False, default=True, help_text='Only in-stock items')
    ordering = serializers.ChoiceField(
        choices=[
            ('price', 'Price: Low to High'),
            ('-price', 'Price: High to Low'),
            ('-total_sold', 'Best Selling'),
            ('-average_rating', 'Top Rated'),
            ('-created_at', 'Newest'),
        ],
        required=False,
        default='-created_at'
    )
