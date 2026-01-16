"""
Dashboard API Views

Provides REST API endpoints for dashboard data consumption.
Frontend applications will call these endpoints to render dashboard widgets.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .permissions import IsExecutive, IsProcurementOfficer, IsFarmer
from .services import ExecutiveDashboardService, OfficerDashboardService, FarmerDashboardService


class ExecutiveDashboardView(APIView):
    """
    Executive Dashboard API Endpoint
    
    GET /api/dashboards/executive/
    
    Returns comprehensive national-level metrics:
    - Farm statistics
    - Procurement overview
    - Financial metrics
    - Recent activities
    
    Permission: National Admin only
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def get(self, request):
        service = ExecutiveDashboardService()
        
        # Get all dashboard data
        data = {
            'overview': service.get_overview_stats(),
            'revenue_trend': service.get_revenue_trend(months=6),
            'orders_by_status': service.get_orders_by_status(),
            'top_farms': service.get_top_performing_farms(limit=10),
            'sla_compliance': service.get_approval_sla_compliance(),
            'farm_distribution': service.get_farm_distribution_by_region(),
            'production_types': service.get_production_type_distribution(),
            'recent_activities': service.get_recent_activities(limit=20),
        }
        
        return Response(data, status=status.HTTP_200_OK)


class ExecutiveOverviewView(APIView):
    """
    Executive Overview Stats Only
    
    GET /api/dashboards/executive/overview/
    
    Returns just the overview statistics for quick loading.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def get(self, request):
        service = ExecutiveDashboardService()
        data = service.get_overview_stats()
        return Response(data, status=status.HTTP_200_OK)


class ExecutiveChartsView(APIView):
    """
    Executive Charts Data
    
    GET /api/dashboards/executive/charts/
    
    Returns chart data for visualization.
    """
    permission_classes = [IsAuthenticated, IsExecutive]
    
    def get(self, request):
        service = ExecutiveDashboardService()
        
        months = int(request.query_params.get('months', 6))
        
        data = {
            'revenue_trend': service.get_revenue_trend(months=months),
            'orders_by_status': service.get_orders_by_status(),
            'farm_distribution': service.get_farm_distribution_by_region(),
            'production_types': service.get_production_type_distribution(),
        }
        
        return Response(data, status=status.HTTP_200_OK)


class OfficerDashboardView(APIView):
    """
    Procurement Officer Dashboard API Endpoint
    
    GET /api/dashboards/officer/
    
    Returns officer-specific metrics:
    - My orders
    - Pending approvals
    - Overdue items
    - Performance metrics
    
    Permission: Procurement Officer or National Admin
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        service = OfficerDashboardService(request.user)
        
        # Get all dashboard data
        data = {
            'overview': service.get_overview_stats(),
            'my_orders': service.get_my_orders(limit=50),
            'pending_approvals': service.get_pending_approvals(),
            'overdue_items': service.get_overdue_items(),
            'performance': service.get_performance_metrics(days=30),
        }
        
        return Response(data, status=status.HTTP_200_OK)


class OfficerOverviewView(APIView):
    """
    Officer Overview Stats Only
    
    GET /api/dashboards/officer/overview/
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        service = OfficerDashboardService(request.user)
        data = service.get_overview_stats()
        return Response(data, status=status.HTTP_200_OK)


class OfficerOrdersView(APIView):
    """
    Officer Orders List
    
    GET /api/dashboards/officer/orders/
    GET /api/dashboards/officer/orders/?status=active
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        service = OfficerDashboardService(request.user)
        
        status_filter = request.query_params.get('status', None)
        limit = int(request.query_params.get('limit', 50))
        
        data = service.get_my_orders(status=status_filter, limit=limit)
        return Response(data, status=status.HTTP_200_OK)


class OfficerOrderTimelineView(APIView):
    """
    Order Timeline Details
    
    GET /api/dashboards/officer/orders/{order_id}/timeline/
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request, order_id):
        service = OfficerDashboardService(request.user)
        data = service.get_order_timeline(order_id)
        
        if data is None:
            return Response(
                {'error': 'Order not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(data, status=status.HTTP_200_OK)


class OfficerInvoicesView(APIView):
    """
    Procurement Invoices List
    
    GET /api/admin/procurement/invoices/
    GET /api/admin/procurement/invoices/?status=pending
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        from procurement.models import ProcurementInvoice, ProcurementOrder
        from django.db.models import Q
        
        # Get orders this officer has access to
        my_orders = ProcurementOrder.objects.filter(
            Q(created_by=request.user) | Q(assigned_procurement_officer=request.user)
        )
        
        # Get invoices for those orders
        invoices = ProcurementInvoice.objects.filter(
            order__in=my_orders
        ).select_related('farm', 'order')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            invoices = invoices.filter(payment_status=status_filter)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = invoices.count()
        invoices = invoices.order_by('-created_at')[start:end]
        
        data = {
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'results': [
                {
                    'id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                    'order_number': invoice.order.order_number,
                    'order_title': invoice.order.title,
                    'farm_name': invoice.farm.farm_name,
                    'farm_id': str(invoice.farm.id),
                    'total_amount': float(invoice.total_amount),
                    'payment_status': invoice.payment_status,
                    'status_display': invoice.get_payment_status_display(),
                    'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
                    'created_at': invoice.created_at.isoformat(),
                }
                for invoice in invoices
            ]
        }
        
        return Response(data, status=status.HTTP_200_OK)


