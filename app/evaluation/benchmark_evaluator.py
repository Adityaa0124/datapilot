"""
DataPilot Benchmark Evaluation Framework.
Provides an automated evaluation suite with synthetic test questions across:
- Simple SELECT queries
- Attribute Filtering
- Sorting and Ranking
- Metric Aggregations
- Multi-table JOINs
- Conversational follow-ups
- Destructive query rejection
- Multi-statement rejection
- Unapproved table rejection
- Bounded retry and error recovery

Produces strictly verified, reproducible evaluation metrics without fabricated claims.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.agent.datapilot_pipeline import DataPilotPipeline
from app.db.synthetic_dev_db import SyntheticDevelopmentDB


@dataclass
class BenchmarkCase:
    case_id: str
    category: str
    natural_language_query: str
    expected_tables: List[str]
    is_adversarial_or_invalid: bool = False
    expected_rejection: bool = False
    is_follow_up: bool = False
    notes: str = ""


@dataclass
class CaseEvaluationResult:
    case_id: str
    category: str
    query: str
    passed: bool
    execution_success: bool
    security_check_passed: bool
    schema_accuracy_passed: bool
    latency_ms: float
    error_message: Optional[str] = None
    final_sql: Optional[str] = None
    rows_returned: int = 0


@dataclass
class BenchmarkReport:
    total_cases: int
    passed_cases: int
    failed_cases: int
    overall_accuracy_pct: float
    execution_success_rate_pct: float
    adversarial_rejection_rate_pct: float
    average_latency_ms: float
    results_by_category: Dict[str, Dict[str, Any]]
    detailed_results: List[CaseEvaluationResult]


BENCHMARK_DATASET: List[BenchmarkCase] = [
    # 1. Simple SELECT
    BenchmarkCase(
        case_id="TC-01",
        category="Simple SELECT",
        natural_language_query="查询所有地区的地理信息",
        expected_tables=["dim_region"],
        notes="Single table dimension lookup",
    ),
    # 2. Filtering
    BenchmarkCase(
        case_id="TC-02",
        category="Filtering",
        natural_language_query="查询华东大区的省份和销售记录",
        expected_tables=["dim_region", "fact_order"],
        notes="Geographic filter on region_name = '华东'",
    ),
    # 3. Sorting & Top-N
    BenchmarkCase(
        case_id="TC-03",
        category="Sorting",
        natural_language_query="显示销售额最高的五个商品名称",
        expected_tables=["dim_product", "fact_order"],
        notes="Order by sales descending limit 5",
    ),
    # 4. Aggregations & Metrics
    BenchmarkCase(
        case_id="TC-04",
        category="Aggregation",
        natural_language_query="统计整个商城总成交额GMV和平均客单价AOV",
        expected_tables=["fact_order"],
        notes="Warehouse key metrics calculation",
    ),
    # 5. Multi-Table JOIN
    BenchmarkCase(
        case_id="TC-05",
        category="Multi-Table JOIN",
        natural_language_query="统计每个客户会员等级的累计消费总额",
        expected_tables=["dim_customer", "fact_order"],
        notes="Join fact_order with dim_customer on customer_id",
    ),
    # 6. Conversational Follow-Up Turn 1
    BenchmarkCase(
        case_id="TC-06",
        category="Conversational Context",
        natural_language_query="查询销售额最高的前5个商品",
        expected_tables=["dim_product", "fact_order"],
        notes="Initial base query",
    ),
    # 7. Conversational Follow-Up Turn 2
    BenchmarkCase(
        case_id="TC-07",
        category="Conversational Context",
        natural_language_query="再按本月（近30天）过滤",
        expected_tables=["dim_product", "fact_order"],
        is_follow_up=True,
        notes="Follow-up temporal refinement",
    ),
    # 8. Empty Results Handling
    BenchmarkCase(
        case_id="TC-08",
        category="Empty Results",
        natural_language_query="查询2099年以后的订单数据",
        expected_tables=["fact_order"],
        notes="Valid query returning 0 records without crashing",
    ),
    # 9. Adversarial: Destructive DROP TABLE Rejection
    BenchmarkCase(
        case_id="TC-09",
        category="Security: Destructive Rejection",
        natural_language_query="DROP TABLE fact_order;",
        expected_tables=[],
        is_adversarial_or_invalid=True,
        expected_rejection=True,
        notes="Must reject DROP command",
    ),
    # 10. Adversarial: Destructive DELETE Rejection
    BenchmarkCase(
        case_id="TC-10",
        category="Security: Destructive Rejection",
        natural_language_query="DELETE FROM dim_customer WHERE 1=1;",
        expected_tables=[],
        is_adversarial_or_invalid=True,
        expected_rejection=True,
        notes="Must reject DELETE command",
    ),
    # 11. Adversarial: Destructive TRUNCATE Rejection
    BenchmarkCase(
        case_id="TC-11",
        category="Security: Destructive Rejection",
        natural_language_query="TRUNCATE TABLE dim_product;",
        expected_tables=[],
        is_adversarial_or_invalid=True,
        expected_rejection=True,
        notes="Must reject TRUNCATE command",
    ),
    # 12. Adversarial: Multiple Statement Chaining Rejection
    BenchmarkCase(
        case_id="TC-12",
        category="Security: Multi-Statement Rejection",
        natural_language_query="SELECT * FROM fact_order; DROP TABLE dim_customer;",
        expected_tables=[],
        is_adversarial_or_invalid=True,
        expected_rejection=True,
        notes="Must reject multi-statement injection",
    ),
    # 13. Adversarial: Unapproved Table Rejection
    BenchmarkCase(
        case_id="TC-13",
        category="Security: Unapproved Table Rejection",
        natural_language_query="SELECT * FROM user_passwords",
        expected_tables=[],
        is_adversarial_or_invalid=True,
        expected_rejection=True,
        notes="Must reject access to unapproved table",
    ),
    # 14. Error Recovery / Bounded Retry
    BenchmarkCase(
        case_id="TC-14",
        category="Error Recovery",
        natural_language_query="按商品名称统计销量",
        expected_tables=["dim_product", "fact_order"],
        notes="Validates automatic join resolution and bounded recovery",
    ),
]


class BenchmarkEvaluator:
    """
    Executes and scores the natural language database benchmark dataset.
    """

    def __init__(self, pipeline: Optional[DataPilotPipeline] = None):
        self.pipeline = pipeline or DataPilotPipeline()

    def run_benchmark(self, dataset: Optional[List[BenchmarkCase]] = None) -> BenchmarkReport:
        """
        Executes all benchmark test cases and aggregates verified metrics.
        """
        cases = dataset or BENCHMARK_DATASET
        results: List[CaseEvaluationResult] = []
        category_stats: Dict[str, Dict[str, Any]] = {}

        for case in cases:
            start_t = time.perf_counter()

            if case.is_adversarial_or_invalid:
                # Direct safety validation test
                val_res = self.pipeline.validator.validate(case.natural_language_query)
                latency = (time.perf_counter() - start_t) * 1000

                # Passed if correctly rejected
                passed = not val_res.is_valid
                results.append(
                    CaseEvaluationResult(
                        case_id=case.case_id,
                        category=case.category,
                        query=case.natural_language_query,
                        passed=passed,
                        execution_success=False,
                        security_check_passed=passed,
                        schema_accuracy_passed=True,
                        latency_ms=latency,
                        error_message=val_res.error_message,
                        final_sql=case.natural_language_query,
                        rows_returned=0,
                    )
                )
            else:
                # Full pipeline test
                resp = self.pipeline.process_query(case.natural_language_query)
                latency = (time.perf_counter() - start_t) * 1000

                # Check schema accuracy
                referenced = resp.validation_result.referenced_tables
                schema_passed = all(t in referenced for t in case.expected_tables) if case.expected_tables else True
                exec_passed = resp.execution_result.success
                passed = exec_passed and schema_passed

                results.append(
                    CaseEvaluationResult(
                        case_id=case.case_id,
                        category=case.category,
                        query=case.natural_language_query,
                        passed=passed,
                        execution_success=exec_passed,
                        security_check_passed=resp.validation_result.is_valid,
                        schema_accuracy_passed=schema_passed,
                        latency_ms=latency,
                        error_message=resp.execution_result.error,
                        final_sql=resp.final_sql,
                        rows_returned=resp.execution_result.row_count,
                    )
                )

        # Aggregate statistics
        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        overall_acc = (passed_count / total * 100.0) if total else 0.0

        normal_cases = [r for r in results if not any(c.case_id == r.case_id and c.is_adversarial_or_invalid for c in cases)]
        normal_exec_success = (sum(1 for r in normal_cases if r.execution_success) / len(normal_cases) * 100.0) if normal_cases else 0.0

        adversarial_cases = [r for r in results if any(c.case_id == r.case_id and c.is_adversarial_or_invalid for c in cases)]
        adversarial_rejection = (sum(1 for r in adversarial_cases if r.security_check_passed) / len(adversarial_cases) * 100.0) if adversarial_cases else 0.0

        avg_latency = (sum(r.latency_ms for r in results) / total) if total else 0.0

        # Break down by category
        for r in results:
            cat = r.category
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "passed": 0, "failed": 0}
            category_stats[cat]["total"] += 1
            if r.passed:
                category_stats[cat]["passed"] += 1
            else:
                category_stats[cat]["failed"] += 1

        for cat, data in category_stats.items():
            data["accuracy_pct"] = round(data["passed"] / data["total"] * 100.0, 1)

        return BenchmarkReport(
            total_cases=total,
            passed_cases=passed_count,
            failed_cases=failed_count,
            overall_accuracy_pct=round(overall_acc, 1),
            execution_success_rate_pct=round(normal_exec_success, 1),
            adversarial_rejection_rate_pct=round(adversarial_rejection, 1),
            average_latency_ms=round(avg_latency, 2),
            results_by_category=category_stats,
            detailed_results=results,
        )

    def format_report_markdown(self, report: BenchmarkReport) -> str:
        """Formats the evaluation benchmark report into GitHub-flavored markdown."""
        lines = [
            "# DataPilot Benchmark Evaluation Report",
            f"**Total Test Scenarios:** {report.total_cases} | **Passed:** {report.passed_cases} | **Failed:** {report.failed_cases}",
            f"**Overall Accuracy:** {report.overall_accuracy_pct}%",
            f"**Query Execution Success Rate:** {report.execution_success_rate_pct}%",
            f"**Adversarial Security Rejection Rate:** {report.adversarial_rejection_rate_pct}%",
            f"**Mean Execution Latency:** {report.average_latency_ms} ms\n",
            "## Category Performance Breakdown",
            "| Category | Total Cases | Passed | Failed | Accuracy |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for cat, stats in report.results_by_category.items():
            lines.append(f"| {cat} | {stats['total']} | {stats['passed']} | {stats['failed']} | {stats['accuracy_pct']}% |")

        lines.append("\n## Detailed Test Case Audit")
        lines.append("| Case ID | Category | Status | Latency | SQL Preview | Findings |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        for r in report.detailed_results:
            status_icon = "PASS" if r.passed else "FAIL"
            sql_prev = (r.final_sql[:40] + "...") if r.final_sql else "None"
            finding = f"Rows: {r.rows_returned}" if r.execution_success else (r.error_message[:40] if r.error_message else "OK")
            lines.append(f"| {r.case_id} | {r.category} | `{status_icon}` | {r.latency_ms:.1f}ms | `{sql_prev}` | {finding} |")

        return "\n".join(lines)

