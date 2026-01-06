"""
Google AdSense Management API Service

Provides integration with Google AdSense for retrieving ad revenue,
performance metrics, and payment history.

Requirements:
    - google-auth>=2.0.0
    - google-auth-oauthlib>=1.0.0
    - google-api-python-client>=2.0.0

Setup:
    1. Enable AdSense Management API in Google Cloud Console
    2. Create OAuth 2.0 credentials (Web Application)
    3. Set environment variables:
        - GOOGLE_ADSENSE_CLIENT_ID
        - GOOGLE_ADSENSE_CLIENT_SECRET
        - GOOGLE_ADSENSE_ACCOUNT_ID
"""

import logging
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# Cache keys
ADSENSE_TOKEN_CACHE_KEY = 'adsense_oauth_token'
ADSENSE_EARNINGS_CACHE_PREFIX = 'adsense_earnings_'
ADSENSE_CACHE_TIMEOUT = 3600  # 1 hour


class AdSenseConfig:
    """AdSense configuration from environment variables"""
    
    def __init__(self):
        self.client_id = getattr(settings, 'GOOGLE_ADSENSE_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'GOOGLE_ADSENSE_CLIENT_SECRET', '')
        self.account_id = getattr(settings, 'GOOGLE_ADSENSE_ACCOUNT_ID', '')
        self.redirect_uri = getattr(settings, 'GOOGLE_ADSENSE_REDIRECT_URI', '')
        self.enabled = bool(self.client_id and self.client_secret)
    
    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.account_id)


