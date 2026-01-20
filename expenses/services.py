"""
Expense Services

Business logic for expense tracking, including smart cost calculations
that integrate feed consumption and medication/vaccination tracking data.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Optional, Tuple, Any
from django.db.models import Sum, Avg, F, Q
from django.db.models.functions import Coalesce


class BirdInvestmentCalculator:
    """
    Calculates the total investment (feed, medication, vaccination) per bird
    in a flock up to a specific date.
    
    This enables accurate mortality loss tracking by using actual tracked data
    rather than manual estimates.
    
    Example Usage:
        calculator = BirdInvestmentCalculator(flock)
        investment = calculator.calculate_investment_per_bird(mortality_date)
        
        # For mortality loss:
        feed_cost_invested = investment['feed_cost_per_bird'] * birds_lost
        other_costs_invested = investment['medication_cost_per_bird'] * birds_lost
    """
    
    def __init__(self, flock):
        """
        Initialize calculator with a flock.
        
        Args:
            flock: Flock model instance
        """
        self.flock = flock
        self.farm = flock.farm
    
    def calculate_investment_per_bird(
        self,
        up_to_date: date,
        include_acquisition: bool = False
    ) -> Dict[str, Decimal]:
        """
        Calculate cumulative cost invested per bird up to a specific date.
        
        This method aggregates:
        1. Feed costs from FeedConsumption records
        2. Medication costs from MedicationRecord
        3. Vaccination costs from VaccinationRecord
        4. Vet visit costs from VetVisit records
        
        The per-bird cost is calculated using the average bird count during
        the period to account for mortalities that occurred before the date.
        
        Args:
            up_to_date: Calculate costs up to and including this date
            include_acquisition: Whether to include acquisition cost per bird
            
        Returns:
            Dictionary with:
                - feed_cost_total: Total feed cost for flock up to date
                - feed_cost_per_bird: Feed cost per bird
                - medication_cost_total: Total medication cost
                - medication_cost_per_bird: Medication cost per bird
                - vaccination_cost_total: Total vaccination cost
                - vaccination_cost_per_bird: Vaccination cost per bird
                - vet_visit_cost_total: Total vet visit fees
                - vet_visit_cost_per_bird: Vet visit cost per bird
                - other_costs_total: medication + vaccination + vet visit total
                - other_costs_per_bird: medication + vaccination + vet visit per bird
                - total_investment_per_bird: All costs per bird
                - average_bird_count: Average birds during period
                - days_of_investment: Number of days costs accumulated
                - acquisition_cost_per_bird: (if include_acquisition=True)
        """
        from feed_inventory.models import FeedConsumption
        from medication_management.models import MedicationRecord, VaccinationRecord, VetVisit
        
        # Calculate the period from flock arrival to mortality date
        start_date = self.flock.arrival_date
        days_of_investment = (up_to_date - start_date).days + 1
        
        # Get feed costs up to the date
        feed_data = self._calculate_feed_costs(up_to_date)
        
        # Get medication costs up to the date
        medication_data = self._calculate_medication_costs(up_to_date)
        
        # Get vaccination costs up to the date
        vaccination_data = self._calculate_vaccination_costs(up_to_date)
        
        # Get vet visit costs up to the date
        vet_visit_data = self._calculate_vet_visit_costs(up_to_date)
        
        # Calculate average bird count during the period
        # This accounts for mortalities that reduced the flock over time
        average_bird_count = self._calculate_average_bird_count(start_date, up_to_date)
        
        # Avoid division by zero
        if average_bird_count <= 0:
            average_bird_count = self.flock.initial_count or 1
        
        # Calculate per-bird costs
        feed_cost_per_bird = feed_data['total'] / Decimal(str(average_bird_count))
        medication_cost_per_bird = medication_data['total'] / Decimal(str(average_bird_count))
        vaccination_cost_per_bird = vaccination_data['total'] / Decimal(str(average_bird_count))
        vet_visit_cost_per_bird = vet_visit_data['total'] / Decimal(str(average_bird_count))
        
        # Combined other costs (medication + vaccination + vet visits)
        other_costs_total = (
            medication_data['total'] + 
            vaccination_data['total'] + 
            vet_visit_data['total']
        )
        other_costs_per_bird = (
            medication_cost_per_bird + 
            vaccination_cost_per_bird + 
            vet_visit_cost_per_bird
        )
        
        total_investment_per_bird = feed_cost_per_bird + other_costs_per_bird
        
        result = {
            # Feed costs
            'feed_cost_total': feed_data['total'],
            'feed_cost_per_bird': feed_cost_per_bird.quantize(Decimal('0.01')),
            'feed_consumption_kg': feed_data['quantity_kg'],
            
            # Medication costs
            'medication_cost_total': medication_data['total'],
            'medication_cost_per_bird': medication_cost_per_bird.quantize(Decimal('0.01')),
            'medication_records_count': medication_data['count'],
            
            # Vaccination costs
            'vaccination_cost_total': vaccination_data['total'],
            'vaccination_cost_per_bird': vaccination_cost_per_bird.quantize(Decimal('0.01')),
            'vaccination_records_count': vaccination_data['count'],
            
            # Vet visit costs
            'vet_visit_cost_total': vet_visit_data['total'],
            'vet_visit_cost_per_bird': vet_visit_cost_per_bird.quantize(Decimal('0.01')),
            'vet_visit_records_count': vet_visit_data['count'],
            
            # Combined other costs (medication + vaccination + vet visits)
            'other_costs_total': other_costs_total,
            'other_costs_per_bird': other_costs_per_bird.quantize(Decimal('0.01')),
            
            # Total investment
            'total_investment_per_bird': total_investment_per_bird.quantize(Decimal('0.01')),
            
            # Context
            'average_bird_count': average_bird_count,
            'days_of_investment': days_of_investment,
            'calculation_start_date': start_date.isoformat(),
            'calculation_end_date': up_to_date.isoformat(),
        }
        
        # Optionally include acquisition cost
        if include_acquisition:
            acquisition_cost = self.flock.purchase_price_per_bird or Decimal('0.00')
            result['acquisition_cost_per_bird'] = acquisition_cost
            result['total_investment_per_bird'] = (
                total_investment_per_bird + acquisition_cost
            ).quantize(Decimal('0.01'))
        
        return result
    
    def calculate_mortality_loss(
        self,
        mortality_date: date,
        birds_lost: int,
        acquisition_cost_per_bird: Optional[Decimal] = None,
        potential_revenue_per_bird: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calculate the total economic loss from a mortality event.
        
        Uses actual tracked data to compute feed and medication costs invested
        in the birds that died.
        
        Args:
            mortality_date: Date when birds died
            birds_lost: Number of birds lost
            acquisition_cost_per_bird: Cost per bird (defaults to flock's purchase price)
            potential_revenue_per_bird: Expected revenue if bird had been sold (optional)
            
        Returns:
            Dictionary with all calculated loss values ready for MortalityLossRecord
        """
        # Get investment breakdown
        investment = self.calculate_investment_per_bird(mortality_date, include_acquisition=False)
        
        # Use provided or default acquisition cost
        if acquisition_cost_per_bird is None:
            acquisition_cost_per_bird = self.flock.purchase_price_per_bird or Decimal('0.00')
        
        # Calculate losses
        acquisition_loss = acquisition_cost_per_bird * birds_lost
        feed_cost_invested = investment['feed_cost_per_bird'] * birds_lost
        other_costs_invested = investment['other_costs_per_bird'] * birds_lost
        
        # Calculate potential revenue lost (if provided)
        potential_revenue_lost = Decimal('0.00')
        if potential_revenue_per_bird:
            potential_revenue_lost = potential_revenue_per_bird * birds_lost
        
        # Total economic loss (includes acquisition - for insurance claims, full analysis)
        total_loss_value = acquisition_loss + feed_cost_invested + other_costs_invested
        
        # Additional investment value (excludes acquisition - for expense tracking)
        # This prevents double-counting since acquisition was already recorded when flock purchased
        additional_investment_value = feed_cost_invested + other_costs_invested
        
        # Calculate age at death
        age_at_death_weeks = self._calculate_age_at_date(mortality_date)
        
        return {
            # Values for MortalityLossRecord
            'acquisition_cost_per_bird': acquisition_cost_per_bird.quantize(Decimal('0.01')),
            'feed_cost_invested': feed_cost_invested.quantize(Decimal('0.01')),
            'other_costs_invested': other_costs_invested.quantize(Decimal('0.01')),
            'potential_revenue_lost': potential_revenue_lost.quantize(Decimal('0.01')),
            'total_loss_value': total_loss_value.quantize(Decimal('0.01')),
            'additional_investment_value': additional_investment_value.quantize(Decimal('0.01')),
            'age_at_death_weeks': age_at_death_weeks,
            
            # Breakdown for transparency
            'breakdown': {
                'acquisition_loss': acquisition_loss.quantize(Decimal('0.01')),
                'feed_cost_per_bird': investment['feed_cost_per_bird'],
                'medication_cost_per_bird': investment['medication_cost_per_bird'],
                'vaccination_cost_per_bird': investment['vaccination_cost_per_bird'],
                'average_bird_count_in_period': investment['average_bird_count'],
                'days_investment_period': investment['days_of_investment'],
            },
            
            # Data source info
            'data_sources': {
                'feed_consumption_kg': investment['feed_consumption_kg'],
                'medication_records_count': investment['medication_records_count'],
                'vaccination_records_count': investment['vaccination_records_count'],
            },
            
            # Accounting guidance
            'accounting_note': (
                'total_loss_value includes acquisition cost (for insurance claims, economic analysis). '
                'additional_investment_value excludes acquisition (for expense tracking to avoid double-counting).'
            )
        }
    
    def _calculate_feed_costs(self, up_to_date: date) -> Dict[str, Decimal]:
        """
        Calculate total feed costs from FeedConsumption records.
        
        Falls back to DailyProduction.feed_cost_today if FeedConsumption
        records don't exist (for backward compatibility).
        """
        from feed_inventory.models import FeedConsumption
        from flock_management.models import DailyProduction
        
        # Try FeedConsumption records first (more detailed)
        feed_aggregates = FeedConsumption.objects.filter(
            flock=self.flock,
            date__lte=up_to_date
        ).aggregate(
            total_cost=Coalesce(Sum('total_cost'), Decimal('0.00')),
            total_quantity=Coalesce(Sum('quantity_consumed_kg'), Decimal('0.00'))
        )
        
        if feed_aggregates['total_cost'] > 0:
            return {
                'total': feed_aggregates['total_cost'],
                'quantity_kg': feed_aggregates['total_quantity']
            }
        
        # Fallback: Use DailyProduction.feed_cost_today
        # Note: DailyProduction uses 'production_date' field
        daily_feed = DailyProduction.objects.filter(
            flock=self.flock,
            production_date__lte=up_to_date
        ).aggregate(
            total_cost=Coalesce(Sum('feed_cost_today'), Decimal('0.00')),
            total_quantity=Coalesce(Sum('feed_consumed_kg'), Decimal('0.00'))
        )
        
        return {
            'total': daily_feed['total_cost'],
            'quantity_kg': daily_feed['total_quantity']
        }
    
    def _calculate_medication_costs(self, up_to_date: date) -> Dict[str, Any]:
        """Calculate total medication costs from MedicationRecord."""
        from medication_management.models import MedicationRecord
        
        medication_data = MedicationRecord.objects.filter(
            flock=self.flock,
            administered_date__lte=up_to_date
        ).aggregate(
            total_cost=Coalesce(Sum('total_cost'), Decimal('0.00')),
            count=Coalesce(Sum(1), 0)
        )
        
        # Count manually since Sum(1) doesn't work as expected
        count = MedicationRecord.objects.filter(
            flock=self.flock,
            administered_date__lte=up_to_date
        ).count()
        
        return {
            'total': medication_data['total_cost'],
            'count': count
        }
    
    def _calculate_vaccination_costs(self, up_to_date: date) -> Dict[str, Any]:
        """Calculate total vaccination costs from VaccinationRecord."""
        from medication_management.models import VaccinationRecord
        
        vaccination_data = VaccinationRecord.objects.filter(
            flock=self.flock,
            vaccination_date__lte=up_to_date
        ).aggregate(
            total_cost=Coalesce(Sum('total_cost'), Decimal('0.00'))
        )
        
        count = VaccinationRecord.objects.filter(
            flock=self.flock,
            vaccination_date__lte=up_to_date
        ).count()
        
        return {
            'total': vaccination_data['total_cost'],
            'count': count
        }
    
    def _calculate_vet_visit_costs(self, up_to_date: date) -> Dict[str, Any]:
        """
        Calculate total vet visit costs from VetVisit records.
        
        Only includes completed visits to the specific flock.
        This ensures we only count actual costs, not scheduled visits.
        """
        from medication_management.models import VetVisit
        
        # Only count completed visits to this specific flock
        vet_visit_data = VetVisit.objects.filter(
            flock=self.flock,
            visit_date__lte=up_to_date,
            status='COMPLETED'
        ).aggregate(
            total_cost=Coalesce(Sum('visit_fee'), Decimal('0.00'))
        )
        
        count = VetVisit.objects.filter(
            flock=self.flock,
            visit_date__lte=up_to_date,
            status='COMPLETED'
        ).count()
        
        return {
            'total': vet_visit_data['total_cost'],
            'count': count
        }
    
    def _calculate_average_bird_count(self, start_date: date, end_date: date) -> int:
        """
        Calculate the average bird count during a period.
        
        Uses mortality records to track the declining bird count over time.
        Returns a weighted average based on days at each count level.
        """
        from flock_management.models import MortalityRecord
        
        # Get all mortality events in the period
        # MortalityRecord uses 'date_discovered' for the date field
        mortalities = MortalityRecord.objects.filter(
            flock=self.flock,
            date_discovered__lte=end_date
        ).order_by('date_discovered')
        
        if not mortalities.exists():
            # No mortality - average is just initial count
            return self.flock.initial_count
        
        # Build a timeline of bird counts
        timeline = []
        current_count = self.flock.initial_count
        current_date = start_date
        
        for mortality in mortalities:
            if mortality.date_discovered > end_date:
                break
                
            # Days at current count before this mortality
            if mortality.date_discovered > current_date:
                days = (mortality.date_discovered - current_date).days
                timeline.append((days, current_count))
                current_date = mortality.date_discovered
            
            # Reduce count (MortalityRecord uses 'number_of_birds' not 'count')
            current_count -= mortality.number_of_birds
            current_count = max(current_count, 0)
        
        # Add remaining days at final count
        if current_date <= end_date:
            days = (end_date - current_date).days + 1
            timeline.append((days, current_count))
        
        # Calculate weighted average
        if not timeline:
            return self.flock.initial_count
        
        total_bird_days = sum(days * count for days, count in timeline)
        total_days = sum(days for days, count in timeline)
        
        if total_days == 0:
            return self.flock.initial_count
        
        return int(total_bird_days / total_days)
    
    def _calculate_age_at_date(self, target_date: date) -> Decimal:
        """Calculate flock age in weeks at a given date."""
        # Age at arrival (in weeks)
        age_at_arrival = self.flock.age_at_arrival_weeks or Decimal('0')
        
        # Days since arrival
        days_since_arrival = (target_date - self.flock.arrival_date).days
        
        # Convert to weeks and add to arrival age
        weeks_since_arrival = Decimal(str(days_since_arrival)) / Decimal('7')
        
        return (age_at_arrival + weeks_since_arrival).quantize(Decimal('0.1'))


