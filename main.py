"""
FastAPI Application Entrypoint

Initializes the FastAPI application instance, registers the lifespan handler,
mounts API routers, provides health check endpoints, and serves the static frontend
single-page application (SPA) distribution when compiled.
"""

import os
import sys
from pathlib import Path
import uuid

# Ensure workspace root is always on sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.core.context import request_id_ctx_var

# Lifespan manages resource initialization and graceful cleanup on startup/shutdown
app = FastAPI(
    title="DataPilot API",
    description="Autonomous Database Analyst — Natural Language to SQL",
    version="1.0.0",
    lifespan=lifespan,
)

# Register query router (/api/datapilot/query, /api/datapilot/benchmark, /api/query)
app.include_router(query_router)


@app.get("/health", tags=["System"])
@app.get("/api/health", tags=["System"])
def health_check():
    """
    Health check probe for container orchestrators, load balancers, and uptime monitors.
    Returns current service health, version, and database execution mode.
    """
    is_external = os.getenv("ENABLE_EXTERNAL_SERVICES", "false").lower() in ("true", "1")
    return {
        "status": "healthy",
        "service": "datapilot",
        "version": "1.0.0",
        "mode": "enterprise_infrastructure" if is_external else "standalone_synthetic",
    }


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # Before request processing: assign unique request ID
    request_id = uuid.uuid4()
    request_id_ctx_var.set(request_id)
    response = await call_next(request)
    # After request processing: return response with trace context header
    response.headers["X-Request-ID"] = str(request_id)
    return response


# Optional: Mount production frontend build if dist/ exists
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        target = frontend_dist / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_dist / "index.html")
