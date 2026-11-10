# Initial Codebase Audit: DataPilot
**Autonomous Database Analyst — Natural Language to SQL**
**Audit Date:** November 2026  
**Auditor:** Senior AI Systems & Security Engineer (Subagent Independent Audit)

---

## 1. Executive Summary

The foundational repository is an open-source prototype of an e-commerce natural-language-to-SQL (NL2SQL) system built on **LangGraph**, **FastAPI**, **SQLAlchemy**, and vector/full-text search engines (**Qdrant**, **Elasticsearch**, **MySQL**).

While the architectural blueprint demonstrates a solid domain-driven design (separating clients, repositories, domain entities, and LangGraph workflow nodes), an in-depth technical inspection reveals critical safety vulnerabilities, structural gaps in the query lifecycle, missing validation layers, and total absence of automated testing.

This audit documents the actual codebase implementation, identified architectural flaws, critical security vulnerabilities, external infrastructure blockers, and the roadmap for transforming it into a robust, secure, production-grade AI portfolio project.

---

## 2. Codebase Inventory & Folder Structure

```
datapilot/
├── .editorconfig
├── .env.example                     # Minimal: contains only LLM_API_KEY=
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version                  # Contains '3.14' (unrealistic target)
├── LICENSE                          # MIT License
├── README.md                        # Documentation
├── main.py                          # FastAPI entrypoint & request ID middleware
├── pyproject.toml                   # Project metadata and dependencies
├── uv.lock                          # Dependency lockfile
├── app/
│   ├── agent/
│   │   ├── context.py               # DataAgentContext (DI container for repositories/clients)
│   │   ├── graph.py                 # LangGraph StateGraph orchestration
│   │   ├── llm.py                   # Chat model initialization (OpenAI-compatible)
│   │   ├── state.py                 # DataAgentState definition (TypedDict)
│   │   └── nodes/
│   │       ├── add_extra_context.py # Formats date and db_info contexts
│   │       ├── correct_sql.py       # Single-pass SQL correction on validation failure
│   │       ├── extract_keywords.py  # LLM keyword extraction from user query
│   │       ├── filter_metric.py     # LLM candidate metric filter
│   │       ├── filter_table.py      # LLM candidate table/column filter
│   │       ├── generate_sql.py      # LLM SQL query synthesis
│   │       ├── merge_retrieved_info.py # Joins retrieved columns, metrics, and values
│   │       ├── recall_column.py     # Vector search over column embeddings (Qdrant)
│   │       ├── recall_metric.py     # Vector search over metric embeddings (Qdrant)
│   │       ├── recall_value.py      # Full-text search over field values (Elasticsearch)
│   │       ├── run_sql.py           # Executes SQL query against MySQL
│   │       └── validate_sql.py      # Runs EXPLAIN <sql> against MySQL
│   ├── api/
│   │   ├── dependencies.py          # FastAPI DI for QueryService and repositories
│   │   ├── lifespan.py              # Startup/shutdown lifecycle hooks
│   │   ├── routers/
│   │   │   └── query_router.py      # POST /api/query (SSE streaming)
│   │   └── schemas/
│   │       └── query_schema.py      # Query input model (Pydantic)
│   ├── clients/                     # Client managers (MySQL, Qdrant, ES, Embeddings)
│   ├── conf/                        # OmegaConf YAML configuration loader
│   ├── core/                        # Logging and request context variables
│   ├── entities/                    # Domain models: ColumnInfo, MetricInfo, ValueInfo
│   ├── models/                      # SQLAlchemy ORM models for metadata tables
│   ├── prompt/                      # Prompt loader utility
│   ├── repositories/                # Data access layers (MySQL DW, MySQL Meta, Qdrant, ES)
│   ├── scripts/                     # build_meta_knowledge.py (offline indexing script)
│   └── services/                    # QueryService (workflow execution) & MetaKnowledgeService
├── conf/
│   ├── app_config.yaml              # Application & service infrastructure configs
│   └── meta_config.yaml             # E-commerce data warehouse schema & metric definitions
├── docker/
│   ├── docker-compose.yaml          # Orchestrates MySQL, Elasticsearch, Kibana, Qdrant, Embeddings
│   ├── elasticsearch/               # ES Dockerfile & IK analysis plugin config
│   └── mysql/
│       ├── dw.sql                   # E-commerce warehouse schema & 120+ synthetic records
│       └── meta.sql                 # Metadata dictionary schema
├── docs/
│   └── images/                      # Architecture diagrams and UI screenshots
└── frontend/                        # React + Vite + Tailwind CSS frontend interface
```

