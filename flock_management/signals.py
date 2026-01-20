"""
Flock Management Signals

Automatic actions triggered by flock-related model events.

UNIFIED DATA ENTRY SIGNALS:
1. MortalityRecord → auto-creates MortalityLossRecord (Expense)
2. HealthRecord → auto-creates MedicationRecord, VaccinationRecord, or VetVisit

This UNIFIES the user experience:
- User records data in ONE place (Flock Management)
- Detailed tracking records are AUTOMATICALLY created
- No duplicate data entry required
- Prevents double-counting of costs
"""

import logging
from decimal import Decimal
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(post_save, sender='flock_management.MortalityRecord')
def auto_create_mortality_expense(sender, instance, created, **kwargs):
    """
    Automatically create a MortalityLossRecord (expense) when a MortalityRecord is created.
    
    This eliminates the confusing dual-entry requirement where users had to:
    1. Record mortality in Flock Management
    2. THEN manually create an expense record in Expense Tracking
    
    Now:
    1. User records mortality in Flock Management (single entry point)
    2. System automatically creates the financial record with smart calculations
    
    The expense record:
    - Links to the source MortalityRecord
    - Uses BirdInvestmentCalculator for accurate cost calculation
    - Sets costs_auto_calculated=True to indicate values came from tracked data
    
    Note: Only creates expense if no linked MortalityLossRecord already exists.
    """
    if not created:
        # Only create expense for NEW mortality records
        return
    
    # Check if this mortality record already has a linked expense
    if hasattr(instance, 'loss_records') and instance.loss_records.exists():
        logger.debug(f"MortalityRecord {instance.id} already has expense record(s), skipping auto-creation")
        return
    
    try:
        # Import here to avoid circular imports
        from expenses.models import Expense, MortalityLossRecord
        from expenses.services import BirdInvestmentCalculator
        
        # Calculate the loss using our smart calculator
        # BirdInvestmentCalculator takes flock, not farm
        calculator = BirdInvestmentCalculator(instance.flock)
        loss_calculation = calculator.calculate_mortality_loss(
            mortality_date=instance.date_discovered,
            birds_lost=instance.number_of_birds,
            acquisition_cost_per_bird=instance.estimated_value_per_bird or Decimal('0'),
        )
        
        # Determine the total amount for the expense
        # Use total_loss_value for full economic loss
        total_amount = loss_calculation['total_loss_value']
        
        # Create expense and mortality loss record in a transaction
        with transaction.atomic():
            # Create the parent Expense record
            expense = Expense.objects.create(
                farm=instance.farm,
                flock=instance.flock,  # Link to the flock for cost tracking
                category='MORTALITY_LOSS',
                description=f"Mortality loss: {instance.number_of_birds} birds from {instance.flock.flock_number}",
                expense_date=instance.date_discovered,
                quantity=instance.number_of_birds,
                unit='birds',
                unit_cost=loss_calculation['total_loss_value'] / instance.number_of_birds if instance.number_of_birds > 0 else Decimal('0'),
                total_amount=total_amount,
                payment_status='N/A',
                payment_method='N/A',
                payee_name='N/A - Loss',
                notes=f"Auto-created from mortality record. Cause: {instance.probable_cause}",
                created_by=instance.reported_by,
            )
            
            # Create the detailed MortalityLossRecord
            MortalityLossRecord.objects.create(
                expense=expense,
                farm=instance.farm,
                flock=instance.flock,
                mortality_record=instance,  # Link to the source record!
                mortality_date=instance.date_discovered,
                birds_lost=instance.number_of_birds,
                cause_of_death=instance.probable_cause,
                
                # Cost breakdown from calculator
                acquisition_cost_per_bird=loss_calculation['acquisition_cost_per_bird'],
                feed_cost_invested=loss_calculation['feed_cost_invested'],
                other_costs_invested=loss_calculation['other_costs_invested'],
                
                # Calculated totals
                total_loss_value=loss_calculation['total_loss_value'],
                additional_investment_value=loss_calculation['additional_investment_value'],
                age_at_death_weeks=loss_calculation['age_at_death_weeks'],
                
                # Mark as auto-calculated
                costs_auto_calculated=True,
            )
            
            logger.info(
                f"Auto-created expense record for MortalityRecord {instance.id}: "
                f"{instance.number_of_birds} birds, total loss: GHS {total_amount}"
            )
    
    except Exception as e:
        # Log error but don't fail the mortality record creation
        logger.error(
            f"Failed to auto-create expense for MortalityRecord {instance.id}: {str(e)}",
            exc_info=True
        )
        # Don't raise - we don't want to block mortality record creation
        # Users can still manually create expense record if needed


