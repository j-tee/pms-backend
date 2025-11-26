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
