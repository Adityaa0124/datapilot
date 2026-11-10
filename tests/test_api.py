"""
FastAPI Route and Integration Unit Tests for DataPilot endpoints.
Tests route handlers, request validation, Pydantic schemas, health check, and FastAPI route registration.
"""

from app.api.routers.query_router import (
    datapilot_query_handler,
    datapilot_benchmark_handler,
    DataPilotQueryResponse,
    query_router,
)
from app.api.schemas.query_schema import QuerySchema
from main import app, health_check


def test_api_datapilot_query_handler():
    req = QuerySchema(query="Show the top 5 products by sales")
    res = datapilot_query_handler(req)
    assert isinstance(res, DataPilotQueryResponse)
    assert "final_sql" in res.model_dump()
    assert res.row_count == 5
    assert len(res.data) == 5
    assert "PASSED" in res.validation_status
    assert "SUCCESS" in res.execution_status
    assert len(res.markdown_report) > 0
    assert res.latency_ms >= 0


def test_api_datapilot_benchmark_handler():
    report = datapilot_benchmark_handler()
    assert report["overall_accuracy_pct"] == 100.0
    assert report["total_cases"] >= 14
    assert report["failed_cases"] == 0
    assert "markdown_report" in report


def test_api_health_check_endpoint():
    res = health_check()
    assert res["status"] == "healthy"
    assert res["service"] == "datapilot"
    assert res["version"] == "1.0.0"
    assert res["mode"] in ("standalone_synthetic", "enterprise_infrastructure")


def test_api_fastapi_route_registration():
    router_paths = [r.path for r in query_router.routes]
    assert "/api/datapilot/query" in router_paths
    assert "/api/datapilot/benchmark" in router_paths
    assert "/api/query" in router_paths
    # Verify health endpoints registered on app
    app_paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/health" in app_paths
    assert "/api/health" in app_paths
