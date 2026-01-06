"""
Shared pytest fixtures for dashboards tests.
"""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """API client for making requests."""
    return APIClient()
