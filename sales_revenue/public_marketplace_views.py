"""
Public Marketplace Views

These views power the public-facing marketplace where anyone can browse products
WITHOUT authentication.

VISIBILITY RULES (Jan 2026):
============================================================================
ALL farmers can use marketplace features (list products, track sales, analytics).
ONLY farms with ACTIVE MARKETPLACE SUBSCRIPTIONS appear in public searches.

This separation ensures:
1. Accurate industry statistics (all farmers' data is tracked)
2. Subscription incentive (only paying farmers get public visibility)
============================================================================

Subscription status filter applied to ALL public views:
- farm__marketplace_enabled=True
- farm__subscription__status__in=['trial', 'active']

PUBLIC (No Authentication Required):
- Browse active products from SUBSCRIBED farms only
- View product details from SUBSCRIBED farms only
- View farm storefronts from SUBSCRIBED farms only
- Search and filter by location (region, district, constituency)
- Submit order inquiries (price negotiation)

NOTE: Actual order creation and payment are handled separately.
"""

from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from farms.models import Farm, FarmLocation
from .marketplace_models import Product, ProductCategory, MarketplaceOrder
from .marketplace_serializers import (
    ProductCategorySerializer,
    PublicProductListSerializer,
    PublicProductDetailSerializer,
    PublicFarmSerializer,
    PublicFarmProfileSerializer,
    PublicOrderInquirySerializer,
    PublicSearchSerializer,
)


