"""
Management command to test dashboard API services.
Tests all three dashboard services (Executive, Officer, Farmer) with sample data.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from dashboards.services import (
    ExecutiveDashboardService,
    OfficerDashboardService, 
    FarmerDashboardService
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Test dashboard API services with sample data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== TESTING DASHBOARD API SERVICES ===\n'))

        # Test Executive Dashboard
        self.stdout.write(self.style.NOTICE('1. Testing Executive Dashboard Service...'))
        self.test_executive_dashboard()
        
        # Test Officer Dashboard
        self.stdout.write(self.style.NOTICE('\n2. Testing Officer Dashboard Service...'))
        self.test_officer_dashboard()
        
        # Test Farmer Dashboard
        self.stdout.write(self.style.NOTICE('\n3. Testing Farmer Dashboard Service...'))
        self.test_farmer_dashboard()
        
        self.stdout.write(self.style.SUCCESS('\n=== ALL DASHBOARD TESTS COMPLETED ===\n'))

    def test_executive_dashboard(self):
        """Test executive dashboard service methods."""
        service = ExecutiveDashboardService()
        
        # Test overview stats
        self.stdout.write('  ✓ Testing get_overview_stats()...')
        overview = service.get_overview_stats()
        self.stdout.write(f'    - Farms: {overview["farms"]["total"]} total, {overview["farms"]["approved"]} approved')
        self.stdout.write(f'    - Orders: {overview["procurement"]["total_orders"]} total, {overview["procurement"]["active_orders"]} active')
        self.stdout.write(f'    - Budget Utilization: {overview["financials"]["budget_utilization"]:.2f}%')
        
        # Test revenue trend
        self.stdout.write('  ✓ Testing get_revenue_trend()...')
        revenue = service.get_revenue_trend(months=6)
        self.stdout.write(f'    - Revenue data points: {len(revenue)}')
        if revenue:
            self.stdout.write(f'    - Latest month: {revenue[-1]["month"]} - GHS {revenue[-1]["revenue"]:,.2f}')
        
        # Test orders by status
        self.stdout.write('  ✓ Testing get_orders_by_status()...')
        orders_status = service.get_orders_by_status()
        self.stdout.write(f'    - Status distribution: {len(orders_status)} statuses')
        for item in orders_status:
            self.stdout.write(f'      - {item["status"]}: {item["count"]} orders')
        
        # Test top farms
        self.stdout.write('  ✓ Testing get_top_performing_farms()...')
        top_farms = service.get_top_performing_farms(limit=5)
        self.stdout.write(f'    - Top performing farms: {len(top_farms)}')
        for idx, farm in enumerate(top_farms[:3], 1):
            self.stdout.write(f'      {idx}. {farm["farm_name"]} - GHS {farm["revenue"]:,.2f}')
        
        # Test SLA compliance
        self.stdout.write('  ✓ Testing get_approval_sla_compliance()...')
        sla = service.get_approval_sla_compliance()
        self.stdout.write(f'    - Compliance rate: {sla["compliance_rate"]:.2f}%')
        self.stdout.write(f'    - Within SLA: {sla["within_sla"]}, Overdue: {sla["overdue"]}')
        
        # Test farm distribution
        self.stdout.write('  ✓ Testing get_farm_distribution_by_region()...')
        regions = service.get_farm_distribution_by_region()
        self.stdout.write(f'    - Regions: {len(regions)}')
        for region in regions[:3]:
            self.stdout.write(f'      - {region["region"]}: {region["count"]} farms')
        
        # Test production types
        self.stdout.write('  ✓ Testing get_production_type_distribution()...')
        prod_types = service.get_production_type_distribution()
        self.stdout.write(f'    - Production types: {len(prod_types)}')
        for ptype in prod_types:
            if 'percentage' in ptype:
                self.stdout.write(f'      - {ptype["type"]}: {ptype["count"]} farms ({ptype["percentage"]:.1f}%)')
            else:
                self.stdout.write(f'      - {ptype["type"]}: {ptype["count"]} farms')
        
        # Test recent activities
        self.stdout.write('  ✓ Testing get_recent_activities()...')
        activities = service.get_recent_activities(limit=5)
        self.stdout.write(f'    - Recent activities: {len(activities)}')
        for act in activities[:3]:
            self.stdout.write(f'      - {act["type"]}: {act["description"]}')

    def test_officer_dashboard(self):
        """Test officer dashboard service methods."""
        # Get a procurement officer or use first user
        officer = User.objects.filter(role='procurement_officer').first()
        if not officer:
            self.stdout.write(self.style.WARNING('  ⚠ No procurement officer found, using first user'))
            officer = User.objects.first()
        
        if not officer:
            self.stdout.write(self.style.WARNING('  ⚠ No users in database, skipping officer tests'))
            return
        
        service = OfficerDashboardService(officer)
        
        # Test overview stats
        self.stdout.write('  ✓ Testing get_overview_stats()...')
        overview = service.get_overview_stats()
        self.stdout.write(f'    - Total orders: {overview["orders"]["total"]}')
        self.stdout.write(f'    - Active orders: {overview["orders"]["active"]}')
        self.stdout.write(f'    - Pending actions: {overview["pending_actions"]["total"]}')
        self.stdout.write(f'    - Budget utilization: {overview["budget"]["utilization"]:.2f}%')
        
        # Test my orders
        self.stdout.write('  ✓ Testing get_my_orders()...')
        my_orders = service.get_my_orders(limit=10)
        self.stdout.write(f'    - My orders: {len(my_orders)}')
        for order in my_orders[:3]:
            self.stdout.write(f'      - Order #{order["order_number"]}: {order["status"]}')
        
        # Test pending approvals
        self.stdout.write('  ✓ Testing get_pending_approvals()...')
        approvals = service.get_pending_approvals()
        self.stdout.write(f'    - Pending verifications: {len(approvals["pending_verifications"])}')
        self.stdout.write(f'    - Ready for delivery: {len(approvals["ready_for_delivery"])}')
        
        # Test overdue items
        self.stdout.write('  ✓ Testing get_overdue_items()...')
        overdue = service.get_overdue_items()
        self.stdout.write(f'    - Overdue orders: {len(overdue["orders"])}')
        self.stdout.write(f'    - Overdue invoices: {len(overdue["invoices"])}')
        
        # Test performance metrics
        self.stdout.write('  ✓ Testing get_performance_metrics()...')
        performance = service.get_performance_metrics(days=30)
        self.stdout.write(f'    - Completion rate: {performance["completion_rate"]:.2f}%')
        self.stdout.write(f'    - Avg fulfillment days: {performance["avg_fulfillment_days"]:.1f}')
        self.stdout.write(f'    - On-time rate: {performance["on_time_delivery_rate"]:.2f}%')

    def test_farmer_dashboard(self):
        """Test farmer dashboard service methods."""
        # Get a farmer or use first user
        farmer = User.objects.filter(role='farmer').first()
        if not farmer:
            self.stdout.write(self.style.WARNING('  ⚠ No farmers found, using first user'))
            farmer = User.objects.first()
        
        if not farmer:
            self.stdout.write(self.style.WARNING('  ⚠ No users in database, skipping farmer tests'))
            return
        
        service = FarmerDashboardService(farmer)
        
        # Test overview stats
        self.stdout.write('  ✓ Testing get_overview_stats()...')
        overview = service.get_overview_stats()
        self.stdout.write(f'    - Total assignments: {overview["assignments"]["total"]}')
        self.stdout.write(f'    - Pending assignments: {overview["assignments"]["pending"]}')
        self.stdout.write(f'    - Total earnings: GHS {overview["earnings"]["total"]:,.2f}')
        self.stdout.write(f'    - Quality score: {overview["performance"]["avg_quality"]:.2f}%')
        
        # Test assignments
        self.stdout.write('  ✓ Testing get_my_assignments()...')
        assignments = service.get_my_assignments(limit=10)
        self.stdout.write(f'    - My assignments: {len(assignments)}')
        for assignment in assignments[:3]:
            self.stdout.write(f'      - {assignment["order_number"]}: {assignment["quantity_assigned"]} birds ({assignment["status"]})')
        
        # Test pending actions
        self.stdout.write('  ✓ Testing get_pending_actions()...')
        actions = service.get_pending_actions()
        self.stdout.write(f'    - Pending responses: {len(actions["pending_responses"])}')
        self.stdout.write(f'    - Preparing orders: {len(actions["preparing_orders"])}')
        self.stdout.write(f'    - Ready for delivery: {len(actions["ready_for_delivery"])}')
        
        # Test earnings breakdown
        self.stdout.write('  ✓ Testing get_earnings_breakdown()...')
        earnings = service.get_earnings_breakdown()
        if earnings:
            total_earnings = sum(earnings['by_status'].values())
            total_deductions = earnings['deductions']['total']
            net_earnings = total_earnings - total_deductions
            self.stdout.write(f'    - Total earnings: GHS {total_earnings:,.2f}')
            self.stdout.write(f'    - Total deductions: GHS {total_deductions:,.2f}')
            self.stdout.write(f'    - Net earnings: GHS {net_earnings:,.2f}')
            self.stdout.write(f'    - Monthly data points: {len(earnings.get("monthly_trend", []))}')
        else:
            self.stdout.write('    - No earnings data')
        
        # Test delivery history
        self.stdout.write('  ✓ Testing get_delivery_history()...')
        deliveries = service.get_delivery_history(limit=5)
        self.stdout.write(f'    - Delivery history: {len(deliveries)}')
        for delivery in deliveries[:3]:
            quality = "Passed" if delivery["quality_passed"] else "Failed"
            self.stdout.write(f'      - {delivery["order_number"]}: {delivery["quantity"]} birds (Quality: {quality})')
        
        # Test performance summary
        self.stdout.write('  ✓ Testing get_performance_summary()...')
        performance = service.get_performance_summary()
        if performance:
            self.stdout.write(f'    - Completion rate: {performance.get("completion_rate", 0):.2f}%')
            self.stdout.write(f'    - On-time rate: {performance.get("on_time_rate", 0):.2f}%')
            self.stdout.write(f'    - Avg quality score: {performance.get("avg_quality_score", 0):.2f}')
            self.stdout.write(f'    - Rejection rate: {performance.get("rejection_rate", 0):.2f}%')
        else:
            self.stdout.write('    - No performance data')
