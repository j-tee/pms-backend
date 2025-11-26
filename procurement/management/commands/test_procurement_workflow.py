"""
Management command to test the procurement workflow with comprehensive sample data.

This command tests the complete government procurement flow:
1. Officer creates procurement order
2. Order is published and auto-assigned to recommended farms
3. Farms accept/reject assignments
4. Deliveries are made and quality inspected
5. Invoices are auto-generated with deductions
6. Payments are processed

Usage:
    python manage.py test_procurement_workflow
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random

from farms.models import Farm
from procurement.models import ProcurementOrder, OrderAssignment, DeliveryConfirmation, ProcurementInvoice
from procurement.services import ProcurementWorkflowService

User = get_user_model()


class Command(BaseCommand):
    help = 'Test procurement workflow with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Delete existing test procurement data before running',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('TESTING GOVERNMENT PROCUREMENT WORKFLOW'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        if options['cleanup']:
            self.stdout.write('Cleaning up existing test data...')
            ProcurementInvoice.objects.filter(invoice_number__startswith='INV-TEST').delete()
            DeliveryConfirmation.objects.filter(delivery_number__startswith='DEL-TEST').delete()
            OrderAssignment.objects.filter(assignment_number__startswith='ASG-TEST').delete()
            ProcurementOrder.objects.filter(order_number__startswith='ORD-TEST').delete()
            self.stdout.write(self.style.SUCCESS('✓ Test data cleaned up\n'))

        try:
            service = ProcurementWorkflowService()

            # Test 1: Create Users
            self.stdout.write(self.style.WARNING('\n[TEST 1] Creating Test Users'))
            self.stdout.write('-' * 70)
            
            officer = self._get_or_create_user(
                username='procurement_officer',
                email='officer@yea.gov.gh',
                first_name='John',
                last_name='Mensah',
                role='PROCUREMENT_OFFICER',
                phone='+233244000001'
            )
            self.stdout.write(f'✓ Created procurement officer: {officer.get_full_name()}')

            finance_officer = self._get_or_create_user(
                username='finance_officer',
                email='finance@yea.gov.gh',
                first_name='Grace',
                last_name='Owusu',
                role='NATIONAL_ADMIN',
                phone='+233244000002'
            )
            self.stdout.write(f'✓ Created finance officer: {finance_officer.get_full_name()}')

            # Test 2: Get Approved Farms
            self.stdout.write(self.style.WARNING('\n[TEST 2] Finding Approved Farms'))
            self.stdout.write('-' * 70)

            # Filter approved farms with broiler production
            approved_farms = Farm.objects.filter(
                application_status='Approved - Farm ID Assigned',
                primary_production_type='Broilers'
            ).select_related('user')[:5]

            if approved_farms.count() == 0:
                self.stdout.write(self.style.ERROR('✗ No approved broiler farms found!'))
                self.stdout.write('Run "python manage.py test_approval_workflow" first to create test farms.')
                return

            for farm in approved_farms:
                self.stdout.write(f'✓ Found farm: {farm.farm_name} (Owner: {farm.user.get_full_name()})')
                # Update inventory for testing
                farm.current_bird_count = random.randint(1000, 5000)
                farm.save()

            # Test 3: Create Procurement Order
                self.stdout.write(self.style.WARNING('\n[TEST 3] Creating Procurement Order'))
                self.stdout.write('-' * 70)

                order = service.create_order(
                    created_by=officer,
                    title='School Feeding Program - Q4 2025',
                    description='Bulk procurement of broilers for government school feeding program covering Greater Accra and Central regions.',
                    production_type='Broilers',
                    quantity_needed=10000,
                    unit='Birds',
                    price_per_unit=Decimal('25.00'),
                    delivery_location='National Food Storage Facility, Accra',
                    delivery_location_gps='5.6037,-0.1870',
                    delivery_deadline=date.today() + timedelta(days=30),
                    delivery_instructions='All deliveries must be made between 6:00 AM and 12:00 PM. Birds must be alive and healthy.',
                    min_weight_per_bird_kg=Decimal('2.0'),
                    quality_requirements='Minimum 2kg average weight, mortality not exceeding 1%, healthy and disease-free.',
                    auto_assign=True,
                    preferred_region='Greater Accra',
                    max_farms=5,
                    priority='high',
                    assigned_procurement_officer=officer,
                    internal_notes='This is a test order for system validation.'
                )

                self.stdout.write(f'✓ Created order: {order.order_number}')
                self.stdout.write(f'  Title: {order.title}')
                self.stdout.write(f'  Quantity: {order.quantity_needed:,} {order.unit}')
                self.stdout.write(f'  Budget: GHS {order.total_budget:,.2f}')
                self.stdout.write(f'  Deadline: {order.delivery_deadline}')
                self.stdout.write(f'  Status: {order.get_status_display()}')

                # Test 4: Publish Order
                self.stdout.write(self.style.WARNING('\n[TEST 4] Publishing Order'))
                self.stdout.write('-' * 70)

                service.publish_order(order)
                order.refresh_from_db()
                self.stdout.write(f'✓ Order published at: {order.published_at}')
                self.stdout.write(f'  Status changed to: {order.get_status_display()}')

                # Test 5: Farm Recommendations
                self.stdout.write(self.style.WARNING('\n[TEST 5] Getting Farm Recommendations'))
                self.stdout.write('-' * 70)

                recommendations = service.recommend_farms(order, limit=5)
                self.stdout.write(f'✓ Found {len(recommendations)} recommended farms:')
                
                for i, rec in enumerate(recommendations, 1):
                    farm = rec['farm']
                    self.stdout.write(f'  {i}. {farm.farm_name}')
                    self.stdout.write(f'     Inventory: {farm.current_bird_count:,} birds')
                    self.stdout.write(f'     Recommended qty: {rec["recommended_quantity"]:,} birds')
                    self.stdout.write(f'     Priority score: {rec["priority_score"]}')

                # Test 6: Auto-Assign Order
                self.stdout.write(self.style.WARNING('\n[TEST 6] Auto-Assigning Order to Farms'))
                self.stdout.write('-' * 70)

                assignments = service.auto_assign_order(order)
                self.stdout.write(f'✓ Created {len(assignments)} assignments:')
                
                for assignment in assignments:
                    self.stdout.write(f'  • {assignment.assignment_number}')
                    self.stdout.write(f'    Farm: {assignment.farm.farm_name}')
                    self.stdout.write(f'    Quantity: {assignment.quantity_assigned:,} birds')
                    self.stdout.write(f'    Value: GHS {assignment.total_value:,.2f}')
                    self.stdout.write(f'    Status: {assignment.get_status_display()}')

                order.refresh_from_db()
                self.stdout.write(f'\n✓ Order status updated to: {order.get_status_display()}')
                self.stdout.write(f'  Total assigned: {order.quantity_assigned:,}/{order.quantity_needed:,}')

                # Test 7: Farm Acceptance/Rejection
                self.stdout.write(self.style.WARNING('\n[TEST 7] Farm Responses (Accept/Reject)'))
                self.stdout.write('-' * 70)

                for idx, assignment in enumerate(assignments):
                    if idx == 0:  # First farm rejects
                        service.farm_reject_assignment(
                            assignment,
                            reason='Insufficient capacity due to existing orders'
                        )
                        self.stdout.write(f'✗ {assignment.farm.farm_name} REJECTED assignment')
                        self.stdout.write(f'  Reason: {assignment.rejection_reason}')
                    else:  # Others accept
                        expected_date = date.today() + timedelta(days=random.randint(15, 25))
                        service.farm_accept_assignment(assignment, expected_ready_date=expected_date)
                        self.stdout.write(f'✓ {assignment.farm.farm_name} ACCEPTED assignment')
                        self.stdout.write(f'  Expected ready date: {assignment.expected_ready_date}')

                # Test 8: Mark Ready for Delivery
                self.stdout.write(self.style.WARNING('\n[TEST 8] Farms Mark Orders Ready'))
                self.stdout.write('-' * 70)

                accepted_assignments = OrderAssignment.objects.filter(order=order, status='accepted')
                for assignment in accepted_assignments[:2]:  # First 2 farms ready
                    service.mark_ready_for_delivery(assignment)
                    self.stdout.write(f'✓ {assignment.farm.farm_name} marked order as READY')
                    self.stdout.write(f'  Status: {assignment.get_status_display()}')

                # Test 9: Create Deliveries with Quality Inspection
                self.stdout.write(self.style.WARNING('\n[TEST 9] Recording Deliveries & Quality Inspection'))
                self.stdout.write('-' * 70)

                ready_assignments = accepted_assignments.filter(status='ready')
                for assignment in ready_assignments:
                    # First delivery (partial)
                    delivery_qty = int(assignment.quantity_assigned * 0.6)  # 60% delivery
                    avg_weight = round(random.uniform(2.0, 2.8), 2)
                    mortality = random.randint(0, 5)
                    quality_passed = avg_weight >= 2.0 and mortality <= int(delivery_qty * 0.01)

                    delivery = service.create_delivery(
                        assignment=assignment,
                        quantity_delivered=delivery_qty,
                        delivery_date=date.today(),
                        received_by=officer,
                        average_weight_per_bird=Decimal(str(avg_weight)),
                        mortality_count=mortality,
                        quality_passed=quality_passed,
                        quality_issues='None' if quality_passed else 'Below weight standard',
                        delivery_note_number=f'DN-{random.randint(1000, 9999)}',
                        vehicle_registration=f'GH-{random.randint(1000, 9999)}-{random.randint(10, 99)}',
                        driver_name='Kwame Delivery',
                        driver_phone='+233244567890',
                        notes='First batch delivery'
                    )

                    self.stdout.write(f'✓ Delivery recorded: {delivery.delivery_number}')
                    self.stdout.write(f'  Farm: {assignment.farm.farm_name}')
                    self.stdout.write(f'  Quantity: {delivery_qty:,} birds')
                    self.stdout.write(f'  Avg weight: {avg_weight} kg')
                    self.stdout.write(f'  Mortality: {mortality} birds')
                    self.stdout.write(f'  Quality: {"✓ PASSED" if quality_passed else "✗ FAILED"}')

                    # Second delivery (complete remaining)
                    remaining_qty = assignment.quantity_assigned - delivery_qty
                    avg_weight2 = round(random.uniform(2.0, 2.8), 2)
                    mortality2 = random.randint(0, 3)
                    quality_passed2 = avg_weight2 >= 2.0 and mortality2 <= int(remaining_qty * 0.01)

                    delivery2 = service.create_delivery(
                        assignment=assignment,
                        quantity_delivered=remaining_qty,
                        delivery_date=date.today() + timedelta(days=1),
                        received_by=officer,
                        average_weight_per_bird=Decimal(str(avg_weight2)),
                        mortality_count=mortality2,
                        quality_passed=quality_passed2,
                        delivery_note_number=f'DN-{random.randint(1000, 9999)}',
                        vehicle_registration=f'GH-{random.randint(1000, 9999)}-{random.randint(10, 99)}',
                        driver_name='Kofi Transport',
                        driver_phone='+233244567891',
                        notes='Final batch delivery - completes order'
                    )

                    self.stdout.write(f'✓ Final delivery: {delivery2.delivery_number}')
                    self.stdout.write(f'  Quantity: {remaining_qty:,} birds')
                    self.stdout.write(f'  Quality: {"✓ PASSED" if quality_passed2 else "✗ FAILED"}')

                # Test 10: Verify Deliveries
                self.stdout.write(self.style.WARNING('\n[TEST 10] Verifying Deliveries'))
                self.stdout.write('-' * 70)

                deliveries = DeliveryConfirmation.objects.filter(
                    assignment__in=ready_assignments
                )

                for delivery in deliveries:
                    service.verify_delivery(
                        delivery=delivery,
                        verified_by=officer,
                        quality_passed=delivery.quality_passed,
                        average_weight_per_bird=delivery.average_weight_per_bird,
                        mortality_count=delivery.mortality_count,
                        quality_notes='Verified by quality control officer'
                    )

                    self.stdout.write(f'✓ Verified: {delivery.delivery_number}')
                    self.stdout.write(f'  Quality: {"✓ PASSED" if delivery.quality_passed else "✗ FAILED"}')

                # Test 11: Invoice Generation
                self.stdout.write(self.style.WARNING('\n[TEST 11] Generating Invoices'))
                self.stdout.write('-' * 70)

                for assignment in ready_assignments:
                    assignment.refresh_from_db()
                    if assignment.status == 'delivered' and assignment.is_fully_delivered:
                        invoice = service.generate_invoice(assignment)
                        
                        self.stdout.write(f'✓ Invoice generated: {invoice.invoice_number}')
                        self.stdout.write(f'  Farm: {assignment.farm.farm_name}')
                        self.stdout.write(f'  Subtotal: GHS {invoice.subtotal:,.2f}')
                        
                        if invoice.quality_deduction > 0:
                            self.stdout.write(f'  Quality deduction: -GHS {invoice.quality_deduction:,.2f}')
                        if invoice.mortality_deduction > 0:
                            self.stdout.write(f'  Mortality deduction: -GHS {invoice.mortality_deduction:,.2f}')
                        if invoice.other_deductions > 0:
                            self.stdout.write(f'  Other deductions: -GHS {invoice.other_deductions:,.2f}')
                        
                        self.stdout.write(f'  TOTAL: GHS {invoice.total_amount:,.2f}')
                        self.stdout.write(f'  Due date: {invoice.due_date}')

                # Test 12: Invoice Approval
                self.stdout.write(self.style.WARNING('\n[TEST 12] Approving Invoices'))
                self.stdout.write('-' * 70)

                invoices = ProcurementInvoice.objects.filter(
                    assignment__in=ready_assignments,
                    payment_status='pending'
                )

                for invoice in invoices:
                    service.approve_invoice(invoice, approved_by=finance_officer)
                    self.stdout.write(f'✓ Approved: {invoice.invoice_number}')
                    self.stdout.write(f'  Approved by: {finance_officer.get_full_name()}')
                    self.stdout.write(f'  Status: {invoice.get_payment_status_display()}')

                # Test 13: Process Payments
                self.stdout.write(self.style.WARNING('\n[TEST 13] Processing Payments'))
                self.stdout.write('-' * 70)

                approved_invoices = invoices.filter(payment_status='approved')
                for invoice in approved_invoices:
                    payment_reference = f'PAY-{random.randint(10000, 99999)}'
                    
                    service.process_payment(
                        invoice=invoice,
                        payment_method='bank_transfer',
                        payment_reference=payment_reference,
                        paid_to_account=invoice.farm.paystack_subaccount_code or 'N/A',
                        notes='Test payment via government treasury'
                    )

                    self.stdout.write(f'✓ Payment processed: {invoice.invoice_number}')
                    self.stdout.write(f'  Reference: {payment_reference}')
                    self.stdout.write(f'  Amount: GHS {invoice.total_amount:,.2f}')
                    self.stdout.write(f'  Farm account: {invoice.farm.farm_name}')

                # Test 14: Order Summary
                self.stdout.write(self.style.WARNING('\n[TEST 14] Order Summary'))
                self.stdout.write('-' * 70)

                order.refresh_from_db()
                summary = service.get_order_summary(order)

                self.stdout.write(f'Order: {order.order_number}')
                self.stdout.write(f'Status: {order.get_status_display()}')
                self.stdout.write(f'')
                self.stdout.write(f'Farms:')
                self.stdout.write(f'  Total assigned: {summary["total_farms_assigned"]}')
                self.stdout.write(f'  Accepted: {summary["farms_accepted"]}')
                self.stdout.write(f'  Preparing: {summary["farms_preparing"]}')
                self.stdout.write(f'  Delivered: {summary["farms_delivered"]}')
                self.stdout.write(f'  Paid: {summary["farms_paid"]}')
                self.stdout.write(f'')
                self.stdout.write(f'Quantities:')
                self.stdout.write(f'  Needed: {summary["quantity_needed"]:,}')
                self.stdout.write(f'  Assigned: {summary["quantity_assigned"]:,}')
                self.stdout.write(f'  Delivered: {summary["quantity_delivered"]:,}')
                self.stdout.write(f'  Fulfillment: {summary["fulfillment_percentage"]:.1f}%')
                self.stdout.write(f'')
                self.stdout.write(f'Financials:')
                self.stdout.write(f'  Budget: GHS {summary["total_budget"]:,.2f}')
                self.stdout.write(f'  Actual cost: GHS {summary["total_cost_actual"]:,.2f}')

                # Final Summary
                self.stdout.write(self.style.SUCCESS('\n' + '='*70))
                self.stdout.write(self.style.SUCCESS('PROCUREMENT WORKFLOW TEST COMPLETED SUCCESSFULLY'))
                self.stdout.write(self.style.SUCCESS('='*70))
                
                stats = {
                    'Orders created': ProcurementOrder.objects.filter(order_number__startswith='ORD-TEST').count(),
                    'Assignments created': OrderAssignment.objects.filter(assignment_number__startswith='ASG-TEST').count(),
                    'Deliveries recorded': DeliveryConfirmation.objects.filter(delivery_number__startswith='DEL-TEST').count(),
                    'Invoices generated': ProcurementInvoice.objects.filter(invoice_number__startswith='INV-TEST').count(),
                    'Payments processed': ProcurementInvoice.objects.filter(
                        invoice_number__startswith='INV-TEST',
                        payment_status='paid'
                    ).count(),
                }

                self.stdout.write('\nTest Statistics:')
                for key, value in stats.items():
                    self.stdout.write(f'  ✓ {key}: {value}')

                self.stdout.write(self.style.SUCCESS('\n✓ All tests passed! Procurement system is working correctly.\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error during testing: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())

    def _get_or_create_user(self, username, email, first_name, last_name, role, phone):
        """Helper to get or create a user"""
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'phone': phone,
                'is_active': True,
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
        return user
