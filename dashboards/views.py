"""
Dashboard API Views

Provides REST API endpoints for dashboard data consumption.
Frontend applications will call these endpoints to render dashboard widgets.
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .permissions import IsExecutive, IsProcurementOfficer, IsFarmer
from .services import ExecutiveDashboardService, OfficerDashboardService, FarmerDashboardService

logger = logging.getLogger(__name__)


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
    Officer Orders List and Create
    
    GET /api/dashboards/officer/orders/
    GET /api/dashboards/officer/orders/?status=active
    
    POST /api/dashboards/officer/orders/
    POST /api/admin/procurement/orders/
    
    Create order with optional pre-selected farms from distress recommendations.
    Request body:
    {
        "title": "Order Title",
        "description": "Description",
        "production_type": "Broilers",
        "quantity_needed": 1000,
        "unit": "birds",
        "price_per_unit": 50.00,
        "delivery_deadline": "2024-03-01",
        "delivery_location": "Ministry of Health, Accra",
        "preferred_region": "Greater Accra",
        "selected_farm_ids": ["farm-uuid-1", "farm-uuid-2"],  // Optional
        "farm_quantities": {"farm-uuid-1": 500, "farm-uuid-2": 500},  // Optional
        "auto_assign": false
    }
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        service = OfficerDashboardService(request.user)
        
        status_filter = request.query_params.get('status', None)
        limit = int(request.query_params.get('limit', 50))
        
        data = service.get_my_orders(status=status_filter, limit=limit)
        return Response(data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create a new procurement order with optional farm pre-selection."""
        from procurement.services.procurement_workflow import ProcurementWorkflowService
        from decimal import Decimal
        
        data = request.data
        
        # Validate required fields
        required_fields = ['title', 'production_type', 'quantity_needed']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return Response(
                {'error': f'Missing required fields: {", ".join(missing)}', 'code': 'MISSING_FIELDS'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse and validate data
        try:
            quantity_needed = int(data['quantity_needed'])
            if quantity_needed <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            return Response(
                {'error': 'quantity_needed must be a positive integer', 'code': 'INVALID_QUANTITY'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        price_per_unit = data.get('price_per_unit')
        if price_per_unit:
            try:
                price_per_unit = Decimal(str(price_per_unit))
            except:
                price_per_unit = None
        
        # Extract farm selection data (from frontend distress recommendations)
        selected_farm_ids = data.get('selected_farm_ids', [])
        farm_quantities = data.get('farm_quantities')  # Optional {farm_id: quantity}
        
        # Build order data
        order_data = {
            'title': data['title'],
            'description': data.get('description', ''),
            'production_type': data['production_type'],
            'quantity_needed': quantity_needed,
            'unit': data.get('unit', 'birds'),
            'price_per_unit': price_per_unit,
            'delivery_location': data.get('delivery_location', ''),
            'delivery_deadline': data.get('delivery_deadline'),
            'preferred_region': data.get('preferred_region'),
            'max_farms': data.get('max_farms', 10),
            'auto_assign': data.get('auto_assign', False),
            'priority': data.get('priority', 'medium'),
            'quality_requirements': data.get('quality_requirements', ''),
            'delivery_instructions': data.get('delivery_instructions', ''),
        }
        
        # Remove None values
        order_data = {k: v for k, v in order_data.items() if v is not None}
        
        service = ProcurementWorkflowService()
        
        try:
            if selected_farm_ids:
                # Create order and assign to selected farms in one operation
                result = service.create_and_assign_order(
                    created_by=request.user,
                    selected_farm_ids=selected_farm_ids,
                    farm_quantities=farm_quantities,
                    **order_data
                )
                
                order = result['order']
                
                return Response({
                    'success': True,
                    'message': 'Order created and farms assigned',
                    'order': {
                        'id': str(order.id),
                        'order_number': order.order_number,
                        'title': order.title,
                        'status': order.status,
                        'quantity_needed': order.quantity_needed,
                        'quantity_assigned': order.quantity_assigned,
                        'remaining': order.quantity_needed - order.quantity_assigned,
                    },
                    'assignments': {
                        'count': result['assignment_count'],
                        'total_assigned': result['total_assigned'],
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                # Create draft order without farm assignment
                result = service.create_order(
                    created_by=request.user,
                    **order_data
                )
                
                order = result['order']
                
                return Response({
                    'success': True,
                    'message': 'Order created as draft',
                    'order': {
                        'id': str(order.id),
                        'order_number': order.order_number,
                        'title': order.title,
                        'status': order.status,
                        'quantity_needed': order.quantity_needed,
                    }
                }, status=status.HTTP_201_CREATED)
                
        except ValueError as e:
            return Response(
                {'error': str(e), 'code': 'VALIDATION_ERROR'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return Response(
                {'error': 'Failed to create order', 'code': 'CREATE_ERROR'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
    - distress_factors (array of contributing factors with weights)
    - recommended_action (URGENT_PURCHASE, PRIORITY_PURCHASE, etc.)
    - capacity info
    - inventory (total_birds_available, stock_age_days)
    - sales_history (days_without_sales, last_sale_date)
    - procurement_history
    - contact info (phone, email, constituency)
    - historical_trend (90-day trend data)
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
        assessment = service.calculate_distress_score(farm, include_full_details=True)
        
        # Get historical trend for 90-day chart
        trend = FarmDistressHistory.get_farm_trend(farm, days=90)
        assessment['historical_trend'] = trend
        
        # Get average daily production from flock data
        avg_daily_production = self._get_avg_daily_production(farm)
        assessment['avg_daily_production'] = avg_daily_production
        
        return Response(assessment, status=status.HTTP_200_OK)
    
    def _get_avg_daily_production(self, farm):
        """Get average daily egg production for the farm."""
        try:
            from flock_management.models import DailyProduction
            from django.db.models import Avg
            from datetime import timedelta
            from django.utils import timezone
            
            thirty_days_ago = timezone.now() - timedelta(days=30)
            avg = DailyProduction.objects.filter(
                flock__farm=farm,
                date__gte=thirty_days_ago.date()
            ).aggregate(avg_eggs=Avg('eggs_collected'))
            
            return round(avg['avg_eggs'] or 0, 1)
        except Exception:
            return 0


class OrderRecommendationsView(APIView):
    """
    AI-powered order recommendations for distressed farmers.
    
    GET /api/admin/procurement/order-recommendations/
    GET /api/admin/procurement/order-recommendations/?production_type=Broilers&region=Ashanti
    
    This endpoint provides smart recommendations for which farms should
    receive procurement orders based on their distress levels and available capacity.
    
    Query Parameters:
    - production_type: Filter by 'Broilers', 'Layers' (optional)
    - region: Filter by region name (optional)
    - limit: Maximum recommendations (default: 20)
    
    Response matches frontend spec:
    - recommendations array with distress info, urgency, suggested_quantity
    - summary with total_recommendations, critical_farms, can_fulfill_demand
    - pending_orders showing current unfulfilled orders
    """
    permission_classes = [IsAuthenticated, IsProcurementOfficer]
    
    def get(self, request):
        from procurement.services.farmer_distress_v2 import get_distress_service
        
        # Parse query parameters
        production_type = request.query_params.get('production_type')
        region = request.query_params.get('region')
        
        try:
            limit = int(request.query_params.get('limit', 20))
            if limit < 1:
                limit = 20
        except (ValueError, TypeError):
            limit = 20
        
        service = get_distress_service(days_lookback=30)
        result = service.get_order_recommendations(
            production_type=production_type,
            region=region,
            limit=limit
        )
        
        return Response(result, status=status.HTTP_200_OK)


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


class FarmerDeliveriesView(APIView):
    """
    Farmer Delivery History
    
    GET /api/procurement/deliveries/
    GET /api/procurement/deliveries/?limit=50
    
    Returns delivery history for the farmer's farm, showing:
    - Delivery number and order details
    - Quantities delivered
    - Quality inspection results
    - Verification status
    """
    permission_classes = [IsAuthenticated, IsFarmer]
    
    def get(self, request):
        service = FarmerDashboardService(request.user)
        
        # Parse limit parameter with validation
        try:
            limit = int(request.query_params.get('limit', 50))
            # Ensure limit is positive
            if limit < 0:
                limit = 0
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid limit parameter. Must be a positive integer.', 'code': 'INVALID_LIMIT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = service.get_delivery_history(limit=limit)
        return Response({
            'count': len(data),
            'results': data,
        }, status=status.HTTP_200_OK)
