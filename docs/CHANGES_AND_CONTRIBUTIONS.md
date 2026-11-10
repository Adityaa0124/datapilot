# Record of Changes & Engineering Contributions
**Project:** DataPilot (Autonomous Database Analyst)  
**Author:** Senior AI Systems & Security Engineer  
**Date:** November 2026  

---

## 1. Baseline vs. Enhanced Architecture Comparison

| Architectural Dimension | Initial Open-Source Baseline | DataPilot (Enhanced Portfolio Implementation) |
| :--- | :--- | :--- |
| **SQL Safety & Validation** | Raw `EXPLAIN <sql>` directly on MySQL. Zero command filtering, no AST parsing, no table whitelist. | Dedicated AST-based `SQLSafetyValidator`. Strictly blocks DDL/DML, multi-statements, unapproved tables, and clamps row limits. |
| **Multi-Agent Synthesis** | Monolithic single-prompt SQL generation (`generate_sql.py`). | Ensemble of 3 **Blind Independent Subagents** (`Pragmatic`, `Defensive`, `Analytical`) evaluated by a centralized **Lead Evaluator**. |
| **Error Recovery** | Single-pass correction (`correct_sql.py`) routed directly to execution without re-validation or retry bounding. | **Bounded Query Correction Loop** (`bounded_correction.py`) with surgical error feedback, safety re-validation, and max retry bounding (3 attempts). |
| **Conversational Context** | Stateless: each query initialized an empty state, discarding prior queries and tables. | **Multi-Turn Conversational Memory** (`memory.py`) supporting contextual follow-ups and temporal refinements. |
| **Query Explanation** | Abruptly terminated after `run_sql`. Returned raw dictionary rows with no narrative explanation. | **Query Explanation Engine** (`explainer.py`) producing structured markdown separating verified data from AI hypotheses. |
| **Database Dependencies** | Required 5 external Docker containers (MySQL, ES, Qdrant, Kibana, TEI). Crashed immediately if unavailable. | Bundled **Synthetic Development Database** (`synthetic_dev_db.py`) running in-memory with zero external dependencies. |
| **Automated Testing** | **0 test files** in the entire repository. | **24 comprehensive Pytest test cases** covering all 15 edge cases, security constraints, and benchmarks. |
| **Evaluation Framework** | None. | Automated **Benchmark Evaluation Suite** (`benchmark_evaluator.py`) measuring accuracy across 14 scenarios. |
| **Documentation & Language**| Chinese-only README with broken external links. Redundant nested folder structure. | **100% Professional English** documentation (`README.md`, `ARCHITECTURE.md`, `INTERVIEW_PREPARATION.md`, `CHANGES_AND_CONTRIBUTIONS.md`). Clean root layout. |

---

## 2. Inventory of New Files Created

1. `app/core/sql_safety.py`:
   - Dedicated AST-based SQL safety validation engine.
   - Detects and rejects multi-statements, destructive DDL/DML, and unapproved tables.
   - Automatically clamps queries with `LIMIT 1000`.
2. `app/db/synthetic_dev_db.py`:
   - Self-contained, disposable SQLite development database engine.
   - Seeded with complete dimensional schema and 120+ realistic e-commerce warehouse records.
   - Enforces read-only execution modes and query execution timeouts.
3. `app/agent/schema_retriever.py`:
   - Dynamic schema retriever extracting only semantically relevant tables, columns, and foreign keys.
   - Pre-computes approved join paths and metric definitions.
4. `app/agent/blind_sql_subagents.py`:
   - Three independent, blind candidate subagent implementations:
     - `PragmaticSQLSubagent`: Direct ANSI joins and standard aggregations.
     - `DefensiveSQLSubagent`: Defensive NULL handling (`COALESCE`) and boundary checks.
     - `AnalyticalSQLSubagent`: Common Table Expressions (`WITH ... AS`) and ranking logic.
   - `BlindSubagentOrchestrator`: Runs candidate subagents in complete isolation.
5. `app/agent/sql_evaluator.py`:
   - Centralized Lead Evaluator and Arbiter.
   - Scores candidate queries across safety, schema fidelity, dry-run execution, and efficiency.
   - Selects the winning query or initiates bounded error recovery.
6. `app/agent/bounded_correction.py`:
   - Bounded self-healing query correction workflow.
   - Enforces strict retry limits (`MAX_RETRIES = 3`) to eliminate infinite loops.
   - Re-validates all corrected queries through the safety layer.
