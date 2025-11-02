"""
Tailscale Authentication Middleware (Sprint 18)
================================================

Implements app-level authentication using Tailscale network access.

Access Levels:
1. **Admin** (header + in TAILSCALE_ADMINS): Full access including /vpn
2. **Viewer with account** (header but NOT admin): All routes EXCEPT /vpn
3. **Viewer via node share** (no header but Tailscale IP): All routes EXCEPT /vpn

Node Share Support:
- When you share a node with another Tailnet, they access WITHOUT headers
- We detect Tailscale CGNAT IP (100.64.0.0/10) to allow node shares
- Node shares have same access as registered viewers (everything except /vpn)

Headers injected by Tailscale (when user is in YOUR Tailnet):
- Tailscale-User-Login: user@example.com
- Tailscale-User-Name: John Doe
- Tailscale-User-Profile-Pic: https://...

Note: Headers only present for users in your Tailnet, NOT for node shares.
"""

import logging
import ipaddress
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List

logger = logging.getLogger(__name__)


class TailscaleAuthMiddleware(BaseHTTPMiddleware):
    """
    Tailscale authentication middleware.

    Reads Tailscale-User-Login header and enforces role-based access control.
    """

    def __init__(
        self,
        app,
        enabled: bool = True,
        admin_users: Optional[List[str]] = None,
        bypass_local: bool = True
    ):
        """
        Initialize Tailscale auth middleware.

        Args:
            app: FastAPI application
            enabled: Enable/disable auth (default: True)
            admin_users: List of admin user emails (default: [])
            bypass_local: Allow localhost without auth (default: True for dev)
        """
        super().__init__(app)
        self.enabled = enabled
        self.admin_users = admin_users or []
        self.bypass_local = bypass_local

        # Protected routes requiring admin role (only /vpn for now)
        self.admin_routes = [
            "/vpn"
        ]

        # Routes excluded from auth (public)
        self.public_routes = [
            "/health",
            "/ready",
            "/version",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static"
        ]

        logger.info(f"TailscaleAuthMiddleware initialized (enabled={enabled}, admins={len(self.admin_users)})")

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public (no auth required)."""
        return any(path.startswith(public) for public in self.public_routes)

    def _is_admin_route(self, path: str) -> bool:
        """Check if route requires admin role."""
        return any(path.startswith(admin) for admin in self.admin_routes)

    def _is_local_request(self, request: Request) -> bool:
        """Check if request originates from localhost."""
        if not request.client:
            return False

        client_host = request.client.host
        return client_host in ["127.0.0.1", "localhost", "::1"]

    def _get_user_from_headers(self, request: Request) -> Optional[str]:
        """Extract user email from Tailscale headers."""
        return request.headers.get("Tailscale-User-Login")

    def _is_admin(self, user_login: str) -> bool:
        """Check if user is admin."""
        return user_login in self.admin_users

    def _is_tailscale_ip(self, ip: str) -> bool:
        """
        Check if IP is from Tailscale CGNAT range (100.64.0.0/10).

        Tailscale uses CGNAT IP range for all nodes in the mesh network.
        This allows detection of node shares without user headers.
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
            tailscale_net = ipaddress.ip_network("100.64.0.0/10")
            return ip_obj in tailscale_net
        except ValueError:
            return False

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get real client IP from request."""
        # Try X-Forwarded-For first (nginx proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Try X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client
        if request.client:
            return request.client.host

        return None

    async def dispatch(self, request: Request, call_next):
        """
        Process request with Tailscale auth.

        Logic:
        1. Public routes → allow
        2. Localhost (dev) → bypass if enabled
        3. Check if Tailscale IP (100.64.0.0/10)
        4. If NOT Tailscale IP → 401 Unauthorized
        5. If has header + admin → ADMIN role
        6. If has header + NOT admin → VIEWER role
        7. If NO header but Tailscale IP → VIEWER role (node share)
        8. Admin routes (/vpn) → require ADMIN role
        9. All other routes → allow VIEWER
        """

        # Skip if auth disabled
        if not self.enabled:
            return await call_next(request)

        # Skip public routes
        if self._is_public_route(request.url.path):
            return await call_next(request)

        # Bypass localhost in development
        if self.bypass_local and self._is_local_request(request):
            logger.debug(f"Bypassing auth for localhost: {request.url.path}")
            request.state.user_login = "localhost_dev"
            request.state.role = "admin"  # Localhost has admin in dev
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if coming from Tailscale network
        is_tailscale = client_ip and self._is_tailscale_ip(client_ip)

        if not is_tailscale:
            logger.warning(f"Unauthorized: {request.url.path} from non-Tailscale IP {client_ip}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Access via Tailscale required. Connect to VPN first."
                }
            )

        # Extract user from Tailscale headers
        user_login = self._get_user_from_headers(request)

        # Determine role
        if user_login:
            # Has header - user in YOUR Tailnet
            if self._is_admin(user_login):
                role = "admin"
                logger.debug(f"Admin user: {user_login} → {request.url.path}")
            else:
                role = "viewer"
                logger.debug(f"Viewer user: {user_login} → {request.url.path}")
        else:
            # No header but Tailscale IP - node share
            role = "viewer"
            user_login = f"shared-node-{client_ip}"
            logger.debug(f"Node share access: {user_login} → {request.url.path}")

        # Attach to request state for audit logging
        request.state.user_login = user_login
        request.state.role = role

        # Check admin routes
        if self._is_admin_route(request.url.path):
            if role != "admin":
                logger.warning(f"Forbidden: {user_login} (role={role}) attempted admin route {request.url.path}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "message": f"Admin access required. Route '/vpn' is restricted to administrators."
                    }
                )

            logger.info(f"Admin access granted: {user_login} → {request.url.path}")

        # Process request
        response = await call_next(request)

        # Add audit headers
        response.headers["X-Authenticated-User"] = user_login
        response.headers["X-User-Role"] = role

        return response


def tailscale_auth_middleware(
    enabled: bool = True,
    admin_users: Optional[List[str]] = None,
    bypass_local: bool = True
):
    """
    Factory function to create Tailscale auth middleware.

    Usage in main.py:
        from api.middleware import tailscale_auth_middleware
        app.add_middleware(
            TailscaleAuthMiddleware,
            enabled=settings.TAILSCALE_AUTH_ENABLED,
            admin_users=settings.TAILSCALE_ADMINS,
            bypass_local=settings.ENVIRONMENT == "development"
        )

    Args:
        enabled: Enable/disable auth
        admin_users: List of admin emails
        bypass_local: Allow localhost without auth (dev mode)

    Returns:
        Middleware configuration tuple
    """
    return TailscaleAuthMiddleware, {
        "enabled": enabled,
        "admin_users": admin_users,
        "bypass_local": bypass_local
    }
