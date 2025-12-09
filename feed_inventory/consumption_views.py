"""
Feed Consumption API Views

Provides endpoints for tracking feed consumption with batch selection,
balance validation, and analytics.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farms.models import Farm
from flock_management.models import Flock, DailyProduction

from .models import FeedConsumption, FeedPurchase, FeedType


class AvailableFeedStockView(APIView):
    """
    GET /api/feed/stock/available/
    
    Returns feed stock with balance > 0 for dropdown selection.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List available feed stock for consumption."""
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get stock with positive balance
        available_stock = (
            FeedPurchase.objects.filter(
                farm=farm,
                stock_balance_kg__gt=0
            )
            .select_related('feed_type')
            .order_by('-purchase_date', 'batch_number')
        )
        
        data = [
            {
                'stock_id': str(stock.id),
                'batch_number': stock.batch_number,
                'feed_type': stock.feed_type.name,
                'feed_type_id': str(stock.feed_type_id),
                'brand': stock.brand,
                'stock_balance_kg': float(stock.stock_balance_kg),
                'unit_price': float(stock.unit_price),
                'purchase_date': stock.purchase_date.isoformat(),
            }
            for stock in available_stock
        ]
        
        return Response({'available_stock': data, 'total': len(data)})
    
    def _get_farm(self, request):
        try:
            return Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return None


class FeedConsumptionView(APIView):
    """
    GET  /api/feed/consumption/ - List consumption records with analytics
    POST /api/feed/consumption/ - Create consumption record with batch selection
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List consumption records with analytics."""
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)
        
        # Optional filters
        flock_id = request.query_params.get('flock_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Build query
        consumption_qs = FeedConsumption.objects.filter(farm=farm).select_related(
            'feed_stock', 'feed_type', 'flock', 'daily_production'
        )
        
        if flock_id:
            consumption_qs = consumption_qs.filter(flock_id=flock_id)
        
        if start_date:
            try:
                start = datetime.fromisoformat(start_date).date()
                consumption_qs = consumption_qs.filter(date__gte=start)
            except ValueError:
                pass
        
        if end_date:
            try:
                end = datetime.fromisoformat(end_date).date()
                consumption_qs = consumption_qs.filter(date__lte=end)
            except ValueError:
                pass
        
        consumption_records = consumption_qs.order_by('-date', '-created_at')
        
        # Format response
        data = [
            {
                'id': str(record.id),
                'date': record.date.isoformat(),
                'flock_id': str(record.flock_id),
                'flock_name': record.flock.flock_number,
                'stock_id': str(record.feed_stock_id) if record.feed_stock_id else None,
                'batch_number': record.feed_stock.batch_number if record.feed_stock else None,
                'feed_type': record.feed_type.name,
                'feed_type_id': str(record.feed_type_id),
                'quantity_consumed_kg': float(record.quantity_consumed_kg),
                'cost_per_kg': float(record.cost_per_kg),
                'total_cost': float(record.total_cost),
                'birds_count': record.birds_count_at_consumption,
                'consumption_per_bird_grams': float(record.consumption_per_bird_grams),
                'stock_balance_after': float(record.feed_stock.stock_balance_kg) if record.feed_stock else None,
                'created_at': record.created_at.isoformat(),
            }
            for record in consumption_records
        ]
        
        # Calculate analytics
        analytics = self._calculate_analytics(farm, flock_id)
        
        return Response({
            'consumption_records': data,
            'total': len(data),
            'analytics': analytics
        })
    
    def post(self, request):
        """Create consumption record with batch selection."""
        farm = self._get_farm(request)
        if not farm:
            return Response({'error': 'No farm found for this user'}, status=status.HTTP_404_NOT_FOUND)
        
        # Extract required fields
        stock_id = request.data.get('stock_id')
        flock_id = request.data.get('flock_id')
        quantity_consumed_kg = self._to_decimal(request.data.get('quantity_consumed_kg'), 0)
        consumption_date = self._parse_date(request.data.get('date'))
        daily_production_id = request.data.get('daily_production_id')
        
        # Validation
        if not stock_id:
            return Response({'error': 'stock_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not flock_id:
            return Response({'error': 'flock_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if quantity_consumed_kg <= 0:
            return Response({'error': 'quantity_consumed_kg must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not consumption_date:
            consumption_date = timezone.now().date()
        
        # Get feed stock
        try:
            feed_stock = FeedPurchase.objects.select_related('feed_type').get(id=stock_id, farm=farm)
        except FeedPurchase.DoesNotExist:
            # Debug: log what we're looking for
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Feed stock not found - stock_id: {stock_id}, farm: {farm.id if farm else None}")
            available_stocks = FeedPurchase.objects.filter(farm=farm).values_list('id', flat=True)
            logger.error(f"Available stock IDs for this farm: {list(available_stocks)}")
            return Response({
                'error': 'Feed stock not found',
                'stock_id_received': str(stock_id),
                'farm_id': str(farm.id) if farm else None,
                'available_stock_ids': [str(sid) for sid in available_stocks]
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate stock balance
        if quantity_consumed_kg > feed_stock.stock_balance_kg:
            return Response({
                'error': f'Insufficient stock. Available: {feed_stock.stock_balance_kg} kg, Requested: {quantity_consumed_kg} kg'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get flock
        try:
            flock = Flock.objects.get(id=flock_id, farm=farm)
        except Flock.DoesNotExist:
            return Response({'error': 'Flock not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create daily production record
        daily_production = None
        if daily_production_id:
            try:
                daily_production = DailyProduction.objects.get(id=daily_production_id, farm=farm, flock=flock)
            except DailyProduction.DoesNotExist:
                pass
        
        if not daily_production:
            # Create daily production record
            daily_production, created = DailyProduction.objects.get_or_create(
                farm=farm,
                flock=flock,
                production_date=consumption_date,
                defaults={
                    'eggs_collected': 0,
                    'mortality_count': 0,
                    'culls_count': 0,
                }
            )
        
        # Calculate bird count
        birds_count = flock.get_current_bird_count(as_of_date=consumption_date)
        
        # Create consumption record
        try:
            with transaction.atomic():
                consumption = FeedConsumption(
                    daily_production=daily_production,
                    farm=farm,
                    flock=flock,
                    feed_stock=feed_stock,
                    date=consumption_date,
                    quantity_consumed_kg=quantity_consumed_kg,
                    birds_count_at_consumption=birds_count,
                )
                consumption.full_clean()
                consumption.save()
        
        except Exception as exc:
            from django.core.exceptions import ValidationError
            
            if isinstance(exc, ValidationError):
                return Response({'errors': exc.message_dict}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': 'Feed consumption recorded successfully',
            'consumption_id': str(consumption.id),
            'batch_number': feed_stock.batch_number,
            'stock_balance_remaining': float(feed_stock.stock_balance_kg),
            'birds_count': birds_count,
            'consumption_per_bird_grams': float(consumption.consumption_per_bird_grams),
        }, status=status.HTTP_201_CREATED)
    
    def _get_farm(self, request):
        try:
            return Farm.objects.get(user=request.user)
        except Farm.DoesNotExist:
            return None
    
    def _parse_date(self, date_str):
        if not date_str:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except Exception:
                continue
        try:
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00')).date()
        except Exception:
            return None
    
    def _to_decimal(self, value, default=0):
        try:
            if value in (None, ''):
                return Decimal(str(default))
            return Decimal(str(value))
        except Exception:
            return Decimal(str(default))
    
    def _calculate_analytics(self, farm, flock_id=None):
        """Calculate consumption analytics."""
        now = timezone.now().date()
        first_of_month = now.replace(day=1)
        
        # Base query
        qs = FeedConsumption.objects.filter(farm=farm)
        if flock_id:
            qs = qs.filter(flock_id=flock_id)
        
        # This month's consumption
        this_month_consumption = qs.filter(
            date__gte=first_of_month,
            date__lte=now
        ).aggregate(
            total=Sum('quantity_consumed_kg')
        )['total'] or Decimal('0.00')
        
        # Last 30 days average
        thirty_days_ago = now - timedelta(days=30)
        last_30_days = qs.filter(
            date__gte=thirty_days_ago,
            date__lte=now
        )
        
        total_30_days = last_30_days.aggregate(
            total=Sum('quantity_consumed_kg')
        )['total'] or Decimal('0.00')
        
        days_with_consumption = last_30_days.values('date').distinct().count()
        average_daily_consumption = (
            total_30_days / days_with_consumption if days_with_consumption > 0 else Decimal('0.00')
        )
        
        # Days of stock remaining
        total_stock_balance = FeedPurchase.objects.filter(
            farm=farm,
            stock_balance_kg__gt=0
        ).aggregate(
            total=Sum('stock_balance_kg')
        )['total'] or Decimal('0.00')
        
        days_remaining = (
            total_stock_balance / average_daily_consumption 
            if average_daily_consumption > 0 
            else None
        )
        
        return {
            'this_month_consumption_kg': float(this_month_consumption),
            'average_daily_consumption_kg': float(average_daily_consumption),
            'total_stock_balance_kg': float(total_stock_balance),
            'days_of_stock_remaining': float(days_remaining) if days_remaining else None,
        }
