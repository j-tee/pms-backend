"""
Shared pytest fixtures for dashboards tests.
"""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test to prevent pollution."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """API client for making requests."""
    return APIClient()
