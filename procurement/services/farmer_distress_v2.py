"""
Farmer Distress Scoring Service v2

Enhanced version that aligns with frontend requirements for:
- Detailed distress factor breakdowns
- Sales history tracking
- Procurement history
- Region-based analytics

DISTRESS INDICATORS (Frontend Spec):
1. Inventory Stagnation (25%) - Products sitting unsold
2. Sales Performance (25%) - Declining/low sales
3. Financial Stress (20%) - Outstanding payments, late payments
4. Production Issues (15%) - Mortality, low production
5. Market Access (15%) - No marketplace, low customer base

DISTRESS LEVELS (Updated to match frontend spec):
- 80-100: CRITICAL - Urgent intervention needed
- 60-79: HIGH - Significant struggle
- 40-59: MODERATE - Some difficulties
- 20-39: LOW - Minor issues
- 0-19: STABLE - Healthy operations
"""

from django.db.models import Q, Sum, Avg, Count, F, Value, Case, When, IntegerField
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

from farms.models import Farm

logger = logging.getLogger(__name__)


# Distress Level Constants (matching frontend spec)
DISTRESS_LEVELS = {
    'CRITICAL': {'min': 80, 'max': 100, 'action': 'Prioritize immediately'},
    'HIGH': {'min': 60, 'max': 79, 'action': 'High priority for next orders'},
    'MODERATE': {'min': 40, 'max': 59, 'action': 'Include in regular assignments'},
    'LOW': {'min': 20, 'max': 39, 'action': 'Consider for larger orders'},
    'STABLE': {'min': 0, 'max': 19, 'action': 'Assign only if capacity needed'},
}


def get_distress_level(score):
    """Convert numeric score to distress level string."""
    if score >= 80:
        return 'CRITICAL'
    elif score >= 60:
        return 'HIGH'
    elif score >= 40:
        return 'MODERATE'
    elif score >= 20:
        return 'LOW'
    else:
        return 'STABLE'


