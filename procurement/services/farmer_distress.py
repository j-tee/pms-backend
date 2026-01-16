"""
Farmer Distress Scoring Service

Calculates a "distress score" for farmers to help government officers
prioritize purchasing from farmers who are struggling the most.

DISTRESS INDICATORS:
1. High unsold inventory (eggs aging, birds overstocked)
2. Low/no marketplace sales activity
3. Recent mortality events (flock health issues)
4. Low marketplace engagement (not using platform)
5. Financial stress signals (missed targets)
6. Geographic isolation (rural areas)

SCORE RANGES:
- 0-25: Healthy (selling well, low inventory)
- 26-50: Moderate (some concerns)
- 51-75: High Distress (needs attention)
- 76-100: Critical (urgent intervention needed)

PRIORITY FOR PROCUREMENT:
Higher distress score = Higher priority for government purchases
"""

from django.db.models import Q, Sum, Avg, Count, F, Value, Case, When, IntegerField
from django.db.models.functions import Coalesce, Now, ExtractDay
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

from farms.models import Farm

logger = logging.getLogger(__name__)


class FarmerDistressService:
    """
    Service for calculating and retrieving farmer distress scores.
    
    The distress score helps government officers identify farmers who
    need the most help selling their products.
    """
    
    # Scoring weights (total = 100)
    WEIGHTS = {
        'inventory_aging': 25,       # Unsold inventory aging
        'sales_activity': 25,        # Recent sales activity
        'mortality_rate': 15,        # Recent bird mortality
        'marketplace_engagement': 15, # Platform usage
        'capacity_utilization': 10,  # Overstocking risk
        'payment_history': 10,       # Financial health
    }
    
    def __init__(self, days_lookback=30):
        """
        Initialize the distress service.
        
        Args:
            days_lookback: Number of days to analyze for activity metrics
        """
        self.days_lookback = days_lookback
        self.cutoff_date = timezone.now() - timedelta(days=days_lookback)
    
    def calculate_distress_score(self, farm):
        """
        Calculate comprehensive distress score for a single farm.
        
        Args:
            farm: Farm instance
            
        Returns:
            dict with score breakdown and recommendations
        """
        scores = {
            'inventory_aging': self._score_inventory_aging(farm),
            'sales_activity': self._score_sales_activity(farm),
            'mortality_rate': self._score_mortality_rate(farm),
            'marketplace_engagement': self._score_marketplace_engagement(farm),
            'capacity_utilization': self._score_capacity_utilization(farm),
            'payment_history': self._score_payment_history(farm),
        }
        
        # Calculate weighted total
        total_score = sum(
            scores[key] * (self.WEIGHTS[key] / 100)
            for key in scores
        )
        
        # Determine distress level
        if total_score >= 76:
            distress_level = 'critical'
            priority = 'urgent'
        elif total_score >= 51:
            distress_level = 'high'
            priority = 'high'
        elif total_score >= 26:
            distress_level = 'moderate'
            priority = 'normal'
        else:
            distress_level = 'healthy'
            priority = 'low'
        
        # Generate recommendations
        recommendations = self._generate_recommendations(scores, farm)
        
        return {
            'farm_id': str(farm.id),
            'farm_name': farm.farm_name,
            'farmer_name': farm.user.get_full_name() if farm.user else 'N/A',
            'total_score': round(total_score, 1),
            'distress_level': distress_level,
            'priority': priority,
            'score_breakdown': {
                key: {
                    'score': round(scores[key], 1),
                    'weight': self.WEIGHTS[key],
                    'weighted_contribution': round(scores[key] * (self.WEIGHTS[key] / 100), 1)
                }
                for key in scores
            },
            'recommendations': recommendations,
            'available_inventory': self._get_available_inventory(farm),
            'contact': {
                'phone': str(farm.primary_phone),
                'region': farm.region,
                'district': farm.district,
                'constituency': farm.primary_constituency,
            }
        }
    
    def _score_inventory_aging(self, farm):
        """
        Score based on unsold inventory and aging.
        Higher score = more distress (older/more inventory)
        
        Factors:
        - Days since oldest stock
        - Quantity of aging inventory
        - Egg freshness (critical for layers)
        """
        try:
            from sales_revenue.inventory_models import FarmInventory
            
            inventory = FarmInventory.objects.filter(farm=farm)
            
            if not inventory.exists():
                return 50  # No inventory data = moderate concern
            
            total_score = 0
            
            # Check for aging eggs (critical - eggs expire quickly)
            egg_inventory = inventory.filter(category='eggs')
            for item in egg_inventory:
                if item.oldest_stock_date:
                    days_old = (timezone.now().date() - item.oldest_stock_date).days
                    if days_old > 21:  # Eggs older than 3 weeks
                        total_score += 40
                    elif days_old > 14:
                        total_score += 25
                    elif days_old > 7:
                        total_score += 10
                
                # Large unsold egg quantity
                if item.quantity_available > 100:  # More than 100 crates
                    total_score += 20
            
            # Check for overstocked birds
            bird_inventory = inventory.filter(category__in=['live_birds', 'broilers', 'layers'])
            total_birds = bird_inventory.aggregate(total=Coalesce(Sum('quantity_available'), Decimal('0')))['total']
            
            if total_birds:
                capacity = farm.total_bird_capacity or 500
                utilization = (float(total_birds) / capacity) * 100
                if utilization > 100:  # Overstocked
                    total_score += 30
                elif utilization > 85:
                    total_score += 15
            
            return min(100, total_score)
            
        except Exception as e:
            logger.warning(f"Error calculating inventory aging score for farm {farm.id}: {e}")
            return 30  # Default moderate score on error
    
    def _score_sales_activity(self, farm):
        """
        Score based on recent sales activity.
        Higher score = less sales (more distress)
        """
        try:
            from sales_revenue.models import EggSale, BirdSale
            from sales_revenue.marketplace_models import MarketplaceOrder
            
            # Count sales in lookback period
            egg_sales = EggSale.objects.filter(
                farm=farm,
                sale_date__gte=self.cutoff_date.date()
            ).count()
            
            bird_sales = BirdSale.objects.filter(
                farm=farm,
                sale_date__gte=self.cutoff_date.date()
            ).count()
            
            marketplace_orders = MarketplaceOrder.objects.filter(
                farm=farm,
                created_at__gte=self.cutoff_date,
                status='completed'
            ).count()
            
            total_sales = egg_sales + bird_sales + marketplace_orders
            
            # Score: No sales = 100, many sales = 0
            if total_sales == 0:
                return 100
            elif total_sales <= 2:
                return 75
            elif total_sales <= 5:
                return 50
            elif total_sales <= 10:
                return 25
            else:
                return 0
                
        except Exception as e:
            logger.warning(f"Error calculating sales activity score for farm {farm.id}: {e}")
            return 50
    
    def _score_mortality_rate(self, farm):
        """
        Score based on recent bird mortality.
        Higher score = more mortality (distress indicator)
        """
        try:
            from flock_management.models import MortalityRecord, Flock
            
            # Get recent mortality
            recent_mortality = MortalityRecord.objects.filter(
                flock__farm=farm,
                date__gte=self.cutoff_date.date()
            ).aggregate(total=Coalesce(Sum('count'), 0))['total']
            
            # Get current flock size
            current_birds = farm.current_bird_count or 0
            
            if current_birds == 0:
                return 0  # No birds = no mortality concern
            
            # Calculate mortality rate
            mortality_rate = (recent_mortality / (current_birds + recent_mortality)) * 100
            
            if mortality_rate > 10:  # >10% mortality is critical
                return 100
            elif mortality_rate > 5:
                return 70
            elif mortality_rate > 2:
                return 40
            else:
                return 0
                
        except Exception as e:
            logger.warning(f"Error calculating mortality score for farm {farm.id}: {e}")
            return 20
    
    def _score_marketplace_engagement(self, farm):
        """
        Score based on marketplace platform usage.
        Higher score = less engagement (may not know how to sell)
        """
        try:
            from sales_revenue.marketplace_models import Product
            from subscriptions.models import MarketplaceSubscription
            
            # Check if farm has marketplace subscription
            has_subscription = MarketplaceSubscription.objects.filter(
                farm=farm,
                is_active=True
            ).exists()
            
            # Check if farm has products listed
            product_count = Product.objects.filter(
                farm=farm,
                status='active'
            ).count()
            
            # Score
            if not has_subscription:
                return 80  # Not on marketplace = high concern
            elif product_count == 0:
                return 60  # On marketplace but no listings
            elif product_count < 3:
                return 30  # Few listings
            else:
                return 0  # Good engagement
                
        except Exception as e:
            logger.warning(f"Error calculating marketplace engagement for farm {farm.id}: {e}")
            return 40
    
    def _score_capacity_utilization(self, farm):
        """
        Score based on capacity utilization.
        Too high = overstocking risk, too low = underperforming
        """
        capacity = farm.total_bird_capacity or 0
        current = farm.current_bird_count or 0
        
        if capacity == 0:
            return 50  # Unknown capacity
        
        utilization = (current / capacity) * 100
        
        if utilization > 100:  # Overstocked
            return 100
        elif utilization > 90:  # Near capacity - might have trouble selling
            return 60
        elif utilization < 20:  # Very underutilized - might be struggling
            return 40
        else:
            return 0  # Healthy utilization
    
    def _score_payment_history(self, farm):
        """
        Score based on financial indicators.
        """
        try:
            from procurement.models import ProcurementInvoice
            
            # Check for pending payments (government owes them = might be in distress)
            pending_payments = ProcurementInvoice.objects.filter(
                farm=farm,
                payment_status__in=['pending', 'approved']
            ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
            
            if pending_payments > 50000:  # > GHS 50,000 pending
                return 60
            elif pending_payments > 20000:
                return 40
            elif pending_payments > 5000:
                return 20
            else:
                return 0
                
        except Exception as e:
            return 0
    
    def _generate_recommendations(self, scores, farm):
        """Generate actionable recommendations based on scores."""
        recommendations = []
        
        if scores['inventory_aging'] >= 50:
            recommendations.append({
                'category': 'inventory',
                'priority': 'high',
                'action': 'Purchase aging inventory immediately',
                'reason': 'Farm has significant aging stock that may spoil'
            })
        
        if scores['sales_activity'] >= 75:
            recommendations.append({
                'category': 'sales',
                'priority': 'high',
                'action': 'Prioritize this farm for procurement orders',
                'reason': 'Farm has had little to no sales activity recently'
            })
        
        if scores['mortality_rate'] >= 50:
            recommendations.append({
                'category': 'health',
                'priority': 'medium',
                'action': 'Dispatch veterinary officer for health check',
                'reason': 'Farm is experiencing higher than normal mortality rates'
            })
        
        if scores['marketplace_engagement'] >= 60:
            recommendations.append({
                'category': 'training',
                'priority': 'medium',
                'action': 'Extension officer to assist with marketplace onboarding',
                'reason': 'Farm is not utilizing marketplace platform effectively'
            })
        
        return recommendations
    
    def _get_available_inventory(self, farm):
        """Get summary of available inventory for procurement."""
        try:
            from sales_revenue.inventory_models import FarmInventory
            
            inventory = FarmInventory.objects.filter(
                farm=farm,
                quantity_available__gt=0
            )
            
            return [
                {
                    'category': item.category,
                    'product_name': item.product_name,
                    'quantity': float(item.quantity_available),
                    'unit': item.unit,
                    'days_old': (timezone.now().date() - item.oldest_stock_date).days if item.oldest_stock_date else None,
                }
                for item in inventory
            ]
        except Exception:
            return []
    
    def get_distressed_farmers(self, production_type=None, region=None, min_score=50, limit=50):
        """
        Get list of farmers sorted by distress score (highest first).
        
        Args:
            production_type: Filter by 'Broilers', 'Layers', or 'Both'
            region: Filter by region name
            min_score: Minimum distress score to include
            limit: Maximum number of results
            
        Returns:
            List of farm distress assessments
        """
        # Base query: Active, approved farms
        farms = Farm.objects.filter(
            farm_status='Active',
            application_status='Approved - Farm ID Assigned'
        ).select_related('user')
        
        # Apply filters
        if production_type:
            if production_type == 'Broilers':
                farms = farms.filter(primary_production_type__in=['Broilers', 'Both'])
            elif production_type == 'Layers':
                farms = farms.filter(primary_production_type__in=['Layers', 'Both'])
        
        if region:
            farms = farms.filter(region=region)
        
        # Calculate distress scores
        results = []
        for farm in farms:
            assessment = self.calculate_distress_score(farm)
            if assessment['total_score'] >= min_score:
                results.append(assessment)
        
        # Sort by distress score (highest first)
        results.sort(key=lambda x: x['total_score'], reverse=True)
        
        return results[:limit]
    
    def get_farms_for_procurement_priority(self, order, limit=20):
        """
        Get farms prioritized by distress for a specific procurement order.
        
        This is the main method used by the procurement workflow to
        recommend farms based on who needs help the most.
        
        Args:
            order: ProcurementOrder instance
            limit: Maximum farms to return
            
        Returns:
            List of (farm, distress_score, recommended_quantity) tuples
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
        
        # Preferred region gets a boost but doesn't exclude others
        if order.preferred_region:
            farms = farms.annotate(
                region_match=Case(
                    When(region=order.preferred_region, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        
        # Calculate distress scores and available quantity
        results = []
        remaining_needed = order.quantity_needed - order.quantity_assigned
        
        for farm in farms:
            assessment = self.calculate_distress_score(farm)
            
            # Calculate available quantity from farm
            available_qty = farm.current_bird_count or 0
            recommended_qty = min(available_qty, remaining_needed)
            
            results.append({
                'farm': farm,
                'distress_score': assessment['total_score'],
                'distress_level': assessment['distress_level'],
                'recommended_quantity': recommended_qty,
                'available_quantity': available_qty,
                'region_match': hasattr(farm, 'region_match') and farm.region_match == 1,
                'contact': assessment['contact'],
                'recommendations': assessment['recommendations'],
            })
        
        # Sort by distress score (highest first), then by region match
        results.sort(key=lambda x: (x['distress_score'], x.get('region_match', False)), reverse=True)
        
        return results[:limit]


# Convenience function
def get_distress_service(days_lookback=30):
    """Get an instance of the FarmerDistressService."""
    return FarmerDistressService(days_lookback=days_lookback)
