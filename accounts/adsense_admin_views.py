"""
AdSense Admin Views

Provides endpoints for managing Google AdSense integration,
viewing ad revenue, and generating performance reports.

Endpoints:
    GET  /api/admin/adsense/status/ - Check connection status
    GET  /api/admin/adsense/connect/ - Get OAuth URL to connect
    GET  /api/admin/adsense/callback/ - OAuth callback handler
    POST /api/admin/adsense/disconnect/ - Disconnect AdSense
    GET  /api/admin/adsense/earnings/ - Earnings summary
    GET  /api/admin/adsense/reports/ - Detailed reports
    GET  /api/admin/adsense/payments/ - Payment history
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.adsense_service import get_adsense_service, AdSenseService

logger = logging.getLogger(__name__)


class IsSuperAdmin(IsAuthenticated):
    """
    Permission class for AdSense admin endpoints.
    Only SUPER_ADMIN can manage AdSense integration.
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.role == 'SUPER_ADMIN'


class IsFinanceViewer(IsAuthenticated):
    """
    Permission class for viewing AdSense data.
    Allows: SUPER_ADMIN, YEA_OFFICIAL, NATIONAL_ADMIN
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        allowed_roles = ['SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN']
        return request.user.role in allowed_roles


class AdSenseStatusView(APIView):
    """
    GET /api/admin/adsense/status/
    
    Check AdSense integration status.
    """
    permission_classes = [IsFinanceViewer]
    
    def get(self, request):
        service = get_adsense_service()
        
        response_data = {
            'configured': service.is_configured(),
            'connected': service.is_available(),
            'account_info': None,
        }
        
        if service.is_available():
            account_info = service.get_account_info()
            if account_info:
                response_data['account_info'] = account_info
        
        return Response(response_data)


class AdSenseConnectView(APIView):
    """
    GET /api/admin/adsense/connect/
    
    Get OAuth authorization URL to connect AdSense account.
    Only Super Admin can connect/disconnect.
    """
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        service = get_adsense_service()
        
        if not service.is_configured():
            return Response({
                'error': 'AdSense not configured',
                'message': 'Set GOOGLE_ADSENSE_CLIENT_ID and GOOGLE_ADSENSE_CLIENT_SECRET in environment',
                'code': 'NOT_CONFIGURED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if service.is_available():
            return Response({
                'message': 'AdSense already connected',
                'connected': True,
                'account_info': service.get_account_info()
            })
        
        try:
            auth_url = service.get_authorization_url()
            return Response({
                'authorization_url': auth_url,
                'message': 'Redirect user to this URL to authorize AdSense access',
                'instructions': [
                    '1. Open the authorization URL in a browser',
                    '2. Sign in with your Google account that has AdSense',
                    '3. Grant access to the application',
                    '4. You will be redirected back with an authorization code',
                ]
            })
        except ImportError as e:
            return Response({
                'error': 'Missing dependencies',
                'message': 'Install: pip install google-auth-oauthlib google-api-python-client',
                'code': 'MISSING_DEPENDENCIES'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Failed to generate auth URL: {e}")
            return Response({
                'error': 'Failed to generate authorization URL',
                'message': str(e),
                'code': 'AUTH_URL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdSenseCallbackView(APIView):
    """
    GET /api/admin/adsense/callback/
    
    Handle OAuth callback from Google.
    
    Query Parameters:
        - code: Authorization code from Google
        - state: State parameter for verification
    """
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        error = request.query_params.get('error')
        
        if error:
            return Response({
                'error': 'Authorization denied',
                'message': error,
                'code': 'AUTH_DENIED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not code or not state:
            return Response({
                'error': 'Missing parameters',
                'message': 'Authorization code and state are required',
                'code': 'MISSING_PARAMS'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_adsense_service()
        
        try:
            success = service.handle_oauth_callback(code, state)
            
            if success:
                account_info = service.get_account_info()
                return Response({
                    'success': True,
                    'message': 'AdSense connected successfully',
                    'account_info': account_info
                })
            else:
                return Response({
                    'error': 'Failed to connect AdSense',
                    'message': 'OAuth callback processing failed',
                    'code': 'CALLBACK_FAILED'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return Response({
                'error': 'Connection failed',
                'message': str(e),
                'code': 'CONNECTION_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdSenseDisconnectView(APIView):
    """
    POST /api/admin/adsense/disconnect/
    
    Disconnect AdSense account.
    """
    permission_classes = [IsSuperAdmin]
    
    def post(self, request):
        service = get_adsense_service()
        
        if not service.is_available():
            return Response({
                'message': 'AdSense not connected',
                'connected': False
            })
        
        success = service.disconnect()
        
        if success:
            return Response({
                'success': True,
                'message': 'AdSense disconnected successfully',
                'connected': False
            })
        else:
            return Response({
                'error': 'Failed to disconnect',
                'code': 'DISCONNECT_FAILED'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdSenseEarningsView(APIView):
    """
    GET /api/admin/adsense/earnings/
    
    Get earnings summary for dashboard display.
    
    Response includes:
        - today, yesterday, this_week, this_month, last_month earnings
        - top performing pages
    """
    permission_classes = [IsFinanceViewer]
    
    def get(self, request):
        service = get_adsense_service()
        
        if not service.is_available():
            return Response({
                'connected': False,
                'message': 'AdSense not connected',
                'earnings': None
            })
        
        try:
            summary = service.get_earnings_summary()
            top_pages = service.get_top_performing_pages(days=30, limit=5)
            
            # Convert Decimal to string for JSON serialization
            for key in ['today', 'yesterday', 'this_week', 'this_month', 'last_month']:
                if key in summary and isinstance(summary[key], Decimal):
                    summary[key] = str(summary[key])
            
            return Response({
                'connected': True,
                'earnings': summary,
                'top_pages': top_pages,
            })
            
        except Exception as e:
            logger.error(f"Failed to get earnings: {e}")
            return Response({
                'connected': True,
                'error': str(e),
                'earnings': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdSenseReportsView(APIView):
    """
    GET /api/admin/adsense/reports/
    
    Get detailed earnings reports with custom date range.
    
    Query Parameters:
        - start_date: YYYY-MM-DD (default: 30 days ago)
        - end_date: YYYY-MM-DD (default: today)
        - dimension: DATE, MONTH, AD_UNIT_NAME, COUNTRY_NAME (default: DATE)
    """
    permission_classes = [IsFinanceViewer]
    
    def get(self, request):
        service = get_adsense_service()
        
        if not service.is_available():
            return Response({
                'connected': False,
                'message': 'AdSense not connected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse date range
        today = timezone.now().date()
        default_start = today - timedelta(days=30)
        
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        dimension = request.query_params.get('dimension', 'DATE').upper()
        
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                start_date = default_start
            
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            else:
                end_date = today
                
        except ValueError:
            return Response({
                'error': 'Invalid date format',
                'message': 'Use YYYY-MM-DD format',
                'code': 'INVALID_DATE'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate dimension
        valid_dimensions = ['DATE', 'MONTH', 'WEEK', 'AD_UNIT_NAME', 'COUNTRY_NAME', 'PLATFORM_TYPE_NAME']
        if dimension not in valid_dimensions:
            return Response({
                'error': 'Invalid dimension',
                'valid_dimensions': valid_dimensions,
                'code': 'INVALID_DIMENSION'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            report = service.get_earnings(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
                dimensions=[dimension],
                metrics=['ESTIMATED_EARNINGS', 'IMPRESSIONS', 'CLICKS', 'PAGE_VIEWS', 'AD_REQUESTS_CTR']
            )
            
            if not report:
                return Response({
                    'error': 'Failed to fetch report',
                    'code': 'REPORT_ERROR'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Convert Decimals to strings
            for row in report.get('rows', []):
                for key, value in row.items():
                    if isinstance(value, Decimal):
                        row[key] = str(value)
            
            for key, value in report.get('totals', {}).items():
                if isinstance(value, Decimal):
                    report['totals'][key] = str(value)
            
            return Response({
                'connected': True,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'dimension': dimension,
                'report': report,
            })
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return Response({
                'error': 'Report generation failed',
                'message': str(e),
                'code': 'REPORT_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdSensePaymentsView(APIView):
    """
    GET /api/admin/adsense/payments/
    
    Get AdSense payment history.
    
    Query Parameters:
        - limit: Maximum number of payments (default: 12)
    """
    permission_classes = [IsFinanceViewer]
    
    def get(self, request):
        service = get_adsense_service()
        
        if not service.is_available():
            return Response({
                'connected': False,
                'message': 'AdSense not connected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        limit = int(request.query_params.get('limit', 12))
        
        try:
            payments = service.get_payments_history(limit=limit)
            
            return Response({
                'connected': True,
                'payments': payments,
                'count': len(payments),
            })
            
        except Exception as e:
            logger.error(f"Failed to get payments: {e}")
            return Response({
                'error': 'Failed to fetch payments',
                'message': str(e),
                'code': 'PAYMENTS_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
