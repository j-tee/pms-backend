"""
Test Approval Workflow

Creates sample data and tests the complete approval workflow:
1. Submit application
2. Officer claims for review
3. Approve through all levels
4. Test rejection flow
5. Test change request flow
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from farms.models import Farm, FarmReviewAction, FarmApprovalQueue, FarmNotification
from farms.services.approval_workflow import FarmApprovalWorkflowService
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the farm approval workflow with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Clean up test data after running',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Testing Farm Approval Workflow ===\n'))
        
        # Create test users
        farmer, const_officer, regional_officer, national_admin = self.create_test_users()
        
        # Create test farm
        farm = self.create_test_farm(farmer)
        
        # Initialize workflow service
        workflow = FarmApprovalWorkflowService()
        
        # Test 1: Submit Application
        self.stdout.write('\n--- Test 1: Submit Application ---')
        workflow.submit_application(farm)
        farm.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Application submitted: {farm.application_status}'))
        self.stdout.write(f'  Current level: {farm.current_review_level}')
        
        # Check queue created
        queue_entry = FarmApprovalQueue.objects.filter(farm=farm, review_level='constituency').first()
        if queue_entry:
            self.stdout.write(self.style.SUCCESS(f'✓ Queue entry created with SLA due date: {queue_entry.sla_due_date}'))
        
        # Check notifications
        notif_count = FarmNotification.objects.filter(farm=farm).count()
        self.stdout.write(self.style.SUCCESS(f'✓ {notif_count} notifications created'))
        
        # Test 2: Constituency Officer Claims
        self.stdout.write('\n--- Test 2: Officer Claims for Review ---')
        workflow.claim_for_review(farm, const_officer, 'constituency')
        farm.refresh_from_db()
        queue_entry.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Farm claimed: {farm.application_status}'))
        self.stdout.write(f'  Assigned to: {queue_entry.assigned_to.get_full_name()}')
        
        # Test 3: Constituency Approval
        self.stdout.write('\n--- Test 3: Constituency Approval ---')
        workflow.approve_and_forward(
            farm, 
            const_officer, 
            'constituency',
            'Farm meets all constituency requirements. Location verified.'
        )
        farm.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Approved at constituency: {farm.application_status}'))
        self.stdout.write(f'  Current level: {farm.current_review_level}')
        self.stdout.write(f'  Constituency approved at: {farm.constituency_approved_at}')
        
        # Check regional queue created
        regional_queue = FarmApprovalQueue.objects.filter(farm=farm, review_level='regional').first()
        if regional_queue:
            self.stdout.write(self.style.SUCCESS(f'✓ Regional queue entry created'))
        
        # Test 4: Regional Officer Claims
        self.stdout.write('\n--- Test 4: Regional Officer Claims ---')
        workflow.claim_for_review(farm, regional_officer, 'regional')
        farm.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Farm claimed at regional level'))
        
        # Test 5: Regional Approval
        self.stdout.write('\n--- Test 5: Regional Approval ---')
        workflow.approve_and_forward(
            farm,
            regional_officer,
            'regional',
            'Farm infrastructure verified. Production plan is sound.'
        )
        farm.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Approved at regional: {farm.application_status}'))
        self.stdout.write(f'  Current level: {farm.current_review_level}')
        self.stdout.write(f'  Regional approved at: {farm.regional_approved_at}')
        
        # Test 6: National Admin Claims
        self.stdout.write('\n--- Test 6: National Admin Claims ---')
        workflow.claim_for_review(farm, national_admin, 'national')
        farm.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Farm claimed at national level'))
        
        # Test 7: Final Approval with Farm ID
        self.stdout.write('\n--- Test 7: Final Approval & Farm ID Assignment ---')
        workflow.finalize_approval(
            farm,
            national_admin,
            'All requirements met. Welcome to YEA program.'
        )
        farm.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ FINAL APPROVAL: {farm.application_status}'))
        self.stdout.write(self.style.WARNING(f'  🎉 Farm ID Assigned: {farm.farm_id}'))
        self.stdout.write(f'  Farm Status: {farm.farm_status}')
        self.stdout.write(f'  Final approved at: {farm.final_approved_at}')
        
        # Test 8: Review Actions Audit Trail
        self.stdout.write('\n--- Test 8: Audit Trail ---')
        actions = FarmReviewAction.objects.filter(farm=farm).order_by('created_at')
        self.stdout.write(f'Total actions recorded: {actions.count()}')
        for action_record in actions:
            self.stdout.write(f'  [{action_record.created_at.strftime("%Y-%m-%d %H:%M")}] '
                            f'{action_record.action} by {action_record.reviewer.get_full_name()} '
                            f'at {action_record.review_level} level')
        
        # Test 9: Notifications Summary
        self.stdout.write('\n--- Test 9: Notifications Summary ---')
        notifications = FarmNotification.objects.filter(farm=farm)
        for channel in ['email', 'sms', 'in_app']:
            channel_notifs = notifications.filter(channel=channel)
            sent = channel_notifs.filter(status='sent').count()
            total = channel_notifs.count()
            self.stdout.write(f'  {channel.upper()}: {sent}/{total} sent')
        
        # Test 10: Create another farm to test rejection
        self.stdout.write('\n--- Test 10: Test Rejection Flow ---')
        farmer2 = self.create_additional_farmer('2')
        farm2 = self.create_test_farm(farmer2, name_suffix='2')
        workflow.submit_application(farm2)
        workflow.claim_for_review(farm2, const_officer, 'constituency')
        workflow.reject_application(
            farm2,
            const_officer,
            'constituency',
            'Farm location does not meet minimum requirements. Infrastructure inadequate.'
        )
        farm2.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Farm rejected: {farm2.application_status}'))
        self.stdout.write(f'  Rejected at: {farm2.rejected_at}')
        
        # Test 11: Create another farm to test change request
        self.stdout.write('\n--- Test 11: Test Change Request Flow ---')
        farmer3 = self.create_additional_farmer('3')
        farm3 = self.create_test_farm(farmer3, name_suffix='3')
        workflow.submit_application(farm3)
        workflow.claim_for_review(farm3, const_officer, 'constituency')
        
        workflow.request_changes(
            farm3,
            const_officer,
            'constituency',
            'Please provide more details about water source and waste management.',
            [
                'Update water source information',
                'Add waste management plan',
                'Upload photos of housing infrastructure'
            ],
            7  # deadline_days
        )
        farm3.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Changes requested: {farm3.application_status}'))
        
        # Farmer resubmits
        workflow.farmer_submits_changes(farm3)
        farm3.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f'✓ Changes resubmitted: {farm3.application_status}'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ All workflow tests passed!'))
        self.stdout.write('='*60)
        
        self.stdout.write('\nTest Results Summary:')
        self.stdout.write(f'  Farm 1: {farm.farm_id} - APPROVED ✓')
        self.stdout.write(f'  Farm 2: {farm2.application_id} - REJECTED ✗')
        self.stdout.write(f'  Farm 3: {farm3.application_id} - CHANGES RESUBMITTED ⟳')
        
        self.stdout.write(f'\nTotal Review Actions: {FarmReviewAction.objects.count()}')
        self.stdout.write(f'Total Queue Entries: {FarmApprovalQueue.objects.count()}')
        self.stdout.write(f'Total Notifications: {FarmNotification.objects.count()}')
        
        # Cleanup if requested
        if options['clean']:
            self.stdout.write('\n--- Cleaning up test data ---')
            Farm.objects.filter(farm_name__startswith='Test Farm').delete()
            User.objects.filter(email__startswith='test_').delete()
            self.stdout.write(self.style.SUCCESS('✓ Test data cleaned up'))
        else:
            self.stdout.write('\n💡 Run with --clean flag to remove test data')
    
    def create_test_users(self):
        """Create test users for workflow"""
        self.stdout.write('Creating test users...')
        
        # Farmer
        farmer, _ = User.objects.get_or_create(
            email='test_farmer@example.com',
            defaults={
                'username': 'test_farmer',
                'first_name': 'Kwame',
                'last_name': 'Mensah',
                'phone': '+233244567890',
                'role': 'farmer',
            }
        )
        farmer.set_password('testpass123')
        farmer.save()
        
        # Constituency Officer
        const_officer, _ = User.objects.get_or_create(
            email='test_constituency@example.com',
            defaults={
                'username': 'test_constituency',
                'first_name': 'Ama',
                'last_name': 'Owusu',
                'phone': '+233244567891',
                'role': 'constituency_officer',
            }
        )
        const_officer.set_password('testpass123')
        const_officer.save()
        
        # Regional Officer
        regional_officer, _ = User.objects.get_or_create(
            email='test_regional@example.com',
            defaults={
                'username': 'test_regional',
                'first_name': 'Kofi',
                'last_name': 'Asante',
                'phone': '+233244567892',
                'role': 'regional_officer',
            }
        )
        regional_officer.set_password('testpass123')
        regional_officer.save()
        
        # National Admin
        national_admin, _ = User.objects.get_or_create(
            email='test_national@example.com',
            defaults={
                'username': 'test_national',
                'first_name': 'Akosua',
                'last_name': 'Boateng',
                'phone': '+233244567893',
                'role': 'national_admin',
            }
        )
        national_admin.set_password('testpass123')
        national_admin.save()
        
        self.stdout.write(self.style.SUCCESS('✓ Test users created'))
        return farmer, const_officer, regional_officer, national_admin
    
    def create_additional_farmer(self, suffix):
        """Create an additional farmer for testing"""
        farmer = User.objects.create(
            email=f'test_farmer{suffix}@example.com',
            username=f'test_farmer{suffix}',
            first_name=f'Farmer',
            last_name=f'Test{suffix}',
            phone=f'+23324456780{suffix}',
            role='farmer',
        )
        farmer.set_password('testpass123')
        farmer.save()
        return farmer
    
    def create_test_farm(self, farmer, name_suffix=''):
        """Create a test farm"""
        from datetime import date, timedelta
        
        farm = Farm.objects.create(
            user=farmer,
            
            # Personal Identity
            first_name='Kwame',
            last_name='Mensah',
            date_of_birth='1985-05-15',
            gender='Male',
            ghana_card_number=f'GHA-12345678{name_suffix or "9"}-1',
            marital_status='Married',
            number_of_dependents=2,
            
            # Contact
            primary_phone=f'+23324456789{name_suffix or "0"}',
            email=f'kwame{name_suffix}@example.com',
            preferred_contact_method='Phone Call',
            residential_address='123 Main Street, Accra',
            
            # Next of Kin
            nok_full_name='Ama Mensah',
            nok_relationship='Spouse',
            nok_phone='+233244567899',
            nok_residential_address='123 Main Street, Accra',
            
            # Education & Experience
            education_level='SHS/Technical',
            literacy_level='Can Read & Write',
            years_in_poultry=Decimal('5.0'),
            previous_training='Basic poultry management training',
            farming_full_time=True,
            other_occupation='',
            
            # Business
            farm_name=f'Test Farm {name_suffix}' if name_suffix else 'Test Farm',
            ownership_type='Sole Proprietorship',
            tin=f'123456789{name_suffix or "0"}',
            business_registration_number=f'BN12345{name_suffix}' if name_suffix else 'BN12345',
            
            # Banking - use unique value per farm to avoid constraint issues
            paystack_subaccount_code=f'TEST-SUB-{name_suffix or "0"}',
            
            # Infrastructure
            number_of_poultry_houses=2,
            total_bird_capacity=2000,
            current_bird_count=500,
            housing_type='Deep Litter',
            total_infrastructure_value_ghs=Decimal('50000.00'),
            
            # Production Planning
            primary_production_type='Broilers',
            planned_production_start_date=date.today() + timedelta(days=30),
            hatchery_operation=False,
            feed_formulation=False,
            
            # Financial Information
            initial_investment_amount=Decimal('50000.00'),
            funding_source=['Personal Savings', 'Family'],
            monthly_operating_budget=Decimal('5000.00'),
            expected_monthly_revenue=Decimal('10000.00'),
            has_outstanding_debt=False,
            
            # Status
            application_status='draft',
            farm_status='draft',
        )
        
        self.stdout.write(self.style.SUCCESS(f'✓ Test farm created: {farm.farm_name}'))
        return farm
