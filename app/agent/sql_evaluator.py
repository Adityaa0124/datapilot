"""
SQL Evaluator and Arbiter Agent.
Objectively evaluates candidate SQL queries generated blindly by independent subagents,
scores them against standardized safety and correctness rubrics, executes dry-runs against
the development database, selects the optimal winning query, and triggers bounded recovery if needed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.agent.blind_sql_subagents import CandidateSQL
from app.agent.schema_retriever import SchemaContext
from app.core.sql_safety import SQLSafetyValidator, SQLValidationResult
from app.db.synthetic_dev_db import QueryExecutionResult, SyntheticDevelopmentDB


@dataclass
class CandidateEvaluation:
    candidate_id: str
    strategy_name: str
    sql: str
    validation: SQLValidationResult
    execution: QueryExecutionResult
    safety_score: float  # max 40
    schema_fidelity_score: float  # max 30
    execution_score: float  # max 20
    efficiency_score: float  # max 10
    total_score: float  # max 100
    notes: List[str] = field(default_factory=list)


@dataclass
class EvaluatorDecision:
    approved: bool
    winner_candidate_id: Optional[str]
    selected_sql: Optional[str]
    execution_result: Optional[QueryExecutionResult]
    candidate_evaluations: List[CandidateEvaluation]
    rationale: str
    requires_retry: bool = False
    retry_feedback: Optional[str] = None


class SQLEvaluatorAgent:
    """
    Independent Lead QA & Evaluator for Natural Language to SQL Agents.
    Assesses candidate SQL queries objectively using concrete runtime evidence.
    """

    def __init__(
        self,
        dev_db: Optional[SyntheticDevelopmentDB] = None,
        validator: Optional[SQLSafetyValidator] = None,
    ):
        self.dev_db = dev_db or SyntheticDevelopmentDB()
        self.validator = validator or SQLSafetyValidator()

    def evaluate_candidates(
        self,
        query: str,
        candidates: List[CandidateSQL],
        schema_context: SchemaContext,
    ) -> EvaluatorDecision:
        """
        Evaluates, dry-runs, and scores all candidate solutions.
        Selects the best performing query or flags for bounded error correction.
        """
        evaluations: List[CandidateEvaluation] = []
        approved_tables = set(self.validator.approved_tables)

        for candidate in candidates:
            notes = []

            # 1. Safety Validation Phase (Weight: 40 points)
            val_res = self.validator.validate(candidate.sql)
            if not val_res.is_valid:
                safety_score = 0.0
                notes.append(f"Safety Violation: {val_res.error_message}")
            else:
                safety_score = 40.0
                notes.append("Passed all AST safety checks (read-only, no multi-statements, approved tables)")

            # 2. Schema Fidelity Phase (Weight: 30 points)
            schema_fidelity_score = 0.0
            if val_res.is_valid:
                tables_valid = all(t in approved_tables for t in val_res.referenced_tables)
                if tables_valid and len(val_res.referenced_tables) > 0:
                    schema_fidelity_score += 20.0
                    notes.append(f"Referenced approved tables: {val_res.referenced_tables}")
                # Check join logic
                if len(val_res.referenced_tables) > 1:
                    if "JOIN" in candidate.sql.upper() and "ON" in candidate.sql.upper():
                        schema_fidelity_score += 10.0
                        notes.append("Explicit join conditions verified")
                else:
                    schema_fidelity_score += 10.0

            # 3. Dry-Run Execution Phase (Weight: 20 points)
            exec_res = self.dev_db.execute_query(candidate.sql)
            execution_score = 0.0
            if exec_res.success:
                execution_score += 15.0
                if exec_res.row_count > 0:
                    execution_score += 5.0
                    notes.append(f"Executed cleanly returning {exec_res.row_count} rows in {exec_res.execution_time_ms:.1f}ms")
                else:
                    notes.append("Executed cleanly but returned 0 rows")
            else:
                notes.append(f"Database execution error: {exec_res.error}")

            # 4. Efficiency & Clarity Phase (Weight: 10 points)
            efficiency_score = 0.0
            if exec_res.success:
                efficiency_score += 5.0
                if "LIMIT" in candidate.sql.upper():
                    efficiency_score += 3.0
                if exec_res.execution_time_ms < 50.0:
                    efficiency_score += 2.0

            total = safety_score + schema_fidelity_score + execution_score + efficiency_score

            evaluations.append(
                CandidateEvaluation(
                    candidate_id=candidate.candidate_id,
                    strategy_name=candidate.strategy_name,
                    sql=exec_res.sql if exec_res.success else candidate.sql,
                    validation=val_res,
                    execution=exec_res,
                    safety_score=safety_score,
                    schema_fidelity_score=schema_fidelity_score,
                    execution_score=execution_score,
                    efficiency_score=efficiency_score,
                    total_score=total,
                    notes=notes,
                )
            )

        # Sort evaluations by total score descending
        evaluations.sort(key=lambda e: e.total_score, reverse=True)
        best_candidate = evaluations[0] if evaluations else None

        # Check if the highest scoring candidate is viable
        if best_candidate and best_candidate.execution.success and best_candidate.total_score >= 70.0:
            rationale = (
                f"Selected '{best_candidate.strategy_name}' (Score: {best_candidate.total_score:.1f}/100). "
                f"Delivered verified execution with {best_candidate.execution.row_count} records. "
                f"Notes: {'; '.join(best_candidate.notes)}"
            )
            return EvaluatorDecision(
                approved=True,
                winner_candidate_id=best_candidate.candidate_id,
                selected_sql=best_candidate.sql,
                execution_result=best_candidate.execution,
                candidate_evaluations=evaluations,
                rationale=rationale,
                requires_retry=False,
            )
        else:
            # If all candidates failed, format detailed diagnosis for error correction
            err_details = [
                f"{e.strategy_name}: {e.execution.error or e.validation.error_message}"
                for e in evaluations
            ]
            feedback = f"All candidate queries failed evaluation. Errors: {' | '.join(err_details)}"
            return EvaluatorDecision(
                approved=False,
                winner_candidate_id=None,
                selected_sql=None,
                execution_result=None,
                candidate_evaluations=evaluations,
                rationale="Candidate evaluation failed. Initiating bounded error correction.",
                requires_retry=True,
                retry_feedback=feedback,
            )