def calculate_mortality_loss_from_record(
    mortality_record,
    potential_revenue_per_bird: Optional[Decimal] = None
) -> Dict[str, Any]:
    """
    Convenience function to calculate mortality loss from a MortalityRecord instance.
    
    Args:
        mortality_record: MortalityRecord model instance
        potential_revenue_per_bird: Expected revenue if bird had been sold
        
    Returns:
        Dictionary with all calculated loss values
    """
    calculator = BirdInvestmentCalculator(mortality_record.flock)
    return calculator.calculate_mortality_loss(
        mortality_date=mortality_record.date,
        birds_lost=mortality_record.count,
        potential_revenue_per_bird=potential_revenue_per_bird
    )


def get_flock_investment_summary(flock, as_of_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Get a summary of all investments made in a flock.
    
    Args:
        flock: Flock model instance
        as_of_date: Date to calculate up to (defaults to today)
        
    Returns:
        Investment summary dictionary
    """
    from django.utils import timezone
    
    if as_of_date is None:
        as_of_date = timezone.now().date()
    
    calculator = BirdInvestmentCalculator(flock)
    investment = calculator.calculate_investment_per_bird(as_of_date, include_acquisition=True)
    
    return {
        'flock_id': str(flock.id),
        'flock_number': flock.flock_number,
        'breed': flock.breed,
        'current_count': flock.current_count,
        'initial_count': flock.initial_count,
        'as_of_date': as_of_date.isoformat(),
        'investment': investment,
        'total_flock_investment': (
            Decimal(str(investment['total_investment_per_bird'])) * 
            Decimal(str(flock.current_count))
        ).quantize(Decimal('0.01'))
    }
