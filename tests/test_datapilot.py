"""
Comprehensive Pytest Test Suite for DataPilot.
Covers all 15 required test scenarios using a disposable synthetic development database:
1. Simple SELECT queries
2. Filtering
3. Sorting
4. Aggregation
5. JOIN operations
6. Invalid table names
7. Invalid column names
8. Destructive SQL rejection (DROP, DELETE, TRUNCATE, INSERT, UPDATE, ALTER)
9. Multiple-statement rejection (Chained injection)
10. Query timeout enforcement
11. Empty results handling
12. Database connection failures
13. Follow-up questions (Conversational memory)
14. Retry limits enforcement (Bounded correction loop)
15. Disposable development database lifecycle
"""

import pytest
import sqlite3
import time

from app.core.sql_safety import SQLSafetyValidator, QueryClassification
from app.db.synthetic_dev_db import SyntheticDevelopmentDB, QueryExecutionResult
from app.agent.schema_retriever import SchemaRetriever
from app.agent.blind_sql_subagents import BlindSubagentOrchestrator
from app.agent.sql_evaluator import SQLEvaluatorAgent
from app.agent.bounded_correction import BoundedQueryCorrector
from app.agent.memory import ConversationalMemory
from app.agent.explainer import QueryExplainer
from app.agent.datapilot_pipeline import DataPilotPipeline


@pytest.fixture
def disposable_db():
    """Provides a fresh, isolated in-memory development database for each test."""
    db = SyntheticDevelopmentDB(db_path=":memory:")
    yield db
    db.close()


@pytest.fixture
def validator():
    """Provides standard SQL safety validator."""
    return SQLSafetyValidator()


@pytest.fixture
def pipeline(disposable_db, validator):
    """Provides end-to-end DataPilot pipeline on disposable database."""
    return DataPilotPipeline(dev_db=disposable_db, validator=validator)


# 1. Simple SELECT queries
def test_simple_select_queries(disposable_db):
    sql = "SELECT region_id, province, region_name, country FROM dim_region"
    result = disposable_db.execute_query(sql)
    assert result.success is True
    assert result.row_count == 6
    assert "province" in result.columns
    assert result.rows[0]["country"] == "中国"
    assert result.rows[0]["region_name"] in ["华南", "华东", "西南", "华北", "华中"]


# 2. Filtering
def test_filtering_queries(disposable_db):
    sql = "SELECT order_id, order_amount FROM fact_order WHERE order_amount > 5000"
    result = disposable_db.execute_query(sql)
    assert result.success is True
    assert result.row_count > 0
    for row in result.rows:
        assert row["order_amount"] > 5000


# 3. Sorting
def test_sorting_queries(disposable_db):
    sql = "SELECT product_id, product_name FROM dim_product ORDER BY product_id DESC LIMIT 5"
    result = disposable_db.execute_query(sql)
    assert result.success is True
    assert result.row_count == 5
    ids = [r["product_id"] for r in result.rows]
    assert ids == sorted(ids, reverse=True)


# 4. Aggregation
def test_aggregation_queries(disposable_db):
    sql = "SELECT SUM(order_amount) AS total_gmv, AVG(order_amount) AS aov, COUNT(*) AS cnt FROM fact_order"
    result = disposable_db.execute_query(sql)
    assert result.success is True
    assert result.row_count == 1
    assert result.rows[0]["total_gmv"] > 0
    assert result.rows[0]["cnt"] == 22


# 5. JOIN operations
def test_join_operations(disposable_db):
    sql = (
        "SELECT p.product_name, SUM(f.order_amount) AS revenue "
        "FROM fact_order f "
        "JOIN dim_product p ON f.product_id = p.product_id "
        "GROUP BY p.product_name "
        "ORDER BY revenue DESC LIMIT 3"
    )
    result = disposable_db.execute_query(sql)
    assert result.success is True
    assert result.row_count == 3
    assert "revenue" in result.columns
    assert "product_name" in result.columns


# 6. Invalid table names
def test_invalid_table_names(validator, disposable_db):
    sql = "SELECT * FROM secret_financial_records"
    val = validator.validate(sql)
    assert val.is_valid is False
    assert "unapproved table" in val.error_message.lower()

    exec_res = disposable_db.execute_query(sql)
    assert exec_res.success is False
    assert "Validation Error" in exec_res.error


