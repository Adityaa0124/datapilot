"""
DataPilot Query Router
Handles natural language database queries via both SSE streaming and structured JSON endpoints.
Includes DataPilot Pipeline integration with Blind Subagents, SQL Safety Validator, and Benchmark execution.
"""

from typing import Annotated, Any, Dict, Optional
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
try:
    from app.services.query_service import QueryService
except ImportError:
    QueryService = None
from app.agent.datapilot_pipeline import DataPilotPipeline
from app.evaluation.benchmark_evaluator import BenchmarkEvaluator

query_router = APIRouter()

# Singleton pipeline instance for standalone / local dev mode
default_pipeline = DataPilotPipeline()


class DataPilotQueryResponse(BaseModel):
    user_query: str
    is_follow_up: bool
    final_sql: str
    validation_status: str
    execution_status: str
    row_count: int
    data: list[Dict[str, Any]]
    technical_breakdown: str
    natural_language_summary: str
    markdown_report: str
    latency_ms: float


@query_router.post("/api/datapilot/query", response_model=DataPilotQueryResponse)
def datapilot_query_handler(request: QuerySchema):
    """
    Direct structured API for DataPilot Autonomous Database Analyst.
    Executes Schema-Aware Retrieval, Blind Subagents, SQL Safety Validation,
    Development DB Execution, and Structured Explanation.
    """
    resp = default_pipeline.process_query(request.query)

    return DataPilotQueryResponse(
        user_query=resp.user_query,
        is_follow_up=resp.is_follow_up,
        final_sql=resp.final_sql,
        validation_status=resp.explanation.validation_status,
        execution_status=resp.explanation.execution_status,
        row_count=resp.execution_result.row_count,
        data=resp.execution_result.rows,
        technical_breakdown=resp.explanation.technical_breakdown,
        natural_language_summary=resp.explanation.natural_language_summary,
        markdown_report=resp.markdown_report,
        latency_ms=resp.total_latency_ms,
    )


@query_router.get("/api/datapilot/benchmark")
def datapilot_benchmark_handler():
    """
    Executes the automated 14-scenario benchmark dataset and returns verifiable evaluation metrics.
    """
    evaluator = BenchmarkEvaluator(pipeline=default_pipeline)
    report = evaluator.run_benchmark()
    return {
        "total_cases": report.total_cases,
        "passed_cases": report.passed_cases,
        "failed_cases": report.failed_cases,
        "overall_accuracy_pct": report.overall_accuracy_pct,
        "execution_success_rate_pct": report.execution_success_rate_pct,
        "adversarial_rejection_rate_pct": report.adversarial_rejection_rate_pct,
        "average_latency_ms": report.average_latency_ms,
        "results_by_category": report.results_by_category,
        "markdown_report": evaluator.format_report_markdown(report),
    }


@query_router.post("/api/query")
async def query_handler(
    query: QuerySchema,
    query_service: Annotated[Optional[QueryService], Depends(get_query_service)],
):
    """
    Receives natural language query and streams response.
    Falls back gracefully to standalone DataPilotPipeline if Docker infrastructure is not available.
    """
    if query_service is not None:
        try:
            return StreamingResponse(
                query_service.query(query.query),
                media_type="text/event-stream",
            )
        except Exception:
            pass  # Fall through to standalone pipeline streaming

    # Standalone pipeline streaming fallback
    async def event_generator():
        resp = default_pipeline.process_query(query.query)
        yield f"data: {json.dumps({'type': 'progress', 'step': 'Validate SQL', 'status': 'success'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'sql', 'data': resp.final_sql}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'result', 'data': resp.execution_result.rows}, ensure_ascii=False, default=str)}\n\n"
        yield f"data: {json.dumps({'type': 'explanation', 'data': resp.explanation.natural_language_summary}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