7. `app/agent/memory.py`:
   - Multi-turn conversational memory manager.
   - Detects follow-ups and synthesizes constraints onto prior SQL statements.
8. `app/agent/explainer.py`:
   - Generates structured analysis reports.
   - Strictly separates database facts (source truth) from AI analytical insights.
   - Redacts sensitive credentials and connection strings.
9. `app/agent/datapilot_pipeline.py`:
   - End-to-end orchestration pipeline tying together memory, retrieval, blind subagents, evaluation, correction, and explanation.
10. `app/evaluation/benchmark_evaluator.py`:
    - 14-scenario benchmark dataset covering happy paths, multi-table joins, follow-ups, and adversarial security tests.
    - Generates verifiable, reproducible performance metrics.
11. `tests/test_datapilot.py`:
    - 20 Pytest unit and integration tests covering all 15 required evaluation criteria.
12. `tests/test_benchmark.py`:
    - Integration test for the benchmark evaluation suite.
13. `tests/test_api.py`:
    - FastAPI endpoint integration tests for queries, streaming, and benchmarks.
14. `docs/INITIAL_CODEBASE_AUDIT.md`:
    - Initial comprehensive codebase audit and vulnerability assessment.
15. `docs/ARCHITECTURE.md`:
    - Deep-dive architectural documentation and Mermaid diagrams.
16. `docs/INTERVIEW_PREPARATION.md`:
    - In-depth technical interview guide covering all core concepts with code examples.
17. `docs/CHANGES_AND_CONTRIBUTIONS.md`:
    - This detailed record of changes and engineering contributions.

---

## 3. Inventory of Modified Files

1. `app/api/routers/query_router.py`:
   - Added `POST /api/datapilot/query` for direct structured query execution.
   - Added `GET /api/datapilot/benchmark` for running automated benchmark evaluations.
   - Enhanced `POST /api/query` with streaming fallback to the standalone DataPilot pipeline.
2. `app/api/lifespan.py`:
   - Wrapped external service initializations in defensive guards (`ENABLE_EXTERNAL_SERVICES`).
   - Enabled graceful fallback to standalone development database mode when Docker is absent.
3. `app/api/dependencies.py`:
   - Added defensive import guards and null checks so API endpoints can boot in standalone mode.
4. `app/core/log.py`:
   - Added standard library `logging` fallback if `loguru` is not installed.
5. `README.md`:
   - Completely rewritten in professional English.
   - Documented project overview, features, architecture, installation, API endpoints, testing, benchmarks, attribution, and contributions.
6. Cleaned root directory:
   - Removed redundant nested directory structure for clean single-root repository layout.

---

## 4. Critical Bugs & Vulnerabilities Fixed

1. **Destructive SQL Execution Vulnerability**:
   - *Original*: `DWMySQLRepository.run(sql)` executed arbitrary model-generated SQL. A hallucinated or injected `DROP TABLE`, `DELETE`, or `TRUNCATE` command would execute directly.
   - *Fix*: Integrated `SQLSafetyValidator` prior to execution. All non-`SELECT` statements are deterministically rejected.
2. **Multi-Statement Chaining Vulnerability**:
   - *Original*: Queries containing semicolons (e.g. `SELECT 1; DROP TABLE users;`) were not detected.
   - *Fix*: Implemented quote-aware statement splitting. Any query with $>1$ statements is rejected with `MULTI_STATEMENT_REJECTED`.
3. **Unbounded Full Table Scans (OOM Vulnerability)**:
   - *Original*: Queries like `SELECT * FROM fact_order` ran without row limits, threatening server memory exhaustion.
   - *Fix*: Implemented automatic row clamping to `LIMIT 1000`.
4. **Infinite Error Correction Loop**:
   - *Original*: In `app/agent/graph.py`, `correct_sql` had no retry counter and fed directly into `run_sql` without re-validation.
   - *Fix*: Implemented `BoundedQueryCorrector` enforcing `MAX_RETRIES = 3` and passing all corrections through `SQLSafetyValidator`.
5. **Format String SQL Injection in Repository Methods**:
   - *Original*: `DWMySQLRepository` used `f"show columns from {table_name}"` and `f"select distinct {column_name}..."`.
   - *Fix*: Added table and column identifier validation against the approved schema whitelist.