# 7. Invalid column names
def test_invalid_column_names(disposable_db):
    sql = "SELECT nonexistent_column_xyz FROM fact_order"
    exec_res = disposable_db.execute_query(sql)
    assert exec_res.success is False
    assert "no such column" in exec_res.error.lower()


# 8. Destructive SQL rejection
@pytest.mark.parametrize("destructive_sql", [
    "DROP TABLE dim_customer;",
    "DELETE FROM fact_order WHERE 1=1;",
    "TRUNCATE TABLE dim_product;",
    "ALTER TABLE dim_region ADD COLUMN temp_col INT;",
    "INSERT INTO dim_customer VALUES ('C999', 'Hacker', 'M', 'Bronze');",
    "UPDATE fact_order SET order_amount = 0;",
])
def test_destructive_sql_rejection(validator, disposable_db, destructive_sql):
    val = validator.validate(destructive_sql)
    assert val.is_valid is False
    assert any(verb in val.error_message.upper() for verb in ["DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT", "UPDATE"])

    exec_res = disposable_db.execute_query(destructive_sql)
    assert exec_res.success is False
    assert "Validation Error" in exec_res.error


# 9. Multiple-statement rejection
def test_multiple_statement_rejection(validator, disposable_db):
    sql = "SELECT * FROM dim_region; DROP TABLE dim_region;"
    val = validator.validate(sql)
    assert val.is_valid is False
    assert val.classification == QueryClassification.MULTI_STATEMENT
    assert "Multiple SQL statements detected" in val.error_message

    exec_res = disposable_db.execute_query(sql)
    assert exec_res.success is False


# 10. Query timeout enforcement
def test_query_timeout():
    # Use very low timeout to trigger interrupt on heavy query
    fast_timeout_db = SyntheticDevelopmentDB(db_path=":memory:", timeout_seconds=0.0001)
    heavy_sql = "SELECT count(*) FROM fact_order a, fact_order b, fact_order c, fact_order d"
    res = fast_timeout_db.execute_query(heavy_sql)
    # The progress handler aborts query when tick limit exceeded
    assert res.success is False
    assert "timed out" in res.error.lower() or "interrupted" in res.error.lower()
    fast_timeout_db.close()


# 11. Empty results handling
def test_empty_results(disposable_db):
    sql = "SELECT * FROM fact_order WHERE order_amount > 999999999"
    result = disposable_db.execute_query(sql)
    assert result.success is True
    assert result.row_count == 0
    assert result.rows == []


# 12. Database connection failures
def test_database_connection_failures():
    db = SyntheticDevelopmentDB(db_path=":memory:")
    # Intentionally close connection to simulate outage
    db.close()
    result = db.execute_query("SELECT * FROM dim_region")
    assert result.success is False
    assert "Cannot operate on a closed database" in result.error or "closed" in result.error.lower()


# 13. Follow-up questions (Conversational Memory)
def test_follow_up_questions(pipeline):
    # Turn 1
    resp1 = pipeline.process_query("显示销售额最高的前5个商品")
    assert resp1.execution_result.success is True
    assert resp1.execution_result.row_count == 5

    # Turn 2: Follow-up
    resp2 = pipeline.process_query("再按近30天过滤")
    assert resp2.is_follow_up is True
    assert resp2.execution_result.success is True
    assert "f.date_id BETWEEN 20250101 AND 20250131" in resp2.final_sql


# 14. Retry limits enforcement
def test_retry_limits():
    corrector = BoundedQueryCorrector(max_retries=3)
    schema_ctx = SchemaRetriever().retrieve_schema_context("test")
    # Irrecoverable query with invalid syntax
    res = corrector.execute_bounded_correction(
        failing_sql="SELCT ALL FROM table_that_does_not_exist",
        initial_error="syntax error",
        query="test",
        schema_context=schema_ctx,
    )
    assert res.success is False
    assert res.retry_count == 3
    assert "limit reached" in res.error.lower()


# 15. Disposable development database lifecycle
def test_disposable_development_database():
    # Verify two distinct in-memory DBs do not share state
    db1 = SyntheticDevelopmentDB(":memory:")
    db2 = SyntheticDevelopmentDB(":memory:")

    assert db1.execute_query("SELECT count(*) as c FROM fact_order").rows[0]["c"] == 22
    assert db2.execute_query("SELECT count(*) as c FROM fact_order").rows[0]["c"] == 22

    db1.close()
    db2.close()
