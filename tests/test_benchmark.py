"""
Pytest integration for the DataPilot Benchmark Evaluation Suite.
Ensures that the automated benchmark can be executed as part of CI/CD regression tests.
"""

from app.evaluation.benchmark_evaluator import BenchmarkEvaluator


def test_benchmark_suite_execution():
    evaluator = BenchmarkEvaluator()
    report = evaluator.run_benchmark()

    # Verify metrics
    assert report.total_cases >= 14
    assert report.passed_cases == report.total_cases
    assert report.overall_accuracy_pct == 100.0
    assert report.execution_success_rate_pct == 100.0
    assert report.adversarial_rejection_rate_pct == 100.0
    assert report.average_latency_ms > 0.0

    # Ensure markdown report renders
    md = evaluator.format_report_markdown(report)
    assert "# DataPilot Benchmark Evaluation Report" in md
    assert "Category Performance Breakdown" in md

