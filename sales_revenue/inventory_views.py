"""
Inventory Views and API Endpoints

Provides:
1. Farmer views - Manage their own inventory
2. Government/Admin views - Analytics and intervention planning
"""

from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

from .inventory_models import (
    FarmInventory, 
    StockMovement, 
    InventoryBatch,
    BirdsReadyForMarket,
    FarmInventoryAnalytics,
    InventoryCategory,
    StockMovementType
)


class IsFarmer(BasePermission):
    """
    Permission class to check if user is a farmer with an associated farm.
    """
    message = 'You must be a registered farmer to access this resource.'
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'farm') and
            request.user.farm is not None
        )


# =============================================================================
# FARMER INVENTORY VIEWS
# =============================================================================

class FarmInventoryListView(generics.ListAPIView):
    """
    List all inventory items for the authenticated farmer's farm.
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def get_queryset(self):
        return FarmInventory.objects.filter(
            farm=self.request.user.farm,
            is_active=True
        ).order_by('category', 'product_name')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Summary statistics
        summary = queryset.aggregate(
            total_value=Coalesce(Sum('total_value'), 0),
            total_items=Count('id'),
            low_stock_count=Count('id', filter=Q(is_low_stock=True)),
            eggs_in_stock=Sum('quantity_available', filter=Q(category=InventoryCategory.EGGS)),
            birds_in_stock=Sum('quantity_available', filter=Q(category=InventoryCategory.BIRDS)),
        )
        
        # Inventory list
        inventory_data = []
        for item in queryset:
            inventory_data.append({
                'id': str(item.id),
                'category': item.category,
                'product_name': item.product_name,
                'quantity_available': float(item.quantity_available),
                'unit': item.unit,
                'unit_cost': float(item.unit_cost),
                'total_value': float(item.total_value),
                'is_low_stock': item.is_low_stock,
                'oldest_stock_date': item.oldest_stock_date,
                'average_age_days': item.average_age_days,
                'days_since_last_sale': item.days_since_last_sale,
                'stock_health': item.stock_health,
                'turnover_rate': item.turnover_rate,
                'total_sold': float(item.total_sold),
                'total_revenue': float(item.total_revenue),
                'last_stock_update': item.last_stock_update,
                'last_sale_date': item.last_sale_date,
            })
        
        return Response({
            'summary': summary,
            'inventory': inventory_data
        })


class FarmInventoryDetailView(generics.RetrieveAPIView):
    """
    View detailed inventory item with movement history.
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    lookup_field = 'id'
    
    def get_queryset(self):
        return FarmInventory.objects.filter(
            farm=self.request.user.farm,
            is_active=True
        )
    
    def retrieve(self, request, *args, **kwargs):
        item = self.get_object()
        
        # Recent movements
        movements = StockMovement.objects.filter(
            inventory=item
        ).order_by('-created_at')[:50]
        
        movements_data = [{
            'id': str(m.id),
            'movement_type': m.movement_type,
            'movement_type_display': m.get_movement_type_display(),
            'quantity': float(m.quantity),
            'balance_after': float(m.balance_after),
            'stock_date': m.stock_date,
            'notes': m.notes,
            'created_at': m.created_at,
        } for m in movements]
        
        # Active batches (for FIFO tracking)
        batches = InventoryBatch.objects.filter(
            inventory=item,
            is_depleted=False
        ).order_by('production_date')
        
        batches_data = [{
            'id': str(b.id),
            'batch_number': b.batch_number,
            'current_quantity': float(b.current_quantity),
            'production_date': b.production_date,
            'expiry_date': b.expiry_date,
            'age_days': b.age_days,
            'days_until_expiry': b.days_until_expiry,
            'is_expired': b.is_expired,
        } for b in batches]
        
        return Response({
            'id': str(item.id),
            'category': item.category,
            'product_name': item.product_name,
            'quantity_available': float(item.quantity_available),
            'unit': item.unit,
            'unit_cost': float(item.unit_cost),
            'total_value': float(item.total_value),
            'is_low_stock': item.is_low_stock,
            'low_stock_threshold': float(item.low_stock_threshold),
            'oldest_stock_date': item.oldest_stock_date,
            'average_age_days': item.average_age_days,
            'max_shelf_life_days': item.max_shelf_life_days,
            'stock_health': item.stock_health,
            'total_added': float(item.total_added),
            'total_sold': float(item.total_sold),
            'total_lost': float(item.total_lost),
            'total_revenue': float(item.total_revenue),
            'turnover_rate': item.turnover_rate,
            'movements': movements_data,
            'batches': batches_data,
        })


