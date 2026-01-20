"""
Expense Tracking Signals

Handles automatic updates when expenses are created, updated, or deleted.
Ensures flock accumulated costs stay synchronized with expense records.
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
import logging

from .models import Expense, ExpenseCategory

logger = logging.getLogger(__name__)


def update_flock_category_total(flock, category):
    """
    Recalculate and update the flock's accumulated cost for a specific category.
    
    This is called after expense create/update/delete to keep flock totals accurate.
    """
    if not flock:
        return
    
    # Map categories to flock fields
    category_field_map = {
        ExpenseCategory.LABOR: 'total_labor_cost',
        ExpenseCategory.UTILITIES: 'total_utilities_cost',
        ExpenseCategory.BEDDING: 'total_bedding_cost',
        ExpenseCategory.TRANSPORT: 'total_transport_cost',
        ExpenseCategory.MAINTENANCE: 'total_maintenance_cost',
        ExpenseCategory.OVERHEAD: 'total_overhead_cost',
        ExpenseCategory.MORTALITY_LOSS: 'total_mortality_loss_value',
        ExpenseCategory.MISCELLANEOUS: 'total_miscellaneous_cost',
    }
    
    field_name = category_field_map.get(category)
    if not field_name or not hasattr(flock, field_name):
        return
    
    # Calculate sum of all expenses in this category for this flock
    total = Expense.objects.filter(
        flock=flock,
        category=category
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Update flock field
    setattr(flock, field_name, total)
    flock.save(update_fields=[field_name, 'updated_at'])
    
    logger.debug(
        f"Updated flock {flock.flock_number} {field_name}: GHS {total}"
    )


@receiver(post_delete, sender=Expense)
def expense_deleted_update_flock(sender, instance, **kwargs):
    """
    When an expense is deleted, recalculate flock totals.
    
    The save() method handles create/update, but delete needs a signal
    because there's no save() call on delete.
    """
    if instance.flock:
        update_flock_category_total(instance.flock, instance.category)
        logger.info(
            f"Expense deleted - updated flock {instance.flock.flock_number} "
            f"{instance.category} total"
        )


@receiver(pre_save, sender=Expense)
def expense_pre_save_track_changes(sender, instance, **kwargs):
    """
    Track if expense's flock or category changed to update old flock totals.
    """
    if instance.pk:  # Existing expense being updated
        try:
            old_expense = Expense.objects.get(pk=instance.pk)
            # Store old values for post_save to use
            instance._old_flock = old_expense.flock
            instance._old_category = old_expense.category
            instance._old_amount = old_expense.total_amount
        except Expense.DoesNotExist:
            instance._old_flock = None
            instance._old_category = None
            instance._old_amount = None
    else:
        instance._old_flock = None
        instance._old_category = None
        instance._old_amount = None


@receiver(post_save, sender=Expense)
def expense_saved_handle_flock_change(sender, instance, created, **kwargs):
    """
    Handle cases where expense's flock or category changed during update.
    
    If flock or category changed, we need to:
    1. Update the OLD flock's totals (decrement)
    2. Update the NEW flock's totals (increment)
    """
    old_flock = getattr(instance, '_old_flock', None)
    old_category = getattr(instance, '_old_category', None)
    
    # If this is an update and the flock or category changed
    if not created:
        flock_changed = old_flock != instance.flock
        category_changed = old_category != instance.category
        
        if old_flock and (flock_changed or category_changed):
            # Update old flock's old category total
            update_flock_category_total(old_flock, old_category)
            logger.info(
                f"Expense moved - updated old flock {old_flock.flock_number} "
                f"{old_category} total"
            )