class FarmerDistressService:
    """
    Enhanced service for calculating and retrieving farmer distress scores.
    Aligned with frontend specification for procurement officer UX.
    """
    
    # Scoring weights (total = 100) - aligned with frontend spec
    WEIGHTS = {
        'inventory_stagnation': 25,  # Unsold inventory aging
        'sales_performance': 25,     # Sales trends and activity
        'financial_stress': 20,      # Outstanding payments, financial health
        'production_issues': 15,     # Mortality, production efficiency
        'market_access': 15,         # Marketplace engagement, customer base
    }
    
    def __init__(self, days_lookback=30):
        """
        Initialize the distress service.
        
        Args:
            days_lookback: Number of days to analyze for activity metrics
        """
        self.days_lookback = days_lookback
        self.cutoff_date = timezone.now() - timedelta(days=days_lookback)
        self.ninety_days_ago = timezone.now() - timedelta(days=90)
    
    def calculate_distress_score(self, farm):
        """
        Calculate comprehensive distress score for a single farm.
        Returns detailed breakdown matching frontend spec.
        
        Args:
            farm: Farm instance
            
        Returns:
            dict with full distress assessment
        """
        # Calculate individual factor scores
        inventory_result = self._score_inventory_stagnation(farm)
        sales_result = self._score_sales_performance(farm)
        financial_result = self._score_financial_stress(farm)
        production_result = self._score_production_issues(farm)
        market_result = self._score_market_access(farm)
        
        # Collect raw scores
        scores = {
            'inventory_stagnation': inventory_result['score'],
            'sales_performance': sales_result['score'],
            'financial_stress': financial_result['score'],
            'production_issues': production_result['score'],
            'market_access': market_result['score'],
        }
        
        # Calculate weighted total
        total_score = sum(
            scores[key] * (self.WEIGHTS[key] / 100)
            for key in scores
        )
        total_score = round(min(100, max(0, total_score)), 1)
        
        # Determine distress level
        distress_level = get_distress_level(total_score)
        
        # Build distress factors array (frontend format)
        distress_factors = []
        
        if inventory_result['score'] >= 40:
            distress_factors.append({
                'factor': 'INVENTORY_STAGNATION',
                'score': inventory_result['score'],
                'detail': inventory_result['detail'],
            })
        
        if sales_result['score'] >= 40:
            distress_factors.append({
                'factor': 'SALES_PERFORMANCE',
                'score': sales_result['score'],
                'detail': sales_result['detail'],
            })
        
        if financial_result['score'] >= 40:
            distress_factors.append({
                'factor': 'FINANCIAL_STRESS',
                'score': financial_result['score'],
                'detail': financial_result['detail'],
            })
        
        if production_result['score'] >= 40:
            distress_factors.append({
                'factor': 'PRODUCTION_ISSUES',
                'score': production_result['score'],
                'detail': production_result['detail'],
            })
        
        if market_result['score'] >= 40:
            distress_factors.append({
                'factor': 'MARKET_ACCESS',
                'score': market_result['score'],
                'detail': market_result['detail'],
            })
        
        # Sort by score descending
        distress_factors.sort(key=lambda x: x['score'], reverse=True)
        
        # Get sales history
        sales_history = self._get_sales_history(farm)
        
        # Get procurement history
        procurement_history = self._get_procurement_history(farm)
        
        # Get capacity information
        capacity = self._get_capacity_info(farm)
        
        return {
            'farm_id': str(farm.id),
            'farm_name': farm.farm_name,
            'farmer_name': farm.user.get_full_name() if farm.user else 'N/A',
            'region': farm.region,
            'district': farm.district,
            'production_type': farm.primary_production_type,
            
            'distress_score': total_score,
            'distress_level': distress_level,
            'distress_factors': distress_factors,
            
            'capacity': capacity,
            'sales_history': sales_history,
            'procurement_history': procurement_history,
            
            'contact': {
                'phone': str(farm.primary_phone),
                'location_coordinates': self._get_coordinates(farm),
                'constituency': farm.primary_constituency,
            },
            
            # Detailed score breakdown for debugging/analytics
            'score_breakdown': {
                key: {
                    'score': round(scores[key], 1),
                    'weight': self.WEIGHTS[key],
                    'weighted_contribution': round(scores[key] * (self.WEIGHTS[key] / 100), 1),
                    'detail': {
                        'inventory_stagnation': inventory_result,
                        'sales_performance': sales_result,
                        'financial_stress': financial_result,
                        'production_issues': production_result,
                        'market_access': market_result,
                    }.get(key, {}).get('detail', '')
                }
                for key in scores
            },
        }
    
    def _score_inventory_stagnation(self, farm):
        """
        Score: Products sitting unsold for extended periods.
        
        Metrics:
        - Days since last sale
        - Inventory turnover rate
        - Percentage of production unsold
        - Products approaching expiry (eggs)
        """
        try:
            from sales_revenue.inventory_models import FarmInventory
            
            inventory = FarmInventory.objects.filter(farm=farm)
            
            if not inventory.exists():
                return {'score': 50, 'detail': 'No inventory data available'}
            
            total_score = 0
            details = []
            
            # Check for aging eggs (critical - eggs expire quickly)
            egg_inventory = inventory.filter(category='eggs')
            for item in egg_inventory:
                if item.oldest_stock_date:
                    days_old = (timezone.now().date() - item.oldest_stock_date).days
                    qty = item.quantity_available or 0
                    
                    if days_old > 21:  # Eggs older than 3 weeks
                        total_score += 50
                        details.append(f'{qty} crates of eggs {days_old} days old (critical)')
                    elif days_old > 14:
                        total_score += 30
                        details.append(f'{qty} crates of eggs {days_old} days old')
                    elif days_old > 7:
                        total_score += 15
            
            # Check for overstocked birds ready for market
            bird_inventory = inventory.filter(category__in=['live_birds', 'broilers', 'layers'])
            total_birds = bird_inventory.aggregate(
                total=Coalesce(Sum('quantity_available'), Decimal('0'))
            )['total']
            
            if total_birds and total_birds > 0:
                # Check oldest stock date for birds
                for item in bird_inventory:
                    if item.oldest_stock_date:
                        days_stocked = (timezone.now().date() - item.oldest_stock_date).days
                        if days_stocked > 60:  # Birds in stock > 2 months
                            total_score += 40
                            details.append(f'{int(total_birds)} birds ready for {days_stocked} days')
                        elif days_stocked > 30:
                            total_score += 20
                            details.append(f'{int(total_birds)} birds ready for {days_stocked} days')
            
            # Check capacity overstock
            capacity = farm.total_bird_capacity or 500
            current = farm.current_bird_count or 0
            if current > capacity:
                total_score += 20
                details.append(f'Overstocked: {current}/{capacity} birds')
            
            detail_str = '; '.join(details) if details else 'Inventory levels normal'
            return {'score': min(100, total_score), 'detail': detail_str}
            
        except Exception as e:
            logger.warning(f"Error calculating inventory stagnation for farm {farm.id}: {e}")
            return {'score': 30, 'detail': 'Error calculating inventory metrics'}
    
    def _score_sales_performance(self, farm):
        """
        Score: Declining or low sales compared to capacity.
        
        Metrics:
        - Days since last sale
        - Sales trend (30/60/90 day comparison)
        - Revenue vs operational costs
        - Order fulfillment rate
        """
        try:
            from sales_revenue.models import EggSale, BirdSale
            from sales_revenue.marketplace_models import MarketplaceOrder
            
            # Get sales in different periods
            now = timezone.now()
            thirty_days = now - timedelta(days=30)
            sixty_days = now - timedelta(days=60)
            ninety_days = now - timedelta(days=90)
            
            # Count sales in each period
            def count_sales(start_date, end_date=None):
                filters = {'farm': farm, 'sale_date__gte': start_date.date()}
                if end_date:
                    filters['sale_date__lt'] = end_date.date()
                
                egg_count = EggSale.objects.filter(**filters).count()
                bird_count = BirdSale.objects.filter(**{k.replace('sale_date', 'sale_date'): v for k, v in filters.items()}).count()
                
                # Marketplace orders use created_at
                mkt_filters = {'farm': farm, 'created_at__gte': start_date, 'status': 'completed'}
                if end_date:
                    mkt_filters['created_at__lt'] = end_date
                mkt_count = MarketplaceOrder.objects.filter(**mkt_filters).count()
                
                return egg_count + bird_count + mkt_count
            
            sales_30d = count_sales(thirty_days)
            sales_30_60 = count_sales(sixty_days, thirty_days)
            sales_60_90 = count_sales(ninety_days, sixty_days)
            sales_90d_total = sales_30d + sales_30_60 + sales_60_90
            
            # Find last sale date
            last_egg_sale = EggSale.objects.filter(farm=farm).order_by('-sale_date').first()
            last_bird_sale = BirdSale.objects.filter(farm=farm).order_by('-sale_date').first()
            last_mkt_order = MarketplaceOrder.objects.filter(
                farm=farm, status='completed'
            ).order_by('-created_at').first()
            
            last_sale_dates = []
            if last_egg_sale:
                last_sale_dates.append(last_egg_sale.sale_date)
            if last_bird_sale:
                last_sale_dates.append(last_bird_sale.sale_date)
            if last_mkt_order:
                last_sale_dates.append(last_mkt_order.created_at.date())
            
            days_since_sale = None
            if last_sale_dates:
                last_sale = max(last_sale_dates)
                days_since_sale = (timezone.now().date() - last_sale).days
            
            # Calculate score
            total_score = 0
            details = []
            
            # Days since last sale is critical
            if days_since_sale is None:
                total_score += 100
                details.append('No sales recorded')
            elif days_since_sale > 60:
                total_score += 90
                details.append(f'No sales in {days_since_sale} days')
            elif days_since_sale > 30:
                total_score += 60
                details.append(f'No sales in {days_since_sale} days')
            elif days_since_sale > 14:
                total_score += 30
                details.append(f'{days_since_sale} days since last sale')
            
            # Sales trend - declining is bad
            if sales_30_60 > 0 and sales_30d == 0:
                total_score += 30
                details.append('Sales dropped to zero this month')
            elif sales_60_90 > 0 and sales_30d + sales_30_60 == 0:
                total_score += 20
                details.append('No sales in 60 days')
            
            detail_str = '; '.join(details) if details else f'{sales_30d} sales in last 30 days'
            return {'score': min(100, total_score), 'detail': detail_str}
            
        except Exception as e:
            logger.warning(f"Error calculating sales performance for farm {farm.id}: {e}")
            return {'score': 50, 'detail': 'Error calculating sales metrics'}
    
    def _score_financial_stress(self, farm):
        """
        Score: Signs of financial difficulty.
        
        Metrics:
        - Outstanding payments owed to farmer
        - Days since last payment received
        - Subscription payment issues
        """
        try:
            from procurement.models import ProcurementInvoice
            from subscriptions.models import MarketplaceSubscription
            
            total_score = 0
            details = []
            
            # Check for pending procurement payments
            pending_payments = ProcurementInvoice.objects.filter(
                farm=farm,
                payment_status__in=['pending', 'approved']
            ).aggregate(
                total=Coalesce(Sum('total_amount'), Decimal('0')),
                count=Count('id')
            )
            
            pending_amount = pending_payments['total']
            pending_count = pending_payments['count']
            
            if pending_amount > 50000:  # > GHS 50,000 pending
                total_score += 80
                details.append(f'GHS {pending_amount:,.0f} in {pending_count} pending payments')
            elif pending_amount > 20000:
                total_score += 50
                details.append(f'GHS {pending_amount:,.0f} pending')
            elif pending_amount > 5000:
                total_score += 25
            
            # Check oldest pending payment
            oldest_pending = ProcurementInvoice.objects.filter(
                farm=farm,
                payment_status__in=['pending', 'approved']
            ).order_by('created_at').first()
            
            if oldest_pending:
                days_pending = (timezone.now() - oldest_pending.created_at).days
                if days_pending > 90:
                    total_score += 40
                    details.append(f'Payment pending {days_pending} days')
                elif days_pending > 60:
                    total_score += 25
                elif days_pending > 30:
                    total_score += 10
            
            # Check subscription status (failed payments = financial stress)
            sub = MarketplaceSubscription.objects.filter(farm=farm).first()
            if sub and not sub.is_active and sub.subscription_type != 'FREE':
                total_score += 30
                details.append('Marketplace subscription inactive')
            
            detail_str = '; '.join(details) if details else 'No financial stress indicators'
            return {'score': min(100, total_score), 'detail': detail_str}
            
        except Exception as e:
            logger.warning(f"Error calculating financial stress for farm {farm.id}: {e}")
            return {'score': 0, 'detail': 'Unable to assess financial status'}
    
    def _score_production_issues(self, farm):
        """
        Score: Struggling with production.
        
        Metrics:
        - High mortality rate
        - Low production rate vs capacity
        - Health incidents
        """
        try:
            from flock_management.models import MortalityRecord, Flock
            
            total_score = 0
            details = []
            
            # Get recent mortality
            recent_mortality = MortalityRecord.objects.filter(
                flock__farm=farm,
                date__gte=self.cutoff_date.date()
            ).aggregate(total=Coalesce(Sum('count'), 0))['total']
            
            # Get current flock size
            current_birds = farm.current_bird_count or 0
            capacity = farm.total_bird_capacity or 500
            
            if current_birds > 0:
                # Calculate mortality rate
                mortality_rate = (recent_mortality / (current_birds + recent_mortality)) * 100
                
                if mortality_rate > 10:  # >10% mortality is critical
                    total_score += 100
                    details.append(f'{mortality_rate:.1f}% mortality rate')
                elif mortality_rate > 5:
                    total_score += 60
                    details.append(f'{mortality_rate:.1f}% mortality rate')
                elif mortality_rate > 2:
                    total_score += 30
            
            # Check capacity utilization
            if capacity > 0:
                utilization = (current_birds / capacity) * 100
                if utilization < 20:  # Very underutilized
                    total_score += 40
                    details.append(f'Only {utilization:.0f}% capacity utilized')
                elif utilization > 100:  # Overstocked = stress
                    total_score += 30
                    details.append(f'Overstocked at {utilization:.0f}%')
            
            detail_str = '; '.join(details) if details else 'Production metrics normal'
            return {'score': min(100, total_score), 'detail': detail_str}
            
        except Exception as e:
            logger.warning(f"Error calculating production issues for farm {farm.id}: {e}")
            return {'score': 20, 'detail': 'Unable to assess production'}
    
    def _score_market_access(self, farm):
        """
        Score: Limited access to buyers.
        
        Metrics:
        - No marketplace subscription
        - Low customer base
        - Remote location
        - No previous government procurement
        """
        try:
            from sales_revenue.marketplace_models import Product
            from subscriptions.models import MarketplaceSubscription
            from sales_revenue.models import Customer
            from procurement.models import OrderAssignment
            
            total_score = 0
            details = []
            
            # Check marketplace subscription
            sub = MarketplaceSubscription.objects.filter(farm=farm, is_active=True).first()
            if not sub:
                total_score += 50
                details.append('No marketplace subscription')
            elif sub.subscription_type == 'FREE':
                total_score += 20
                details.append('On FREE marketplace tier')
            
            # Check product listings
            product_count = Product.objects.filter(farm=farm, status='active').count()
            if product_count == 0:
                total_score += 30
                details.append('No products listed')
            elif product_count < 3:
                total_score += 15
            
            # Check customer base
            customer_count = Customer.objects.filter(farm=farm, is_active=True).count()
            if customer_count == 0:
                total_score += 25
                details.append('No registered customers')
            elif customer_count < 5:
                total_score += 10
            
            # Check procurement history
            procurement_count = OrderAssignment.objects.filter(
                farm=farm,
                status__in=['verified', 'paid', 'completed']
            ).count()
            
            if procurement_count == 0:
                total_score += 15
                details.append('No previous government procurement')
            
            detail_str = '; '.join(details) if details else 'Good market access'
            return {'score': min(100, total_score), 'detail': detail_str}
            
        except Exception as e:
            logger.warning(f"Error calculating market access for farm {farm.id}: {e}")
            return {'score': 40, 'detail': 'Unable to assess market access'}
    
    def _get_sales_history(self, farm):
        """Get sales history summary for frontend display."""
        try:
            from sales_revenue.models import EggSale, BirdSale
            from sales_revenue.marketplace_models import MarketplaceOrder
            
            now = timezone.now()
            thirty_days = now - timedelta(days=30)
            ninety_days = now - timedelta(days=90)
            
            # Find last sale date
            last_egg_sale = EggSale.objects.filter(farm=farm).order_by('-sale_date').first()
            last_bird_sale = BirdSale.objects.filter(farm=farm).order_by('-sale_date').first()
            last_mkt_order = MarketplaceOrder.objects.filter(
                farm=farm, status='completed'
            ).order_by('-created_at').first()
            
            last_sale_dates = []
            if last_egg_sale:
                last_sale_dates.append(last_egg_sale.sale_date)
            if last_bird_sale:
                last_sale_dates.append(last_bird_sale.sale_date)
            if last_mkt_order:
                last_sale_dates.append(last_mkt_order.created_at.date())
            
            last_sale_date = max(last_sale_dates) if last_sale_dates else None
            days_since_sale = (now.date() - last_sale_date).days if last_sale_date else None
            
            # Get revenue totals
            sales_30d = EggSale.objects.filter(
                farm=farm, sale_date__gte=thirty_days.date()
            ).aggregate(total=Coalesce(Sum('subtotal'), Decimal('0')))['total']
            
            sales_30d += BirdSale.objects.filter(
                farm=farm, sale_date__gte=thirty_days.date()
            ).aggregate(total=Coalesce(Sum('subtotal'), Decimal('0')))['total']
            
            sales_30d += MarketplaceOrder.objects.filter(
                farm=farm, created_at__gte=thirty_days, status='completed'
            ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
            
            sales_90d = EggSale.objects.filter(
                farm=farm, sale_date__gte=ninety_days.date()
            ).aggregate(total=Coalesce(Sum('subtotal'), Decimal('0')))['total']
            
            sales_90d += BirdSale.objects.filter(
                farm=farm, sale_date__gte=ninety_days.date()
            ).aggregate(total=Coalesce(Sum('subtotal'), Decimal('0')))['total']
            
            sales_90d += MarketplaceOrder.objects.filter(
                farm=farm, created_at__gte=ninety_days, status='completed'
            ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
            
            return {
                'last_sale_date': last_sale_date.isoformat() if last_sale_date else None,
                'days_since_sale': days_since_sale,
                'total_sales_30d': float(sales_30d),
                'total_sales_90d': float(sales_90d),
            }
        except Exception as e:
            logger.warning(f"Error getting sales history for farm {farm.id}: {e}")
            return {
                'last_sale_date': None,
                'days_since_sale': None,
                'total_sales_30d': 0,
                'total_sales_90d': 0,
            }
    
    def _get_procurement_history(self, farm):
        """Get procurement history summary."""
        try:
            from procurement.models import OrderAssignment
            
            assignments = OrderAssignment.objects.filter(
                farm=farm,
                status__in=['verified', 'paid', 'completed']
            )
            
            total_orders = assignments.count()
            total_value = assignments.aggregate(
                total=Coalesce(Sum('total_value'), Decimal('0'))
            )['total']
            
            last_assignment = assignments.order_by('-assigned_at').first()
            last_date = last_assignment.assigned_at.date() if last_assignment else None
            
            return {
                'total_government_orders': total_orders,
                'last_procurement_date': last_date.isoformat() if last_date else None,
                'total_value_received': float(total_value),
            }
        except Exception as e:
            logger.warning(f"Error getting procurement history for farm {farm.id}: {e}")
            return {
                'total_government_orders': 0,
                'last_procurement_date': None,
                'total_value_received': 0,
            }
    
    def _get_capacity_info(self, farm):
        """Get farm capacity information."""
        try:
            from sales_revenue.inventory_models import FarmInventory
            
            # Get available stock from inventory
            inventory = FarmInventory.objects.filter(
                farm=farm,
                quantity_available__gt=0
            )
            
            available_for_sale = 0
            avg_weight = None
            
            for item in inventory:
                if item.category in ['live_birds', 'broilers', 'layers']:
                    available_for_sale += int(item.quantity_available)
                    # Try to get weight if tracked
                    if hasattr(item, 'average_weight_kg'):
                        avg_weight = float(item.average_weight_kg)
            
            # Fallback to current_bird_count if no inventory
            if available_for_sale == 0:
                available_for_sale = farm.current_bird_count or 0
            
            return {
                'total_birds': farm.total_bird_capacity or 0,
                'available_for_sale': available_for_sale,
                'average_weight_kg': avg_weight,
                'production_type': farm.primary_production_type,
            }
        except Exception as e:
            return {
                'total_birds': farm.total_bird_capacity or 0,
                'available_for_sale': farm.current_bird_count or 0,
                'average_weight_kg': None,
                'production_type': farm.primary_production_type,
            }
    
    def _get_coordinates(self, farm):
        """Get farm GPS coordinates if available."""
        try:
            from farms.models import FarmLocation
            
            location = FarmLocation.objects.filter(farm=farm).first()
            if location and location.coordinates:
                return [location.coordinates.y, location.coordinates.x]  # [lat, lng]
            return None
        except Exception:
            return None
    
    # =========================================================================
    # PUBLIC METHODS FOR VIEWS
    # =========================================================================
    
    def get_distressed_farmers(
        self,
        production_type=None,
        region=None,
        district=None,
        min_distress_score=0,
        min_capacity=None,
        has_available_stock=False,
        limit=50,
        ordering='-distress_score'
    ):
        """
        Get list of farmers sorted by distress score (highest first).
        
        Matches frontend specification for:
        GET /api/admin/procurement/farmers/distressed/
        
        Args:
            production_type: Filter by 'Broilers', 'Layers', or 'Both'
            region: Filter by region name
            district: Filter by district name
            min_distress_score: Minimum distress score to include (0-100)
            min_capacity: Minimum bird capacity
            has_available_stock: Only include farms with stock to sell
            limit: Maximum number of results
            ordering: Sort order ('-distress_score' default)
            
        Returns:
            dict with count, summary stats, and results list
        """
        # Base query: Active, approved farms
        farms = Farm.objects.filter(
            farm_status='Active',
            application_status='Approved - Farm ID Assigned'
        ).select_related('user')
        
        # Apply filters
        if production_type:
            if production_type in ['Broilers', 'BROILERS']:
                farms = farms.filter(primary_production_type__in=['Broilers', 'Both'])
            elif production_type in ['Layers', 'LAYERS']:
                farms = farms.filter(primary_production_type__in=['Layers', 'Both'])
        
        # Region filtering - since region is a derived property, we filter in Python
        # For performance, we should add a region field to the model in the future
        
        if district:
            farms = farms.filter(district__iexact=district)
        
        if min_capacity:
            farms = farms.filter(total_bird_capacity__gte=min_capacity)
        
        if has_available_stock:
            farms = farms.filter(current_bird_count__gt=0)
        
        # Calculate distress scores
        results = []
        for farm in farms:
            # Filter by region after fetching (since region is a property)
            if region and farm.region.lower() != region.lower():
                continue
                
            assessment = self.calculate_distress_score(farm)
            if assessment['distress_score'] >= min_distress_score:
                results.append(assessment)
        
        # Sort by distress score (highest first) by default
        reverse = ordering.startswith('-')
        sort_key = ordering.lstrip('-')
        
        if sort_key == 'distress_score':
            results.sort(key=lambda x: x['distress_score'], reverse=reverse)
        elif sort_key == 'farm_name':
            results.sort(key=lambda x: x['farm_name'], reverse=reverse)
        
        # Calculate summary stats
        all_scores = [r['distress_score'] for r in results]
        critical_count = sum(1 for s in all_scores if s >= 80)
        high_count = sum(1 for s in all_scores if 60 <= s < 80)
        moderate_count = sum(1 for s in all_scores if 40 <= s < 60)
        
        return {
            'count': len(results),
            'summary': {
                'total': len(results),
                'critical': critical_count,
                'high': high_count,
                'moderate': moderate_count,
            },
            'results': results[:limit],
        }
    
    def get_farms_for_order(self, order, limit=20):
        """
        Get farms prioritized by distress for a specific procurement order.
        
        Matches frontend specification for:
        GET /api/admin/procurement/orders/{order_id}/recommend-farms/
        
        Args:
            order: ProcurementOrder instance
            limit: Maximum farms to return
            
        Returns:
            dict with order info, recommendations, and summary
        """
        from procurement.models import OrderAssignment
        
        # Get eligible farms
        farms = Farm.objects.filter(
            farm_status='Active',
            application_status='Approved - Farm ID Assigned',
            current_bird_count__gt=0
        ).select_related('user')
        
        # Filter by production type
        if order.production_type == 'Broilers':
            farms = farms.filter(primary_production_type__in=['Broilers', 'Both'])
        elif order.production_type == 'Layers':
            farms = farms.filter(primary_production_type__in=['Layers', 'Both'])
        
        # Exclude already assigned farms
        assigned_farm_ids = OrderAssignment.objects.filter(
            order=order
        ).values_list('farm_id', flat=True)
        farms = farms.exclude(id__in=assigned_farm_ids)
        
        # Preferred region filter (optional)
        if order.preferred_region:
            # Prefer farms in region but don't exclude others
            farms = farms.annotate(
                region_match=Case(
                    When(region=order.preferred_region, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        
        # Calculate distress scores and build recommendations
        remaining_needed = order.quantity_needed - order.quantity_assigned
        recommendations = []
        
        for farm in farms:
            assessment = self.calculate_distress_score(farm)
            
            # Get available quantity
            available_qty = assessment['capacity']['available_for_sale']
            recommended_qty = min(available_qty, remaining_needed)
            
            recommendations.append({
                'farm_id': str(farm.id),
                'farm_name': farm.farm_name,
                'farmer_name': assessment['farmer_name'],
                
                # Distress info
                'distress_score': assessment['distress_score'],
                'distress_level': assessment['distress_level'],
                'priority_reason': assessment['distress_factors'][0]['detail'] if assessment['distress_factors'] else 'Available for procurement',
                
                # Capacity matching
                'available_quantity': available_qty,
                'recommended_quantity': recommended_qty,
                'capacity_match': available_qty >= remaining_needed,
                'location_match': hasattr(farm, 'region_match') and farm.region_match == 1,
                
                # Contact
                'contact': {
                    'phone': str(farm.primary_phone),
                    'region': farm.region,
                    'district': farm.district,
                },
                
                # Additional context
                'production_type': farm.primary_production_type,
                'sales_history': assessment['sales_history'],
                'procurement_history': assessment['procurement_history'],
            })
        
        # Sort by distress score (highest first)
        recommendations.sort(key=lambda x: x['distress_score'], reverse=True)
        recommendations = recommendations[:limit]
        
        # Calculate summary
        can_fulfill = sum(r['available_quantity'] for r in recommendations) >= remaining_needed
        critical_farms = sum(1 for r in recommendations if r['distress_level'] == 'CRITICAL')
        high_farms = sum(1 for r in recommendations if r['distress_level'] == 'HIGH')
        
        return {
            'order': {
                'id': str(order.id),
                'order_number': order.order_number,
                'title': order.title,
                'quantity_needed': order.quantity_needed,
                'quantity_assigned': order.quantity_assigned,
                'remaining_needed': remaining_needed,
                'production_type': order.production_type,
            },
            'recommendations': recommendations,
            'summary': {
                'total_farms': len(recommendations),
                'can_fulfill': can_fulfill,
                'critical_farms': critical_farms,
                'high_farms': high_farms,
                'total_available': sum(r['available_quantity'] for r in recommendations),
            },
        }
    
    def get_distress_summary(self, region=None):
        """
        Get overall distress summary for dashboard.
        
        Matches frontend specification for:
        GET /api/admin/procurement/distress-summary/
        
        Args:
            region: Optional region filter
            
        Returns:
            dict with overview, by_region, by_production_type, and trends
        """
        from procurement.models import OrderAssignment
        
        # Get all active farms
        farms = Farm.objects.filter(
            farm_status='Active',
            application_status='Approved - Farm ID Assigned'
        )
        
        if region:
            farms = farms.filter(region__iexact=region)
        
        # Calculate scores for all farms
        farm_scores = []
        for farm in farms:
            assessment = self.calculate_distress_score(farm)
            farm_scores.append({
                'farm': farm,
                'score': assessment['distress_score'],
                'level': assessment['distress_level'],
            })
        
        # Overview stats
        total_farms = len(farm_scores)
        distressed = [f for f in farm_scores if f['score'] >= 40]
        critical = [f for f in farm_scores if f['score'] >= 80]
        high = [f for f in farm_scores if 60 <= f['score'] < 80]
        moderate = [f for f in farm_scores if 40 <= f['score'] < 60]
        
        overview = {
            'total_registered_farms': total_farms,
            'farms_in_distress': len(distressed),
            'critical_distress': len(critical),
            'high_distress': len(high),
            'moderate_distress': len(moderate),
        }
        
        # By region breakdown
        region_stats = {}
        for fs in farm_scores:
            r = fs['farm'].region or 'Unknown'
            if r not in region_stats:
                region_stats[r] = {'total': 0, 'distressed': 0, 'critical': 0, 'scores': []}
            region_stats[r]['total'] += 1
            region_stats[r]['scores'].append(fs['score'])
            if fs['score'] >= 40:
                region_stats[r]['distressed'] += 1
            if fs['score'] >= 80:
                region_stats[r]['critical'] += 1
        
        by_region = [
            {
                'region': r,
                'total_farms': stats['total'],
                'distressed_farms': stats['distressed'],
                'critical': stats['critical'],
                'avg_distress_score': round(sum(stats['scores']) / len(stats['scores']), 1) if stats['scores'] else 0,
            }
            for r, stats in region_stats.items()
        ]
        by_region.sort(key=lambda x: x['distressed_farms'], reverse=True)
        
        # By production type breakdown
        type_stats = {}
        for fs in farm_scores:
            pt = fs['farm'].primary_production_type or 'Unknown'
            if pt not in type_stats:
                type_stats[pt] = {'total': 0, 'distressed': 0, 'scores': []}
            type_stats[pt]['total'] += 1
            type_stats[pt]['scores'].append(fs['score'])
            if fs['score'] >= 40:
                type_stats[pt]['distressed'] += 1
        
        by_production_type = [
            {
                'type': pt,
                'total_farms': stats['total'],
                'distressed_farms': stats['distressed'],
                'avg_distress_score': round(sum(stats['scores']) / len(stats['scores']), 1) if stats['scores'] else 0,
            }
            for pt, stats in type_stats.items()
        ]
        
        # Get trends (requires history - simplified for now)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Farmers helped = assignments made to distressed farmers
        # For now, count assignments in last 30 days
        recent_assignments = OrderAssignment.objects.filter(
            assigned_at__gte=thirty_days_ago,
            status__in=['accepted', 'verified', 'paid', 'completed']
        )
        
        farmers_helped = recent_assignments.values('farm').distinct().count()
        total_value = recent_assignments.aggregate(
            total=Coalesce(Sum('total_value'), Decimal('0'))
        )['total']
        
        trends = {
            'distress_trend_30d': 'N/A',  # Would need historical data
            'farmers_helped_30d': farmers_helped,
            'total_value_distributed': float(total_value),
        }
        
        return {
            'overview': overview,
            'by_region': by_region,
            'by_production_type': by_production_type,
            'trends': trends,
        }


# Convenience function
def get_distress_service(days_lookback=30):
    """Get an instance of the FarmerDistressService."""
    return FarmerDistressService(days_lookback=days_lookback)
