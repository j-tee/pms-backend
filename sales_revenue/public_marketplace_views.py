"""
Public Marketplace Views

These views power the public-facing marketplace where anyone can browse products
from all farms without authentication. Order placement and inquiries require
basic contact information but not a user account.

PUBLIC (No Authentication Required):
- Browse all active products from all farms
- View individual product details
- View farm storefronts/profiles
- Search and filter products by location (region, district, constituency)
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
    Browse all active products from all farms.
    
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
        """Return all active products from active farms."""
        queryset = Product.objects.filter(
            status='active',
            farm__farm_status='Active'  # Only from active farms
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
        return Product.objects.filter(
            status='active',
            farm__farm_status='Active'
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
    that have active farms with products.
    
    GET /api/public/marketplace/locations/
    GET /api/public/marketplace/locations/?region=Greater Accra  (get districts for region)
    GET /api/public/marketplace/locations/?district=Accra Metropolitan  (get constituencies)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get locations only from active farms with active products
        active_farm_ids = Farm.objects.filter(
            farm_status='Active',
            marketplace_products__status='active'
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
    List all farms with active products.
    
    Shows public farm information for marketplace browsing.
    
    Supports filtering by:
    - region: Farm region
    - district: Farm district
    - constituency: Farm constituency
    - q: Search farm by name
    """
    permission_classes = [AllowAny]
    serializer_class = PublicFarmSerializer
    
    def get_queryset(self):
        # Only farms that have active products
        queryset = Farm.objects.filter(
            farm_status='Active',
            marketplace_products__status='active'
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
    
    Returns:
    - Farm info (name, location, description, logo)
    - Featured products
    - Product categories in this farm
    - Delivery options
    """
    permission_classes = [AllowAny]
    
    def get(self, request, farm_id):
        farm = get_object_or_404(
            Farm.objects.annotate(
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
    
    Same filtering options as PublicProductListView but scoped to one farm.
    """
    permission_classes = [AllowAny]
    serializer_class = PublicProductListSerializer
    
    def get_queryset(self):
        farm_id = self.kwargs['farm_id']
        
        queryset = Product.objects.filter(
            farm_id=farm_id,
            status='active',
            farm__farm_status='Active'
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
            farm__farm_status='Active'
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
    
    Returns:
    - Featured products
    - Top categories
    - Top farms
    - Latest products
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Featured products
        featured_products = Product.objects.filter(
            status='active',
            is_featured=True,
            farm__farm_status='Active'
        ).select_related('category', 'farm').order_by('-total_sold')[:8]
        
        # Latest products
        latest_products = Product.objects.filter(
            status='active',
            farm__farm_status='Active'
        ).select_related('category', 'farm').order_by('-created_at')[:8]
        
        # Best selling products
        best_selling = Product.objects.filter(
            status='active',
            farm__farm_status='Active'
        ).select_related('category', 'farm').order_by('-total_sold')[:8]
        
        # Categories with product counts
        categories = ProductCategory.objects.filter(
            is_active=True
        ).annotate(
            product_count=Count('products', filter=Q(products__status='active'))
        ).filter(product_count__gt=0).order_by('display_order')[:8]
        
        # Top farms
        top_farms = Farm.objects.filter(
            farm_status='Active',
            marketplace_products__status='active'
        ).distinct().annotate(
            product_count=Count('marketplace_products', filter=Q(marketplace_products__status='active')),
            avg_rating=Avg('marketplace_products__average_rating')
        ).order_by('-product_count')[:6]
        
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
                'total_products': Product.objects.filter(status='active').count(),
                'total_farms': Farm.objects.filter(
                    farm_status='Active',
                    marketplace_products__status='active'
                ).distinct().count(),
                'total_categories': ProductCategory.objects.filter(is_active=True).count(),
            }
        })