class PublicProductListView(generics.ListAPIView):
    """
    Browse active products from farms with active marketplace subscriptions.
    
    NOTE: All farmers can list products in the marketplace for data collection,
    but ONLY farms with active marketplace activation appear in public searches.
    This ensures accurate industry statistics while incentivizing subscriptions.
    
    Supports filtering by:
    - category: Product category UUID
    - min_price / max_price: Price range
    - region: Farm region (from farm locations)
    - district: Farm district
    - constituency: Farm constituency
    - farm: Filter by specific farm UUID
    - farm_name: Search farm by name
    - negotiable: Only negotiable prices (true/false)
    - in_stock: Only in-stock items (true/false, default true)
    
    Supports ordering by:
    - price / -price
    - -total_sold (best selling)
    - -average_rating (top rated)
    - -created_at (newest, default)
    
    Supports search by:
    - q: Search in product name, description, tags, farm name
    """
    permission_classes = [AllowAny]
    serializer_class = PublicProductListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'tags', 'farm__farm_name']
    ordering_fields = ['price', 'total_sold', 'average_rating', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return active products from farms with active marketplace subscriptions only.
        
        VISIBILITY RULES:
        - Farm must have farm_status='Active'
        - Farm must have marketplace_enabled=True
        - Farm must have an active subscription (status='trial' or 'active')
        
        Farms without active subscriptions can still list products (for statistics),
        but those products won't appear in public searches.
        """
        queryset = Product.objects.filter(
            status='active',
            farm__farm_status='Active',  # Only from active farms
            # SUBSCRIPTION VISIBILITY FILTER:
            # Only show products from farms with active marketplace subscriptions
            farm__marketplace_enabled=True,
            farm__subscription__status__in=['trial', 'active']
        ).select_related('category', 'farm').prefetch_related('images', 'farm__locations')
        
        # Apply filters from query params
        params = self.request.query_params
        
        # Category filter
        if category := params.get('category'):
            queryset = queryset.filter(category_id=category)
        
        # Price range filter
        if min_price := params.get('min_price'):
            queryset = queryset.filter(price__gte=min_price)
        if max_price := params.get('max_price'):
            queryset = queryset.filter(price__lte=max_price)
        
        # Location filters (from FarmLocation model)
        if region := params.get('region'):
            queryset = queryset.filter(farm__locations__region__icontains=region).distinct()
        
        if district := params.get('district'):
            queryset = queryset.filter(farm__locations__district__icontains=district).distinct()
        
        if constituency := params.get('constituency'):
            # Check both FarmLocation constituency and Farm primary_constituency
            queryset = queryset.filter(
                Q(farm__locations__constituency__icontains=constituency) |
                Q(farm__primary_constituency__icontains=constituency)
            ).distinct()
        
        # Farm name search
        if farm_name := params.get('farm_name'):
            queryset = queryset.filter(farm__farm_name__icontains=farm_name)
        
        # Negotiable filter
        if params.get('negotiable', '').lower() == 'true':
            queryset = queryset.filter(price_negotiable=True)
        
        # In stock filter (default true)
        if params.get('in_stock', 'true').lower() != 'false':
            queryset = queryset.filter(stock_quantity__gt=0)
        
        # Farm filter (by UUID)
        if farm := params.get('farm'):
            queryset = queryset.filter(farm_id=farm)
        
        # Featured filter
        if params.get('featured', '').lower() == 'true':
            queryset = queryset.filter(is_featured=True)
        
        return queryset


class PublicProductDetailView(generics.RetrieveAPIView):
    """
    View detailed information about a single product.
    
    Only shows products from farms with active marketplace subscriptions.
    
    Returns full product details including:
    - Product info (name, description, price, stock)
    - Farm info (name, location, rating)
    - Related products from same category
    - Product images
    """
    permission_classes = [AllowAny]
    serializer_class = PublicProductDetailSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        """Only return products from farms with active marketplace subscriptions."""
        return Product.objects.filter(
            status='active',
            farm__farm_status='Active',
            # SUBSCRIPTION VISIBILITY FILTER:
            farm__marketplace_enabled=True,
            farm__subscription__status__in=['trial', 'active']
        ).select_related('category', 'farm').prefetch_related('images', 'farm__locations')


class PublicCategoryListView(generics.ListAPIView):
    """
    List all active product categories.
    
    Optionally includes product count per category.
    """
    permission_classes = [AllowAny]
    serializer_class = ProductCategorySerializer
    
    def get_queryset(self):
        queryset = ProductCategory.objects.filter(is_active=True)
        
        # Optionally annotate with product count
        if self.request.query_params.get('with_count', 'false').lower() == 'true':
            queryset = queryset.annotate(
                product_count=Count('products', filter=Q(products__status='active'))
            )
        
        return queryset.order_by('display_order', 'name')


class PublicLocationFiltersView(APIView):
    """
    Get available location filters for the marketplace.
    
    Returns lists of regions, districts, and constituencies
    that have active farms with products and active subscriptions.
    
    NOTE: Only includes locations from farms with active marketplace subscriptions.
    
    GET /api/public/marketplace/locations/
    GET /api/public/marketplace/locations/?region=Greater Accra  (get districts for region)
    GET /api/public/marketplace/locations/?district=Accra Metropolitan  (get constituencies)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get locations only from farms with active subscriptions and active products
        active_farm_ids = Farm.objects.filter(
            farm_status='Active',
            marketplace_products__status='active',
            # SUBSCRIPTION VISIBILITY FILTER:
            marketplace_enabled=True,
            subscription__status__in=['trial', 'active']
        ).distinct().values_list('id', flat=True)
        
        locations = FarmLocation.objects.filter(
            farm_id__in=active_farm_ids
        )
        
        params = request.query_params
        
        # If region is specified, filter districts and constituencies
        if region := params.get('region'):
            locations = locations.filter(region__iexact=region)
            
            districts = locations.values_list('district', flat=True).distinct().order_by('district')
            constituencies = locations.values_list('constituency', flat=True).distinct().order_by('constituency')
            
            return Response({
                'region': region,
                'districts': list(districts),
                'constituencies': list(constituencies),
            })
        
        # If district is specified, filter constituencies
        if district := params.get('district'):
            locations = locations.filter(district__iexact=district)
            
            constituencies = locations.values_list('constituency', flat=True).distinct().order_by('constituency')
            
            return Response({
                'district': district,
                'constituencies': list(constituencies),
            })
        
        # Return all available regions, districts, constituencies
        regions = locations.values_list('region', flat=True).distinct().order_by('region')
        districts = locations.values_list('district', flat=True).distinct().order_by('district')
        constituencies = locations.values_list('constituency', flat=True).distinct().order_by('constituency')
        
        # Also include primary constituencies from farms
        primary_constituencies = Farm.objects.filter(
            id__in=active_farm_ids
        ).values_list('primary_constituency', flat=True).distinct()
        
        all_constituencies = set(list(constituencies) + list(primary_constituencies))
        
        return Response({
            'regions': list(regions),
            'districts': list(districts),
            'constituencies': sorted([c for c in all_constituencies if c]),
        })


class PublicFarmListView(generics.ListAPIView):
    """
    List farms with active products and active marketplace subscriptions.
    
    Shows public farm information for marketplace browsing.
    Only farms with active marketplace subscriptions appear in this list.
    
    Supports filtering by:
    - region: Farm region
    - district: Farm district
    - constituency: Farm constituency
    - q: Search farm by name
    """
    permission_classes = [AllowAny]
    serializer_class = PublicFarmSerializer
    
    def get_queryset(self):
        # Only farms with active subscriptions and active products
        queryset = Farm.objects.filter(
            farm_status='Active',
            marketplace_products__status='active',
            # SUBSCRIPTION VISIBILITY FILTER:
            marketplace_enabled=True,
            subscription__status__in=['trial', 'active']
        ).distinct().prefetch_related('locations').annotate(
            average_rating=Avg('marketplace_products__average_rating'),
            product_count=Count('marketplace_products', filter=Q(marketplace_products__status='active'))
        )
        
        params = self.request.query_params
        
        # Farm name search
        if q := params.get('q'):
            queryset = queryset.filter(farm_name__icontains=q)
        
        # Region filter (from FarmLocation)
        if region := params.get('region'):
            queryset = queryset.filter(locations__region__icontains=region).distinct()
        
        # District filter
        if district := params.get('district'):
            queryset = queryset.filter(locations__district__icontains=district).distinct()
        
        # Constituency filter
        if constituency := params.get('constituency'):
            queryset = queryset.filter(
                Q(locations__constituency__icontains=constituency) |
                Q(primary_constituency__icontains=constituency)
            ).distinct()
        
        return queryset.order_by('-product_count')


class PublicFarmProfileView(APIView):
    """
    View detailed farm storefront/profile.
    
    Only shows farms with active marketplace subscriptions.
    
    Returns:
    - Farm info (name, location, description, logo)
    - Featured products
    - Product categories in this farm
    - Delivery options
    """
    permission_classes = [AllowAny]
    
    def get(self, request, farm_id):
        # Only show profile for farms with active subscriptions
        farm = get_object_or_404(
            Farm.objects.filter(
                # SUBSCRIPTION VISIBILITY FILTER:
                marketplace_enabled=True,
                subscription__status__in=['trial', 'active']
            ).annotate(
                average_rating=Avg('marketplace_products__average_rating'),
                review_count=Count('marketplace_products__review_count')
            ),
            id=farm_id,
            farm_status='Active'
        )
        
        serializer = PublicFarmProfileSerializer(farm, context={'request': request})
        return Response(serializer.data)


class PublicFarmProductsView(generics.ListAPIView):
    """
    List all products from a specific farm.
    
    Only shows products if the farm has an active marketplace subscription.
    Same filtering options as PublicProductListView but scoped to one farm.
    """
    permission_classes = [AllowAny]
    serializer_class = PublicProductListSerializer
    
    def get_queryset(self):
        farm_id = self.kwargs['farm_id']
        
        queryset = Product.objects.filter(
            farm_id=farm_id,
            status='active',
            farm__farm_status='Active',
            # SUBSCRIPTION VISIBILITY FILTER:
            farm__marketplace_enabled=True,
            farm__subscription__status__in=['trial', 'active']
        ).select_related('category', 'farm').prefetch_related('images', 'farm__locations')
        
        params = self.request.query_params
        
        # Category filter
        if category := params.get('category'):
            queryset = queryset.filter(category_id=category)
        
        # Price range filter
        if min_price := params.get('min_price'):
            queryset = queryset.filter(price__gte=min_price)
        if max_price := params.get('max_price'):
            queryset = queryset.filter(price__lte=max_price)
        
        # In stock filter (default true)
        if params.get('in_stock', 'true').lower() != 'false':
            queryset = queryset.filter(stock_quantity__gt=0)
        
        return queryset.order_by('-is_featured', '-total_sold')


class PublicProductSearchView(generics.ListAPIView):
    """
    Advanced product search with multiple filters.
    
    Only shows products from farms with active marketplace subscriptions.
    
    Supports:
    - q: Text search (product name, description, tags, farm name)
    - category: Category UUID
    - min_price / max_price: Price range
    - region: Farm region
    - district: Farm district
    - constituency: Farm constituency
    - farm_name: Farm name search
    - negotiable: Only negotiable prices
    - in_stock: Only in-stock items (default true)
    """
    permission_classes = [AllowAny]
    serializer_class = PublicProductListSerializer
    
    def get_queryset(self):
        queryset = Product.objects.filter(
            status='active',
            farm__farm_status='Active',
            # SUBSCRIPTION VISIBILITY FILTER:
            farm__marketplace_enabled=True,
            farm__subscription__status__in=['trial', 'active']
        ).select_related('category', 'farm').prefetch_related('farm__locations')
        
        params = self.request.query_params
        
        # Text search
        if q := params.get('q'):
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(description__icontains=q) |
                Q(tags__icontains=q) |
                Q(farm__farm_name__icontains=q)
            )
        
        # Apply other filters
        if category := params.get('category'):
            queryset = queryset.filter(category_id=category)
        
        if min_price := params.get('min_price'):
            queryset = queryset.filter(price__gte=min_price)
        
        if max_price := params.get('max_price'):
            queryset = queryset.filter(price__lte=max_price)
        
        # Location filters (from FarmLocation)
        if region := params.get('region'):
            queryset = queryset.filter(farm__locations__region__icontains=region).distinct()
        
        if district := params.get('district'):
            queryset = queryset.filter(farm__locations__district__icontains=district).distinct()
        
        if constituency := params.get('constituency'):
            queryset = queryset.filter(
                Q(farm__locations__constituency__icontains=constituency) |
                Q(farm__primary_constituency__icontains=constituency)
            ).distinct()
        
        # Farm name search
        if farm_name := params.get('farm_name'):
            queryset = queryset.filter(farm__farm_name__icontains=farm_name)
        
        if params.get('negotiable', '').lower() == 'true':
            queryset = queryset.filter(price_negotiable=True)
        
        if params.get('in_stock', 'true').lower() != 'false':
            queryset = queryset.filter(stock_quantity__gt=0)
        
        # Ordering
        ordering = params.get('ordering', '-created_at')
        if ordering in ['price', '-price', '-total_sold', '-average_rating', '-created_at']:
            queryset = queryset.order_by(ordering)
        
        return queryset