class OfficerDeliveriesView(APIView):
    """
    Procurement Deliveries List
    
    GET /api/admin/procurement/deliveries/
    GET /api/admin/procurement/deliveries/?status=pending
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        from procurement.models import DeliveryConfirmation, ProcurementOrder
        from django.db.models import Q
        
        # Get orders this officer has access to
        my_orders = ProcurementOrder.objects.filter(
            Q(created_by=request.user) | Q(assigned_procurement_officer=request.user)
        )
        
        # Get deliveries for those orders
        deliveries = DeliveryConfirmation.objects.filter(
            assignment__order__in=my_orders
        ).select_related('assignment__farm', 'assignment__order')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            if status_filter == 'pending':
                deliveries = deliveries.filter(verified_at__isnull=True)
            elif status_filter == 'verified':
                deliveries = deliveries.filter(verified_at__isnull=False)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = deliveries.count()
        deliveries = deliveries.order_by('-delivery_date')[start:end]
        
        data = {
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'results': [
                {
                    'id': str(delivery.id),
                    'delivery_number': delivery.delivery_number,
                    'assignment_number': delivery.assignment.assignment_number,
                    'order_number': delivery.assignment.order.order_number,
                    'order_title': delivery.assignment.order.title,
                    'farm_name': delivery.assignment.farm.farm_name,
                    'farm_id': str(delivery.assignment.farm.id),
                    'quantity_delivered': delivery.quantity_delivered,
                    'delivery_date': delivery.delivery_date.isoformat(),
                    'quality_passed': delivery.quality_passed,
                    'mortality_count': delivery.mortality_count,
                    'verified_at': delivery.verified_at.isoformat() if delivery.verified_at else None,
                    'is_pending': delivery.verified_at is None,
                }
                for delivery in deliveries
            ]
        }
        
        return Response(data, status=status.HTTP_200_OK)


class DistressSummaryView(APIView):
    """
    Distress Summary Dashboard for Procurement Officers.
    
    GET /api/admin/procurement/distress-summary/
    GET /api/admin/procurement/distress-summary/?region=Ashanti
    
    Provides overview statistics matching frontend spec:
    - overview: Total farms, distress counts by level
    - by_region: Breakdown per region
    - by_production_type: Breakdown per production type
    - trends: Recent intervention stats
    
    This powers the distress dashboard widget on the frontend.
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        from procurement.services.farmer_distress_v2 import get_distress_service
        
        region = request.query_params.get('region')
        
        service = get_distress_service(days_lookback=30)
        summary = service.get_distress_summary(region=region)
        
        return Response(summary, status=status.HTTP_200_OK)


