# AI Engineering Portfolio: Executive Summary & Project Showcase

**Candidate Specialization:** Senior AI Engineer / Autonomous Agent Systems  
**Primary Frameworks:** LangGraph, LangChain, FastAPI, Pydantic v2, Pytest, Docker, SQLite, MySQL, Qdrant  
**LLM Providers:** SiliconFlow (GLM-5.1), Google Gemini (Gemini 2.5/3.8 Flash), OpenAI (GPT-4o)  

---

## Executive Overview

This portfolio showcases two production-grade, state-of-the-art autonomous agent systems built using **cyclic state machines and multi-agent consensus** rather than naive prompt chains or unbounded ReAct loops.

Both systems incorporate:
1. **Deterministic Guardrails & AST Sandboxing:** Real-world security controls preventing prompt injection, destructive DDL/DML execution, path traversal, and credential leakage.
2. **Multi-Agent Consensus (Blind Subagents + Evaluator):** Mitigation of LLM *anchoring bias* through parallel, information-isolated candidate synthesis evaluated by an objective multi-criteria judge.
3. **Self-Correction & Bounded Loops:** Strict retry budgets (`MAX_RETRIES = 3`) and error diagnostics to eliminate runaway token costs and infinite loops.
4. **100% Verified Testing:** 63 combined unit, integration, and security tests passing with zero failures.
5. **Production Deployment Packaging:** Complete multi-stage Dockerfiles, Docker Compose files, container healthchecks, and single-port React SPA serving.

---

## Project Matrix & Technical Comparison

| Dimension | Project 1: DevPilot | Project 2: DataPilot |
| :--- | :--- | :--- |
| **Domain** | Autonomous Software Engineering (NL to Python) | Autonomous Database Analyst (NL to SQL) |
| **Repository Path** | `multi-agent-langgraph-main/` | `shopkeeper-agent-main/` |
| **Orchestration** | LangGraph Cyclic State Machine (5 Nodes) | LangGraph Multi-Agent Ensemble + Lead Evaluator |
| **Consensus Pattern** | Blind Independent Subagents + Evaluator | 3 Blind Subagents (`Pragmatic`, `Defensive`, `Analytical`) + Arbiter |
| **Security Layer** | Environment Sanitization, Command Whitelist, Timeout | AST SQL Parser, Forbidden Command Blocker, Table Whitelist, Row Clamping |
| **Testing Engine** | Automated `pytest` Generation & Sandbox Execution | Dry-Run Execution against Synthetic In-Memory Warehouse |
| **Self-Correction** | Plan → Dev → Security → Pytest → Review (Max 3) | Bounded Query Correction Loop with Diagnostic Feedback (Max 3) |
| **State Validation** | Pydantic v2 `AppState` with Stage Tracking | Pydantic v2 Models + Typed Multi-Turn Context |
| **Primary LLMs** | Google Gemini 3.8 Flash, OpenAI GPT-4o-mini | SiliconFlow GLM-5.1, OpenAI GPT-4o, Google Gemini |
| **Verified Tests** | **38 / 38 Passed (100%)** | **25 / 25 Passed (100%)** |
| **Benchmark Accuracy** | 5/5 Tasks Completed | **14 / 14 Scenarios Passed (100.0%, 1.21ms latency)** |
| **Web UI** | Clean Developer Dashboard (SSE Streaming) | React 19 + Tailwind CSS + Interactive LangGraph Flow Graph |
| **Deployment** | Docker Compose (Postgres 16 + FastAPI) | Multi-Stage Dockerfile (Node 22 + Python 3.11) / Single-Port SPA |

---

## Resume Bullet Points (Tailored for Senior AI Engineer Roles)