---

## 3. Existing Architecture & Workflow Analysis

### 3.1 LangGraph Workflow Flow
The existing workflow defined in `app/agent/graph.py` orchestrates the following sequence:

```
[START]
   │
   ▼
extract_keywords
   │
   ├───────────────────────┬───────────────────────┐
   ▼                       ▼                       ▼
recall_column (Qdrant)  recall_value (ES)   recall_metric (Qdrant)
   │                       │                       │
   └───────────────────────┼───────────────────────┘
                           ▼
                  merge_retrieved_info
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
        filter_table               filter_metric
             │                           │
             └─────────────┬─────────────┘
                           ▼
                   add_extra_context
                           │
                           ▼
                      generate_sql
                           │
                           ▼
                      validate_sql
                           │
              ┌────────────┴────────────┐
       [error is None]           [error exists]
              │                         │
              │                         ▼
              │                    correct_sql
              │                         │
              └────────────┬────────────┘
                           ▼
                        run_sql
                           │
                           ▼
                         [END]
```

---

## 4. Incomplete, Weak, and Unsafe Implementations

### 4.1 Critical Execution Security Issues

1. **Unrestricted SQL Execution (Arbitrary DDL/DML Injection)**:
   - In `app/repositories/mysql/dw/dw_mysql_repository.py`:
     ```python
     async def run(self, sql: str) -> list[dict]:
         result = await self.session.execute(text(sql))
         return [dict(row) for row in result.mappings().fetchall()]
     ```
   - There is **no query type restriction**. An attacker or hallucinating LLM can generate:
     `DROP TABLE dim_customer;`, `DELETE FROM fact_order;`, `TRUNCATE TABLE dim_product;`, or `ALTER TABLE ...`.
   - The query executes directly with full permissions assigned to the database user.

2. **Inadequate SQL Validation**:
   - In `DWMySQLRepository.validate(sql)`:
     ```python
     async def validate(self, sql: str):
         sql = f"explain {sql}"
         await self.session.execute(text(sql))
     ```
   - Relying solely on `EXPLAIN` does **not** protect against destructive commands. In MySQL and other dialects, certain data manipulation operations or multi-statements will parse or execute.
   - There is **zero SQL parsing** (no AST, no grammar analysis).
   - Multi-statement SQL (e.g., `SELECT 1; DROP TABLE users;`) is neither detected nor rejected.

3. **Format String SQL Injection in Repository Methods**:
   - In `DWMySQLRepository.get_column_types` and `get_column_values`:
     ```python
     sql = f"show columns from {table_name}"
     sql = f"select distinct {column_name} from {table_name} limit {limit}"
     ```
   - Interpolating unescaped, unvalidated identifiers directly into SQL statements creates SQL injection vulnerabilities if parameters originate from untrusted or LLM-generated sources.

4. **Missing Execution Timeouts & Unbounded Result Sets**:
   - `run_sql` runs without query execution timeouts. An expensive query (e.g., cartesian product join on massive tables) can tie up database connection pools indefinitely.
   - There is no mandatory `LIMIT` clause enforcement. An unrestricted `SELECT *` can exhaust server memory (OOM).

5. **Hardcoded Credentials in Configuration**:
   - `conf/app_config.yaml` contained plaintext database passwords in original template configuration:
     ```yaml
     db_meta:
       user: legacy_user
       password: legacy_password
     db_dw:
       user: legacy_user
       password: legacy_password
     ```
   - This violated the secure credential management requirement and was replaced by environment variable interpolation.

### 4.2 Architectural Gaps

