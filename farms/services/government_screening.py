"""
Government Farmer Screening Service

Implements 3-tier approval workflow for government-sponsored farmers:
1. Constituency Level Review (Extension Officer)
2. Regional Level Review (Regional Coordinator)
3. National Level Review (National Administrator)
"""

from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from farms.models import Farm, FarmReviewAction, FarmApprovalQueue, FarmNotification
from accounts.roles import UserRole


class GovernmentScreeningService:
    """
    Service for managing government farmer screening process.
    
    3-Tier Workflow:
    - Constituency → Regional → National
    - Each level can: Approve, Reject, Request Changes
    - Approval at each level advances to next level
    - Final approval assigns Farm ID and activates farm
    """
    
    # SLA (Service Level Agreement) deadlines for each level
    SLA_DAYS = {
        'constituency': 7,   # 7 days for constituency review
        'regional': 5,       # 5 days for regional review
        'national': 3,       # 3 days for national review
    }
    
    @staticmethod
    @transaction.atomic
    def submit_for_screening(farm):
        """
        Submit a government farmer application for screening.
        Creates initial queue entry at constituency level.
        
        Args:
            farm: Farm object (must have registration_source='government_initiative')
        
        Returns:
            (success: bool, message: str, queue_item: FarmApprovalQueue or None)
        """
        # Validate farm is government farmer
        if farm.registration_source != 'government_initiative':
            return False, "Only government initiative farmers go through screening", None
        
        # Check if already in screening
        if FarmApprovalQueue.objects.filter(
            farm=farm,
            review_level='constituency',
            status__in=['pending', 'claimed', 'in_progress']
        ).exists():
            return False, "Farm is already in screening process", None
        
        # Update farm status
        farm.application_status = 'Submitted'
        farm.current_review_level = 'constituency'
        farm.save()
        
        # Create queue entry at constituency level
        queue_item = FarmApprovalQueue.objects.create(
            farm=farm,
            review_level='constituency',
            status='pending',
            priority=GovernmentScreeningService._calculate_priority(farm),
            sla_due_date=timezone.now() + timedelta(days=GovernmentScreeningService.SLA_DAYS['constituency']),
            suggested_constituency=farm.primary_constituency,
        )
        
        # Try to auto-assign to extension officer
        if farm.extension_officer:
            queue_item.assigned_to = farm.extension_officer
            queue_item.assigned_at = timezone.now()
            queue_item.auto_assigned = True
            queue_item.save()
        else:
            # Try to find available extension officer in constituency
            GovernmentScreeningService._auto_assign_officer(queue_item)
        
        # Create notification for assigned officer
        if queue_item.assigned_to:
            FarmNotification.objects.create(
                user=queue_item.assigned_to,
                farm=farm,
                notification_type='assignment',
                channel='in_app',
                subject='New Farm Application for Review',
                message=f'Farm "{farm.farm_name}" has been assigned to you for constituency review.',
                action_url=f'/review/farm/{farm.id}'
            )
        
        # Notify farmer
        FarmNotification.objects.create(
            user=farm.user,
            farm=farm,
            notification_type='application_submitted',
            channel='in_app',
            subject='Application Submitted Successfully',
            message=f'Your farm registration for "{farm.farm_name}" has been submitted and is now under constituency review.',
        )
        
        return True, "Application submitted for screening", queue_item
    
    @staticmethod
    @transaction.atomic
    def approve_at_level(farm, reviewer, review_level, notes=""):
        """
        Approve farm at current review level and advance to next level.
        
        Args:
            farm: Farm object
            reviewer: User object (reviewing officer)
            review_level: str ('constituency', 'regional', 'national')
            notes: str (reviewer notes)
        
        Returns:
            (success: bool, message: str, next_level: str or None)
        """
        # Validate review level matches farm's current level
        if farm.current_review_level != review_level:
            return False, f"Farm is not at {review_level} review level", None
        
        # Validate reviewer has appropriate role
        if not GovernmentScreeningService._validate_reviewer_role(reviewer, review_level):
            return False, f"User does not have permission to review at {review_level} level", None
        
        # Get queue item
        queue_item = FarmApprovalQueue.objects.filter(
            farm=farm,
            review_level=review_level,
            status__in=['pending', 'claimed', 'in_progress']
        ).first()
        
        if not queue_item:
            return False, f"No active queue item found for {review_level} level", None
        
        # Create review action record
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=reviewer,
            review_level=review_level,
            action='approved',
            notes=notes or f'Approved at {review_level} level'
        )
        
        # Mark queue item as completed
        queue_item.status = 'completed'
        queue_item.completed_at = timezone.now()
        queue_item.save()
        
        # Update approval timestamp on farm
        if review_level == 'constituency':
            farm.constituency_approved_at = timezone.now()
        elif review_level == 'regional':
            farm.regional_approved_at = timezone.now()
        elif review_level == 'national':
            farm.final_approved_at = timezone.now()
        
        # Determine next level
        next_level = GovernmentScreeningService._get_next_review_level(review_level)
        
        if next_level:
            # Advance to next level
            farm.application_status = f'{next_level.title()} Review'
            farm.current_review_level = next_level
            farm.save()
            
            # Create queue entry for next level
            new_queue_item = FarmApprovalQueue.objects.create(
                farm=farm,
                review_level=next_level,
                status='pending',
                priority=GovernmentScreeningService._calculate_priority(farm),
                sla_due_date=timezone.now() + timedelta(days=GovernmentScreeningService.SLA_DAYS[next_level]),
            )
            
            # Try to auto-assign
            GovernmentScreeningService._auto_assign_officer(new_queue_item)
            
            # Notify farmer
            FarmNotification.objects.create(
                user=farm.user,
                farm=farm,
                notification_type='approved_next_level',
                channel='in_app',
                subject=f'Application Approved at {review_level.title()} Level',
                message=f'Your application has been approved at {review_level} level and forwarded to {next_level} level for review.',
            )
            
            # Notify next level officer if assigned
            if new_queue_item.assigned_to:
                FarmNotification.objects.create(
                    user=new_queue_item.assigned_to,
                    farm=farm,
                    notification_type='assignment',
                    channel='in_app',
                    subject='New Farm Application for Review',
                    message=f'Farm "{farm.farm_name}" has been forwarded to you for {next_level} level review.',
                    action_url=f'/review/farm/{farm.id}'
                )
            
            return True, f"Approved at {review_level} level. Advanced to {next_level} level.", next_level
        
        else:
            # Final approval - activate farm
            farm.application_status = 'Approved'
            farm.farm_status = 'Active'
            farm.approval_date = timezone.now()
            farm.approved_by = reviewer
            farm.activation_date = timezone.now()
            farm.current_review_level = None
            
            # Generate Farm ID
            if not farm.farm_id:
                farm.farm_id = GovernmentScreeningService._generate_farm_id(farm)
            
            farm.save()
            
            # Notify farmer of final approval
            FarmNotification.objects.create(
                user=farm.user,
                farm=farm,
                notification_type='final_approval',
                channel='in_app',
                subject='Congratulations! Farm Approved',
                message=f'Your farm "{farm.farm_name}" has been approved! Your Farm ID is: {farm.farm_id}. You now have full access to the platform.',
            )
            
            # TODO: Send SMS and Email notifications
            
            return True, f"Final approval granted. Farm ID: {farm.farm_id}", None
    
    @staticmethod
    @transaction.atomic
    def reject_at_level(farm, reviewer, review_level, reason):
        """
        Reject farm application at current review level.
        
        Args:
            farm: Farm object
            reviewer: User object
            review_level: str
            reason: str (rejection reason - required)
        
        Returns:
            (success: bool, message: str)
        """
        if not reason:
            return False, "Rejection reason is required"
        
        # Validate review level
        if farm.current_review_level != review_level:
            return False, f"Farm is not at {review_level} review level"
        
        # Validate reviewer role
        if not GovernmentScreeningService._validate_reviewer_role(reviewer, review_level):
            return False, f"User does not have permission to review at {review_level} level"
        
        # Get queue item
        queue_item = FarmApprovalQueue.objects.filter(
            farm=farm,
            review_level=review_level,
            status__in=['pending', 'claimed', 'in_progress']
        ).first()
        
        if queue_item:
            queue_item.status = 'completed'
            queue_item.completed_at = timezone.now()
            queue_item.save()
        
        # Create review action
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=reviewer,
            review_level=review_level,
            action='rejected',
            notes=reason
        )
        
        # Update farm
        farm.application_status = 'Rejected'
        farm.rejection_reason = reason
        farm.rejected_at = timezone.now()
        farm.current_review_level = None
        farm.save()
        
        # Notify farmer
        FarmNotification.objects.create(
            user=farm.user,
            farm=farm,
            notification_type='rejected',
            channel='in_app',
            subject='Application Rejected',
            message=f'Your farm application has been rejected at {review_level} level. Reason: {reason}',
        )
        
        # TODO: Send email/SMS notification
        
        return True, "Application rejected"
    
    @staticmethod
    @transaction.atomic
    def request_changes(farm, reviewer, review_level, requested_changes, deadline_days=14):
        """
        Request changes/additional information from farmer.
        
        Args:
            farm: Farm object
            reviewer: User object
            review_level: str
            requested_changes: dict or list (specific changes needed)
            deadline_days: int (days farmer has to respond)
        
        Returns:
            (success: bool, message: str)
        """
        # Validate
        if farm.current_review_level != review_level:
            return False, f"Farm is not at {review_level} review level"
        
        if not GovernmentScreeningService._validate_reviewer_role(reviewer, review_level):
            return False, f"User does not have permission to review at {review_level} level"
        
        # Create review action
        FarmReviewAction.objects.create(
            farm=farm,
            reviewer=reviewer,
            review_level=review_level,
            action='request_changes',
            notes=f"Changes requested at {review_level} level",
            requested_changes=requested_changes,
            changes_deadline=timezone.now() + timedelta(days=deadline_days)
        )
        
        # Update farm status
        farm.application_status = 'Changes Requested'
        farm.more_info_requested = str(requested_changes) if isinstance(requested_changes, dict) else '\n'.join(requested_changes)
        farm.save()
        
        # Notify farmer
        changes_text = str(requested_changes) if isinstance(requested_changes, dict) else '\n'.join(requested_changes)
        FarmNotification.objects.create(
            user=farm.user,
            farm=farm,
            notification_type='changes_requested',
            channel='in_app',
            subject='Additional Information Required',
            message=f'The reviewer has requested changes to your application. Please update within {deadline_days} days.\n\nRequired changes:\n{changes_text}',
        )
        
        return True, f"Changes requested. Farmer has {deadline_days} days to respond."
    
    @staticmethod
    def get_review_queue(review_level, officer=None, status='pending'):
        """
        Get review queue for a specific level.
        
        Args:
            review_level: str ('constituency', 'regional', 'national')
            officer: User object (optional - filter by assigned officer)
            status: str (queue status filter)
        
        Returns:
            QuerySet of FarmApprovalQueue objects
        """
        queryset = FarmApprovalQueue.objects.filter(
            review_level=review_level,
            status=status
        ).select_related('farm', 'assigned_to')
        
        if officer:
            queryset = queryset.filter(assigned_to=officer)
        
        return queryset.order_by('-priority', 'entered_queue_at')
    
    @staticmethod
    def claim_for_review(queue_item, officer):
        """
        Officer claims a farm application for review.
        
        Args:
            queue_item: FarmApprovalQueue object
            officer: User object
        
        Returns:
            (success: bool, message: str)
        """
        if queue_item.status != 'pending':
            return False, f"Cannot claim application with status '{queue_item.status}'"
        
        # Validate officer role
        if not GovernmentScreeningService._validate_reviewer_role(officer, queue_item.review_level):
            return False, f"User does not have permission to review at {queue_item.review_level} level"
        
        # Claim the application
        queue_item.claim(officer)
        
        return True, f"Application claimed by {officer.get_full_name()}"
    
    @staticmethod
    def _get_next_review_level(current_level):
        """Get next review level in workflow"""
        flow = ['constituency', 'regional', 'national']
        try:
            current_index = flow.index(current_level)
            if current_index < len(flow) - 1:
                return flow[current_index + 1]
        except ValueError:
            pass
        return None
    
    @staticmethod
    def _validate_reviewer_role(user, review_level):
        """Validate user has appropriate role for review level"""
        role_mapping = {
            'constituency': [UserRole.EXTENSION_OFFICER, UserRole.CONSTITUENCY_COORDINATOR],
            'regional': [UserRole.REGIONAL_COORDINATOR, UserRole.REGIONAL_ADMIN],
            'national': [UserRole.NATIONAL_ADMIN, UserRole.SYSTEM_ADMIN],
        }
        
        required_roles = role_mapping.get(review_level, [])
        return user.role in required_roles or user.is_superuser
    
    @staticmethod
    def _auto_assign_officer(queue_item):
        """
        Auto-assign queue item to appropriate officer.
        Uses constituency matching for constituency level.
        """
        from accounts.models import User
        
        # Role mapping by review level
        role_mapping = {
            'constituency': UserRole.EXTENSION_OFFICER,
            'regional': UserRole.REGIONAL_COORDINATOR,
            'national': UserRole.NATIONAL_ADMIN,
        }
        
        target_role = role_mapping.get(queue_item.review_level)
        if not target_role:
            return
        
        # Find officers with appropriate role
        officers = User.objects.filter(
            role=target_role,
            is_active=True
        )
        
        # For constituency level, match by constituency
        if queue_item.review_level == 'constituency' and queue_item.suggested_constituency:
            # TODO: Add constituency field to User model for better filtering
            pass
        
        # Simple load balancing: assign to officer with fewest assignments
        if officers.exists():
            from django.db.models import Count
            officer = officers.annotate(
                assignment_count=Count('assigned_farm_reviews')
            ).order_by('assignment_count').first()
            
            if officer:
                queue_item.assigned_to = officer
                queue_item.assigned_at = timezone.now()
                queue_item.auto_assigned = True
                queue_item.save()
    
    @staticmethod
    def _calculate_priority(farm):
        """
        Calculate priority score for queue ordering.
        Higher score = reviewed sooner.
        """
        priority = 0
        
        # YEA program farmers get high priority
        if farm.yea_program_batch:
            priority += 50
        
        # Complete documentation adds priority
        doc_count = farm.documents.count()
        if doc_count >= 5:  # Minimum required docs
            priority += 30
        
        # TIN and business registration
        if farm.tin:
            priority += 10
        if farm.business_registration_number:
            priority += 10
        
        return priority
    
    @staticmethod
    def _generate_farm_id(farm):
        """
        Generate unique Farm ID.
        Format: YEA-REG-CONST-XXXX
        """
        from django.db.models import Max
        import re
        
        # Get constituency abbreviation (first 3-4 chars, uppercase)
        const_abbrev = re.sub(r'[^A-Z]', '', farm.primary_constituency.upper())[:4]
        if not const_abbrev:
            const_abbrev = 'UNKN'
        
        # Get next sequential number for this constituency
        last_farm = Farm.objects.filter(
            farm_id__startswith=f'YEA-REG-{const_abbrev}-'
        ).order_by('-farm_id').first()
        
        if last_farm and last_farm.farm_id:
            try:
                last_num = int(last_farm.farm_id.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1
        
        return f'YEA-REG-{const_abbrev}-{next_num:04d}'
    
    @staticmethod
    def get_overdue_reviews(review_level=None):
        """
        Get applications that have exceeded SLA deadlines.
        
        Args:
            review_level: str (optional filter by level)
        
        Returns:
            QuerySet of FarmApprovalQueue objects
        """
        queryset = FarmApprovalQueue.objects.filter(
            status__in=['pending', 'claimed', 'in_progress'],
            sla_due_date__lt=timezone.now()
        )
        
        if review_level:
            queryset = queryset.filter(review_level=review_level)
        
        # Mark as overdue
        queryset.update(is_overdue=True)
        
        return queryset.order_by('sla_due_date')
