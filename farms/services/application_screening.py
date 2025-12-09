"""
Application Screening Service

Handles screening of anonymous farm applications submitted by prospective farmers.
Applications go through 3-tier review BEFORE account creation.

Flow:
1. Farmer submits application (no account)
2. 3-tier screening (constituency → regional → national)
3. Approval → invitation sent
4. Farmer creates account → farm profile created
"""

from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from farms.application_models import FarmApplication, ApplicationReviewAction, ApplicationQueue
from farms.invitation_models import FarmInvitation
from farms.services.spam_detection import SpamDetectionService
from farms.services.invitation_service import InvitationService
from accounts.roles import UserRole


class ApplicationScreeningService:
    """
    Service for screening anonymous farm applications.
    """
    
    # SLA deadlines for each review level
    SLA_DAYS = {
        'constituency': 7,
        'regional': 5,
        'national': 3,
    }
    
    @staticmethod
    @transaction.atomic
    def submit_application(application_data, ip_address=None):
        """
        Submit a new farm application.
        
        Args:
            application_data: dict with all application fields
            ip_address: str (for rate limiting and spam detection)
        
        Returns:
            (success: bool, message: str, application: FarmApplication or None)
        """
        # Check rate limit
        if ip_address:
            from farms.services.spam_detection import RateLimitService
            is_allowed, message = RateLimitService.check_rate_limit(ip_address)
            if not is_allowed:
                return False, message, None
        
        # Run spam detection
        spam_score, spam_flags = SpamDetectionService.check_registration(application_data)
        
        # Create application
        application = FarmApplication.objects.create(
            **application_data,
            spam_score=spam_score,
            spam_flags=spam_flags,
            ip_address=ip_address
        )
        
        # Calculate priority score
        application.calculate_priority_score()
        
        # Start screening workflow
        ApplicationScreeningService._start_screening(application)
        
        # Record rate limit attempt
        if ip_address:
            from farms.services.spam_detection import RateLimitService
            RateLimitService.record_attempt(ip_address)
        
        return True, "Application submitted successfully", application
    
    @staticmethod
    @transaction.atomic
    def _start_screening(application):
        """
        Start the screening workflow at constituency level.
        """
        # Update application status
        application.status = 'constituency_review'
        application.current_review_level = 'constituency'
        application.save()
        
        # Create queue entry at constituency level
        queue_item = ApplicationQueue.objects.create(
            application=application,
            review_level='constituency',
            status='pending',
            priority=application.priority_score,
            sla_due_date=timezone.now() + timedelta(days=ApplicationScreeningService.SLA_DAYS['constituency'])
        )
        
        # Try to auto-assign to extension officer
        ApplicationScreeningService._auto_assign_officer(queue_item)
        
        # TODO: Send email/SMS notification to applicant
        # TODO: Notify assigned officer
    
    @staticmethod
    @transaction.atomic
    def approve_at_level(application, reviewer, review_level, notes=""):
        """
        Approve application at current review level.
        
        Args:
            application: FarmApplication object
            reviewer: User object
            review_level: str ('constituency', 'regional', 'national')
            notes: str
        
        Returns:
            (success: bool, message: str, next_level: str or None)
        """
        # Validate
        if application.current_review_level != review_level:
            return False, f"Application is not at {review_level} review level", None
        
        if not ApplicationScreeningService._validate_reviewer_role(reviewer, review_level):
            return False, f"User does not have permission to review at {review_level} level", None
        
        # Get queue item
        queue_item = ApplicationQueue.objects.filter(
            application=application,
            review_level=review_level,
            status__in=['pending', 'claimed', 'in_progress']
        ).first()
        
        if queue_item:
            queue_item.status = 'completed'
            queue_item.completed_at = timezone.now()
            queue_item.save()
        
        # Create review action
        ApplicationReviewAction.objects.create(
            application=application,
            reviewer=reviewer,
            review_level=review_level,
            action='approved',
            notes=notes or f'Approved at {review_level} level'
        )
        
        # Update approval timestamps
        if review_level == 'constituency':
            application.constituency_approved_at = timezone.now()
            application.constituency_approved_by = reviewer
        elif review_level == 'regional':
            application.regional_approved_at = timezone.now()
            application.regional_approved_by = reviewer
        elif review_level == 'national':
            application.final_approved_at = timezone.now()
            application.final_approved_by = reviewer
        
        # Determine next level
        next_level = ApplicationScreeningService._get_next_review_level(review_level)
        
        if next_level:
            # Advance to next level
            application.status = f'{next_level}_review'
            application.current_review_level = next_level
            application.save()
            
            # Create queue entry for next level
            new_queue_item = ApplicationQueue.objects.create(
                application=application,
                review_level=next_level,
                status='pending',
                priority=application.priority_score,
                sla_due_date=timezone.now() + timedelta(days=ApplicationScreeningService.SLA_DAYS[next_level])
            )
            
            # Auto-assign
            ApplicationScreeningService._auto_assign_officer(new_queue_item)
            
            # TODO: Notify applicant of progress
            # TODO: Notify next level officer
            
            return True, f"Approved at {review_level} level. Advanced to {next_level} level.", next_level
        
        else:
            # Final approval - send invitation
            application.status = 'approved'
            application.current_review_level = None
            application.save()
            
            # Create invitation for account creation
            invitation = InvitationService.create_invitation(
                officer=reviewer,
                constituency=application.primary_constituency,
                invitation_type='government_program' if application.application_type == 'government_program' else 'independent_farmer',
                recipient_email=application.email,
                recipient_phone=application.primary_phone,
                recipient_name=application.full_name,
                is_single_use=True,
                expires_in_days=30,
                notes=f"Approved application {application.application_number}"
            )
            
            # Link invitation to application
            application.invitation = invitation
            application.invitation_sent_at = timezone.now()
            application.save()
            
            # Send invitation
            if application.email:
                InvitationService.send_invitation_email(invitation, custom_message=f"""
Dear {application.full_name},

Congratulations! Your farm application ({application.application_number}) has been approved!

You can now create your account and complete your farm registration.

Your invitation code: {invitation.invitation_code}

This invitation is valid for 30 days.

Best regards,
Poultry Management System Team
                """)
            
            if application.primary_phone:
                InvitationService.send_invitation_sms(invitation, custom_message=f"Congratulations! Your farm application is approved. Code: {invitation.invitation_code}. Valid 30 days.")
            
            return True, f"Final approval granted. Invitation sent to {application.email or application.primary_phone}", None
    
    @staticmethod
    @transaction.atomic
    def reject_at_level(application, reviewer, review_level, reason):
        """
        Reject application at current review level.
        """
        if not reason:
            return False, "Rejection reason is required"
        
        if application.current_review_level != review_level:
            return False, f"Application is not at {review_level} review level"
        
        if not ApplicationScreeningService._validate_reviewer_role(reviewer, review_level):
            return False, f"User does not have permission to review at {review_level} level"
        
        # Get queue item
        queue_item = ApplicationQueue.objects.filter(
            application=application,
            review_level=review_level,
            status__in=['pending', 'claimed', 'in_progress']
        ).first()
        
        if queue_item:
            queue_item.status = 'completed'
            queue_item.completed_at = timezone.now()
            queue_item.save()
        
        # Create review action
        ApplicationReviewAction.objects.create(
            application=application,
            reviewer=reviewer,
            review_level=review_level,
            action='rejected',
            notes=reason
        )
        
        # Update application
        application.status = 'rejected'
        application.rejection_reason = reason
        application.rejected_at = timezone.now()
        application.rejected_by = reviewer
        application.current_review_level = None
        application.save()
        
        # TODO: Send rejection notification
        
        return True, "Application rejected"
    
    @staticmethod
    @transaction.atomic
    def request_changes(application, reviewer, review_level, requested_changes, deadline_days=14):
        """
        Request changes/additional information from applicant.
        """
        if application.current_review_level != review_level:
            return False, f"Application is not at {review_level} review level"
        
        if not ApplicationScreeningService._validate_reviewer_role(reviewer, review_level):
            return False, f"User does not have permission to review at {review_level} level"
        
        # Create review action
        ApplicationReviewAction.objects.create(
            application=application,
            reviewer=reviewer,
            review_level=review_level,
            action='request_changes',
            notes=f"Changes requested: {requested_changes}"
        )
        
        # Update application
        application.status = 'changes_requested'
        application.changes_requested = requested_changes
        application.changes_deadline = timezone.now() + timedelta(days=deadline_days)
        application.save()
        
        # TODO: Notify applicant
        
        return True, f"Changes requested. Applicant has {deadline_days} days to respond."
    
    @staticmethod
    def get_review_queue(review_level, officer=None, status='pending'):
        """
        Get review queue for a specific level.
        """
        queryset = ApplicationQueue.objects.filter(
            review_level=review_level,
            status=status
        ).select_related('application', 'assigned_to')
        
        if officer:
            queryset = queryset.filter(assigned_to=officer)
        
        return queryset.order_by('-priority', 'entered_queue_at')
    
    @staticmethod
    def claim_for_review(queue_item, officer):
        """
        Officer claims an application for review.
        """
        if queue_item.status != 'pending':
            return False, f"Cannot claim application with status '{queue_item.status}'"
        
        if not ApplicationScreeningService._validate_reviewer_role(officer, queue_item.review_level):
            return False, f"User does not have permission to review at {queue_item.review_level} level"
        
        queue_item.claim(officer)
        return True, f"Application claimed by {officer.get_full_name()}"
    
    @staticmethod
    @transaction.atomic
    def create_account_from_application(application, invitation_code, password):
        """
        Create user account and farm profile from approved application.
        Called when farmer uses invitation to register.
        
        Args:
            application: FarmApplication object
            invitation_code: str (to validate invitation)
            password: str (for new account)
        
        Returns:
            (success: bool, message: str, user: User or None, farm: Farm or None)
        """
        from accounts.models import User
        from farms.models import Farm
        
        # Validate application is approved
        if not application.is_approved:
            return False, "Application is not approved", None, None
        
        # Validate invitation
        if not application.invitation or application.invitation.invitation_code != invitation_code:
            return False, "Invalid invitation code", None, None
        
        if not application.invitation.is_valid:
            return False, "Invitation has expired or already used", None, None
        
        # Check if account already created
        if application.user_account:
            return False, "Account already created for this application", None, None
        
        # Create user account
        user = User.objects.create_user(
            email=application.email,
            phone=application.primary_phone,
            password=password,
            first_name=application.first_name,
            middle_name=application.middle_name,
            last_name=application.last_name,
            role=UserRole.FARMER
        )
        
        # Link user to application
        application.user_account = user
        application.account_created_at = timezone.now()
        
        # Create farm profile from application
        farm = Farm.objects.create(
            user=user,
            first_name=application.first_name,
            middle_name=application.middle_name,
            last_name=application.last_name,
            date_of_birth=application.date_of_birth,
            gender=application.gender,
            ghana_card_number=application.ghana_card_number,
            primary_phone=application.primary_phone,
            alternate_phone=application.alternate_phone,
            email=application.email,
            residential_address=application.residential_address,
            primary_constituency=application.primary_constituency,
            farm_name=application.proposed_farm_name,
            primary_production_type=application.primary_production_type,
            total_bird_capacity=application.planned_bird_capacity,
            years_in_poultry=application.years_in_poultry,
            registration_source='government_initiative' if application.application_type == 'government_program' else 'self_registered',
            yea_program_batch=application.yea_program_batch,
            referral_source=application.referral_source,
            application_status='Approved',
            farm_status='Active',
            approval_date=application.final_approved_at,
            approved_by=application.final_approved_by,
            activation_date=timezone.now(),
        )
        
        # Generate Farm ID
        if application.application_type == 'government_program':
            farm.farm_id = ApplicationScreeningService._generate_farm_id(farm)
        
        # Assign extension officer if government program
        if application.assigned_extension_officer:
            farm.extension_officer = application.assigned_extension_officer
        
        farm.save()
        
        # Link farm to application
        application.farm_profile = farm
        application.farm_created_at = timezone.now()
        application.status = 'account_created'
        application.save()
        
        # Mark invitation as used
        application.invitation.use(user)
        
        return True, "Account and farm profile created successfully", user, farm
    
    # Helper methods
    
    @staticmethod
    def _get_next_review_level(current_level):
        """Get next review level"""
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
        """Validate user has appropriate role"""
        from accounts.models import User
        
        role_mapping = {
            'constituency': [User.UserRole.CONSTITUENCY_OFFICIAL],
            'regional': [User.UserRole.CONSTITUENCY_OFFICIAL, User.UserRole.NATIONAL_ADMIN],
            'national': [User.UserRole.NATIONAL_ADMIN],
        }
        required_roles = role_mapping.get(review_level, [])
        return user.role in required_roles or user.is_superuser
    
    @staticmethod
    def _auto_assign_officer(queue_item):
        """Auto-assign queue item to officer"""
        from accounts.models import User
        
        role_mapping = {
            'constituency': User.UserRole.CONSTITUENCY_OFFICIAL,
            'regional': User.UserRole.CONSTITUENCY_OFFICIAL,
            'national': User.UserRole.NATIONAL_ADMIN,
        }
        
        target_role = role_mapping.get(queue_item.review_level)
        if not target_role:
            return
        
        officers = User.objects.filter(role=target_role, is_active=True)
        
        if officers.exists():
            from django.db.models import Count
            officer = officers.annotate(
                assignment_count=Count('assigned_application_reviews')
            ).order_by('assignment_count').first()
            
            if officer:
                queue_item.assigned_to = officer
                queue_item.assigned_at = timezone.now()
                queue_item.auto_assigned = True
                queue_item.save()
    
    @staticmethod
    def _generate_farm_id(farm):
        """Generate unique Farm ID for government farmers"""
        from farms.models import Farm
        import re
        
        const_abbrev = re.sub(r'[^A-Z]', '', farm.primary_constituency.upper())[:4]
        if not const_abbrev:
            const_abbrev = 'UNKN'
        
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
        """Get applications past SLA deadline"""
        queryset = ApplicationQueue.objects.filter(
            status__in=['pending', 'claimed', 'in_progress'],
            sla_due_date__lt=timezone.now()
        )
        
        if review_level:
            queryset = queryset.filter(review_level=review_level)
        
        queryset.update(is_overdue=True)
        return queryset.order_by('sla_due_date')
