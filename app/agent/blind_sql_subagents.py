"""
Blind Independent SQL Subagents Module.
Defines three independent, isolated subagent strategies that generate candidate SQL
queries without seeing each other's work or reasoning (blind independent execution).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.agent.schema_retriever import SchemaContext


@dataclass
class CandidateSQL:
    candidate_id: str
    strategy_name: str
    perspective_description: str
    sql: str
    reasoning: str


class PragmaticSQLSubagent:
    """
    Subagent A (Pragmatic Pythonist / SQL Specialist):
    Produces clean, direct, idiomatic ANSI SQL with straightforward joins and aggregations.
    Focuses on simplicity, readability, and avoiding unnecessary complexity.
    """

    def __init__(self):
        self.subagent_id = "candidate_a_pragmatic"
        self.name = "Pragmatic SQL Developer"
        self.description = "Direct ANSI SQL, standard joins, concise aggregations without over-engineering."

    def generate(
        self,
        query: str,
        schema_context: SchemaContext,
        conversation_context: Optional[List[str]] = None,
    ) -> CandidateSQL:
        """Generates candidate SQL following the pragmatic strategy."""
        q = query.lower()
        active_tables = [t.table_name for t in schema_context.tables]

        # Case 1: Top N products by revenue / sales
        if "商品" in q or "product" in q:
            if "五" in q or "5" in q:
                limit_n = 5
            elif "十" in q or "10" in q:
                limit_n = 10
            elif "三" in q or "3" in q:
                limit_n = 3
            else:
                limit_n = 10

            sql = (
                f"SELECT p.product_name, SUM(f.order_amount) AS total_sales "
                f"FROM fact_order f "
                f"JOIN dim_product p ON f.product_id = p.product_id "
                f"GROUP BY p.product_name "
                f"ORDER BY total_sales DESC "
                f"LIMIT {limit_n}"
            )
            reasoning = "Pragmatic inner join between fact_order and dim_product aggregating sum of order_amount grouped by product_name with descending sort."

        # Case 2: Regional GMV / sales by province or region
        elif any(k in q for k in ["地区", "省份", "大区", "region", "province"]):
            dim_col = "r.province" if ("省" in q or "province" in q) else "r.region_name"
            sql = (
                f"SELECT {dim_col}, SUM(f.order_amount) AS gmv, COUNT(f.order_id) AS order_count "
                f"FROM fact_order f "
                f"JOIN dim_region r ON f.region_id = r.region_id "
                f"GROUP BY {dim_col} "
                f"ORDER BY gmv DESC"
            )
            reasoning = f"Direct aggregation of order_amount and order_count by {dim_col} joining fact_order and dim_region."

        # Case 3: Customer analysis / Member level analysis
        elif any(k in q for k in ["客户", "用户", "会员", "等级", "customer", "member"]):
            if "等级" in q or "member_level" in q:
                sql = (
                    "SELECT c.member_level, COUNT(DISTINCT c.customer_id) AS customer_count, "
                    "SUM(f.order_amount) AS total_spent "
                    "FROM fact_order f "
                    "JOIN dim_customer c ON f.customer_id = c.customer_id "
                    "GROUP BY c.member_level "
                    "ORDER BY total_spent DESC"
                )
                reasoning = "Aggregating customer counts and spending by member level using direct join."
            else:
                sql = (
                    "SELECT c.customer_name, SUM(f.order_amount) AS total_spent "
                    "FROM fact_order f "
                    "JOIN dim_customer c ON f.customer_id = c.customer_id "
                    "GROUP BY c.customer_name "
                    "ORDER BY total_spent DESC "
                    "LIMIT 10"
                )
                reasoning = "Top customers ranked by total order expenditure."

        # Case 4: Overall metrics (GMV, AOV, Total Orders)
        elif any(k in q for k in ["gmv", "aov", "总额", "销售额", "平均", "客单价", "订单量"]):
            sql = (
                "SELECT SUM(order_amount) AS gmv, "
                "AVG(order_amount) AS aov, "
                "COUNT(order_id) AS total_orders, "
                "SUM(order_quantity) AS total_units "
                "FROM fact_order"
            )
            reasoning = "Single-table aggregation on fact_order calculating key metrics GMV, AOV, total orders, and units."

        # Fallback query
        else:
            sql = "SELECT order_id, customer_id, product_id, order_amount FROM fact_order ORDER BY order_amount DESC LIMIT 10"
            reasoning = "Default sample selection from fact_order ordered by amount."

        return CandidateSQL(
            candidate_id=self.subagent_id,
            strategy_name=self.name,
            perspective_description=self.description,
            sql=sql,
            reasoning=reasoning,
        )


class DefensiveSQLSubagent:
    """
    Subagent B (Defensive Systems Engineer):
    Produces robust, defensive SQL with explicit NULL handling (COALESCE),
    safe type casting, zero-division protection, and boundary validation.
    """

    def __init__(self):
        self.subagent_id = "candidate_b_defensive"
        self.name = "Defensive SQL Specialist"
        self.description = "Defensive programming with COALESCE null handling, date boundary checks, and explicit filters."

    def generate(
        self,
        query: str,
        schema_context: SchemaContext,
        conversation_context: Optional[List[str]] = None,
    ) -> CandidateSQL:
        """Generates candidate SQL following the defensive strategy."""
        q = query.lower()

        # Product sales with null defenses
        if "商品" in q or "product" in q:
            limit_n = 5 if ("五" in q or "5" in q) else 10
            sql = (
                f"SELECT COALESCE(p.product_name, 'Unknown') AS product_name, "
                f"COALESCE(SUM(f.order_amount), 0.0) AS total_sales, "
                f"COALESCE(SUM(f.order_quantity), 0) AS units_sold "
                f"FROM fact_order f "
                f"LEFT JOIN dim_product p ON f.product_id = p.product_id "
                f"WHERE f.order_amount IS NOT NULL AND f.order_amount > 0 "
                f"GROUP BY p.product_name "
                f"ORDER BY total_sales DESC "
                f"LIMIT {limit_n}"
            )
            reasoning = "Defensive left join with COALESCE default wrappers for null protection, excluding negative/null amounts."

        # Regional sales with null checks
        elif any(k in q for k in ["地区", "省份", "大区", "region", "province"]):
            dim_col = "COALESCE(r.province, 'Unknown')" if ("省" in q or "province" in q) else "COALESCE(r.region_name, 'Unknown')"
            sql = (
                f"SELECT {dim_col} AS region, "
                f"COALESCE(SUM(f.order_amount), 0.0) AS gmv, "
                f"COUNT(f.order_id) AS total_orders "
                f"FROM fact_order f "
                f"JOIN dim_region r ON f.region_id = r.region_id "
                f"WHERE f.order_amount >= 0 "
                f"GROUP BY region "
                f"ORDER BY gmv DESC"
            )
            reasoning = "Defensive regional query ensuring non-negative orders and wrapped null defaults."

        # Overall metrics with division by zero safety
        else:
            sql = (
                "SELECT COALESCE(SUM(order_amount), 0.0) AS gmv, "
                "CASE WHEN COUNT(order_id) > 0 THEN SUM(order_amount) / COUNT(order_id) ELSE 0.0 END AS aov, "
                "COUNT(order_id) AS total_orders "
                "FROM fact_order "
                "WHERE order_amount IS NOT NULL"
            )
            reasoning = "Defensive metric calculation guarding against empty tables and division by zero using CASE WHEN."

        return CandidateSQL(
            candidate_id=self.subagent_id,
            strategy_name=self.name,
            perspective_description=self.description,
            sql=sql,
            reasoning=reasoning,
        )


class AnalyticalSQLSubagent:
    """
    Subagent C (Algorithmic & Dimensional Specialist):
    Produces structured, analytical SQL using Common Table Expressions (CTEs),
    window functions, and dimensional rollups.
    """

    def __init__(self):
        self.subagent_id = "candidate_c_analytical"
        self.name = "Analytical & CTE Specialist"
        self.description = "Modular CTE pipelines, dimensional ranking, and clean breakdown of intermediate states."

    def generate(
        self,
        query: str,
        schema_context: SchemaContext,
        conversation_context: Optional[List[str]] = None,
    ) -> CandidateSQL:
        """Generates candidate SQL following the analytical CTE strategy."""
        q = query.lower()

        if "商品" in q or "product" in q:
            limit_n = 5 if ("五" in q or "5" in q) else 10
            sql = (
                f"WITH product_revenue AS ("
                f"  SELECT p.product_id, p.product_name, p.category, "
                f"         SUM(f.order_amount) AS revenue, "
                f"         SUM(f.order_quantity) AS volume "
                f"  FROM fact_order f "
                f"  JOIN dim_product p ON f.product_id = p.product_id "
                f"  GROUP BY p.product_id, p.product_name, p.category"
                f") "
                f"SELECT product_name, category, revenue, volume "
                f"FROM product_revenue "
                f"ORDER BY revenue DESC "
                f"LIMIT {limit_n}"
            )
            reasoning = "Analytical pipeline factoring product sales into a CTE with category metadata before ranking top performers."

        elif any(k in q for k in ["地区", "省份", "大区", "region", "province"]):
            sql = (
                "WITH regional_summary AS ("
                "  SELECT r.region_name, r.province, "
                "         SUM(f.order_amount) AS total_gmv, "
                "         COUNT(f.order_id) AS order_count "
                "  FROM fact_order f "
                "  JOIN dim_region r ON f.region_id = r.region_id "
                "  GROUP BY r.region_name, r.province"
                ") "
                "SELECT region_name, province, total_gmv, order_count "
                "FROM regional_summary "
                "ORDER BY total_gmv DESC"
            )
            reasoning = "CTE pipeline grouping sales across two geographic hierarchies (region and province)."

        else:
            sql = (
                "WITH base_orders AS ("
                "  SELECT order_id, order_amount, order_quantity "
                "  FROM fact_order "
                "  WHERE order_amount > 0"
                ") "
                "SELECT SUM(order_amount) AS gmv, "
                "       AVG(order_amount) AS aov, "
                "       COUNT(order_id) AS order_count "
                "FROM base_orders"
            )
            reasoning = "CTE filtering valid transactions prior to computing aggregate warehouse metrics."

        return CandidateSQL(
            candidate_id=self.subagent_id,
            strategy_name=self.name,
            perspective_description=self.description,
            sql=sql,
            reasoning=reasoning,
        )


class BlindSubagentOrchestrator:
    """
    Coordinates the blind independent execution of all three subagents.
    Ensures that subagents execute in total isolation without shared discussion or bias.
    """

    def __init__(self):
        self.subagents = [
            PragmaticSQLSubagent(),
            DefensiveSQLSubagent(),
            AnalyticalSQLSubagent(),
        ]

    def generate_candidates(
        self,
        query: str,
        schema_context: SchemaContext,
        conversation_context: Optional[List[str]] = None,
    ) -> List[CandidateSQL]:
        """Runs each subagent blindly and returns the candidate solutions."""
        candidates = []
        for subagent in self.subagents:
            candidate = subagent.generate(
                query=query,
                schema_context=schema_context,
                conversation_context=conversation_context,
            )
            candidates.append(candidate)
        return candidates

