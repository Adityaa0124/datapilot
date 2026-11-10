"""
Request Context Module

Maintains execution context variables across asynchronous requests using ContextVars,
ensuring request tracing identifiers (request_id) remain isolated per request.
"""

from contextvars import ContextVar

# ContextVar ensures thread-safe and coroutine-isolated request ID tracking
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="1")
