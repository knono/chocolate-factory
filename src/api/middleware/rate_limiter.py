# src/api/middleware/rate_limiter.py
"""Rate limiting middleware for API protection."""

import time
from typing import Dict, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        enable_ip_tracking: bool = True
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute
            burst_size: Allow burst up to this many requests
            enable_ip_tracking: Track requests per IP
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.enable_ip_tracking = enable_ip_tracking
        
        # Storage for request tracking
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque())
        self.blocked_ips: Dict[str, float] = {}  # IP -> unblock time
        
        # Statistics
        self.total_requests = 0
        self.blocked_requests = 0
        self.unique_clients = set()
    
    def get_client_id(self, request: Request) -> str:
        """
        Get client identifier from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client identifier string
        """
        if self.enable_ip_tracking:
            # Try to get real IP from headers (for proxied requests)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
            
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip
            
            # Fallback to client host
            if request.client:
                return request.client.host
        
        # Default to a generic identifier if IP tracking is disabled
        return "anonymous"
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed for client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if allowed, False if rate limited
        """
        current_time = time.time()
        
        # Check if IP is temporarily blocked
        if client_id in self.blocked_ips:
            if current_time < self.blocked_ips[client_id]:
                return False
            else:
                # Unblock time has passed
                del self.blocked_ips[client_id]
                logger.info(f"Client {client_id} unblocked")
        
        # Get request history for this client
        request_history = self.request_times[client_id]
        
        # Remove requests older than 1 minute
        cutoff_time = current_time - 60
        while request_history and request_history[0] < cutoff_time:
            request_history.popleft()
        
        # Check if under rate limit
        if len(request_history) < self.requests_per_minute:
            request_history.append(current_time)
            return True
        
        # Check burst allowance
        if len(request_history) < self.requests_per_minute + self.burst_size:
            # Allow burst but log warning
            logger.warning(f"Client {client_id} using burst allowance")
            request_history.append(current_time)
            return True
        
        return False
    
    def block_client(self, client_id: str, duration: int = 300):
        """
        Temporarily block a client.
        
        Args:
            client_id: Client identifier
            duration: Block duration in seconds
        """
        self.blocked_ips[client_id] = time.time() + duration
        logger.warning(f"Client {client_id} blocked for {duration} seconds")
    
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics."""
        return {
            'total_requests': self.total_requests,
            'blocked_requests': self.blocked_requests,
            'unique_clients': len(self.unique_clients),
            'currently_blocked': len(self.blocked_ips),
            'block_rate': round(
                (self.blocked_requests / self.total_requests * 100)
                if self.total_requests > 0 else 0,
                2
            )
        }
    
    def reset_client(self, client_id: str):
        """Reset rate limit for a specific client."""
        if client_id in self.request_times:
            del self.request_times[client_id]
        if client_id in self.blocked_ips:
            del self.blocked_ips[client_id]
        logger.info(f"Rate limit reset for client {client_id}")


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting."""
    
    def __init__(
        self,
        rate_limiter: RateLimiter,
        exclude_paths: Optional[list] = None
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            rate_limiter: RateLimiter instance
            exclude_paths: List of paths to exclude from rate limiting
        """
        self.rate_limiter = rate_limiter
        self.exclude_paths = exclude_paths or ['/docs', '/redoc', '/openapi.json']
    
    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get client identifier
        client_id = self.rate_limiter.get_client_id(request)
        
        # Track statistics
        self.rate_limiter.total_requests += 1
        self.rate_limiter.unique_clients.add(client_id)
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(client_id):
            self.rate_limiter.blocked_requests += 1
            
            # Check if we should block the client
            recent_blocks = self.rate_limiter.blocked_requests
            if recent_blocks > 10:  # Too many attempts
                self.rate_limiter.block_client(client_id)
            
            # Return rate limit error
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + 60))
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        request_history = self.rate_limiter.request_times[client_id]
        remaining = max(0, self.rate_limiter.requests_per_minute - len(request_history))
        
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        
        return response


# Create global rate limiter instances for different endpoints
default_rate_limiter = RateLimiter(requests_per_minute=60, burst_size=10)
ml_rate_limiter = RateLimiter(requests_per_minute=30, burst_size=5)  # More restrictive for ML endpoints
public_rate_limiter = RateLimiter(requests_per_minute=120, burst_size=20)  # More permissive for public endpoints