class InventoryAdjustmentView(APIView):
    """
    Manual inventory adjustments (add/remove stock).
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def post(self, request, inventory_id):
        """
        Add or remove stock manually.
        
        Request body:
        {
            "action": "add" | "remove",
            "quantity": 10,
            "reason": "spoilage" | "breakage" | "adjustment" | "personal_use",
            "notes": "Optional notes"
        }
        """
        try:
            inventory = FarmInventory.objects.get(
                id=inventory_id,
                farm=request.user.farm
            )
        except FarmInventory.DoesNotExist:
            return Response(
                {'error': 'Inventory not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        action = request.data.get('action')
        quantity = request.data.get('quantity', 0)
        reason = request.data.get('reason', 'adjustment')
        notes = request.data.get('notes', '')
        
        if not action or action not in ['add', 'remove']:
            return Response(
                {'error': 'Action must be "add" or "remove"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be positive'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if action == 'add':
                movement = inventory.add_stock(
                    quantity=quantity,
                    movement_type=StockMovementType.ADJUSTMENT_ADD,
                    notes=notes,
                    recorded_by=request.user
                )
            else:
                # Map reason to movement type
                movement_type_map = {
                    'spoilage': StockMovementType.SPOILAGE,
                    'breakage': StockMovementType.BREAKAGE,
                    'personal_use': StockMovementType.PERSONAL_USE,
                    'adjustment': StockMovementType.ADJUSTMENT_REMOVE,
                }
                movement_type = movement_type_map.get(reason, StockMovementType.ADJUSTMENT_REMOVE)
                
                movement = inventory.remove_stock(
                    quantity=quantity,
                    movement_type=movement_type,
                    notes=notes,
                    recorded_by=request.user
                )
            
            return Response({
                'message': f'Successfully {"added" if action == "add" else "removed"} {quantity}',
                'new_balance': float(inventory.quantity_available),
                'movement_id': str(movement.id)
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class BirdsReadyForMarketView(APIView):
    """
    Record birds as ready for market.
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def get(self, request):
        """List all market-ready bird records."""
        records = BirdsReadyForMarket.objects.filter(
            farm=request.user.farm
        ).select_related('flock').order_by('-date_ready')
        
        data = [{
            'id': str(r.id),
            'flock_number': r.flock.flock_number,
            'date_ready': r.date_ready,
            'bird_type': r.bird_type,
            'quantity': r.quantity,
            'quantity_sold': r.quantity_sold,
            'quantity_remaining': r.quantity_remaining,
            'average_weight_kg': float(r.average_weight_kg) if r.average_weight_kg else None,
            'estimated_price_per_bird': float(r.estimated_price_per_bird),
            'total_estimated_value': float(r.total_estimated_value),
            'is_fully_sold': r.is_fully_sold,
        } for r in records]
        
        return Response(data)
    
    def post(self, request):
        """
        Record birds as ready for market.
        
        Request body:
        {
            "flock_id": "uuid",
            "quantity": 100,
            "bird_type": "broiler",
            "average_weight_kg": 2.5,
            "estimated_price_per_bird": 50.00,
            "notes": "Optional notes"
        }
        """
        from flock_management.models import Flock
        
        flock_id = request.data.get('flock_id')
        quantity = request.data.get('quantity')
        bird_type = request.data.get('bird_type')
        
        if not all([flock_id, quantity, bird_type]):
            return Response(
                {'error': 'flock_id, quantity, and bird_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            flock = Flock.objects.get(id=flock_id, farm=request.user.farm)
        except Flock.DoesNotExist:
            return Response(
                {'error': 'Flock not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if quantity > flock.current_count:
            return Response(
                {'error': f'Quantity exceeds current flock count ({flock.current_count})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        record = BirdsReadyForMarket.objects.create(
            farm=request.user.farm,
            flock=flock,
            quantity=quantity,
            bird_type=bird_type,
            average_weight_kg=request.data.get('average_weight_kg'),
            estimated_price_per_bird=request.data.get('estimated_price_per_bird', 0),
            notes=request.data.get('notes', ''),
            recorded_by=request.user
        )
        
        return Response({
            'message': f'{quantity} {bird_type}s marked as ready for market',
            'id': str(record.id),
            'inventory_entry_id': str(record.inventory_entry.id) if record.inventory_entry else None
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# GOVERNMENT/ADMIN ANALYTICS VIEWS
# =============================================================================

class GovernmentInventoryAnalyticsView(APIView):
    """
    Government dashboard for inventory analytics.
    Shows farms with selling challenges for intervention planning.
    
    Requires admin authentication.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get overview of inventory challenges across all farms.
        
        Query params:
        - region: Filter by region
        - days_threshold: Days without sales to flag (default: 7)
        - min_value: Minimum stock value to consider (default: 100)
        """
        # Check if user has admin permissions
        if not request.user.is_staff and request.user.role not in ['Super Admin', 'National Admin', 'Regional Admin']:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        region = request.query_params.get('region')
        days_threshold = int(request.query_params.get('days_threshold', 7))
        min_value = float(request.query_params.get('min_value', 100))
        
        # Overall statistics
        total_farms_with_inventory = FarmInventory.objects.filter(
            is_active=True,
            quantity_available__gt=0
        ).values('farm').distinct().count()
        
        total_inventory_value = FarmInventory.objects.filter(
            is_active=True
        ).aggregate(total=Coalesce(Sum('total_value'), 0))['total']
        
        # Farms with selling challenges
        threshold_date = timezone.now() - timedelta(days=days_threshold)
        
        challenging_farms_qs = FarmInventory.objects.filter(
            is_active=True,
            quantity_available__gt=0,
            total_value__gte=min_value
        ).filter(
            Q(last_sale_date__isnull=True) |
            Q(last_sale_date__lt=threshold_date)
        ).select_related('farm')
        
        if region:
            challenging_farms_qs = challenging_farms_qs.filter(
                farm__primary_region__icontains=region
            )
        
        # Aggregate by farm
        farms_with_challenges = challenging_farms_qs.values(
            'farm__id',
            'farm__farm_name',
            'farm__primary_region',
            'farm__primary_constituency',
        ).annotate(
            total_stock_value=Sum('total_value'),
            total_quantity=Sum('quantity_available'),
            inventory_items=Count('id'),
        ).order_by('-total_stock_value')[:50]
        
        # Expiring stock
        expiry_threshold = timezone.now().date() + timedelta(days=3)
        expiring_batches = InventoryBatch.objects.filter(
            is_depleted=False,
            is_expired=False,
            expiry_date__lte=expiry_threshold,
            current_quantity__gt=0
        ).select_related('inventory__farm')
        
        expiring_summary = expiring_batches.values(
            'inventory__farm__id',
            'inventory__farm__farm_name',
            'inventory__farm__primary_region',
        ).annotate(
            expiring_quantity=Sum('current_quantity'),
            batch_count=Count('id'),
        ).order_by('-expiring_quantity')[:20]
        
        # Regional breakdown
        regional_stats = FarmInventory.objects.filter(
            is_active=True,
            quantity_available__gt=0
        ).values(
            'farm__primary_region'
        ).annotate(
            total_farms=Count('farm', distinct=True),
            total_value=Sum('total_value'),
            total_quantity=Sum('quantity_available'),
            farms_not_selling=Count(
                'farm',
                distinct=True,
                filter=Q(last_sale_date__isnull=True) | Q(last_sale_date__lt=threshold_date)
            )
        ).order_by('farm__primary_region')
        
        return Response({
            'overview': {
                'total_farms_with_inventory': total_farms_with_inventory,
                'total_inventory_value': float(total_inventory_value),
                'farms_with_challenges': len(farms_with_challenges),
                'threshold_days': days_threshold,
            },
            'farms_needing_intervention': [
                {
                    'farm_id': str(f['farm__id']),
                    'farm_name': f['farm__farm_name'],
                    'region': f['farm__primary_region'],
                    'constituency': f['farm__primary_constituency'],
                    'stock_value': float(f['total_stock_value']),
                    'total_quantity': float(f['total_quantity']),
                    'inventory_items': f['inventory_items'],
                }
                for f in farms_with_challenges
            ],
            'expiring_stock': [
                {
                    'farm_id': str(e['inventory__farm__id']),
                    'farm_name': e['inventory__farm__farm_name'],
                    'region': e['inventory__farm__primary_region'],
                    'expiring_quantity': float(e['expiring_quantity']),
                    'batch_count': e['batch_count'],
                }
                for e in expiring_summary
            ],
            'regional_breakdown': [
                {
                    'region': r['farm__primary_region'] or 'Unknown',
                    'total_farms': r['total_farms'],
                    'total_value': float(r['total_value']),
                    'total_quantity': float(r['total_quantity']),
                    'farms_not_selling': r['farms_not_selling'],
                    'challenge_rate': round(
                        (r['farms_not_selling'] / r['total_farms'] * 100) 
                        if r['total_farms'] > 0 else 0, 1
                    )
                }
                for r in regional_stats
            ]
        })


class FarmInventoryInterventionView(APIView):
    """
    Detailed view for a specific farm needing intervention.
    Allows government admins to see what help a farmer needs.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, farm_id):
        """Get detailed inventory information for a specific farm."""
        from farms.models import Farm
        
        # Check admin permissions
        if not request.user.is_staff and request.user.role not in ['Super Admin', 'National Admin', 'Regional Admin']:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            farm = Farm.objects.get(id=farm_id)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'Farm not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Farm info
        farm_info = {
            'id': str(farm.id),
            'farm_name': farm.farm_name,
            'farmer_name': farm.owner.get_full_name() if farm.owner else None,
            'phone': farm.owner.phone_number if farm.owner else None,
            'email': farm.owner.email if farm.owner else None,
            'region': farm.primary_region,
            'constituency': farm.primary_constituency,
            'location': farm.location,
        }
        
        # Inventory summary
        inventory = FarmInventory.objects.filter(
            farm=farm,
            is_active=True
        )
        
        inventory_data = []
        total_value = 0
        total_unsold_days = 0
        items_count = 0
        
        for item in inventory:
            days_without_sale = item.days_since_last_sale or (
                (timezone.now() - item.created_at).days if item.created_at else 0
            )
            
            inventory_data.append({
                'category': item.category,
                'product_name': item.product_name,
                'quantity': float(item.quantity_available),
                'unit': item.unit,
                'value': float(item.total_value),
                'days_without_sale': days_without_sale,
                'stock_health': item.stock_health,
                'oldest_stock_date': item.oldest_stock_date,
            })
            
            total_value += float(item.total_value)
            total_unsold_days += days_without_sale
            items_count += 1
        
        # Expiring batches
        expiry_threshold = timezone.now().date() + timedelta(days=5)
        expiring = InventoryBatch.objects.filter(
            inventory__farm=farm,
            is_depleted=False,
            expiry_date__lte=expiry_threshold,
            current_quantity__gt=0
        ).order_by('expiry_date')
        
        expiring_data = [{
            'batch_number': b.batch_number,
            'product': b.inventory.product_name,
            'quantity': float(b.current_quantity),
            'expiry_date': b.expiry_date,
            'days_until_expiry': b.days_until_expiry,
        } for b in expiring]
        
        # Intervention recommendations
        recommendations = self._generate_recommendations(
            inventory_data, expiring_data, total_value
        )
        
        return Response({
            'farm': farm_info,
            'summary': {
                'total_inventory_value': total_value,
                'inventory_items': items_count,
                'average_days_without_sale': round(
                    total_unsold_days / items_count if items_count > 0 else 0, 1
                ),
                'expiring_batches': len(expiring_data),
            },
            'inventory': inventory_data,
            'expiring_soon': expiring_data,
            'recommendations': recommendations,
        })
    
    def _generate_recommendations(self, inventory, expiring, total_value):
        """Generate intervention recommendations based on inventory status."""
        recommendations = []
        
        # Check for high-value stuck inventory
        if total_value > 5000:
            recommendations.append({
                'priority': 'high',
                'type': 'market_linkage',
                'message': f'High inventory value (GHS {total_value:.2f}) requires urgent market linkage support'
            })
        
        # Check for expiring products
        if expiring:
            total_expiring = sum(item['quantity'] for item in expiring)
            recommendations.append({
                'priority': 'critical',
                'type': 'immediate_sale',
                'message': f'{total_expiring} units expiring soon - consider emergency buyer connection or price reduction'
            })
        
        # Check for items not selling
        not_selling = [i for i in inventory if i.get('days_without_sale', 0) > 14]
        if not_selling:
            recommendations.append({
                'priority': 'medium',
                'type': 'marketing_support',
                'message': f'{len(not_selling)} products have not sold in 14+ days - review pricing and marketing'
            })
        
        # Check stock health
        critical = [i for i in inventory if i.get('stock_health') == 'critical']
        if critical:
            recommendations.append({
                'priority': 'high',
                'type': 'stock_management',
                'message': f'{len(critical)} inventory items in critical condition'
            })
        
        if not recommendations:
            recommendations.append({
                'priority': 'low',
                'type': 'monitoring',
                'message': 'Inventory appears healthy - continue monitoring'
            })
        
        return recommendations
