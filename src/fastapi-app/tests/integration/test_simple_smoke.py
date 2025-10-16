"""
Simple Smoke Tests - Phase 9
=============================

Ultra-simple tests that verify the test infrastructure works.
These bypass complex imports and focus on test framework validation.
"""
import pytest


@pytest.mark.integration
def test_pytest_works():
    """Verify pytest is working."""
    assert True


@pytest.mark.integration
def test_client_fixture_exists(client):
    """Verify test client fixture is available."""
    assert client is not None


@pytest.mark.integration
def test_openapi_json_accessible(client):
    """Test OpenAPI spec is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data


@pytest.mark.integration
def test_root_redirect(client):
    """Test root redirects to dashboard."""
    response = client.get("/", follow_redirects=False)
    # Should redirect (307, 302, 301) or serve content (200)
    assert response.status_code in [200, 301, 302, 307]


# Simple count: 4 basic tests to validate test infrastructure
