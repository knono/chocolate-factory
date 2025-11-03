"""
Unit Tests for Tailscale Authentication Middleware (Sprint 18)
===============================================================

Tests for role-based access control using Tailscale network + headers.

Test Cases:
1. Admin (header + in TAILSCALE_ADMINS) → full access including /vpn
2. Viewer with account (header but NOT admin) → all except /vpn
3. Viewer via node share (no header but Tailscale IP) → all except /vpn
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from api.middleware.tailscale_auth import TailscaleAuthMiddleware


# Test app setup
@pytest.fixture
def test_app():
    """Create test FastAPI app with Tailscale auth middleware."""
    app = FastAPI()

    # Add middleware
    app.add_middleware(
        TailscaleAuthMiddleware,
        enabled=True,
        admin_users=["admin@example.com", "owner@example.com"],
        bypass_local=False  # Disable bypass for testing
    )

    # Test routes
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/dashboard")
    async def dashboard():
        return {"page": "dashboard"}

    @app.get("/vpn")
    async def vpn():
        return {"page": "vpn"}

    @app.post("/predict/train")
    async def train():
        return {"status": "training"}

    @app.post("/gaps/backfill")
    async def backfill():
        return {"status": "backfilling"}

    @app.post("/chat/ask")
    async def chat():
        return {"answer": "response"}

    return app


@pytest.fixture
def client(test_app):
    """Test client fixture."""
    return TestClient(test_app)


# Tests
def test_public_route_no_auth_required(client):
    """Test that public routes don't require authentication."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_non_tailscale_ip_returns_401(client):
    """Test that non-Tailscale IP (public internet) returns 401 Unauthorized."""
    # TestClient uses 127.0.0.1 by default (not Tailscale IP)
    # Simulate request from public IP without Tailscale
    response = client.get("/dashboard")
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["error"]
    assert "Tailscale" in response.json()["message"]


def test_viewer_with_account_can_access_dashboard(client):
    """Test that viewer with valid header (user in Tailnet) can access dashboard."""
    headers = {
        "Tailscale-User-Login": "viewer@example.com",
        "X-Forwarded-For": "100.64.1.50"  # Tailscale IP
    }
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"page": "dashboard"}
    assert response.headers.get("X-User-Role") == "viewer"


def test_node_share_can_access_dashboard(client):
    """Test that node share (no header but Tailscale IP) can access dashboard."""
    headers = {"X-Forwarded-For": "100.64.2.100"}  # Tailscale IP, no user header
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"page": "dashboard"}
    assert response.headers.get("X-User-Role") == "viewer"
    # User login should be synthetic: shared-node-{IP}
    assert "shared-node-" in response.headers.get("X-Authenticated-User", "")


def test_viewer_with_account_cannot_access_vpn(client):
    """Test that viewer with account cannot access admin route /vpn."""
    headers = {
        "Tailscale-User-Login": "viewer@example.com",
        "X-Forwarded-For": "100.64.1.50"
    }
    response = client.get("/vpn", headers=headers)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["error"]
    assert "Admin access required" in response.json()["message"]


def test_node_share_cannot_access_vpn(client):
    """Test that node share cannot access admin route /vpn."""
    headers = {"X-Forwarded-For": "100.64.2.100"}  # Tailscale IP, no user header
    response = client.get("/vpn", headers=headers)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["error"]


def test_admin_can_access_vpn(client):
    """Test that admin can access /vpn."""
    headers = {
        "Tailscale-User-Login": "admin@example.com",
        "X-Forwarded-For": "100.64.1.10"
    }
    response = client.get("/vpn", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"page": "vpn"}
    assert response.headers.get("X-User-Role") == "admin"


def test_viewer_can_access_non_admin_routes(client):
    """Test that viewer (with account) can access all non-admin routes."""
    headers = {
        "Tailscale-User-Login": "viewer@example.com",
        "X-Forwarded-For": "100.64.1.50"
    }

    # Test various viewer-accessible routes
    response = client.post("/predict/train", headers=headers)
    assert response.status_code == 200

    response = client.post("/gaps/backfill", headers=headers)
    assert response.status_code == 200

    response = client.post("/chat/ask", headers=headers)
    assert response.status_code == 200


def test_node_share_can_access_non_admin_routes(client):
    """Test that node share can access all non-admin routes."""
    headers = {"X-Forwarded-For": "100.64.2.100"}

    # Node shares have same access as viewers (all except /vpn)
    response = client.post("/predict/train", headers=headers)
    assert response.status_code == 200

    response = client.post("/gaps/backfill", headers=headers)
    assert response.status_code == 200


def test_authenticated_user_header_in_response(client):
    """Test that authenticated user header is added to response."""
    headers = {
        "Tailscale-User-Login": "viewer@example.com",
        "X-Forwarded-For": "100.64.1.50"
    }
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("X-Authenticated-User") == "viewer@example.com"
    assert response.headers.get("X-User-Role") == "viewer"


def test_localhost_bypass_when_enabled():
    """Test that localhost bypass works when enabled."""
    app = FastAPI()

    # Enable bypass for localhost
    app.add_middleware(
        TailscaleAuthMiddleware,
        enabled=True,
        admin_users=["admin@example.com"],
        bypass_local=True  # Enable bypass
    )

    @app.get("/vpn")
    async def vpn():
        return {"page": "vpn"}

    client = TestClient(app)

    # Access without Tailscale header (simulates localhost)
    # TestClient uses 127.0.0.1 by default
    response = client.get("/vpn")
    assert response.status_code == 200
    assert response.json() == {"page": "vpn"}


def test_auth_disabled():
    """Test that auth can be disabled via config."""
    app = FastAPI()

    # Disable auth
    app.add_middleware(
        TailscaleAuthMiddleware,
        enabled=False,  # Disabled
        admin_users=["admin@example.com"],
        bypass_local=False
    )

    @app.get("/vpn")
    async def vpn():
        return {"page": "vpn"}

    client = TestClient(app)

    # Access without header should work when auth is disabled
    response = client.get("/vpn")
    assert response.status_code == 200
    assert response.json() == {"page": "vpn"}


# Parametrized test for Tailscale IP detection
@pytest.mark.parametrize("ip,expected_tailscale", [
    ("100.64.0.1", True),      # Start of range
    ("100.64.50.100", True),   # Middle of range
    ("100.127.255.254", True), # End of range
    ("192.168.1.1", False),    # Private network
    ("10.0.0.1", False),       # Private network
    ("8.8.8.8", False),        # Public internet
    ("127.0.0.1", False),      # Localhost
])
def test_tailscale_ip_detection(ip, expected_tailscale):
    """Test that Tailscale IP range (100.64.0.0/10) is correctly detected."""
    from api.middleware.tailscale_auth import TailscaleAuthMiddleware
    from unittest.mock import MagicMock

    app = MagicMock()
    middleware = TailscaleAuthMiddleware(app, enabled=True, admin_users=[], bypass_local=False)

    assert middleware._is_tailscale_ip(ip) == expected_tailscale