6. **Hardcoded Infrastructure Blocker**:
   - *Original*: Application crashed on startup if MySQL, Qdrant, Elasticsearch, and TEI were not running.
   - *Fix*: Created `SyntheticDevelopmentDB` and guarded client initializations in `lifespan.py` and `dependencies.py`.
7. **Follow-Up Cue Overlap Bug**:
   - *Original*: Single isolated grouping prepositions were triggering follow-up mode on standalone queries like `"calculate sales by product name"`.
   - *Fix*: Refined follow-up cue detection to explicit conversational modifiers (`"filter by"`, `"narrow by"`, `"further group by"`, `"filter to"`, `"order by"`), resolving query intent correctly.

8. **Production Deployment Packaging**:
   - *Original*: Missing root `Dockerfile`, `.dockerignore`, root `docker-compose.yml`, `requirements.txt`, and container health probes.
   - *Fix*: Created multi-stage `Dockerfile` (Node 22 frontend builder + Python 3.11 runtime), root `docker-compose.yml` with profiles, `requirements.txt`, `.dockerignore`, and automated healthcheck probes (`/health`, `/api/health`).

---

## 5. Verified Test Suite Execution

All 25 automated tests pass cleanly with 100% pass rate:

```bash
$ pytest tests/ -v
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.1.1, pluggy-1.6.0
collected 25 items

tests/test_api.py::test_api_datapilot_query_handler PASSED               [  4%]
tests/test_api.py::test_api_datapilot_benchmark_handler PASSED           [  8%]
tests/test_api.py::test_api_health_check_endpoint PASSED                 [ 12%]
tests/test_api.py::test_api_fastapi_route_registration PASSED            [ 16%]
tests/test_benchmark.py::test_benchmark_suite_execution PASSED           [ 20%]
tests/test_datapilot.py::test_simple_select_queries PASSED               [ 24%]
tests/test_datapilot.py::test_filtering_queries PASSED                   [ 28%]
tests/test_datapilot.py::test_sorting_queries PASSED                     [ 32%]
tests/test_datapilot.py::test_aggregation_queries PASSED                 [ 36%]
tests/test_datapilot.py::test_join_operations PASSED                     [ 40%]
tests/test_datapilot.py::test_invalid_table_names PASSED                 [ 44%]
tests/test_datapilot.py::test_invalid_column_names PASSED                [ 48%]
tests/test_datapilot.py::test_destructive_sql_rejection[DROP] PASSED     [ 52%]
tests/test_datapilot.py::test_destructive_sql_rejection[DELETE] PASSED   [ 56%]
tests/test_datapilot.py::test_destructive_sql_rejection[TRUNCATE] PASSED [ 60%]
tests/test_datapilot.py::test_destructive_sql_rejection[ALTER] PASSED    [ 64%]
tests/test_datapilot.py::test_destructive_sql_rejection[INSERT] PASSED   [ 68%]
tests/test_datapilot.py::test_destructive_sql_rejection[UPDATE] PASSED   [ 72%]
tests/test_datapilot.py::test_multiple_statement_rejection PASSED        [ 76%]
tests/test_datapilot.py::test_query_timeout PASSED                       [ 80%]
tests/test_datapilot.py::test_empty_results PASSED                       [ 84%]
tests/test_datapilot.py::test_database_connection_failures PASSED        [ 88%]
tests/test_datapilot.py::test_follow_up_questions PASSED                 [ 92%]
tests/test_datapilot.py::test_retry_limits PASSED                        [ 96%]
tests/test_datapilot.py::test_disposable_development_database PASSED     [100%]

============================= 25 passed in 1.62s ==============================
```

---

## 6. Known Limitations

1. **Dialect Compatibility**: The synthetic development database uses standard ANSI SQL on SQLite. While all queries adhere to ANSI standard syntax, advanced MySQL-specific functions (e.g. `DATE_SUB`, `JSON_EXTRACT`) require the Docker MySQL environment.
2. **Streaming in Frontend UI**: The React frontend is pre-configured to stream SSE messages from `/api/query`. The new `/api/datapilot/query` endpoint returns structured JSON; full frontend visualization of the multi-agent candidate comparison cards can be added in a future frontend iteration.
3. **Session Persistence**: `ConversationalMemory` operates in-memory per pipeline instance. In a multi-worker production cluster, session turns should be backed by a persistent store like Redis or PostgreSQL.