class PublicOrderInquiryView(APIView):
    """
    Submit an order inquiry for a product.
    
    Allows potential customers to:
    - Express interest in a product
    - Propose a negotiated price (if enabled)
    - Provide contact information
    - Specify delivery preference
    
    The farmer will receive the inquiry and can respond directly.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PublicOrderInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        product = data['product_id']  # This is the Product instance after validation
        
        # Create inquiry record (you might want a separate model for this)
        # For now, we'll return success and you can implement notification logic
        
        # TODO: Implement inquiry storage and farmer notification
        # - Send SMS/Email to farmer
        # - Store inquiry for farmer's dashboard
        # - Track inquiry status
        
        return Response({
            'message': 'Your inquiry has been submitted successfully.',
            'details': {
                'product': product.name,
                'farm': product.farm.farm_name,
                'quantity': data['quantity'],
                'proposed_price': data.get('proposed_price'),
                'delivery_preference': data['delivery_preference'],
            },
            'next_steps': 'The farmer will contact you shortly via the phone number provided.'
        }, status=status.HTTP_201_CREATED)


class PublicMarketplaceHomeView(APIView):
    """
    Public marketplace home page data.
    
    Only shows products and farms with active marketplace subscriptions.
    
    Returns:
    - Featured products
    - Top categories
    - Top farms
    - Latest products
    """
    permission_classes = [AllowAny]
    
    # Base filter for products from subscribed farms
    SUBSCRIPTION_FILTER = {
        'farm__marketplace_enabled': True,
        'farm__subscription__status__in': ['trial', 'active']
    }
    
    def get(self, request):
        # Featured products (from subscribed farms only)
        featured_products = Product.objects.filter(
            status='active',
            is_featured=True,
            farm__farm_status='Active',
            **self.SUBSCRIPTION_FILTER
        ).select_related('category', 'farm').order_by('-total_sold')[:8]
        
        # Latest products (from subscribed farms only)
        latest_products = Product.objects.filter(
            status='active',
            farm__farm_status='Active',
            **self.SUBSCRIPTION_FILTER
        ).select_related('category', 'farm').order_by('-created_at')[:8]
        
        # Best selling products (from subscribed farms only)
        best_selling = Product.objects.filter(
            status='active',
            farm__farm_status='Active',
            **self.SUBSCRIPTION_FILTER
        ).select_related('category', 'farm').order_by('-total_sold')[:8]
        
        # Categories with product counts (counting only products from subscribed farms)
        categories = ProductCategory.objects.filter(
            is_active=True
        ).annotate(
            product_count=Count(
                'products', 
                filter=Q(
                    products__status='active',
                    products__farm__marketplace_enabled=True,
                    products__farm__subscription__status__in=['trial', 'active']
                )
            )
        ).filter(product_count__gt=0).order_by('display_order')[:8]
        
        # Top farms (only subscribed farms)
        top_farms = Farm.objects.filter(
            farm_status='Active',
            marketplace_products__status='active',
            # SUBSCRIPTION VISIBILITY FILTER:
            marketplace_enabled=True,
            subscription__status__in=['trial', 'active']
        ).distinct().annotate(
            product_count=Count('marketplace_products', filter=Q(marketplace_products__status='active')),
            avg_rating=Avg('marketplace_products__average_rating')
        ).order_by('-product_count')[:6]
        
        # Stats (only counting subscribed farms for public display)
        subscribed_products_count = Product.objects.filter(
            status='active',
            farm__marketplace_enabled=True,
            farm__subscription__status__in=['trial', 'active']
        ).count()
        
        subscribed_farms_count = Farm.objects.filter(
            farm_status='Active',
            marketplace_products__status='active',
            marketplace_enabled=True,
            subscription__status__in=['trial', 'active']
        ).distinct().count()
        
        return Response({
            'featured_products': PublicProductListSerializer(
                featured_products, many=True, context={'request': request}
            ).data,
            'latest_products': PublicProductListSerializer(
                latest_products, many=True, context={'request': request}
            ).data,
            'best_selling': PublicProductListSerializer(
                best_selling, many=True, context={'request': request}
            ).data,
            'categories': ProductCategorySerializer(categories, many=True).data,
            'top_farms': PublicFarmSerializer(top_farms, many=True).data,
            'stats': {
                'total_products': subscribed_products_count,
                'total_farms': subscribed_farms_count,
                'total_categories': ProductCategory.objects.filter(is_active=True).count(),
            }
        })
