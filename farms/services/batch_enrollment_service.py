"""
Program Enrollment Screening Service

Handles screening and approval of EXISTING farmers applying to join
government programs (YEA, etc.).

Similar to ApplicationScreeningService but for farmers who already have
accounts and farms registered on the platform.
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import User
from accounts.roles import UserRole
from farms.models import Farm
from farms.batch_enrollment_models import (
    Batch,
    BatchEnrollmentApplication,
    BatchEnrollmentReview,
    ProgramEnrollmentQueue
)
from datetime import timedelta, date


class ProgramEnrollmentService:
    """
    Service for managing program enrollment applications from existing farmers.
    """
    
    # SLA days for each review level
    SLA_DAYS = {
        'eligibility': 1,      # Automated check
        'constituency': 7,     # 1 week at constituency
        'regional': 5,         # 5 days at regional
        'national': 3,         # 3 days at national
    }
    
    @classmethod
    @transaction.atomic
    def submit_application(cls, farm, program, application_data, applicant):
        """
        Submit program enrollment application from existing farmer.
        
        Args:
            farm: Farm instance (existing farm)
            program: Batch instance
            application_data: Dict with application details
            applicant: User (farm owner submitting application)
        
        Returns:
            BatchEnrollmentApplication instance
        """
        # Validate program is accepting applications
        if not program.is_accepting_applications:
            raise ValidationError(
                f"Program {program.batch_name} is not currently accepting applications."
            )
        
        # Check if farm already enrolled in this program
        existing = BatchEnrollmentApplication.objects.filter(
            farm=farm,
            program=program,
            status__in=['submitted', 'constituency_review', 'regional_review', 
                       'national_review', 'approved', 'enrolled']
        ).first()
        
        if existing:
            raise ValidationError(
                f"Farm already has an active application for this program: {existing.application_number}"
            )
        
        # Check if farm already enrolled in similar programs
        if farm.registration_source == 'government_initiative' and farm.yea_program_batch:
            raise ValidationError(
                f"Farm is already enrolled in YEA program: {farm.yea_program_batch}"
            )
        
        # Create application
        application = BatchEnrollmentApplication.objects.create(
            farm=farm,
            program=program,
            applicant=applicant,
            motivation=application_data.get('motivation', ''),
            current_challenges=application_data.get('current_challenges', ''),
            expected_benefits=application_data.get('expected_benefits', ''),
            current_bird_count=application_data.get('current_bird_count', 0),
            current_production_type=application_data.get('current_production_type', 'Both'),
            monthly_revenue=application_data.get('monthly_revenue'),
            years_operational=application_data.get('years_operational', 0),
            farm_photos=application_data.get('farm_photos', []),
            business_documents=application_data.get('business_documents', []),
            status='submitted',
            submitted_at=timezone.now()
        )
        
        # Run eligibility check
        cls._run_eligibility_check(application)
        
        # If passed eligibility, start screening workflow
        if application.meets_eligibility:
            cls._start_screening_workflow(application)
        else:
            # Auto-reject if failed eligibility
            application.status = 'rejected'
            application.rejection_reason = 'ineligible'
            application.rejection_notes = '; '.join(application.eligibility_flags)
            application.final_decision_at = timezone.now()
            application.save()
            
            # Log rejection
            BatchEnrollmentReview.objects.create(
                application=application,
                reviewer=None,  # Automated
                review_level='eligibility',
                action='eligibility_failed',
                notes=application.rejection_notes
            )
        
        return application
    
    @classmethod
    def _run_eligibility_check(cls, application):
        """
        Run automated eligibility checks against program criteria.
        """
        program = application.program_batch
        farm = application.farm
        farmer = application.applicant
        
        eligibility_flags = []
        eligibility_score = 100  # Start at 100, deduct for failures
        
        # 1. Check farmer age
        if farmer.date_of_birth:
            age = (date.today() - farmer.date_of_birth).days // 365
            if age < program.eligible_farmer_age_min:
                eligibility_flags.append(f"Farmer age ({age}) below minimum ({program.eligible_farmer_age_min})")
                eligibility_score -= 30
            elif age > program.eligible_farmer_age_max:
                eligibility_flags.append(f"Farmer age ({age}) above maximum ({program.eligible_farmer_age_max})")
                eligibility_score -= 30
        
        # 2. Check farm operational duration
        years_op = float(application.years_operational)
        months_op = years_op * 12
        
        if program.min_farm_age_months > 0 and months_op < program.min_farm_age_months:
            eligibility_flags.append(
                f"Farm operational for {months_op:.0f} months, requires {program.min_farm_age_months}"
            )
            eligibility_score -= 25
        
        if program.max_farm_age_years and years_op > program.max_farm_age_years:
            eligibility_flags.append(
                f"Farm too established ({years_op:.1f} years), program targets farms < {program.max_farm_age_years} years"
            )
            eligibility_score -= 25
        
        # 3. Check bird capacity
        bird_count = application.current_bird_count
        
        if program.min_bird_capacity and bird_count < program.min_bird_capacity:
            eligibility_flags.append(
                f"Current capacity ({bird_count}) below minimum ({program.min_bird_capacity})"
            )
            eligibility_score -= 20
        
        if program.max_bird_capacity and bird_count > program.max_bird_capacity:
            eligibility_flags.append(
                f"Current capacity ({bird_count}) above maximum ({program.max_bird_capacity})"
            )
            eligibility_score -= 20
        
        # 4. Check constituency eligibility
        if program.eligible_constituencies:
            if farm.primary_constituency not in program.eligible_constituencies:
                eligibility_flags.append(
                    f"Farm constituency ({farm.primary_constituency}) not in eligible list"
                )
                eligibility_score -= 40
        
        # 5. Check application deadline
        if program.application_deadline and date.today() > program.application_deadline:
            eligibility_flags.append(
                f"Application deadline passed: {program.application_deadline}"
            )
            eligibility_score -= 50
        
        # 6. Check program capacity
        if program.slots_available <= 0:
            eligibility_flags.append("Program slots full")
            eligibility_score -= 50
        
        # 7. Check if farm already government-sponsored
        if farm.registration_source == 'government_initiative':
            # Award bonus points for existing government farmers (easier transition)
            eligibility_score += 10
        
        # 8. Check documentation completeness
        if not application.business_documents:
            eligibility_flags.append("No business documents uploaded")
            eligibility_score -= 10
        
        if not application.farm_photos:
            eligibility_flags.append("No farm photos uploaded")
            eligibility_score -= 10
        
        # Update application
        application.eligibility_score = max(0, min(100, eligibility_score))
        application.eligibility_flags = eligibility_flags
        application.meets_eligibility = eligibility_score >= 50  # Pass threshold
        application.save()
        
        # Log eligibility check
        BatchEnrollmentReview.objects.create(
            application=application,
            reviewer=None,  # Automated
            review_level='eligibility',
            action='eligibility_passed' if application.meets_eligibility else 'eligibility_failed',
            notes=f"Eligibility score: {application.eligibility_score}/100. " + 
                  ("; ".join(eligibility_flags) if eligibility_flags else "All checks passed")
        )
    
    @classmethod
    def _start_screening_workflow(cls, application):
        """
        Start 3-tier screening workflow.
        """
        # Update status
        application.status = 'constituency_review'
        application.current_review_level = 'constituency'
        application.calculate_priority_score()
        application.save()
        
        # Create queue entry for constituency review
        sla_deadline = timezone.now() + timedelta(days=cls.SLA_DAYS['constituency'])
        
        ProgramEnrollmentQueue.objects.create(
            application=application,
            review_level='constituency',
            priority=application.priority_score,
            sla_deadline=sla_deadline
        )
        
        # Log workflow start
        BatchEnrollmentReview.objects.create(
            application=application,
            reviewer=None,
            review_level='constituency',
            action='submitted',
            notes="Application entered constituency review queue"
        )
    
    @classmethod
    @transaction.atomic
    def approve_at_level(cls, application, reviewer, notes=''):
        """
        Approve application at current review level.
        Moves to next level or completes enrollment.
        """
        current_level = application.current_review_level
        
        # Validate reviewer has appropriate role
        cls._validate_reviewer_role(reviewer, current_level)
        
        # Mark current queue entry as completed
        queue_entry = ProgramEnrollmentQueue.objects.filter(
            application=application,
            review_level=current_level,
            status__in=['pending', 'assigned', 'in_review']
        ).first()
        
        if queue_entry:
            queue_entry.status = 'completed'
            queue_entry.completed_at = timezone.now()
            queue_entry.save()
        
        # Log approval at this level
        BatchEnrollmentReview.objects.create(
            application=application,
            reviewer=reviewer,
            review_level=current_level,
            action='approved',
            notes=notes or f"Approved at {current_level} level"
        )
        
        # Update approval timestamp
        timestamp_field = f"{current_level}_reviewed_at"
        if hasattr(application, timestamp_field):
            setattr(application, timestamp_field, timezone.now())
        
        # Determine next step
        if current_level == 'constituency':
            # Move to regional
            application.current_review_level = 'regional'
            application.status = 'regional_review'
            application.save()
            
            # Create regional queue entry
            sla_deadline = timezone.now() + timedelta(days=cls.SLA_DAYS['regional'])
            ProgramEnrollmentQueue.objects.create(
                application=application,
                review_level='regional',
                priority=application.priority_score,
                sla_deadline=sla_deadline
            )
        
        elif current_level == 'regional':
            # Move to national
            application.current_review_level = 'national'
            application.status = 'national_review'
            application.save()
            
            # Create national queue entry
            sla_deadline = timezone.now() + timedelta(days=cls.SLA_DAYS['national'])
            ProgramEnrollmentQueue.objects.create(
                application=application,
                review_level='national',
                priority=application.priority_score,
                sla_deadline=sla_deadline
            )
        
        elif current_level == 'national':
            # FINAL APPROVAL - Complete enrollment
            cls._complete_enrollment(application, reviewer, notes)
        
        return application
    
    @classmethod
    @transaction.atomic
    def _complete_enrollment(cls, application, approver, notes=''):
        """
        Complete enrollment after final approval.
        Updates farm to government-sponsored status.
        """
        farm = application.farm
        program = application.program_batch
        
        # Update farm to government-sponsored
        farm.registration_source = 'government_initiative'
        farm.yea_program_batch = program.batch_code
        farm.yea_program_start_date = timezone.now().date()
        
        # Calculate program end date based on program duration
        program_duration_days = (program.end_date - program.start_date).days
        farm.yea_program_end_date = timezone.now().date() + timedelta(days=program_duration_days)
        
        # Assign extension officer (if required and not already assigned)
        if program.requires_extension_officer and not farm.extension_officer:
            # Try to assign from application or auto-assign
            if application.assigned_extension_officer:
                farm.extension_officer = application.assigned_extension_officer
            # else: Could implement auto-assignment logic here
        
        # Set support package
        farm.government_support_package = application.support_package_allocated or program.support_package_details
        
        farm.save()
        
        # Update application status
        application.status = 'enrolled'
        application.approved = True
        application.enrollment_completed = True
        application.enrolled_at = timezone.now()
        application.final_decision_at = timezone.now()
        application.save()
        
        # Decrement program available slots
        program.slots_filled += 1
        program.save()  # Auto-calculates slots_available
        
        # Log enrollment completion
        BatchEnrollmentReview.objects.create(
            application=application,
            reviewer=approver,
            review_level='national',
            action='enrolled',
            notes=notes or f"Enrollment completed. Farm {farm.farm_id} now in {program.batch_code}"
        )
        
        # TODO: Send notification to farmer
        # TODO: Notify extension officer of new assignment
        
        return application
    
    @classmethod
    @transaction.atomic
    def reject_at_level(cls, application, reviewer, rejection_reason, rejection_notes=''):
        """
        Reject application at current review level.
        """
        current_level = application.current_review_level
        
        # Validate reviewer
        cls._validate_reviewer_role(reviewer, current_level)
        
        # Mark queue as completed
        queue_entry = ProgramEnrollmentQueue.objects.filter(
            application=application,
            review_level=current_level,
            status__in=['pending', 'assigned', 'in_review']
        ).first()
        
        if queue_entry:
            queue_entry.status = 'completed'
            queue_entry.completed_at = timezone.now()
            queue_entry.save()
        
        # Update application
        application.status = 'rejected'
        application.approved = False
        application.rejection_reason = rejection_reason
        application.rejection_notes = rejection_notes
        application.final_decision_at = timezone.now()
        application.save()
        
        # Log rejection
        BatchEnrollmentReview.objects.create(
            application=application,
            reviewer=reviewer,
            review_level=current_level,
            action='rejected',
            notes=f"Reason: {rejection_reason}. {rejection_notes}"
        )
        
        # TODO: Send rejection notification to farmer
        
        return application
    
    @classmethod
    @transaction.atomic
    def request_changes(cls, application, reviewer, requested_changes):
        """
        Request changes to application before approval.
        """
        current_level = application.current_review_level
        
        # Validate reviewer
        cls._validate_reviewer_role(reviewer, current_level)
        
        # Update status
        application.status = 'changes_requested'
        application.reviewer_notes = requested_changes
        application.save()
        
        # Mark queue as temporarily completed (will return when resubmitted)
        queue_entry = ProgramEnrollmentQueue.objects.filter(
            application=application,
            review_level=current_level,
            status__in=['pending', 'assigned', 'in_review']
        ).first()
        
        if queue_entry:
            queue_entry.status = 'completed'
            queue_entry.completed_at = timezone.now()
            queue_entry.save()
        
        # Log changes request
        BatchEnrollmentReview.objects.create(
            application=application,
            reviewer=reviewer,
            review_level=current_level,
            action='changes_requested',
            notes=requested_changes
        )
        
        # TODO: Send notification to farmer
        
        return application
    
    @classmethod
    @transaction.atomic
    def resubmit_application(cls, application, updated_data):
        """
        Farmer resubmits application after making requested changes.
        """
        if application.status != 'changes_requested':
            raise ValidationError("Can only resubmit applications in 'changes_requested' status")
        
        # Update application data
        for field, value in updated_data.items():
            if hasattr(application, field):
                setattr(application, field, value)
        
        # Return to review at current level
        level = application.current_review_level
        application.status = f"{level}_review"
        application.save()
        
        # Create new queue entry
        sla_deadline = timezone.now() + timedelta(days=cls.SLA_DAYS[level])
        ProgramEnrollmentQueue.objects.create(
            application=application,
            review_level=level,
            priority=application.priority_score,
            sla_deadline=sla_deadline
        )
        
        # Log resubmission
        BatchEnrollmentReview.objects.create(
            application=application,
            reviewer=None,
            review_level=level,
            action='submitted',
            notes="Application resubmitted with requested changes"
        )
        
        return application
    
    @classmethod
    def get_review_queue(cls, review_level, constituency=None, assigned_to=None):
        """
        Get queue of applications pending review at a specific level.
        """
        queue = ProgramEnrollmentQueue.objects.filter(
            review_level=review_level,
            status__in=['pending', 'assigned', 'in_review']
        ).select_related(
            'application',
            'application__farm',
            'application__program',
            'application__applicant',
            'assigned_to'
        )
        
        # Filter by constituency if specified
        if constituency:
            queue = queue.filter(application__farm__primary_constituency=constituency)
        
        # Filter by assigned officer
        if assigned_to:
            queue = queue.filter(assigned_to=assigned_to)
        
        return queue.order_by('-priority', 'sla_deadline')
    
    @classmethod
    @transaction.atomic
    def claim_for_review(cls, application, officer):
        """
        Officer claims an application for review.
        """
        current_level = application.current_review_level
        
        # Validate officer role
        cls._validate_reviewer_role(officer, current_level)
        
        # Find queue entry
        queue_entry = ProgramEnrollmentQueue.objects.filter(
            application=application,
            review_level=current_level,
            status='pending'
        ).first()
        
        if not queue_entry:
            raise ValidationError("Application not available for claiming")
        
        # Claim it
        queue_entry.claim(officer)
        
        # Log claim
        BatchEnrollmentReview.objects.create(
            application=application,
            reviewer=officer,
            review_level=current_level,
            action='claimed',
            notes=f"Application claimed for review by {officer.get_full_name()}"
        )
        
        return application
    
    @classmethod
    def _validate_reviewer_role(cls, reviewer, review_level):
        """
        Validate reviewer has appropriate role for this review level.
        """
        user_role = reviewer.role
        
        required_roles = {
            'constituency': [UserRole.CONSTITUENCY_OFFICER, UserRole.ADMIN],
            'regional': [UserRole.REGIONAL_OFFICER, UserRole.ADMIN],
            'national': [UserRole.NATIONAL_OFFICER, UserRole.ADMIN],
        }
        
        if user_role not in required_roles.get(review_level, []):
            raise ValidationError(
                f"User role {user_role} not authorized for {review_level} level review"
            )
    
    @classmethod
    def get_farmer_applications(cls, farmer):
        """
        Get all program applications for a farmer.
        """
        farms = Farm.objects.filter(farmer=farmer)
        return BatchEnrollmentApplication.objects.filter(
            farm__in=farms
        ).select_related('farm', 'program').order_by('-created_at')
    
    @classmethod
    def get_program_statistics(cls, program):
        """
        Get statistics for a program.
        """
        applications = BatchEnrollmentApplication.objects.filter(batch=program)
        
        return {
            'total_applications': applications.count(),
            'pending': applications.filter(status__in=[
                'submitted', 'constituency_review', 'regional_review', 'national_review'
            ]).count(),
            'approved': applications.filter(status='approved').count(),
            'enrolled': applications.filter(status='enrolled').count(),
            'rejected': applications.filter(status='rejected').count(),
            'slots_total': program.total_slots,
            'slots_filled': program.slots_filled,
            'slots_available': program.slots_available,
            'acceptance_rate': (
                applications.filter(approved=True).count() / applications.count() * 100
                if applications.count() > 0 else 0
            ),
        }
