"""
DataPilot End-to-End Orchestration Pipeline.
Integrates:
1. Conversational Memory (Multi-turn follow-up resolution)
2. Schema-Aware Retrieval (Compact schema context & foreign keys)
3. Blind Independent Subagents (Candidate generation in isolation)
4. SQL Evaluator & Arbiter (Safety validation, dry-run scoring, winner selection)
5. Bounded Error Recovery (Surgical correction with strict retry limit)
6. Safe Database Execution (Isolated development database)
7. Query Explanation (Distinguishing verified records from AI insights)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.agent.blind_sql_subagents import BlindSubagentOrchestrator, CandidateSQL
from app.agent.bounded_correction import BoundedQueryCorrector, CorrectionWorkflowResult
from app.agent.explainer import QueryExplainer, StructuredExplanation
from app.agent.memory import ConversationalMemory, ConversationTurn
from app.agent.schema_retriever import SchemaContext, SchemaRetriever
from app.agent.sql_evaluator import EvaluatorDecision, SQLEvaluatorAgent
from app.core.sql_safety import SQLSafetyValidator, SQLValidationResult
from app.db.synthetic_dev_db import QueryExecutionResult, SyntheticDevelopmentDB


@dataclass
class DataPilotResponse:
    user_query: str
    is_follow_up: bool
    final_sql: str
    validation_result: SQLValidationResult
    execution_result: QueryExecutionResult
    evaluator_decision: Optional[EvaluatorDecision]
    correction_result: Optional[CorrectionWorkflowResult]
    explanation: StructuredExplanation
    markdown_report: str
    total_latency_ms: float


class DataPilotPipeline:
    """
    Autonomous Database Analyst Pipeline with Blind Independent Subagents and Lead Evaluator.
    """

    def __init__(
        self,
        dev_db: Optional[SyntheticDevelopmentDB] = None,
        validator: Optional[SQLSafetyValidator] = None,
        max_retries: int = 3,
        max_history: int = 5,
    ):
        self.dev_db = dev_db or SyntheticDevelopmentDB()
        self.validator = validator or SQLSafetyValidator()
        self.memory = ConversationalMemory(max_history=max_history)
        self.schema_retriever = SchemaRetriever()
        self.subagent_orchestrator = BlindSubagentOrchestrator()
        self.evaluator = SQLEvaluatorAgent(dev_db=self.dev_db, validator=self.validator)
        self.corrector = BoundedQueryCorrector(dev_db=self.dev_db, validator=self.validator, max_retries=max_retries)
        self.explainer = QueryExplainer()

    def process_query(self, user_query: str) -> DataPilotResponse:
        """
        Processes a natural language database query through the complete pipeline.
        """
        start_time = time.perf_counter()

        # Step 1: Conversational Memory check
        is_follow_up = self.memory.is_follow_up(user_query)
        prior_turn = self.memory.get_last_turn()

        # Step 2: Schema Context Retrieval
        conv_context = [prior_turn.user_query] if prior_turn else []
        schema_context = self.schema_retriever.retrieve_schema_context(
            query=user_query,
            conversation_context=conv_context,
        )

        # Step 3: Handle follow-up or generate blind candidate queries
        correction_result = None
        evaluator_decision = None

        if is_follow_up and prior_turn:
            refined_sql = self.memory.apply_follow_up_to_sql(user_query, prior_turn.generated_sql)
            # Evaluate refined SQL directly
            candidate = CandidateSQL(
                candidate_id="follow_up_adaptation",
                strategy_name="Conversational Follow-Up Adapter",
                perspective_description="Refines prior SQL with newly stated constraints.",
                sql=refined_sql,
                reasoning="Applied follow-up filter to previous conversation turn.",
            )
            candidates = [candidate]
        else:
            candidates = self.subagent_orchestrator.generate_candidates(
                query=user_query,
                schema_context=schema_context,
                conversation_context=conv_context,
            )

        # Step 4: Lead Evaluator assesses all candidates
        evaluator_decision = self.evaluator.evaluate_candidates(
            query=user_query,
            candidates=candidates,
            schema_context=schema_context,
        )

        # Step 5: If approved, proceed; if failed, trigger bounded correction
        if evaluator_decision.approved and evaluator_decision.execution_result and evaluator_decision.execution_result.success:
            final_sql = evaluator_decision.selected_sql
            execution_res = evaluator_decision.execution_result
            validation_res = self.validator.validate(final_sql)
        else:
            # Pick the top candidate to attempt bounded correction
            fallback_candidate = evaluator_decision.candidate_evaluations[0] if evaluator_decision.candidate_evaluations else candidates[0]
            initial_error = fallback_candidate.execution.error or fallback_candidate.validation.error_message or "Execution failure"

            correction_result = self.corrector.execute_bounded_correction(
                failing_sql=fallback_candidate.sql,
                initial_error=initial_error,
                query=user_query,
                schema_context=schema_context,
            )

            if correction_result.success:
                final_sql = correction_result.final_sql
                execution_res = correction_result.execution_result
                validation_res = self.validator.validate(final_sql)
            else:
                final_sql = correction_result.final_sql or fallback_candidate.sql
                execution_res = QueryExecutionResult(
                    success=False,
                    sql=final_sql,
                    error=correction_result.error,
                )
                validation_res = self.validator.validate(final_sql)

        # Step 6: Generate structured explanation
        explanation = self.explainer.explain(
            user_query=user_query,
            sql=final_sql,
            validation=validation_res,
            execution=execution_res,
        )
        markdown_report = self.explainer.format_markdown(explanation)

        # Step 7: Record conversation turn
        if execution_res.success:
            self.memory.add_turn(
                user_query=user_query,
                generated_sql=final_sql,
                referenced_tables=validation_res.referenced_tables,
                row_count=execution_res.row_count,
                summary=explanation.natural_language_summary,
            )

        total_latency = (time.perf_counter() - start_time) * 1000

        return DataPilotResponse(
            user_query=user_query,
            is_follow_up=is_follow_up,
            final_sql=final_sql,
            validation_result=validation_res,
            execution_result=execution_res,
            evaluator_decision=evaluator_decision,
            correction_result=correction_result,
            explanation=explanation,
            markdown_report=markdown_report,
            total_latency_ms=total_latency,
        )

