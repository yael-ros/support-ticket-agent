"""Shared slowapi Limiter instance for api/main.py and api/demo.py.

A single Limiter (and thus a single app.state.limiter / exception handler)
must back every rate-limited route in the app; keeping it here — rather
than in main.py, which owns `app` — lets demo.py import it without a
main.py <-> demo.py circular import (main.py mounts demo.py's router).

Safe to use postponed annotations here: this module defines no route
functions of its own, so the slowapi __globals__ bug (see main.py's
module docstring) doesn't apply.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

API_KEY_HEADER = "X-API-Key"


def key_by_api_key(request: Request) -> str:
    """Default key_func: buckets rate limits per caller API key, not per IP.

    Falls back to a shared 'anonymous' bucket for keyless requests on
    routes that require auth — those get rejected by verify_api_key
    regardless, so the bucket choice there only matters for
    logging/debugging, not security. api/demo.py's unauthenticated route
    overrides this per-limit with an IP-based and a global key instead.
    """
    return request.headers.get(API_KEY_HEADER, "anonymous")


limiter = Limiter(key_func=key_by_api_key)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Like slowapi's default handler, but skips the redundant "Rate limit
    exceeded: " prefix when a route set its own error_message (e.g.
    api/demo.py's spec-exact "Demo limit reached for today..." wording).
    Routes without a custom error_message (currently /tickets's 20/minute
    limit) keep the original "Rate limit exceeded: <limit string>"
    wording — unchanged from slowapi's own default handler.
    """
    message = exc.detail if exc.limit.error_message else f"Rate limit exceeded: {exc.detail}"
    response = JSONResponse({"error": message}, status_code=429)
    return limiter._inject_headers(response, request.state.view_rate_limit)
