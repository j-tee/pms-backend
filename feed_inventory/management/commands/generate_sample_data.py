"""
Django Management Command: Generate Sample Data

Creates comprehensive sample data for all Phase 4 modules:
- Feed Inventory (types, suppliers, purchases, inventory, consumption)
- Medication Management (types, schedules, records, vaccinations, vet visits)

Usage:
    python manage.py generate_sample_data
    python manage.py generate_sample_data --clear  # Clear existing data first
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from accounts.models import User
from farms.models import Farm
from flock_management.models import Flock, DailyProduction
from feed_inventory.models import FeedType, FeedSupplier, FeedPurchase, FeedInventory, FeedConsumption
from medication_management.models import (
    MedicationType, VaccinationSchedule, MedicationRecord,
    VaccinationRecord, VetVisit
)


class Command(BaseCommand):
    help = 'Generate sample data for Feed Inventory and Medication Management modules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sample data before generating new data',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('  SAMPLE DATA GENERATION'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

        if options['clear']:
            self.clear_data()

        try:
            with transaction.atomic():
                # Get or create test user and farm
                user, farm, flock = self.create_base_data()
                
                # Generate Feed Inventory data
                self.stdout.write('\nGenerating Feed Inventory Data...')
                feed_types = self.create_feed_types()
                suppliers = self.create_feed_suppliers()
                purchases = self.create_feed_purchases(suppliers, feed_types, farm)
                inventories = self.create_feed_inventory(farm, feed_types, purchases)
                consumptions = self.create_feed_consumption(farm, flock, feed_types)
                
                # Generate Medication Management data
                self.stdout.write('\nGenerating Medication Management Data...')
                medications = self.create_medication_types()
                schedules = self.create_vaccination_schedules(medications)
                med_records = self.create_medication_records(farm, flock, medications)
                vacc_records = self.create_vaccination_records(farm, flock, medications)
                vet_visits = self.create_vet_visits(farm, flock)
                
                self.print_summary(
                    feed_types, suppliers, purchases, inventories, consumptions,
                    medications, schedules, med_records, vacc_records, vet_visits
                )

                self.stdout.write(self.style.SUCCESS('\n✓ Sample data generated successfully!\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error generating data: {e}\n'))
            raise CommandError(f'Data generation failed: {e}')

    def clear_data(self):
        """Clear existing sample data."""
        self.stdout.write('Clearing existing sample data...')
        
        FeedConsumption.objects.all().delete()
        FeedInventory.objects.all().delete()
        FeedPurchase.objects.all().delete()
        FeedSupplier.objects.all().delete()
        FeedType.objects.all().delete()
        
        VetVisit.objects.all().delete()
        VaccinationRecord.objects.all().delete()
        MedicationRecord.objects.all().delete()
        VaccinationSchedule.objects.all().delete()
        MedicationType.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('✓ Existing data cleared\n'))

    def create_base_data(self):
        """Create or get test user, farm, and flock."""
        self.stdout.write('Setting up base data (User, Farm, Flock)...')
        
        user = User.objects.filter(email='demo@yeapoultry.com').first()
        if not user:
            user = User.objects.create_user(
                username='demo_farmer',
                email='demo@yeapoultry.com',
                password='demo123',
                first_name='Demo',
                last_name='Farmer',
                phone='+233244000099'
            )
        
        farm = Farm.objects.filter(farm_name='Demo Farm - Phase 4').first()
        if not farm:
            farm = Farm.objects.create(
                user=user,
                farm_name='Demo Farm - Phase 4',
                first_name='Demo',
                last_name='Farmer',
                date_of_birth=date(1985, 5, 15),
                gender='Male',
                ghana_card_number='GHA-100000001-1',
                marital_status='Married',
                primary_phone='+233244000001',
                preferred_contact_method='Phone Call',
                residential_address='Demo Address, Accra',
                nok_full_name='Demo Kin',
                nok_relationship='Spouse',
                nok_phone='+233244000002',
                nok_residential_address='Demo Kin Address',
                education_level='Tertiary',
                literacy_level='Can Read & Write',
                years_in_poultry=Decimal('5.0'),
                ownership_type='Sole Proprietorship',
                tin='1000000001',
                number_of_poultry_houses=2,
                total_bird_capacity=2000,
                housing_type='Deep Litter',
                total_infrastructure_value_ghs=Decimal('50000.00'),
                primary_production_type='Eggs',
                initial_investment_amount=Decimal('50000.00'),
                funding_source=['Personal Savings', 'YEA Program'],
                monthly_operating_budget=Decimal('5000.00'),
                expected_monthly_revenue=Decimal('8000.00'),
                planned_production_start_date=date.today() - timedelta(days=180),
                application_status='APPROVED',
                application_date=date.today() - timedelta(days=200)
            )
        
        flock = Flock.objects.filter(farm=farm, flock_number='DEMO-FLOCK-001').first()
        if not flock:
            flock = Flock.objects.create(
                farm=farm,
                flock_number='DEMO-FLOCK-001',
                flock_type='Layers',
                breed='Isa Brown',
                source='YEA Program',
                arrival_date=date.today() - timedelta(days=90),
                initial_count=1500,
                current_count=1450,
                age_at_arrival_weeks=18
            )
        
        self.stdout.write(self.style.SUCCESS(f'✓ Base data ready: {farm.farm_name}, Flock: {flock.flock_number}'))
        return user, farm, flock

    # =======================================================================
    # FEED INVENTORY DATA GENERATION
    # =======================================================================

    def create_feed_types(self):
        """Create feed types."""
        feed_types_data = [
            {
                'name': 'Chick Starter Crumbs',
                'category': 'STARTER',
                'form': 'CRUMBLE',
                'protein_content': Decimal('20.0'),
                'energy_content': Decimal('2900'),
                'calcium_content': Decimal('1.0'),
                'recommended_age_weeks_min': 0,
                'recommended_age_weeks_max': 8,
                'description': 'High protein starter feed for day-old to 8 weeks'
            },
            {
                'name': 'Grower Mash',
                'category': 'GROWER',
                'form': 'MASH',
                'protein_content': Decimal('16.0'),
                'energy_content': Decimal('2750'),
                'calcium_content': Decimal('0.9'),
                'recommended_age_weeks_min': 9,
                'recommended_age_weeks_max': 18,
                'description': 'Growth phase feed for 9-18 weeks'
            },
            {
                'name': 'Layer Mash',
                'category': 'LAYER',
                'form': 'MASH',
                'protein_content': Decimal('17.0'),
                'energy_content': Decimal('2700'),
                'calcium_content': Decimal('3.5'),
                'recommended_age_weeks_min': 19,
                'recommended_age_weeks_max': 72,
                'description': 'Complete layer feed with calcium for egg production'
            },
            {
                'name': 'Broiler Starter',
                'category': 'BROILER_STARTER',
                'form': 'CRUMBLE',
                'protein_content': Decimal('22.0'),
                'energy_content': Decimal('3000'),
                'calcium_content': Decimal('1.0'),
                'recommended_age_weeks_min': 0,
                'recommended_age_weeks_max': 3,
                'description': 'High energy starter for broilers 0-3 weeks'
            },
            {
                'name': 'Broiler Finisher',
                'category': 'BROILER_FINISHER',
                'form': 'PELLET',
                'protein_content': Decimal('19.0'),
                'energy_content': Decimal('3100'),
                'calcium_content': Decimal('0.9'),
                'recommended_age_weeks_min': 4,
                'recommended_age_weeks_max': 8,
                'description': 'Finisher feed for broilers 4-8 weeks'
            },
        ]
        
        feed_types = []
        for data in feed_types_data:
            ft = FeedType.objects.create(**data)
            feed_types.append(ft)
            self.stdout.write(f'  ✓ Created: {ft.name} ({ft.category})')
        
        return feed_types

    def create_feed_suppliers(self):
        """Create feed suppliers."""
        suppliers_data = [
            {
                'name': 'AgriFeeds Ghana Ltd',
                'contact_person': 'Kwame Mensah',
                'phone': '+233244111222',
                'email': 'sales@agrifeedsgh.com',
                'address': 'Tema Industrial Area',
                'is_active': True,
                'notes': 'Reliable supplier with good delivery times'
            },
            {
                'name': 'Topfeeds Company',
                'contact_person': 'Ama Serwaa',
                'phone': '+233244333444',
                'email': 'orders@topfeeds.com',
                'address': 'Kumasi, Ashanti Region',
                'is_active': True,
                'notes': 'Competitive prices for bulk orders'
            },
        ]
        
        suppliers = []
        for data in suppliers_data:
            supplier = FeedSupplier.objects.create(**data)
            suppliers.append(supplier)
            self.stdout.write(f'  ✓ Created: {supplier.name}')
        
        return suppliers

    def create_feed_purchases(self, suppliers, feed_types, farm):
        """Create feed purchase records."""
        purchases = []
        
        for i in range(5):
            days_ago = 60 - (i * 15)
            quantity_kg = Decimal(str(random.randint(500, 2500)))
            unit_price = Decimal(str(round(random.uniform(1.5, 2.5), 2)))
            total_cost = quantity_kg * unit_price
            
            purchase = FeedPurchase.objects.create(
                farm=farm,
                supplier=random.choice(suppliers),
                feed_type=random.choice(feed_types),
                purchase_date=date.today() - timedelta(days=days_ago),
                quantity_kg=quantity_kg,
                unit_price=unit_price,
                total_cost=total_cost,
                delivery_date=date.today() - timedelta(days=days_ago - 2),
                payment_status='PAID' if i < 3 else 'PARTIAL',
                amount_paid=total_cost if i < 3 else total_cost * Decimal('0.5'),
                invoice_number=f'INV-2025-{1000 + i}',
                notes=f'Purchase batch {i+1}'
            )
            purchases.append(purchase)
            self.stdout.write(f'  ✓ Purchase: {purchase.feed_type.name} - {purchase.quantity_kg}kg')
        
        return purchases

    def create_feed_inventory(self, farm, feed_types, purchases):
        """Create feed inventory records."""
        inventories = []
        
        for feed_type in feed_types[:3]:  # Only create inventory for first 3 feeds
            inventory = FeedInventory.objects.create(
                farm=farm,
                feed_type=feed_type,
                current_stock_kg=Decimal(str(random.randint(500, 2500))),
                min_stock_level=Decimal('750.00'),
                max_stock_level=Decimal('5000.00'),
                average_cost_per_kg=Decimal(str(round(random.uniform(1.7, 2.3), 2))),
                storage_location=f'Warehouse {random.choice(["A", "B"])}'
            )
            inventories.append(inventory)
            alert_status = '⚠ LOW STOCK' if inventory.low_stock_alert else '✓'
            self.stdout.write(f'  {alert_status} Inventory: {inventory.feed_type.name} - {inventory.current_stock_kg}kg')
        
        return inventories

    def create_feed_consumption(self, farm, flock, feed_types):
        """Create feed consumption records."""
        consumptions = []
        layer_feed = [ft for ft in feed_types if ft.category == 'LAYER'][0]
        
        # Create a DailyProduction record for each day
        for i in range(7):  # Last 7 days
            consumption_date = date.today() - timedelta(days=i)
            birds_count = 1450 - (i * 2)
            quantity_kg = Decimal(str(round(random.uniform(140, 160), 2)))
            eggs_count = random.randint(1200, 1350)
            
            # Create daily production record
            daily_prod = DailyProduction.objects.create(
                farm=farm,
                flock=flock,
                production_date=consumption_date,
                eggs_collected=eggs_count,
                good_eggs=eggs_count - random.randint(5, 15),
                birds_died=random.randint(0, 2),
                feed_consumed_kg=quantity_kg
            )
            
            consumption = FeedConsumption.objects.create(
                daily_production=daily_prod,
                flock=flock,
                farm=farm,
                feed_type=layer_feed,
                date=consumption_date,
                quantity_consumed_kg=quantity_kg,
                birds_count_at_consumption=birds_count,
                cost_per_kg=Decimal('2.00')
            )
            consumptions.append(consumption)
            self.stdout.write(f'  ✓ Consumption: {consumption.date} - {consumption.quantity_consumed_kg}kg ({consumption.consumption_per_bird_grams}g/bird)')
        
        return consumptions

    # =======================================================================
    # MEDICATION MANAGEMENT DATA GENERATION
    # =======================================================================

    def create_medication_types(self):
        """Create medication types."""
        meds_data = [
            {
                'name': 'Oxytetracycline',
                'category': 'ANTIBIOTIC',
                'administration_route': 'ORAL',
                'dosage': '20mg per kg body weight',
                'indication': 'Respiratory infections, CRD',
                'withdrawal_period_days': 7,
                'egg_withdrawal_days': 5,
                'meat_withdrawal_days': 14,
                'is_active': True
            },
            {
                'name': 'Newcastle Disease Vaccine (La Sota)',
                'category': 'VACCINE',
                'administration_route': 'DRINKING_WATER',
                'dosage': '1 dose per bird',
                'indication': 'Newcastle disease prevention',
                'withdrawal_period_days': 0,
                'is_active': True
            },
            {
                'name': 'Multivitamin Supplement',
                'category': 'VITAMIN',
                'administration_route': 'ORAL',
                'dosage': '1ml per liter of water',
                'indication': 'Stress relief, general health',
                'withdrawal_period_days': 0,
                'is_active': True
            },
            {
                'name': 'Fowl Pox Vaccine',
                'category': 'VACCINE',
                'administration_route': 'WING_WEB',
                'dosage': '1 dose per bird',
                'indication': 'Fowl pox prevention',
                'withdrawal_period_days': 0,
                'is_active': True
            },
        ]
        
        medications = []
        for data in meds_data:
            med = MedicationType.objects.create(**data)
            medications.append(med)
            self.stdout.write(f'  ✓ Created: {med.name} ({med.category})')
        
        return medications

    def create_vaccination_schedules(self, medications):
        """Create vaccination schedules."""
        vaccines = [m for m in medications if m.category == 'VACCINE']
        schedules = []
        
        schedule_data = [
            {
                'medication_type': vaccines[0],  # Newcastle
                'flock_type': 'LAYER',
                'age_in_weeks': 1,
                'dosage_per_bird': '1 dose',
                'disease_prevented': 'Newcastle Disease',
                'is_mandatory': True,
                'priority': 10
            },
            {
                'medication_type': vaccines[1],  # Fowl Pox
                'flock_type': 'LAYER',
                'age_in_weeks': 8,
                'dosage_per_bird': '1 dose',
                'disease_prevented': 'Fowl Pox',
                'is_mandatory': True,
                'priority': 9
            },
        ]
        
        for data in schedule_data:
            schedule = VaccinationSchedule.objects.create(**data)
            schedules.append(schedule)
            self.stdout.write(f'  ✓ Schedule: {schedule.medication_type.name} at week {schedule.age_in_weeks}')
        
        return schedules

    def create_medication_records(self, farm, flock, medications):
        """Create medication records."""
        antibiotics = [m for m in medications if m.category == 'ANTIBIOTIC']
        if not antibiotics:
            return []
        
        records = []
        record = MedicationRecord.objects.create(
            flock=flock,
            farm=farm,
            medication_type=antibiotics[0],
            administered_date=date.today() - timedelta(days=30),
            reason='TREATMENT',
            dosage_given='20mg/kg',
            birds_treated=100,
            treatment_days=5,
            quantity_used=Decimal('500.00'),
            unit_cost=Decimal('0.50'),
            administered_by='Dr. Veterinarian',
            notes='Treated for respiratory infection'
        )
        records.append(record)
        self.stdout.write(f'  ✓ Medication: {record.medication_type.name} - {record.birds_treated} birds')
        
        return records

    def create_vaccination_records(self, farm, flock, medications):
        """Create vaccination records."""
        vaccines = [m for m in medications if m.category == 'VACCINE']
        records = []
        
        for i, vaccine in enumerate(vaccines[:2]):
            record = VaccinationRecord.objects.create(
                flock=flock,
                farm=farm,
                medication_type=vaccine,
                vaccination_date=date.today() - timedelta(days=45 - (i*15)),
                birds_vaccinated=1450,
                flock_age_weeks=20 + i,
                dosage_per_bird='1 dose',
                administration_route=vaccine.administration_route,
                batch_number=f'BATCH-2025-{100+i}',
                expiry_date=date.today() + timedelta(days=365),
                quantity_used=Decimal('1450.00'),
                unit_cost=Decimal('0.30'),
                administered_by='Dr. Vet Tech',
                is_mandatory_compliance=True
            )
            records.append(record)
            self.stdout.write(f'  ✓ Vaccination: {record.medication_type.name} - {record.birds_vaccinated} birds')
        
        return records

    def create_vet_visits(self, farm, flock):
        """Create vet visit records."""
        visits = []
        
        visit = VetVisit.objects.create(
            farm=farm,
            flock=flock,
            visit_date=date.today() - timedelta(days=20),
            visit_type='ROUTINE',
            status='COMPLETED',
            veterinarian_name='Dr. Kwame Veterinarian',
            vet_license_number='VET-2025-001',
            purpose='Routine health inspection',
            findings='Flock in good health, recommended vitamin supplementation',
            recommendations='Continue good biosecurity practices',
            compliance_status='COMPLIANT',
            visit_fee=Decimal('250.00'),
            certificate_issued=True,
            certificate_number='CERT-VET-2025-001'
        )
        visits.append(visit)
        self.stdout.write(f'  ✓ Vet Visit: {visit.visit_type} on {visit.visit_date}')
        
        return visits

    def print_summary(self, feed_types, suppliers, purchases, inventories, consumptions,
                      medications, schedules, med_records, vacc_records, vet_visits):
        """Print generation summary."""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('  GENERATION SUMMARY'))
        self.stdout.write('='*80 + '\n')
        
        self.stdout.write(self.style.WARNING('Feed Inventory Module:'))
        self.stdout.write(f'  • Feed Types: {len(feed_types)}')
        self.stdout.write(f'  • Suppliers: {len(suppliers)}')
        self.stdout.write(f'  • Purchases: {len(purchases)}')
        self.stdout.write(f'  • Inventory Records: {len(inventories)}')
        self.stdout.write(f'  • Consumption Records: {len(consumptions)}')
        
        self.stdout.write(self.style.WARNING('\nMedication Management Module:'))
        self.stdout.write(f'  • Medication Types: {len(medications)}')
        self.stdout.write(f'  • Vaccination Schedules: {len(schedules)}')
        self.stdout.write(f'  • Medication Records: {len(med_records)}')
        self.stdout.write(f'  • Vaccination Records: {len(vacc_records)}')
        self.stdout.write(f'  • Vet Visits: {len(vet_visits)}')
        
        total = (len(feed_types) + len(suppliers) + len(purchases) + len(inventories) + 
                len(consumptions) + len(medications) + len(schedules) + len(med_records) + 
                len(vacc_records) + len(vet_visits))
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal Records Created: {total}'))
