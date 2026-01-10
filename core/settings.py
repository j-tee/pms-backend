"""
Django settings for YEA Poultry Management System.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
env_file = os.path.join(BASE_DIR, '.env.development')
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv()  # Try default .env


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Removed hardcoded fallback - SECRET_KEY MUST be set in environment
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable is not set. "
        "Please add SECRET_KEY to your .env file. "
        "For development, you can generate one with: "
        "python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Frontend URL for email/sms links
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')


# =============================================================================
# REDIS & CACHING (Required for scaling)
# =============================================================================

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')

# Cache configuration - uses Redis in production for cross-worker caching
if os.getenv('REDIS_ENABLED', 'False') == 'True':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'pms',
            'TIMEOUT': 300,  # 5 minutes default
        }
    }
    # Store sessions in Redis
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Development: use local memory cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }


# =============================================================================
# CELERY CONFIGURATION (Background Tasks)
# =============================================================================

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Celery Beat scheduler (for periodic tasks)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for allauth
    'django.contrib.gis',  # PostGIS support for geospatial data
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',  # Required for dj-rest-auth
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'django_celery_beat',  # Celery beat scheduler
    
    # Authentication & Social Auth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    
    # Phone number field
    'phonenumber_field',
    
    # Permissions
    'guardian',
    
    # Local apps
    'accounts',
    'farms',
    'procurement',
    'dashboards',
    'flock_management',
    'feed_inventory',
    'medication_management',
    'sales_revenue',
    'subscriptions',
    'advertising',
    'contact',
    'cms',  # Content Management System (About Us, Privacy Policy, etc.)
]

SITE_ID = 1  # Required for django.contrib.sites

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Required for allauth
    'subscriptions.institutional_auth.InstitutionalAPIUsageMiddleware',  # Rate limiting for institutional API
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',  # PostGIS backend for geospatial support
        'NAME': os.getenv('DB_NAME', 'poultry_db'),
        'USER': os.getenv('DB_USER', 'teejay'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Accra'  # Ghana timezone

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / os.getenv('STATIC_ROOT', 'staticfiles')

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / os.getenv('MEDIA_ROOT', 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# AUTHENTICATION SETTINGS
# =============================================================================

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = (
    # Django Admin Backend
    'django.contrib.auth.backends.ModelBackend',
    
    # Guardian object permissions backend
    'guardian.backends.ObjectPermissionBackend',
    
    # Allauth social authentication backend
    'allauth.account.auth_backends.AuthenticationBackend',
)

# Phone Number Field Settings
PHONENUMBER_DEFAULT_REGION = 'GH'  # Ghana
PHONENUMBER_DB_FORMAT = 'INTERNATIONAL'  # Store as +233XXXXXXXXX


# =============================================================================
# DJANGO-ALLAUTH SETTINGS
# =============================================================================

ACCOUNT_AUTHENTICATION_METHOD = 'email'  # Use email for login
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'  # Require email verification
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'

# Email verification settings
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_CONFIRMATION_COOLDOWN = 180  # 3 minutes between resends

# Login settings
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 900  # 15 minutes lockout

# Social account settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'optional'
SOCIALACCOUNT_QUERY_EMAIL = True

# Social Auth Providers (Add keys in .env file)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
            'key': ''
        }
    },
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
        'FIELDS': [
            'id',
            'email',
            'name',
            'first_name',
            'last_name',
        ],
        'VERIFIED_EMAIL': False,
        'APP': {
            'client_id': os.getenv('FACEBOOK_CLIENT_ID', ''),
            'secret': os.getenv('FACEBOOK_CLIENT_SECRET', ''),
            'key': ''
        }
    },
    'github': {
        'SCOPE': [
            'user',
            'repo',
            'read:org',
        ],
        'APP': {
            'client_id': os.getenv('GITHUB_CLIENT_ID', ''),
            'secret': os.getenv('GITHUB_CLIENT_SECRET', ''),
            'key': ''
        }
    }
}


# =============================================================================
# DJ-REST-AUTH SETTINGS
# =============================================================================

REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'jwt-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'jwt-refresh-token',
    'JWT_AUTH_HTTPONLY': True,
    'USER_DETAILS_SERIALIZER': 'accounts.serializers.UserSerializer',
    'REGISTER_SERIALIZER': 'accounts.serializers.UserRegistrationSerializer',
}


# =============================================================================
# GUARDIAN (OBJECT-LEVEL PERMISSIONS) SETTINGS
# =============================================================================

ANONYMOUS_USER_NAME = None  # Don't create anonymous user
GUARDIAN_RAISE_403 = True  # Raise exception on permission denied


# =============================================================================
# REST FRAMEWORK SETTINGS
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}


# =============================================================================
# JWT SETTINGS
# =============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME', 60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME', 10080))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': os.getenv('JWT_ALGORITHM', 'HS256'),
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}


# =============================================================================
# CORS SETTINGS
# =============================================================================

# For development - allow all origins. In production, use specific CORS_ALLOWED_ORIGINS list
DEBUG_MODE = os.getenv('DEBUG', 'True') == 'True'

if DEBUG_MODE:
    # Development: Allow all origins for easier testing
    CORS_ORIGIN_ALLOW_ALL = True
else:
    # Production: Whitelist specific frontend origins
    cors_origins_env = os.getenv(
        'CORS_ALLOWED_ORIGINS', 
        'https://yourdomain.com'
    )
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_env.split(',')]

# CSRF Trusted Origins (both dev and prod)
csrf_origins_env = os.getenv(
    'CSRF_TRUSTED_ORIGINS', 
    'http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173'
)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins_env.split(',')]

# CORS Headers Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# =============================================================================
# EMAIL SETTINGS
# =============================================================================

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@yea-pms.gov.gh')
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', 60))


# =============================================================================
# SMS SETTINGS (Hubtel)
# =============================================================================

# Enable/disable SMS notifications
SMS_ENABLED = os.getenv('SMS_ENABLED', 'False') == 'True'

# Hubtel API credentials
# Get these from: https://developers.hubtel.com/
HUBTEL_CLIENT_ID = os.getenv('HUBTEL_CLIENT_ID', '')
HUBTEL_CLIENT_SECRET = os.getenv('HUBTEL_CLIENT_SECRET', '')
HUBTEL_SENDER_ID = os.getenv('HUBTEL_SENDER_ID', 'YEA-PMS')

# SMS provider (for backwards compatibility)
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'console')  # Options: 'console', 'hubtel'


# =============================================================================
# GOOGLE ADSENSE SETTINGS
# =============================================================================

# AdSense Management API credentials
# Get these from: https://console.cloud.google.com/
# 1. Create a project and enable AdSense Management API
# 2. Create OAuth 2.0 credentials (Web Application type)
# 3. Set authorized redirect URI to: {BACKEND_URL}/api/admin/adsense/callback/

GOOGLE_ADSENSE_CLIENT_ID = os.getenv('GOOGLE_ADSENSE_CLIENT_ID', '')
GOOGLE_ADSENSE_CLIENT_SECRET = os.getenv('GOOGLE_ADSENSE_CLIENT_SECRET', '')
GOOGLE_ADSENSE_ACCOUNT_ID = os.getenv('GOOGLE_ADSENSE_ACCOUNT_ID', '')
GOOGLE_ADSENSE_REDIRECT_URI = os.getenv(
    'GOOGLE_ADSENSE_REDIRECT_URI', 
    f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/admin/adsense/callback/"
)


# =============================================================================
# FILE UPLOAD SETTINGS
# =============================================================================

MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', 5242880))  # 5MB default
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE


# =============================================================================
# MARKETPLACE ACTIVATION SETTINGS
# =============================================================================

# Marketplace activation fee (all farmers pay same price) - avoid "subscription" terminology
MARKETPLACE_ACTIVATION_FEE = float(os.getenv('MARKETPLACE_ACTIVATION_FEE', 50.00))
MARKETPLACE_SUBSCRIPTION_PRICE = MARKETPLACE_ACTIVATION_FEE  # Backward compatibility alias

# Trial and grace periods
MARKETPLACE_TRIAL_DAYS = int(os.getenv('MARKETPLACE_TRIAL_DAYS', 14))
SUBSCRIPTION_GRACE_PERIOD_DAYS = int(os.getenv('SUBSCRIPTION_GRACE_PERIOD_DAYS', 5))


# =============================================================================
# LOGGING SETTINGS
# =============================================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'False') == 'True'
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/django.log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_FILE_PATH,
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        } if LOG_TO_FILE else {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['console', 'file'] if LOG_TO_FILE else ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if LOG_TO_FILE else ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}


# =============================================================================
# SECURITY SETTINGS (Production)
# =============================================================================

if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True') == 'True'
    SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'True') == 'True'


# =============================================================================
# PAYSTACK PAYMENT SETTINGS
# =============================================================================

PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')
PAYSTACK_BASE_URL = os.getenv('PAYSTACK_BASE_URL', 'https://api.paystack.co')
PAYSTACK_WEBHOOK_SECRET = os.getenv('PAYSTACK_WEBHOOK_SECRET', '')
PAYSTACK_CALLBACK_URL = os.getenv('PAYSTACK_CALLBACK_URL', '')
PAYSTACK_WEBHOOK_URL = os.getenv('PAYSTACK_WEBHOOK_URL', '')

# Paystack Configuration
PAYSTACK_FEE_BEARER = os.getenv('PAYSTACK_FEE_BEARER', 'account')  # Platform pays fees
PAYSTACK_SETTLEMENT_SCHEDULE = os.getenv('PAYSTACK_SETTLEMENT_SCHEDULE', 'auto')  # auto or instant
PAYSTACK_CURRENCY = os.getenv('PAYSTACK_CURRENCY', 'GHS')

# Payment Processing
PAYMENT_RETRY_MAX_ATTEMPTS = int(os.getenv('PAYMENT_RETRY_MAX_ATTEMPTS', 3))
PAYMENT_RETRY_DELAY_SECONDS = int(os.getenv('PAYMENT_RETRY_DELAY_SECONDS', 300))
PAYMENT_AUTO_REFUND_HOURS = int(os.getenv('PAYMENT_AUTO_REFUND_HOURS', 72))
REFUND_ELIGIBILITY_HOURS = int(os.getenv('REFUND_ELIGIBILITY_HOURS', 48))

# Commission Structure (Tiered Percentage)
COMMISSION_TIER_1_PERCENTAGE = float(os.getenv('COMMISSION_TIER_1_PERCENTAGE', 5.0))  # < GHS 100
COMMISSION_TIER_2_PERCENTAGE = float(os.getenv('COMMISSION_TIER_2_PERCENTAGE', 3.0))  # GHS 100-500
COMMISSION_TIER_3_PERCENTAGE = float(os.getenv('COMMISSION_TIER_3_PERCENTAGE', 2.0))  # > GHS 500
COMMISSION_MINIMUM_AMOUNT = float(os.getenv('COMMISSION_MINIMUM_AMOUNT', 2.00))

# Mobile Money Providers
MTN_MOBILE_MONEY_ENABLED = os.getenv('MTN_MOBILE_MONEY_ENABLED', 'True') == 'True'
VODAFONE_CASH_ENABLED = os.getenv('VODAFONE_CASH_ENABLED', 'True') == 'True'
AIRTELTIGO_MONEY_ENABLED = os.getenv('AIRTELTIGO_MONEY_ENABLED', 'True') == 'True'


# =============================================================================
# GOOGLE MAPS API SETTINGS
# =============================================================================

# Google Maps Geocoding API Key (optional for GPS coordinate extraction)
# Used as fallback when GhanaPost GPS custom decoder is not available
# Free tier: 40,000 requests/month
# Get your API key: https://console.cloud.google.com/google/maps-apis/credentials
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')


# =============================================================================
# CONTACT FORM SETTINGS
# =============================================================================

# Contact form email configuration
CONTACT_EMAIL_TO = os.getenv('CONTACT_EMAIL_TO', 'support@yeapms.com')
CONTACT_EMAIL_FROM = os.getenv('CONTACT_EMAIL_FROM', 'noreply@yeapms.com')
CONTACT_EMAIL_REPLY_TO = os.getenv('CONTACT_EMAIL_REPLY_TO', 'support@yeapms.com')

# Rate limiting for contact form
CONTACT_FORM_RATE_LIMIT_PER_HOUR = int(os.getenv('CONTACT_FORM_RATE_LIMIT_PER_HOUR', 5))
CONTACT_FORM_RATE_LIMIT_PER_DAY = int(os.getenv('CONTACT_FORM_RATE_LIMIT_PER_DAY', 20))

# Admin URL for contact management (used in email links)
ADMIN_URL = os.getenv('ADMIN_URL', 'http://localhost:3000')