### DataPilot — Autonomous Database Analyst (Natural Language to SQL)
* Designed an enterprise-grade NL2SQL agent with **schema-aware retrieval**, dynamically selecting only relevant tables, columns, foreign keys, and metrics to eliminate prompt token bloat and hallucinated column joins.
* Built an ensemble of **Blind Independent Subagents** (`Pragmatic`, `Defensive`, `Analytical`) producing candidate SQL queries in information isolation, evaluated by a centralized **Lead Evaluator** performing dry-run scoring (0–100) on disposable dev databases.
* Engineered an **AST SQL Safety Firewall** that parses queries into abstract syntax tree tokens prior to execution, deterministically rejecting destructive operations (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`), multi-statement injection chains (`;`), and unapproved tables while clamping row limits.
* Implemented a **Bounded Query Correction Loop** (`MAX_RETRIES = 3`) that captures database errors, provides surgical diagnostic feedback, and re-validates corrected queries through the safety firewall.
* Developed **Multi-Turn Conversational Memory** supporting contextual drill-downs, filtering refinements, and historical schema reference resolution without cross-contaminating prior sessions.
* Containerized the system into a **production multi-stage Docker build** serving both the compiled React 19 SPA and FastAPI backend on a single port with integrated Docker healthcheck probes (**25/25 verified tests passing**).

### DevPilot — Autonomous Multi-Agent Software Engineering System
* Architected a self-correcting multi-agent engineering pipeline using **LangGraph** and **FastAPI**, orchestrating 5 specialized agents (Planner, Developer, Security Reviewer, Test Generator, and Reviewer) with Server-Sent Events (SSE) streaming.
* Mitigated LLM anchoring bias by implementing a **Blind Independent Subagents + Evaluator** pattern, generating 3 orthogonal candidate implementations in complete isolation before scoring via a multi-criteria judge.
* Hardened execution security against arbitrary code execution risks by implementing credential-stripping subprocess environments, command whitelisting, canonical filesystem path confinement (`workspace/`), and hard timeouts.
* Built an automated test-generation loop that writes dynamic `pytest` suites, executes tests in ephemeral sandboxes, captures runtime failures, and feeds structured error logs back to the developer agent within bounded retry limits (`MAX_ROUNDS = 3`).
* Developed a centralized multi-provider LLM factory supporting **Google Gemini 3.8 Flash** and **OpenAI**, with **38/38 automated tests passing**.

---

## Technical Interview Talking Points

### 1. "Why cyclic graphs (LangGraph) instead of linear chains or ReAct?"
> "Software engineering and database analysis are non-deterministic, iterative disciplines. Linear chains fail because they cannot self-correct when SQL syntax errors occur, tables are missing, or tests fail. Conversely, unstructured ReAct loops frequently fall into infinite loops or hallucinate tool parameters. LangGraph provides deterministic state transitions with cyclic self-correction while enforcing strict boundary conditions: max retries, execution budgets, and context window pruning."

### 2. "How did you solve anchoring bias in multi-agent collaboration?"
> "When agents communicate sequentially, downstream agents naturally anchor on the first proposal, refining a potentially flawed paradigm. With our Blind Subagents architecture, three specialized agents (Pragmatic, Defensive, Analytical) develop solutions with zero cross-visibility. An Evaluator then evaluates the anonymized candidates using weighted rubrics (Correctness, Safety, Efficiency, Schema Fit) against a disposable development database to pick or synthesize the optimal result."

### 3. "How do you guarantee database execution safety against destructive LLM queries?"
> "We enforce a defense-in-depth model that never trusts model self-attestation:
> 1. Dedicated AST SQL Safety Validator parsing statement tokens before database dispatch.
> 2. Hard rejection of all non-`SELECT` statements (`DROP`, `DELETE`, `TRUNCATE`, `ALTER`, `INSERT`, `UPDATE`).
> 3. Multi-statement injection blocking (rejecting any chained `;` commands).
> 4. Table whitelisting ensuring only approved dimensional and fact tables are queryable.
> 5. Mandatory row limit clamping (`LIMIT 1000`) and execution timeout handlers to prevent denial-of-service."

---

## Quickstart & Demo Commands

### Run DataPilot:
```powershell
# 1. Run all 25 verified tests
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests/ -v

# 2. Run the 14-scenario benchmark suite
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -c "from app.evaluation.benchmark_evaluator import BenchmarkEvaluator; print(BenchmarkEvaluator().run_benchmark())"

# 3. Start Unified Server
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Run DevPilot:
```powershell
# 1. Run all 38 verified tests
cd ..\multi-agent-langgraph-main
.\.venv\Scripts\python.exe run_tests.py

# 2. Start Web Dashboard
.\.venv\Scripts\python.exe -m uvicorn app.server:app --port 8001 --reload
```