1. **Unbounded Error Correction Loop**:
   - In `app/agent/graph.py`:
     ```python
     graph_builder.add_conditional_edges(
         source="validate_sql",
         path=lambda state: "run_sql" if state["error"] is None else "correct_sql",
         path_map={"run_sql": "run_sql", "correct_sql": "correct_sql"},
     )
     graph_builder.add_edge("correct_sql", "run_sql")
     ```
   - If `validate_sql` fails, `correct_sql` generates an updated query, but it is piped **directly into `run_sql` without re-validation**!
   - If `correct_sql` produces invalid or destructive SQL, it will be executed without scrutiny.
   - If `run_sql` fails at execution time, there is **zero error recovery** — the graph terminates with an unhandled exception.

2. **Missing Result Explanation Node**:
   - The workflow abruptly terminates at `run_sql`.
   - The user receives raw database dictionary rows.
   - There is no synthesis or natural language summary of the returned records, nor does the system clearly distinguish factual database records from AI reasoning.

3. **Absence of Conversational Context / Multi-Turn Memory**:
   - `QueryService.query` initializes an empty state for every request:
     `state = DataAgentState(query=query)`
   - Follow-up questions (e.g., "Filter those results to January 2025" or "Group that by province") will fail because prior query history, active tables, and generated SQL are completely discarded.

4. **Monolithic Single-Attempt SQL Generation**:
   - The system relies on a single LLM invocation for SQL synthesis. If the model misinterprets metric definitions, joins, or aggregations, the query fails.
   - There is no multi-agent hypothesis testing or blind candidate generation.

5. **Total Absence of Automated Testing**:
   - There are **zero test files** in the entire repository.
   - No unit tests for repositories, nodes, or validation rules.
   - No integration tests or evaluation benchmarks.

6. **Heavy Infrastructure Lock-in**:
   - The project assumes 5 running container services (`mysql`, `elasticsearch`, `kibana`, `qdrant`, and `text-embeddings-inference`).
   - If any of these services are absent, the application crashes on startup.
   - A disposable, lightweight synthetic SQLite/SQLAlchemy dev database mode is needed to enable deterministic testing, offline evaluation, and zero-setup demonstrations.

7. **Invalid Python Version Requirement**:
   - `pyproject.toml` declares `requires-python = ">=3.14"`. Python 3.14 is currently unreleased, causing standard package managers to reject installation.

---

## 5. Required Improvements Checklist

| Category | Improvement Item | Priority | Status |
| :--- | :--- | :--- | :--- |
| **Security** | Implement AST-based SQL Safety Validator (reject DDL/DML, multi-statements, restrict tables) | P0 (Critical) | Pending |
| **Security** | Enforce query row limits and execution timeouts | P0 (Critical) | Pending |
| **Security** | Remove hardcoded passwords; sanitize repository identifier queries | P0 (Critical) | Pending |
| **Execution** | Self-contained Synthetic Dev Database (SQLite/in-memory with seeded DW schema & data) | P0 (Critical) | Pending |
| **Workflow** | Schema-aware SQL generation with foreign keys and compact context | P1 (High) | Pending |
| **Workflow** | Bounded Error Correction with re-validation loop and configurable retry limit | P1 (High) | Pending |
| **Workflow** | Query Explanation node (distinguishing raw records from AI insights) | P1 (High) | Pending |
| **Workflow** | Multi-Turn Conversational Memory | P1 (High) | Pending |
| **Multi-Agent**| Blind Independent Subagents + Lead Evaluator architecture for robust NL2SQL synthesis | P1 (High) | Pending |
| **Testing** | Comprehensive Pytest suite covering all 15+ edge cases and security rules | P0 (Critical) | Pending |
| **Evaluation** | Automated Evaluation Framework with synthetic question benchmark & verifiable metrics | P1 (High) | Pending |
| **Docs** | Architecture, Interview Preparation, and Contributions documentation | P1 (High) | Pending |

---

## 6. Conclusion

The architectural skeleton provides a valuable foundation for multi-stage retrieval and LangGraph orchestration. However, its query execution layer was originally unguarded, lacked resilience, and could not be demonstrated or tested without extensive Docker infrastructure.

By implementing an AST-based SQL safety firewall, a bounded query correction loop, blind candidate subagent synthesis, conversational memory, an explanation layer, and a self-contained synthetic test database, DataPilot can be elevated into a robust, portfolio-ready AI engineering project.