# =============================================================================
# HEALTH RECORD → DETAILED RECORDS AUTO-CREATION
# =============================================================================

@receiver(post_save, sender='flock_management.HealthRecord')
def auto_create_detailed_health_record(sender, instance, created, **kwargs):
    """
    Automatically create detailed medication_management records from HealthRecord.
    
    This eliminates the confusing dual-entry requirement where users could enter
    health costs in BOTH:
    - HealthRecord.cost_ghs (simple form in Flock Management)
    - MedicationRecord/VaccinationRecord/VetVisit (detailed forms in Medication Management)
    
    Now:
    1. User enters data via the simple HealthRecord form (single entry point)
    2. System automatically creates the appropriate detailed record
    3. BirdInvestmentCalculator uses detailed records (no double-counting)
    
    Record type mapping:
    - "Vaccination" → VaccinationRecord
    - "Medication" → MedicationRecord
    - "Vet Visit" / "Health Check" → VetVisit
    """
    if not created:
        # Only create detailed records for NEW health records
        return
    
    # Skip if this health record already has a linked detailed record
    if instance.medication_record_id or instance.vaccination_record_id or instance.vet_visit_id:
        logger.debug(f"HealthRecord {instance.id} already has linked detailed record, skipping")
        return
    
    # Skip if cost is zero (nothing to track financially)
    if instance.cost_ghs <= 0:
        logger.debug(f"HealthRecord {instance.id} has zero cost, skipping detailed record creation")
        return
    
    record_type = instance.record_type.lower()
    
    try:
        with transaction.atomic():
            if 'vaccination' in record_type:
                _create_vaccination_record(instance)
            elif 'medication' in record_type or 'treatment' in record_type:
                _create_medication_record(instance)
            elif 'vet' in record_type or 'health check' in record_type:
                _create_vet_visit_record(instance)
            else:
                # For 'Other' types, default to VetVisit as catch-all
                logger.debug(f"HealthRecord {instance.id} has unknown type '{instance.record_type}', creating VetVisit")
                _create_vet_visit_record(instance)
    
    except Exception as e:
        logger.error(
            f"Failed to auto-create detailed record for HealthRecord {instance.id}: {str(e)}",
            exc_info=True
        )
        # Don't raise - we don't want to block health record creation


def _create_vaccination_record(health_record):
    """Create a VaccinationRecord from a HealthRecord."""
    from medication_management.models import VaccinationRecord, MedicationType
    
    # Try to find or create a generic MedicationType for the vaccine
    medication_type = _get_or_create_medication_type(
        name=health_record.treatment_name or 'Generic Vaccine',
        category='VACCINE',
        dosage=health_record.dosage or 'As prescribed'
    )
    
    # Calculate flock age at vaccination
    flock_age_weeks = 0
    if health_record.flock.arrival_date and health_record.record_date:
        days = (health_record.record_date - health_record.flock.arrival_date).days
        flock_age_weeks = days // 7 + (health_record.flock.age_at_arrival_weeks or 0)
    
    birds_vaccinated = health_record.birds_affected or health_record.flock.current_count or 1
    unit_cost = health_record.cost_ghs / Decimal(str(birds_vaccinated)) if birds_vaccinated > 0 else health_record.cost_ghs
    
    vaccination_record = VaccinationRecord.objects.create(
        flock=health_record.flock,
        farm=health_record.farm,
        medication_type=medication_type,
        vaccination_date=health_record.record_date,
        birds_vaccinated=birds_vaccinated,
        flock_age_weeks=flock_age_weeks,
        dosage_per_bird=health_record.dosage or 'Standard',
        administration_route=health_record.treatment_method or 'As per label',
        batch_number='N/A',
        expiry_date=health_record.record_date + timedelta(days=365),  # Default 1 year
        manufacturer='Unknown',
        quantity_used=Decimal(str(birds_vaccinated)),
        unit_cost=unit_cost,
        total_cost=health_record.cost_ghs,
        administered_by=health_record.administering_person or health_record.vet_name or 'Unknown',
        vet_license_number=health_record.vet_license or '',
        notes=f"Auto-created from HealthRecord. {health_record.notes}",
    )
    
    # Link back to health record
    health_record.vaccination_record = vaccination_record
    health_record.save(update_fields=['vaccination_record'])
    
    logger.info(f"Auto-created VaccinationRecord {vaccination_record.id} from HealthRecord {health_record.id}")