class DistressedFarmersView(APIView):
    """
    List farmers in distress, prioritized for government procurement.
    
    GET /api/admin/procurement/distressed-farmers/
    GET /api/admin/procurement/farmers/distressed/
    
    Query Parameters (matching frontend spec):
    - region: Filter by region name
    - district: Filter by district name
    - production_type: Filter by 'Broilers', 'Layers', 'BROILERS', 'LAYERS'
    - min_distress_score: Minimum distress score (0-100, default: 0)
    - min_capacity: Minimum bird capacity
    - has_available_stock: Only farmers with stock to sell (true/false)
    - limit: Maximum results (default: 50)
    - ordering: Sort order ('-distress_score' default)
    
    Returns farmers sorted by distress score (highest distress first).
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        from procurement.services.farmer_distress_v2 import get_distress_service
        
        # Parse query parameters (matching frontend spec)
        region = request.query_params.get('region')
        district = request.query_params.get('district')
        production_type = request.query_params.get('production_type')
        
        # Parse integer parameters with validation
        try:
            min_distress_score = int(request.query_params.get('min_distress_score', 0))
        except (ValueError, TypeError):
            min_distress_score = 0  # Default to 0 for invalid values
        
        min_capacity = request.query_params.get('min_capacity')
        if min_capacity:
            try:
                min_capacity = int(min_capacity)
            except (ValueError, TypeError):
                min_capacity = None  # Ignore invalid values
                
        has_available_stock = request.query_params.get('has_available_stock', '').lower() == 'true'
        
        try:
            limit = int(request.query_params.get('limit', 50))
            if limit < 0:
                limit = 50  # Use default for negative values
        except (ValueError, TypeError):
            limit = 50  # Default for invalid values
            
        ordering = request.query_params.get('ordering', '-distress_score')
        
        # Get distressed farmers
        service = get_distress_service(days_lookback=30)
        result = service.get_distressed_farmers(
            production_type=production_type,
            region=region,
            district=district,
            min_distress_score=min_distress_score,
            min_capacity=min_capacity,
            has_available_stock=has_available_stock,
            limit=limit,
            ordering=ordering
        )
        
        return Response({
            'count': result['count'],
            'summary': result['summary'],
            'filters': {
                'region': region,
                'district': district,
                'production_type': production_type,
                'min_distress_score': min_distress_score,
                'min_capacity': min_capacity,
                'has_available_stock': has_available_stock,
            },
            'results': result['results'],
        }, status=status.HTTP_200_OK)


class FarmDistressDetailView(APIView):
    """
    Get detailed distress assessment for a specific farm.
    
    GET /api/admin/procurement/farms/{farm_id}/distress/
    
    Returns complete distress assessment matching frontend spec:
    - distress_score (0-100)
    - distress_level (CRITICAL, HIGH, MODERATE, LOW, STABLE)
    - distress_factors (array of contributing factors)
    - capacity info
    - sales_history
    - procurement_history
    - contact info
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request, farm_id):
        from farms.models import Farm
        from procurement.services.farmer_distress_v2 import get_distress_service
        from procurement.models import FarmDistressHistory
        
        try:
            farm = Farm.objects.get(id=farm_id)
        except Farm.DoesNotExist:
            return Response(
                {'error': 'Farm not found', 'code': 'FARM_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        service = get_distress_service(days_lookback=30)
        assessment = service.calculate_distress_score(farm)
        
        # Also get historical trend
        trend = FarmDistressHistory.get_farm_trend(farm, days=90)
        assessment['distress_trend'] = trend
        
        return Response(assessment, status=status.HTTP_200_OK)


class OrderFarmRecommendationsView(APIView):
    """
    Get farm recommendations for a specific order, prioritized by distress.
    
    GET /api/admin/procurement/orders/{order_id}/recommend-farms/
    
    Returns farms that:
    1. Match the order's production type
    2. Have available inventory
    3. Are not already assigned to this order
    4. Sorted by distress score (highest first - farmers who need help most)
    
    Response matches frontend spec with:
    - order info
    - recommendations array with distress_score, distress_level, priority_reason
    - summary with can_fulfill, critical_farms count
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request, order_id):
        from procurement.models import ProcurementOrder
        from procurement.services.farmer_distress_v2 import get_distress_service
        
        try:
            order = ProcurementOrder.objects.get(id=order_id)
        except ProcurementOrder.DoesNotExist:
            return Response(
                {'error': 'Order not found', 'code': 'ORDER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        limit = int(request.query_params.get('limit', 20))
        
        service = get_distress_service(days_lookback=30)
        result = service.get_farms_for_order(order, limit=limit)
        
        return Response(result, status=status.HTTP_200_OK)


class FarmerDashboardView(APIView):
    """
    Farmer Dashboard API Endpoint
    
    GET /api/dashboards/farmer/
    
    Returns farmer-specific metrics:
    - My assignments
    - Earnings and payments
    - Delivery history
    - Performance summary
    
    Permission: Farmer only
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def get(self, request):
        service = FarmerDashboardService(request.user)
        
        # Get all dashboard data
        data = {
            'overview': service.get_overview_stats(),
            'assignments': service.get_my_assignments(limit=50),
            'pending_actions': service.get_pending_actions(),
            'earnings': service.get_earnings_breakdown(),
            'deliveries': service.get_delivery_history(limit=20),
            'performance': service.get_performance_summary(),
        }
        
        return Response(data, status=status.HTTP_200_OK)


class FarmerOverviewView(APIView):
    """
    Farmer Overview Stats Only
    
    GET /api/dashboards/farmer/overview/
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def get(self, request):
        service = FarmerDashboardService(request.user)
        data = service.get_overview_stats()
        return Response(data, status=status.HTTP_200_OK)


class FarmerAssignmentsView(APIView):
    """
    Farmer Assignments List
    
    GET /api/dashboards/farmer/assignments/
    GET /api/dashboards/farmer/assignments/?status=pending
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def get(self, request):
        service = FarmerDashboardService(request.user)
        
        status_filter = request.query_params.get('status', None)
        limit = int(request.query_params.get('limit', 50))
        
        data = service.get_my_assignments(status=status_filter, limit=limit)
        return Response(data, status=status.HTTP_200_OK)


class FarmerEarningsView(APIView):
    """
    Farmer Earnings Breakdown
    
    GET /api/dashboards/farmer/earnings/
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def get(self, request):
        service = FarmerDashboardService(request.user)
        data = service.get_earnings_breakdown()
        return Response(data, status=status.HTTP_200_OK)


class FarmerPendingActionsView(APIView):
    """
    Farmer Pending Actions
    
    GET /api/dashboards/farmer/pending-actions/
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def get(self, request):
        service = FarmerDashboardService(request.user)
        data = service.get_pending_actions()
        return Response(data, status=status.HTTP_200_OK)
