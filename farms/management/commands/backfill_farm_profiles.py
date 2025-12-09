"""
Management command to backfill missing farm profiles for approved applications.
This handles cases where applications were approved but farm profiles were not created.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from farms.application_models import FarmApplication
from farms.models import Farm
from accounts.models import User


class Command(BaseCommand):
    help = 'Backfill missing farm profiles for approved applications with user accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )
        parser.add_argument(
            '--application-id',
            type=str,
            help='Backfill specific application by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_app_id = options.get('application_id')
        
        # Find approved applications with user accounts but no farm profiles
        query = FarmApplication.objects.filter(
            status='approved',
            user_account__isnull=False,
            farm_profile__isnull=True
        )
        
        if specific_app_id:
            query = query.filter(id=specific_app_id)
        
        applications = query.select_related('user_account', 'final_approved_by')
        count = applications.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No applications need backfilling.'))
            return
        
        self.stdout.write(f'Found {count} application(s) needing farm profile backfill.')
        
        created_count = 0
        failed_count = 0
        
        for application in applications:
            self.stdout.write(f'\nProcessing application {application.application_number}...')
            self.stdout.write(f'  Farmer: {application.first_name} {application.last_name}')
            self.stdout.write(f'  Email: {application.email}')
            self.stdout.write(f'  User ID: {application.user_account.id}')
            
            if dry_run:
                self.stdout.write(self.style.WARNING('  [DRY RUN] Would create farm profile'))
                created_count += 1
                continue
            
            try:
                from datetime import date
                
                farm = Farm.objects.create(
                    user=application.user_account,
                    # Section 1: Personal Identity
                    first_name=application.first_name,
                    middle_name=application.middle_name or '',
                    last_name=application.last_name,
                    date_of_birth=application.date_of_birth,
                    gender=application.gender,
                    ghana_card_number=application.ghana_card_number,
                    marital_status='Single',
                    number_of_dependents=0,
                    # Section 1.2: Contact
                    primary_phone=application.primary_phone,
                    alternate_phone=application.alternate_phone or '',
                    email=application.email,
                    preferred_contact_method='Phone Call',
                    residential_address=application.residential_address or '',
                    primary_constituency=application.primary_constituency,
                    # Section 1.3: Next of Kin (required)
                    nok_full_name='To be provided',
                    nok_relationship='To be provided',
                    nok_phone=application.primary_phone,
                    # Section 1.4: Education & Experience
                    education_level='JHS',
                    literacy_level='Can Read & Write',
                    years_in_poultry=application.years_in_poultry or 0,
                    farming_full_time=True,
                    # Section 2: Business Information
                    farm_name=application.proposed_farm_name,
                    ownership_type='Sole Proprietorship',
                    tin=f'{application.id.int % 10000000000:010d}',  # 10 digit numeric TIN
                    # Section 4: Infrastructure
                    number_of_poultry_houses=1,
                    total_bird_capacity=application.planned_bird_capacity,
                    current_bird_count=0,
                    housing_type='Deep Litter',
                    total_infrastructure_value_ghs=0,
                    # Section 5: Production Planning
                    primary_production_type=application.primary_production_type,
                    planned_production_start_date=date.today(),
                    # Section 7: Financial Information (required)
                    initial_investment_amount=0,
                    funding_source=['YEA Program'],
                    monthly_operating_budget=0,
                    expected_monthly_revenue=0,
                    has_outstanding_debt=False,
                    # Section 9: Application Workflow
                    application_status='Approved',
                    farm_status='Pending Setup',
                    approval_date=application.final_approved_at,
                    approved_by=application.final_approved_by,
                    activation_date=timezone.now(),
                    registration_source='government_initiative' if application.application_type == 'government_program' else 'self_registered',
                    yea_program_batch=application.yea_program_batch or '',
                    referral_source=application.referral_source or 'Direct Application',
                )
                
                # Link farm to application
                application.farm_profile = farm
                application.farm_created_at = timezone.now()
                application.save()
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created farm profile: {farm.farm_name} (ID: {farm.id})'))
                created_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to create farm profile: {e}'))
                failed_count += 1
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(f'  Total applications processed: {count}')
        self.stdout.write(self.style.SUCCESS(f'  Successfully created: {created_count}'))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f'  Failed: {failed_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. No changes were made.'))
            self.stdout.write('Run without --dry-run to create farm profiles.')