def _create_medication_record(health_record):
    """Create a MedicationRecord from a HealthRecord."""
    from medication_management.models import MedicationRecord, MedicationType
    
    # Determine medication category from symptoms/disease
    category = 'ANTIBIOTIC'  # Default
    if health_record.disease:
        disease_lower = health_record.disease.lower()
        if 'worm' in disease_lower or 'parasit' in disease_lower:
            category = 'DEWORMER'
        elif 'coccid' in disease_lower:
            category = 'COCCIDIOSTAT'
        elif 'vitamin' in disease_lower or 'deficien' in disease_lower:
            category = 'VITAMIN'
    
    medication_type = _get_or_create_medication_type(
        name=health_record.treatment_name or 'Generic Medication',
        category=category,
        dosage=health_record.dosage or 'As prescribed'
    )
    
    birds_treated = health_record.birds_affected or health_record.flock.current_count or 1
    unit_cost = health_record.cost_ghs / Decimal(str(birds_treated)) if birds_treated > 0 else health_record.cost_ghs
    
    # Determine reason
    reason = 'TREATMENT'  # Default for medications
    if 'prevent' in (health_record.notes or '').lower():
        reason = 'PREVENTION'
    
    medication_record = MedicationRecord.objects.create(
        flock=health_record.flock,
        farm=health_record.farm,
        medication_type=medication_type,
        administered_date=health_record.record_date,
        reason=reason,
        dosage_given=health_record.dosage or 'As prescribed',
        birds_treated=birds_treated,
        treatment_days=1,  # Default, can be updated
        end_date=health_record.record_date,
        quantity_used=Decimal(str(birds_treated)),
        unit_cost=unit_cost,
        total_cost=health_record.cost_ghs,
        administered_by=health_record.administering_person or health_record.vet_name or 'Unknown',
        symptoms_before=health_record.symptoms or '',
        notes=f"Auto-created from HealthRecord. Disease: {health_record.disease}. {health_record.notes}",
    )
    
    # Link back to health record
    health_record.medication_record = medication_record
    health_record.save(update_fields=['medication_record'])
    
    logger.info(f"Auto-created MedicationRecord {medication_record.id} from HealthRecord {health_record.id}")


def _create_vet_visit_record(health_record):
    """Create a VetVisit from a HealthRecord."""
    from medication_management.models import VetVisit
    
    # Determine visit type
    visit_type = 'ROUTINE'  # Default for Health Check
    record_type_lower = health_record.record_type.lower()
    if 'emergency' in record_type_lower or health_record.disease:
        visit_type = 'DISEASE_INVESTIGATION' if health_record.disease else 'EMERGENCY'
    elif 'follow' in record_type_lower:
        visit_type = 'FOLLOW_UP'
    
    vet_visit = VetVisit.objects.create(
        farm=health_record.farm,
        flock=health_record.flock,
        visit_date=health_record.record_date,
        visit_type=visit_type,
        status='COMPLETED',
        veterinarian_name=health_record.vet_name or 'Unknown',
        vet_license_number=health_record.vet_license or 'N/A',
        purpose=f"Health check for flock {health_record.flock.flock_number}",
        findings=health_record.symptoms or '',
        diagnosis=health_record.diagnosis or health_record.disease or '',
        recommendations=health_record.notes or '',
        medications_prescribed=health_record.treatment_name or '',
        follow_up_required=health_record.follow_up_date is not None,
        follow_up_date=health_record.follow_up_date,
        visit_fee=health_record.cost_ghs,
        notes=f"Auto-created from HealthRecord. Outcome: {health_record.outcome}",
    )
    
    # Link back to health record
    health_record.vet_visit = vet_visit
    health_record.save(update_fields=['vet_visit'])
    
    logger.info(f"Auto-created VetVisit {vet_visit.id} from HealthRecord {health_record.id}")


def _get_or_create_medication_type(name: str, category: str, dosage: str):
    """Get or create a MedicationType for auto-created records."""
    from medication_management.models import MedicationType
    
    # Try to find existing medication type by name
    medication_type = MedicationType.objects.filter(name__iexact=name).first()
    
    if not medication_type:
        # Create a generic one
        medication_type = MedicationType.objects.create(
            name=name,
            category=category,
            administration_route='ORAL',  # Default
            dosage=dosage,
            indication=f'Generic {category.lower()} for poultry',
            is_active=True,
            notes='Auto-created from HealthRecord entry'
        )
        logger.info(f"Created new MedicationType: {name} ({category})")
    
    return medication_type