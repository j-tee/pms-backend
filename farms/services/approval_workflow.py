"""
Farm Approval Workflow Service

Handles all approval workflow logic including:
- Submitting applications
- Officers claiming/assigning farms
- Approving/rejecting applications
- Requesting changes
- Status transitions
- Farm ID generation
"""

from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

from farms.models import Farm, FarmReviewAction, FarmApprovalQueue
from .notification_service import FarmNotificationService

logger = logging.getLogger(__name__)


class FarmApprovalWorkflowService:
    """Service for managing farm approval workflow"""
    
    # SLA deadlines for each review level (in days)
    SLA_DAYS = {
        'constituency': 7,   # 1 week
        'regional': 5,       # 5 days
        'national': 3,       # 3 days
    }
    
    def __init__(self):
        self.notification_service = FarmNotificationService()
    
    @transaction.atomic
    def submit_application(self, farm):
        """
        Submit farm application for review.
        Creates entry in constituency queue.
        """
        # Update farm status
        farm.application_status = 'Submitted - Pending Assignment'
        farm.current_review_level = 'constituency'
        farm.save()
        
        # Get suggested location from farm's first location
        suggested_constituency = ''
        suggested_region = ''
        if farm.locations.exists():
            first_location = farm.locations.filter(is_primary_location=True).first()
            if not first_location:
                first_location = farm.locations.first()
            
            if first_location:
                suggested_constituency = first_location.constituency or ''
                suggested_region = first_location.region or ''
        
        # Create queue entry
        queue_item = FarmApprovalQueue.objects.create(
            farm=farm,
            review_level='constituency',
            status='pending',
            priority=0,
            suggested_constituency=suggested_constituency,
            suggested_region=suggested_region,
            sla_due_date=timezone.now() + timedelta(days=self.SLA_DAYS['constituency'])
        )
        
        # Create review action
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=farm.user,  # Farmer submits their own application
            review_level='constituency',
            action='changes_submitted',
            notes='Application submitted for constituency review'
        )
        
        # Send notification to farmer
        self.notification_service.send_application_submitted(farm)
        
        logger.info(f"Application submitted for farm: {farm.farm_name}")
        return queue_item
    
    @transaction.atomic
    def claim_for_review(self, farm, officer, review_level):
        """
        Officer claims a farm from the queue for review.
        """
        try:
            queue_item = FarmApprovalQueue.objects.get(
                farm=farm,
                review_level=review_level,
                status='pending'
            )
        except FarmApprovalQueue.DoesNotExist:
            raise ValueError(f"Farm not available in {review_level} queue")
        
        # Use the queue item's claim method
        queue_item.claim(officer)
        
        # Update farm status
        farm.application_status = f'{review_level.title()} Review'
        farm.save()
        
        # Send notification to farmer
        self.notification_service.send_review_started(farm, officer, review_level)
        
        logger.info(f"Farm {farm.farm_name} claimed by {officer.get_full_name()} for {review_level} review")
        return queue_item
    
    @transaction.atomic
    def approve_and_forward(self, farm, officer, review_level, notes=''):
        """
        Approve at current level and forward to next level.
        """
        # Create review action
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=officer,
            review_level=review_level,
            action='approved',
            notes=notes or f'Approved at {review_level} level'
        )
        
        # Update approval timestamp
        timestamp_field = f'{review_level}_approved_at'
        setattr(farm, timestamp_field, timezone.now())
        
        # Complete current queue item
        try:
            queue_item = FarmApprovalQueue.objects.get(
                farm=farm,
                review_level=review_level
            )
            queue_item.complete()
        except FarmApprovalQueue.DoesNotExist:
            pass
        
        # Determine next level
        if review_level == 'constituency':
            next_level = 'regional'
        elif review_level == 'regional':
            next_level = 'national'
        else:  # national = final approval
            return self.finalize_approval(farm, officer, notes)
        
        # Update farm status
        farm.current_review_level = next_level
        farm.application_status = f'{next_level.title()} Review'
        farm.save()
        
        # Create queue entry for next level
        suggested_region = ''
        if farm.locations.exists():
            first_location = farm.locations.first()
            suggested_region = first_location.region if first_location else ''
        
        next_queue = FarmApprovalQueue.objects.create(
            farm=farm,
            review_level=next_level,
            status='pending',
            priority=1,  # Promoted farms get priority
            suggested_region=suggested_region,
            sla_due_date=timezone.now() + timedelta(days=self.SLA_DAYS[next_level])
        )
        
        # Send notification
        self.notification_service.send_approved_next_level(
            farm, officer, review_level, next_level
        )
        
        logger.info(f"Farm {farm.farm_name} approved at {review_level}, forwarded to {next_level}")
        return next_queue
    
    @transaction.atomic
    def finalize_approval(self, farm, officer, notes=''):
        """
        Final national approval - assign Farm ID and activate.
        """
        # Generate Farm ID
        farm_id = self._generate_farm_id(farm)
        
        # Update farm
        farm.farm_id = farm_id
        farm.application_status = 'Approved - Farm ID Assigned'
        farm.farm_status = 'Active'
        farm.final_approved_at = timezone.now()
        farm.save()
        
        # Create review action
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=officer,
            review_level='national',
            action='approved',
            notes=notes or f'Final approval granted. Farm ID assigned: {farm_id}'
        )
        
        # Complete queue
        try:
            queue_item = FarmApprovalQueue.objects.get(
                farm=farm,
                review_level='national'
            )
            queue_item.complete()
        except FarmApprovalQueue.DoesNotExist:
            pass
        
        # Send notification
        self.notification_service.send_final_approval(farm, officer, farm_id)
        
        logger.info(f"Farm {farm.farm_name} FINAL APPROVAL - Farm ID: {farm_id}")
        return farm
    
    @transaction.atomic
    def reject_application(self, farm, officer, review_level, reason):
        """
        Reject application with reason.
        """
        # Create review action
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=officer,
            review_level=review_level,
            action='rejected',
            notes=reason
        )
        
        # Update farm
        farm.application_status = 'Rejected'
        farm.rejected_at = timezone.now()
        farm.save()
        
        # Complete/remove from queue
        try:
            queue_item = FarmApprovalQueue.objects.get(
                farm=farm,
                review_level=review_level
            )
            queue_item.complete()
        except FarmApprovalQueue.DoesNotExist:
            pass
        
        # Send notification
        self.notification_service.send_rejection(farm, officer, review_level, reason)
        
        logger.info(f"Farm {farm.farm_name} REJECTED at {review_level} level")
        return farm
    
    @transaction.atomic
    def request_changes(self, farm, officer, review_level, feedback, requested_changes_list, deadline_days=14):
        """
        Request changes to application without rejecting.
        Farmer can edit and resubmit.
        """
        deadline = timezone.now().date() + timedelta(days=deadline_days)
        
        # Create review action
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=officer,
            review_level=review_level,
            action='request_changes',
            notes=feedback,
            requested_changes=requested_changes_list,
            changes_deadline=deadline
        )
        
        # Update farm status
        farm.application_status = 'Changes Requested by Reviewer'
        farm.save()
        
        # Keep in queue but mark as in_progress
        try:
            queue_item = FarmApprovalQueue.objects.get(
                farm=farm,
                review_level=review_level
            )
            queue_item.mark_in_progress()
        except FarmApprovalQueue.DoesNotExist:
            pass
        
        # Send notification
        self.notification_service.send_changes_requested(
            farm, officer, review_level, feedback, requested_changes_list, deadline
        )
        
        logger.info(f"Changes requested for farm {farm.farm_name} at {review_level} level")
        return farm
    
    @transaction.atomic
    def farmer_submits_changes(self, farm):
        """
        Farmer has made requested changes and resubmits.
        """
        # Find current review level
        review_level = farm.current_review_level
        if not review_level:
            raise ValueError("No active review level for this farm")
        
        # Create review action
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=farm.user,  # Farmer
            review_level=review_level,
            action='changes_submitted',
            notes='Requested changes have been submitted'
        )
        
        # Update farm status back to under review
        farm.application_status = f'{review_level.title()} Review'
        farm.save()
        
        # Update queue status
        try:
            queue_item = FarmApprovalQueue.objects.get(
                farm=farm,
                review_level=review_level
            )
            if queue_item.status == 'in_progress':
                queue_item.status = 'claimed'  # Back to claimed for review
                queue_item.save()
        except FarmApprovalQueue.DoesNotExist:
            pass
        
        # Notify assigned officer
        if farm.approval_queue_items.filter(review_level=review_level).exists():
            queue_item = farm.approval_queue_items.get(review_level=review_level)
            if queue_item.assigned_to:
                self.notification_service.send_changes_resubmitted(
                    farm, queue_item.assigned_to, review_level
                )
        
        logger.info(f"Changes resubmitted for farm {farm.farm_name}")
        return farm
    
    def _generate_farm_id(self, farm):
        """
        Generate official Farm ID: YEA-REG-CONST-XXXX
        Format: YEA-{REGION_CODE}-{CONSTITUENCY_CODE}-{SEQUENTIAL}
        """
        # Get constituency and region from primary farm location
        location = farm.locations.filter(is_primary_location=True).first()
        if not location:
            location = farm.locations.first()
        
        if not location:
            # Fallback if no location
            region_code = 'UNK'
            const_code = 'UNK'
        else:
            # Get codes (use first 3-4 letters, uppercase)
            region = location.region or 'UNK'
            constituency = location.constituency or 'UNK'
            
            region_code = region[:4].upper().replace(' ', '')
            const_code = constituency[:4].upper().replace(' ', '')
        
        # Get next sequential number for this region/constituency
        prefix = f'YEA-{region_code}-{const_code}'
        
        # Find highest existing number
        existing_farms = Farm.objects.filter(
            farm_id__startswith=prefix
        ).order_by('-farm_id')
        
        if existing_farms.exists():
            last_id = existing_farms.first().farm_id
            try:
                last_num = int(last_id.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        # Format: YEA-ACCR-AYAW-0001
        farm_id = f'{prefix}-{next_num:04d}'
        
        return farm_id
    
    def get_pending_reviews(self, officer, review_level):
        """
        Get all farms pending review at specified level.
        Can be filtered by officer's region/constituency.
        """
        return FarmApprovalQueue.objects.filter(
            review_level=review_level,
            status='pending'
        ).select_related('farm').order_by('-priority', 'entered_queue_at')
    
    def get_my_reviews(self, officer):
        """
        Get all farms assigned to this officer.
        """
        return FarmApprovalQueue.objects.filter(
            assigned_to=officer,
            status__in=['claimed', 'in_progress']
        ).select_related('farm').order_by('-priority', 'claimed_at')
    
    def check_overdue_slas(self):
        """
        Check for overdue reviews and mark them.
        Should be run as periodic task (daily).
        """
        now = timezone.now()
        
        overdue = FarmApprovalQueue.objects.filter(
            status__in=['pending', 'claimed', 'in_progress'],
            sla_due_date__lt=now,
            is_overdue=False
        )
        
        count = overdue.update(is_overdue=True)
        
        logger.info(f"Marked {count} farm reviews as overdue")
        return count
