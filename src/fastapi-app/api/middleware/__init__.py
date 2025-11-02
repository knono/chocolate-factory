"""
API Middleware
==============

Authentication and security middleware for FastAPI.
"""

from .tailscale_auth import tailscale_auth_middleware

__all__ = ["tailscale_auth_middleware"]