class AdSenseService:
    """
    Service for interacting with Google AdSense Management API.
    
    Usage:
        service = AdSenseService()
        if service.is_available():
            earnings = service.get_earnings_summary()
    """
    
    SCOPES = ['https://www.googleapis.com/auth/adsense.readonly']
    API_VERSION = 'v2'
    
    def __init__(self):
        self.config = AdSenseConfig()
        self._credentials = None
        self._service = None
    
    def is_available(self) -> bool:
        """Check if AdSense integration is available and configured"""
        return self.config.is_configured and self._has_valid_token()
    
    def is_configured(self) -> bool:
        """Check if AdSense credentials are configured (may not be connected yet)"""
        return self.config.enabled
    
    def _has_valid_token(self) -> bool:
        """Check if we have a valid OAuth token stored"""
        token_data = cache.get(ADSENSE_TOKEN_CACHE_KEY)
        if not token_data:
            # Try to load from database
            token_data = self._load_token_from_db()
        return token_data is not None
    
    def _load_token_from_db(self) -> Optional[Dict]:
        """Load OAuth token from database"""
        try:
            from sales_revenue.models import PlatformSettings
            settings_obj = PlatformSettings.get_settings()
            if hasattr(settings_obj, 'adsense_oauth_token') and settings_obj.adsense_oauth_token:
                token_data = settings_obj.adsense_oauth_token
                # Cache it
                cache.set(ADSENSE_TOKEN_CACHE_KEY, token_data, ADSENSE_CACHE_TIMEOUT)
                return token_data
        except Exception as e:
            logger.warning(f"Could not load AdSense token from DB: {e}")
        return None
    
    def _save_token_to_db(self, token_data: Dict) -> bool:
        """Save OAuth token to database"""
        try:
            from sales_revenue.models import PlatformSettings
            settings_obj = PlatformSettings.get_settings()
            settings_obj.adsense_oauth_token = token_data
            settings_obj.save(update_fields=['adsense_oauth_token'])
            cache.set(ADSENSE_TOKEN_CACHE_KEY, token_data, ADSENSE_CACHE_TIMEOUT)
            return True
        except Exception as e:
            logger.error(f"Failed to save AdSense token: {e}")
            return False
    
    def get_authorization_url(self) -> str:
        """
        Get the OAuth authorization URL for connecting AdSense account.
        User must visit this URL to grant access.
        """
        if not self.config.enabled:
            raise ValueError("AdSense is not configured. Set GOOGLE_ADSENSE_CLIENT_ID and GOOGLE_ADSENSE_CLIENT_SECRET")
        
        try:
            from google_auth_oauthlib.flow import Flow
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=self.SCOPES,
                redirect_uri=self.config.redirect_uri
            )
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            # Store state for verification
            cache.set(f'adsense_oauth_state_{state}', True, 600)  # 10 minutes
            
            return authorization_url
            
        except ImportError:
            logger.error("google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib google-api-python-client")
            raise ImportError("Google OAuth libraries not installed")
    
    def handle_oauth_callback(self, authorization_code: str, state: str) -> bool:
        """
        Handle the OAuth callback and store the access token.
        
        Args:
            authorization_code: Code from Google OAuth callback
            state: State parameter for verification
            
        Returns:
            True if successful, False otherwise
        """
        # Verify state
        if not cache.get(f'adsense_oauth_state_{state}'):
            logger.warning("Invalid OAuth state parameter")
            return False
        
        try:
            from google_auth_oauthlib.flow import Flow
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=self.SCOPES,
                redirect_uri=self.config.redirect_uri
            )
            
            # Exchange code for token
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Store token
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': list(credentials.scopes),
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
            }
            
            # Clean up state
            cache.delete(f'adsense_oauth_state_{state}')
            
            return self._save_token_to_db(token_data)
            
        except Exception as e:
            logger.error(f"OAuth callback failed: {e}")
            return False
    
    def _get_service(self):
        """Get authenticated AdSense API service"""
        if self._service:
            return self._service
        
        token_data = cache.get(ADSENSE_TOKEN_CACHE_KEY) or self._load_token_from_db()
        if not token_data:
            raise ValueError("AdSense not connected. Complete OAuth flow first.")
        
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            credentials = Credentials(
                token=token_data['token'],
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id', self.config.client_id),
                client_secret=token_data.get('client_secret', self.config.client_secret),
                scopes=token_data.get('scopes', self.SCOPES),
            )
            
            self._service = build('adsense', self.API_VERSION, credentials=credentials)
            return self._service
            
        except ImportError:
            logger.error("Google API libraries not installed")
            raise ImportError("Install: pip install google-auth google-api-python-client")
    
    def get_account_info(self) -> Optional[Dict]:
        """Get AdSense account information"""
        cache_key = f'{ADSENSE_EARNINGS_CACHE_PREFIX}account_info'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            service = self._get_service()
            account = service.accounts().get(
                name=f'accounts/{self.config.account_id}'
            ).execute()
            
            result = {
                'account_id': self.config.account_id,
                'display_name': account.get('displayName', ''),
                'timezone': account.get('timeZone', 'UTC'),
                'state': account.get('state', 'UNKNOWN'),
            }
            
            cache.set(cache_key, result, ADSENSE_CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None
    
    def get_earnings(
        self,
        start_date: datetime,
        end_date: datetime,
        dimensions: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Get earnings report for a date range.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            dimensions: Grouping dimensions (DATE, MONTH, AD_UNIT_NAME, etc.)
            metrics: Metrics to include (ESTIMATED_EARNINGS, IMPRESSIONS, CLICKS, etc.)
            
        Returns:
            Report data with rows and totals
        """
        # Default dimensions and metrics
        if dimensions is None:
            dimensions = ['DATE']
        if metrics is None:
            metrics = ['ESTIMATED_EARNINGS', 'IMPRESSIONS', 'CLICKS', 'PAGE_VIEWS']
        
        # Cache key based on parameters
        cache_key = f'{ADSENSE_EARNINGS_CACHE_PREFIX}{start_date.date()}_{end_date.date()}_{"_".join(dimensions)}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            service = self._get_service()
            
            report = service.accounts().reports().generate(
                account=f'accounts/{self.config.account_id}',
                dateRange='CUSTOM',
                startDate_year=start_date.year,
                startDate_month=start_date.month,
                startDate_day=start_date.day,
                endDate_year=end_date.year,
                endDate_month=end_date.month,
                endDate_day=end_date.day,
                dimensions=dimensions,
                metrics=metrics,
            ).execute()
            
            result = self._parse_report(report, dimensions, metrics)
            cache.set(cache_key, result, ADSENSE_CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Failed to get earnings: {e}")
            return None
    
    def _parse_report(self, report: Dict, dimensions: List[str], metrics: List[str]) -> Dict:
        """Parse AdSense report response into a cleaner format"""
        rows = []
        
        if 'rows' in report:
            for row in report['rows']:
                parsed_row = {}
                
                # Parse dimension values
                if 'cells' in row:
                    for i, dim in enumerate(dimensions):
                        if i < len(row['cells']):
                            parsed_row[dim.lower()] = row['cells'][i].get('value', '')
                    
                    # Parse metric values (after dimensions)
                    for i, metric in enumerate(metrics):
                        cell_index = len(dimensions) + i
                        if cell_index < len(row['cells']):
                            value = row['cells'][cell_index].get('value', '0')
                            parsed_row[metric.lower()] = Decimal(value) if value else Decimal('0')
                
                rows.append(parsed_row)
        
        # Get totals
        totals = {}
        if 'totals' in report and 'cells' in report['totals']:
            for i, metric in enumerate(metrics):
                cell_index = len(dimensions) + i
                if cell_index < len(report['totals']['cells']):
                    value = report['totals']['cells'][cell_index].get('value', '0')
                    totals[metric.lower()] = Decimal(value) if value else Decimal('0')
        
        return {
            'rows': rows,
            'totals': totals,
            'row_count': len(rows),
        }
    
    def get_earnings_summary(self) -> Dict:
        """
        Get a summary of earnings for dashboard display.
        
        Returns:
            {
                'today': Decimal,
                'yesterday': Decimal,
                'this_week': Decimal,
                'this_month': Decimal,
                'last_month': Decimal,
            }
        """
        cache_key = f'{ADSENSE_EARNINGS_CACHE_PREFIX}summary'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        last_month_end = month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        
        summary = {
            'today': Decimal('0.00'),
            'yesterday': Decimal('0.00'),
            'this_week': Decimal('0.00'),
            'this_month': Decimal('0.00'),
            'last_month': Decimal('0.00'),
            'currency': 'USD',
            'last_updated': now.isoformat(),
        }
        
        if not self.is_available():
            summary['error'] = 'AdSense not connected'
            return summary
        
        try:
            # Today
            today_report = self.get_earnings(
                datetime.combine(today, datetime.min.time()),
                datetime.combine(today, datetime.max.time())
            )
            if today_report and 'totals' in today_report:
                summary['today'] = today_report['totals'].get('estimated_earnings', Decimal('0.00'))
            
            # Yesterday
            yesterday_report = self.get_earnings(
                datetime.combine(yesterday, datetime.min.time()),
                datetime.combine(yesterday, datetime.max.time())
            )
            if yesterday_report and 'totals' in yesterday_report:
                summary['yesterday'] = yesterday_report['totals'].get('estimated_earnings', Decimal('0.00'))
            
            # This week
            week_report = self.get_earnings(
                datetime.combine(week_start, datetime.min.time()),
                datetime.combine(today, datetime.max.time())
            )
            if week_report and 'totals' in week_report:
                summary['this_week'] = week_report['totals'].get('estimated_earnings', Decimal('0.00'))
            
            # This month
            month_report = self.get_earnings(
                datetime.combine(month_start, datetime.min.time()),
                datetime.combine(today, datetime.max.time())
            )
            if month_report and 'totals' in month_report:
                summary['this_month'] = month_report['totals'].get('estimated_earnings', Decimal('0.00'))
            
            # Last month
            last_month_report = self.get_earnings(
                datetime.combine(last_month_start, datetime.min.time()),
                datetime.combine(last_month_end, datetime.max.time())
            )
            if last_month_report and 'totals' in last_month_report:
                summary['last_month'] = last_month_report['totals'].get('estimated_earnings', Decimal('0.00'))
            
            cache.set(cache_key, summary, ADSENSE_CACHE_TIMEOUT)
            
        except Exception as e:
            logger.error(f"Failed to get earnings summary: {e}")
            summary['error'] = str(e)
        
        return summary
    
    def get_top_performing_pages(self, days: int = 30, limit: int = 10) -> List[Dict]:
        """
        Get top performing pages by earnings.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of pages to return
        """
        cache_key = f'{ADSENSE_EARNINGS_CACHE_PREFIX}top_pages_{days}_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if not self.is_available():
            return []
        
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            report = self.get_earnings(
                start_date,
                end_date,
                dimensions=['URL_CHANNEL_NAME'],
                metrics=['ESTIMATED_EARNINGS', 'PAGE_VIEWS', 'IMPRESSIONS', 'CLICKS']
            )
            
            if not report or 'rows' not in report:
                return []
            
            # Sort by earnings and limit
            rows = sorted(
                report['rows'],
                key=lambda x: x.get('estimated_earnings', Decimal('0')),
                reverse=True
            )[:limit]
            
            result = [{
                'page': row.get('url_channel_name', 'Unknown'),
                'earnings': str(row.get('estimated_earnings', Decimal('0.00'))),
                'page_views': int(row.get('page_views', 0)),
                'impressions': int(row.get('impressions', 0)),
                'clicks': int(row.get('clicks', 0)),
            } for row in rows]
            
            cache.set(cache_key, result, ADSENSE_CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Failed to get top pages: {e}")
            return []
    
    def get_payments_history(self, limit: int = 12) -> List[Dict]:
        """
        Get payment history from AdSense.
        
        Args:
            limit: Maximum number of payments to return
        """
        cache_key = f'{ADSENSE_EARNINGS_CACHE_PREFIX}payments_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        if not self.is_available():
            return []
        
        try:
            service = self._get_service()
            
            payments = service.accounts().payments().list(
                parent=f'accounts/{self.config.account_id}'
            ).execute()
            
            result = []
            for payment in payments.get('payments', [])[:limit]:
                result.append({
                    'date': payment.get('date', ''),
                    'amount': payment.get('amount', '0'),
                    'name': payment.get('name', ''),
                })
            
            cache.set(cache_key, result, ADSENSE_CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Failed to get payments: {e}")
            return []
    
    def disconnect(self) -> bool:
        """Disconnect AdSense account by removing stored token"""
        try:
            from sales_revenue.models import PlatformSettings
            settings_obj = PlatformSettings.get_settings()
            settings_obj.adsense_oauth_token = None
            settings_obj.save(update_fields=['adsense_oauth_token'])
            
            # Clear cache
            cache.delete(ADSENSE_TOKEN_CACHE_KEY)
            
            # Clear all earnings cache
            # Note: This is a simplified approach; in production you might want
            # to use cache.delete_pattern if using Redis
            
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect AdSense: {e}")
            return False


# Singleton instance
_adsense_service = None


def get_adsense_service() -> AdSenseService:
    """Get the AdSense service singleton"""
    global _adsense_service
    if _adsense_service is None:
        _adsense_service = AdSenseService()
    return _adsense_service
