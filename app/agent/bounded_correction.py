"""
Bounded Query Correction Module.
Implements bounded retry logic for failed SQL queries.
Captures database execution and validation errors, provides schema feedback,
and strictly enforces retry limits to prevent infinite loops.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.agent.schema_retriever import SchemaContext, SchemaRetriever
from app.core.sql_safety import SQLSafetyValidator, SQLValidationResult
from app.db.synthetic_dev_db import QueryExecutionResult, SyntheticDevelopmentDB

DEFAULT_MAX_RETRIES: int = 3


@dataclass
class CorrectionAttempt:
    attempt_number: int
    original_sql: str
    error_message: str
    corrected_sql: Optional[str]
    is_valid: bool
    execution_result: Optional[QueryExecutionResult]


@dataclass
class CorrectionWorkflowResult:
    success: bool
    final_sql: Optional[str]
    attempts: List[CorrectionAttempt]
    retry_count: int
    max_retries: int
    error: Optional[str] = None
    execution_result: Optional[QueryExecutionResult] = None


class BoundedQueryCorrector:
    """
    Manages error analysis and bounded corrective synthesis.
    Stops after max_retries and ensures every correction passes validation.
    """

    def __init__(
        self,
        dev_db: Optional[SyntheticDevelopmentDB] = None,
        validator: Optional[SQLSafetyValidator] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.dev_db = dev_db or SyntheticDevelopmentDB()
        self.validator = validator or SQLSafetyValidator()
        self.max_retries = max_retries
        self.schema_retriever = SchemaRetriever()

    def _correct_sql_rule_based(
        self,
        failing_sql: str,
        error_message: str,
        schema_context: SchemaContext,
    ) -> str:
        """
        Analyzes the error message and applies surgical corrections:
        - Resolves ambiguous column errors (adds table aliases).
        - Corrects misspelled or invalid column/table names.
        - Adds missing JOIN clauses if foreign keys are referenced.
        - Fixes unapproved syntax or missing GROUP BY expressions.
        """
        corrected = failing_sql
        err_lower = error_message.lower()

        # Error Pattern 1: No such column / unknown column
        col_match = re.search(r"no such column:\s*([a-zA-Z0-9_\.]+)", error_message, re.IGNORECASE)
        if col_match:
            missing_col = col_match.group(1)
            # Check if missing column is in a known table and needs a join
            fact_table_pat = r"FROM\s+fact_order(?:\s+(?!WHERE|JOIN|GROUP|ORDER|LIMIT|HAVING)[a-zA-Z0-9_]+)?"
            if "product_name" in missing_col and "dim_product" not in corrected:
                corrected = re.sub(
                    fact_table_pat,
                    r"FROM fact_order f JOIN dim_product p ON f.product_id = p.product_id",
                    corrected,
                    flags=re.IGNORECASE,
                )
                corrected = re.sub(r"\b" + re.escape(missing_col) + r"\b", "p.product_name", corrected)

            elif "region" in missing_col and "dim_region" not in corrected:
                corrected = re.sub(
                    fact_table_pat,
                    r"FROM fact_order f JOIN dim_region r ON f.region_id = r.region_id",
                    corrected,
                    flags=re.IGNORECASE,
                )
                corrected = re.sub(r"\b" + re.escape(missing_col) + r"\b", "r.region_name", corrected)

            elif "customer" in missing_col and "dim_customer" not in corrected:
                corrected = re.sub(
                    fact_table_pat,
                    r"FROM fact_order f JOIN dim_customer c ON f.customer_id = c.customer_id",
                    corrected,
                    flags=re.IGNORECASE,
                )
                corrected = re.sub(r"\b" + re.escape(missing_col) + r"\b", "c.customer_name", corrected)

        # Error Pattern 2: Ambiguous column name
        elif "ambiguous" in err_lower:
            ambig_match = re.search(r"ambiguous column name:\s*([a-zA-Z0-9_]+)", error_message, re.IGNORECASE)
            if ambig_match:
                col_name = ambig_match.group(1)
                # Qualify with the fact table
                corrected = re.sub(r"\b" + col_name + r"\b", f"f.{col_name}", corrected)

        # Error Pattern 3: Missing GROUP BY in aggregate query
        elif "aggregate" in err_lower or "group by" in err_lower:
            # If selecting non-aggregates with SUM/COUNT, append GROUP BY
            if "GROUP BY" not in corrected.upper() and ("SUM(" in corrected.upper() or "COUNT(" in corrected.upper()):
                # Extract first non-aggregate select column
                select_match = re.search(r"SELECT\s+([a-zA-Z0-9_\.]+)", corrected, re.IGNORECASE)
                if select_match:
                    dim_col = select_match.group(1)
                    if not any(agg in dim_col.upper() for agg in ["SUM", "COUNT", "AVG", "MIN", "MAX"]):
                        corrected = f"{corrected} GROUP BY {dim_col}"

        # Error Pattern 4: Multiple statements rejected
        elif "multiple" in err_lower:
            # Strip extra statements
            parts = corrected.split(";")
            corrected = parts[0].strip()

        return corrected

    def execute_bounded_correction(
        self,
        failing_sql: str,
        initial_error: str,
        query: str,
        schema_context: SchemaContext,
    ) -> CorrectionWorkflowResult:
        """
        Executes bounded correction loop:
        1. Attempts correction using error diagnostics.
        2. Validates corrected query with SQLSafetyValidator.
        3. Executes against the development database.
        4. Bounds loop to max_retries.
        """
        attempts: List[CorrectionAttempt] = []
        current_sql = failing_sql
        current_error = initial_error

        for attempt_idx in range(1, self.max_retries + 1):
            # Generate candidate correction
            corrected_sql = self._correct_sql_rule_based(
                failing_sql=current_sql,
                error_message=current_error,
                schema_context=schema_context,
            )

            # 1. Re-validate corrected SQL
            val_res = self.validator.validate(corrected_sql)
            if not val_res.is_valid:
                attempt = CorrectionAttempt(
                    attempt_number=attempt_idx,
                    original_sql=current_sql,
                    error_message=current_error,
                    corrected_sql=corrected_sql,
                    is_valid=False,
                    execution_result=None,
                )
                attempts.append(attempt)
                current_error = f"Validation Error: {val_res.error_message}"
                continue

            # 2. Execute on dev database
            exec_res = self.dev_db.execute_query(val_res.sanitized_sql)
            attempt = CorrectionAttempt(
                attempt_number=attempt_idx,
                original_sql=current_sql,
                error_message=current_error,
                corrected_sql=val_res.sanitized_sql,
                is_valid=True,
                execution_result=exec_res,
            )
            attempts.append(attempt)

            if exec_res.success:
                return CorrectionWorkflowResult(
                    success=True,
                    final_sql=val_res.sanitized_sql,
                    attempts=attempts,
                    retry_count=attempt_idx,
                    max_retries=self.max_retries,
                    execution_result=exec_res,
                )

            # Update for next retry iteration
            current_sql = val_res.sanitized_sql
            current_error = exec_res.error

        # If loop finishes without success, return bounded failure
        return CorrectionWorkflowResult(
            success=False,
            final_sql=current_sql,
            attempts=attempts,
            retry_count=len(attempts),
            max_retries=self.max_retries,
            error=f"Correction limit reached ({self.max_retries} attempts). Last error: {current_error}",
        )
