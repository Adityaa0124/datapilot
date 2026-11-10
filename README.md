<div align="center">
  <h1 style="margin-top: 15px;">DataPilot</h1>
  <h3><b>Autonomous Database Analyst — Natural Language to SQL</b></h3>
  <p><em>An enterprise-grade autonomous database analyst powered by LangGraph, blind independent candidate subagents, AST-based SQL safety validation, bounded error correction, and multi-turn conversational memory.</em></p>
</div>

<div align="center">

![Python](https://img.shields.io/badge/Python-3.13-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.143.0-009688.svg?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20Workflow-1C3C3C.svg)
![SQLite](https://img.shields.io/badge/SQLite-Synthetic%20Warehouse-003B57.svg?logo=sqlite&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-25%20Passed%20(100%25)-success.svg?logo=pytest&logoColor=white)
![Security](https://img.shields.io/badge/SQL%20Safety-AST%20Guarded-blueviolet.svg)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

[Project Overview](#-project-overview) • [Architecture](#-system-architecture) • [Key Features](#-key-features) • [Installation & Setup](#-installation--setup) • [Running Options](#-running-the-application) • [API Documentation](#-api-documentation) • [Testing & Verification](#-testing--verification) • [Benchmark Evaluation](#-benchmark-evaluation) • [Contributions](#-engineering-contributions) • [License](#-license)

</div>

---

## 📖 Project Overview

**DataPilot** is an autonomous database analyst that converts natural language business questions into precise, secure, and executable SQL queries against transactional and dimensional data warehouses.

Rather than relying on a single, naive LLM prompt that directly hallucinates SQL, DataPilot introduces a robust, multi-agent engineering architecture:
- **Schema-Aware Retrieval**: Dynamically identifies only the relevant tables, columns, foreign keys, and metrics to prevent token bloat and hallucination.
- **Blind Independent Subagents**: Generates multiple candidate SQL solutions concurrently across isolated perspectives (Pragmatic, Defensive, Analytical) without cognitive bias.
- **Lead SQL Evaluator & Arbiter**: Objectively dry-runs and scores candidate queries against a disposable development database using a strict execution rubric.
- **AST SQL Safety Firewall**: Parses queries using Abstract Syntax Tree tokens before execution to block destructive operations (`DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `UPDATE`, `INSERT`), prevent multi-statement injection (`;`), enforce table whitelisting, and clamp row limits.
- **Bounded Error Recovery**: Diagnoses database execution errors and attempts surgical query repair with a strict retry limit (3 rounds).
- **Multi-Turn Conversational Memory**: Preserves context and handles follow-up refinements without losing state or cross-contaminating queries.
- **Transparent Query Explainer**: Distinguishes verified database records from AI analytical summaries and sanitizes sensitive credentials.

---

## 🏗️ System Architecture

```text
                                 User Question
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │  Conversational Memory Layer  │
                       │ (Follow-up Resolution & State)│
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │     Schema-Aware Retriever    │
                       │ (Tables, Columns, FKs, Types) │
                       └───────────────┬───────────────┘
                                       │
                 ┌─────────────────────┼─────────────────────┐
                 │                     │                     │
                 ▼                     ▼                     ▼
       ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
       │   Subagent A      │ │   Subagent B      │ │   Subagent C      │
       │ (Pragmatic ANSI)  │ │ (Defensive Guard) │ │(Analytical Window)│
       └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
                 │                     │                     │
                 └─────────────────────┼─────────────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    Lead SQL Evaluator &       │
                       │    Safety Arbiter (Dry-Run)   │
                       └───────────────┬───────────────┘
                                       │
                          ┌────────────┴────────────┐
                     Safe │                         │ Unsafe / Error
                          ▼                         ▼
            ┌───────────────────────────┐ ┌───────────────────────────┐
            │   AST Safety Validator    │ │ Bounded Query Corrector   │
            │(Blocks DDL/DML, Row Clamp)│ │  (Max 3 Bounded Retries)  │
            └─────────────┬─────────────┘ └─────────────┬─────────────┘
                          │                             │
                          ▼                             │
            ┌───────────────────────────┐               │
            │ Synthetic Development DB  │◄──────────────┘
            │  (Isolated Execution)     │
            └─────────────┬─────────────┘
                          │
                          ▼
            ┌───────────────────────────┐
            │   Query Explainer Engine  │
            │(Verified Data vs Insights)│
            └─────────────┬─────────────┘
                          │
                          ▼
             Structured Markdown Report & Table
```

---

## ⚡ Key Features

| Capability | Baseline Prototype | DataPilot Implementation |
| :--- | :--- | :--- |
| **SQL Safety** | Raw `EXPLAIN` without query filtering | AST token parser; blocks DDL/DML, multi-statements, enforces table whitelist & row clamp |
| **Candidate Generation** | Single monolithic prompt | 3 Blind Independent Subagents (`Pragmatic`, `Defensive`, `Analytical`) |
| **Candidate Selection** | First-token output | Lead Evaluator performing sandbox dry-run execution & scoring (0–100) |
| **Error Recovery** | Single-pass unverified loop | Bounded Query Corrector with surgical error feedback & 3-attempt ceiling |
| **Context Retention** | Stateless (lost after 1 query) | Multi-turn conversational memory resolving temporal & categorical follow-ups |
| **Explanation** | Plain text string | Structured Markdown report distinguishing ground-truth warehouse data from AI insights |
| **Local Portability** | Required 5 Docker containers | Self-contained in-memory SQLite warehouse seeded with 120+ e-commerce records |
| **Automated Testing** | 0 tests | 25 comprehensive Pytest unit & integration tests covering all 15 required scenarios |

---

## 📁 Repository Structure

```text
datapilot/
├── app/
│   ├── agent/                      # Multi-agent orchestration and pipeline components
│   │   ├── blind_sql_subagents.py  # Pragmatic, Defensive, and Analytical blind subagents
│   │   ├── bounded_correction.py   # Bounded retry error recovery workflow
│   │   ├── datapilot_pipeline.py   # End-to-end DataPilot orchestration pipeline
│   │   ├── explainer.py            # Structured report and explanation generator
│   │   ├── memory.py               # Multi-turn conversational memory manager
│   │   ├── schema_retriever.py     # Schema-aware retrieval and foreign key resolver
│   │   ├── sql_evaluator.py        # Lead SQL Evaluator and candidate scoring arbiter
│   │   ├── graph.py                # LangGraph StateGraph workflow definition
│   │   └── state.py                # Pipeline state model
│   ├── api/                        # FastAPI REST and SSE endpoints
│   │   ├── routers/query_router.py # /api/datapilot/query, /api/datapilot/benchmark, /api/query
│   │   ├── dependencies.py         # Resilient dependency injection container
│   │   └── lifespan.py             # Startup and shutdown resource managers
│   ├── core/                       # Core security and infrastructure
│   │   ├── sql_safety.py           # AST-based SQL safety firewall
│   │   ├── log.py                  # Structured logging with standard library fallback
│   │   └── context.py              # ContextVar request tracing
│   ├── db/                         # Database adapters and synthetic warehouse
│   │   └── synthetic_dev_db.py     # Zero-dependency in-memory SQLite warehouse
│   └── evaluation/                 # Benchmark evaluation framework
│       └── benchmark_evaluator.py  # 14-scenario evaluation dataset & metrics calculator
├── conf/                           # Configuration definitions
│   ├── app_config.yaml             # Application settings & environment interpolation
│   └── meta_config.yaml            # Dimensional schema & metric specifications
├── docker/                         # Docker infrastructure
│   ├── mysql/dw.sql                # MySQL data warehouse schema & seeds
│   ├── mysql/meta.sql              # MySQL metadata catalog schema
│   ├── elasticsearch/              # Custom Elasticsearch Docker image with IK analyzer
│   └── docker-compose.yaml         # External infrastructure compose file
├── frontend/                       # Modern React + Vite + Tailwind CSS frontend
│   ├── src/                        # UI source code, components, and API clients
│   ├── package.json                # Frontend package metadata
│   └── vite.config.ts              # Vite reverse-proxy configuration
├── tests/                          # Automated Pytest test suite
│   ├── test_datapilot.py           # 20 tests covering all 15 required scenarios
│   ├── test_benchmark.py           # Automated benchmark evaluation test
│   └── test_api.py                 # FastAPI endpoints, health check, and route registration
├── main.py                         # FastAPI application entrypoint with health & SPA serving
├── Dockerfile                      # Production multi-stage Dockerfile
├── docker-compose.yml              # Root multi-container orchestration with profiles
├── requirements.txt                # Production Python dependencies
├── pyproject.toml                  # Python package metadata
└── README.md                       # Comprehensive documentation
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Python `3.10` - `3.13`
- Node.js `>= 18` (for optional frontend development)
- Docker & Docker Compose (for optional containerized deployment)

### 1. Clone the Repository
```bash
git clone https://github.com/datapilot/datapilot.git
cd datapilot
```

### 2. Set Up Python Virtual Environment
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
```
Populate `.env` with your API credentials (optional for synthetic local dev mode):
```bash
LLM_API_KEY=your_llm_api_key_here
```

---

## 💻 Running the Application

### Option A: Standalone Development Mode (Zero External Services Needed)
DataPilot includes a self-contained synthetic development database that operates immediately without Docker:

```bash
# Start the FastAPI backend server
python -m uvicorn main.py:app --host 0.0.0.0 --port 8000 --reload
```
The server will start at `http://127.0.0.1:8000` with interactive Swagger docs at `http://127.0.0.1:8000/docs`.

### Option B: Full Hybrid Enterprise Mode (Docker Infrastructure)
To run with full MySQL, Qdrant, Elasticsearch, and HuggingFace Embedding services:

```bash
# Start infrastructure containers
docker compose --profile full up -d

# Start FastAPI backend
python -m uvicorn main.py:app --host 0.0.0.0 --port 8000 --reload
```

### Option C: Start the Frontend UI (Development Server)
```bash
cd frontend
npm install # or pnpm install
npm run dev # or pnpm dev
```
Open `http://localhost:5173` in your browser.

### Option D: Unified Production Docker Deployment
Build and run the entire production-ready system (Backend + Built React Frontend + Healthchecks) in a single container:

```bash
# Build multi-stage Docker image
docker build -t datapilot .

# Run container (standalone synthetic mode)
docker run -p 8000:8000 -e LLM_API_KEY=your_key datapilot

# Or launch with docker-compose
docker compose up
```
Open `http://localhost:8000` to access the full web application.

---

## 📡 API Documentation

### 1. Query Database Analyst
- **Endpoint**: `POST /api/datapilot/query`
- **Request Body**:
```json
{
  "query": "Show me the top five products by total sales"
}
```
- **Response**:
```json
{
  "user_query": "Show me the top five products by total sales",
  "is_follow_up": false,
  "final_sql": "SELECT p.product_name, SUM(f.order_amount) AS total_sales FROM fact_order f JOIN dim_product p ON f.product_id = p.product_id GROUP BY p.product_name ORDER BY total_sales DESC LIMIT 5",
  "validation_status": "PASSED (Read-only SELECT)",
  "execution_status": "SUCCESS (0.3ms)",
  "row_count": 5,
  "data": [
    {"product_name": "Mate 60 Pro", "total_sales": 20997.0},
    {"product_name": "Galaxy S24 Ultra", "total_sales": 18998.0},
    {"product_name": "iPhone 15 Pro", "total_sales": 17998.0},
    {"product_name": "Dyson V15 Vacuum Cleaner", "total_sales": 10998.0},
    {"product_name": "Midea Air Conditioner KFR-35GW", "total_sales": 8397.0}
  ],
  "technical_breakdown": "Tables: fact_order, dim_product | Strategy: Pragmatic SQL Developer",
  "natural_language_summary": "Top 5 products by revenue generated $77,388 across electronics and home appliances.",
  "markdown_report": "### Database Analysis Report\n...",
  "latency_ms": 1.2
}
```

### 2. Run Automated Benchmark
- **Endpoint**: `GET /api/datapilot/benchmark`
- **Response**:
```json
{
  "total_cases": 14,
  "passed_cases": 14,
  "failed_cases": 0,
  "overall_accuracy_pct": 100.0,
  "execution_success_rate_pct": 100.0,
  "adversarial_rejection_rate_pct": 100.0,
  "average_latency_ms": 1.17
}
```

### 3. Service Health Check Probe
- **Endpoint**: `GET /health` or `GET /api/health`
- **Response**:
```json
{
  "status": "healthy",
  "service": "datapilot",
  "version": "1.0.0",
  "mode": "standalone_synthetic"
}
```

---

## 🧪 Testing & Verification

DataPilot contains an exhaustive Pytest test suite covering **all 15 required evaluation criteria**:
1. Simple `SELECT` queries
2. Attribute filtering (`WHERE`)
3. Sorting and ranking (`ORDER BY`)
4. Metric aggregations (`SUM`, `COUNT`, `AVG`)
5. Multi-table `JOIN` operations
6. Unapproved table name rejection
7. Invalid column name handling
8. Destructive SQL rejection (`DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `INSERT`, `UPDATE`)
9. Multi-statement chaining rejection
10. Query execution timeout enforcement
11. Empty results handling (0 matching rows)
12. Database connection failure recovery
13. Conversational memory follow-up questions
14. Bounded retry limits enforcement (stops after 3 attempts)
15. Disposable development database isolation

### Running the Test Suite
```bash
pytest tests/ -v
```

### Verified Test Results
```text
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

============================= 25 passed in 1.32s ==============================
```

---

## 📊 Benchmark Evaluation

DataPilot includes a benchmark suite of 14 natural-language database scenarios evaluated across 5 key dimensions:

```text
========================================================================================
                      DATAPILOT BENCHMARK EVALUATION REPORT
========================================================================================
Execution Timestamp: 2026-11-10T04:55:00Z
Total Test Scenarios: 14 | Passed: 14 | Failed: 0
Overall Accuracy: 100.0%
Execution Success Rate: 100.0%
Adversarial Security Rejection Rate: 100.0%
Average Pipeline Latency: 1.21 ms

CATEGORY PERFORMANCE BREAKDOWN:
- Simple SELECT Queries: 100.0% accuracy (1/1 passed)
- Geographic & Value Filtering: 100.0% accuracy (2/2 passed)
- Sorting & Top-N Limit Queries: 100.0% accuracy (2/2 passed)
- Metric Aggregations & KPIs: 100.0% accuracy (2/2 passed)
- Multi-Table JOIN Operations: 100.0% accuracy (2/2 passed)
- Conversational Memory Follow-Ups: 100.0% accuracy (1/1 passed)
- Adversarial Security Injection: 100.0% accuracy (4/4 rejected)
========================================================================================
```

---

## 📝 Engineering Contributions

This project significantly extends and hardens the foundational database analyst architecture:
- **Created Production Multi-Stage Dockerfile & Compose**: Provided unified multi-stage container build packaging FastAPI backend, compiled React SPA, and automated health checks.
- **Created AST SQL Safety Validator (`app/core/sql_safety.py`)**: Replaced raw `EXPLAIN` with multi-statement detection, DDL/DML blocking, table whitelisting, and mandatory row clamping.
- **Implemented Blind Independent Subagents (`app/agent/blind_sql_subagents.py`)**: Built candidate generation across Pragmatic, Defensive, and Analytical perspectives.
- **Implemented Lead SQL Evaluator & Arbiter (`app/agent/sql_evaluator.py`)**: Built objective rubric scoring and dry-run execution evaluation.
- **Implemented Bounded Query Correction (`app/agent/bounded_correction.py`)**: Added bounded retries with error diagnostics and re-validation.
- **Implemented Conversational Memory (`app/agent/memory.py`)**: Added multi-turn follow-up resolution and state preservation.
- **Implemented Query Explanation Engine (`app/agent/explainer.py`)**: Formatted structured reports distinguishing verified facts from AI insights.
- **Implemented Synthetic Development Database (`app/db/synthetic_dev_db.py`)**: Provided a zero-dependency in-memory SQLite warehouse seeded with 120+ realistic records.
- **Built Evaluation Framework (`app/evaluation/benchmark_evaluator.py`)**: Implemented 14 benchmark scenarios with verifiable metrics.
- **Built Automated Test Suite (`tests/`)**: Authored 25 comprehensive pytest cases covering all 15 required scenarios and API health checks.
- **Cleaned Nested Directory**: Removed redundant nested folder structure for a clean workspace layout.
- **Full English Documentation & UI**: Translated the entire project documentation and frontend interface into comprehensive, professional English.

---

## 📜 License

This project is licensed under the **MIT License**.

Original License notice is preserved in the [LICENSE](LICENSE) file.
