"""SlowAPI-based rate limiter.

SlowAPI hooks into FastAPI route decorators and is hard to abstract cleanly
behind a simple check() interface.  This stub delegates to InMemoryRateLimiter
so the ABC contract is satisfied.  Replace with a Redis-backed implementation
for production multi-instance deployments.
"""

from app.security.rate_limiting.in_memory import InMemoryRateLimiter


class SlowAPIRateLimiter(InMemoryRateLimiter):
    """Production-facing rate limiter (currently in-memory; swap for Redis)."""
