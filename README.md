# TRACEIQ — Collaborative AI Incident Investigation Platform

> **Deterministic code establishes evidence. AI reasons over normalized evidence. Humans approve recovery.**

TRACEIQ is an incident investigation and recovery platform designed for modern engineering teams. Combining deterministic telemetry analysis, LangGraph stateful orchestration, competing hypothesis generation, and human-in-the-loop recovery gates, TRACEIQ accelerates Mean Time to Resolution (MTTR) while preventing AI hallucinations.

---

## Table of Contents
- [Overview](#overview)
- [Core Architecture & Boundaries](#core-architecture--boundaries)
- [Investigation Workflow](#investigation-workflow)
- [Incident Scenarios](#incident-scenarios)
- [Repository Structure](#repository-structure)
- [Getting Started & Execution](#getting-started--execution)
  - [Prerequisites](#prerequisites)
  - [1. Telemetry Generation & Validation](#1-telemetry-generation--validation)
  - [2. Database Initialization & Seeding](#2-database-initialization--seeding)
  - [3. Running the Backend API](#3-running-the-backend-api)
  - [4. Running the Frontend Workspace](#4-running-the-frontend-workspace)
- [Running Tests & Verifications](#running-tests--verifications)
  - [Backend Tests](#backend-tests)
  - [Frontend Tests & Production Build](#frontend-tests--production-build)
  - [End-to-End Verification Audit](#end-to-end-verification-audit)
- [AI Configuration & Fallback](#ai-configuration--fallback)
- [Security & Ground-Truth Isolation](#security--ground-truth-isolation)

---

## Overview

During high-severity outages, incident responders face alert fatigue, distributed logs, conflicting metrics, and high-pressure decision-making. TRACEIQ addresses this by:

1. **Synthesizing Telemetry into Concrete Evidence**: Automatically normalizes metrics, logs, traces, configuration changes, and deployment events into structured evidence items.
2. **Eliminating AI Hallucinations**: LLMs are never permitted to fabricate telemetry. Every claim must reference verifiable, deterministic evidence IDs (`EV-XXX`).
3. **Exploring Competing Hypotheses**: Rather than prematurely latching onto a single lead, TRACEIQ evaluates competing hypotheses with supporting and contradicting evidence.
4. **Enforcing Human Approval**: Mitigation and recovery actions are never autonomous. Operators inspect recommendations, review blast-radius simulations, and explicitly approve actions.
5. **Preserving Organizational Memory**: Post-incident findings, RCA summaries, and verified recovery actions are indexed into incident memory to assist future investigations.

---

## Core Architecture & Boundaries

TRACEIQ strictly enforces deterministic telemetry boundaries:

```text
       RAW TELEMETRY
(Metrics, Logs, Traces, Deployments, Configs)
             │
             ▼
┌─────────────────────────┐
│   DETERMINISTIC ENGINE  │ ◄─── Authoritative fact-finder (deltas, baselines)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   NORMALIZED EVIDENCE   │ ◄─── Structured evidence bundle (EV-001, EV-002...)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   AI REASONING LAYER    │ ◄─── LangGraph state machine & LLM providers
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   STRUCTURED FINDINGS   │ ◄─── Validated Pydantic contracts & evidence refs
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  HUMAN RECOVERY GATE    │ ◄─── Blast radius simulation & explicit approval
└─────────────────────────┘
```

### Key Architectural Layers:
- **Evidence Engine (`backend/app/evidence/`)**: Ingests scenario telemetry, computes metric deltas, correlates timestamps, and produces typed evidence items.
- **AI Layer (`backend/app/ai/`)**:
  - **Provider Abstraction**: Multi-provider support (`mock`, `gemini`, `openai`, `anthropic`) with masked credential handling.
  - **LangGraph Orchestrator**: Stateful workflow managing `planner` $\rightarrow$ `hypotheses` $\rightarrow$ `evaluator` nodes.
  - **Reference Enforcement**: Rejects any hypothesis that cites invalid or fabricated evidence IDs.
  - **Deterministic Fallback**: Automatically falls back to deterministic rule engines if LLMs are offline, rate-limited, or timing out.
- **Backend Services (`backend/app/services/`)**: SQLite/SQLAlchemy persistence for incidents, investigations, audit entries, historical memories, and recovery simulations.
- **Frontend Workspace (`frontend/`)**: React 18, Vite, TypeScript, and Tailwind/Vanilla CSS providing an investigation console with causal chains, metric charts, evidence explorer, and interactive recovery gates.

---

## Investigation Workflow

```text
INCIDENT ALERT
      │
      ▼
EVIDENCE INGESTION & NORMALIZATION
      │
      ▼
HISTORICAL MEMORY LOOKUP (Prior similar incidents)
      │
      ▼
INVESTIGATION PLANNER (Determines investigation steps & priority)
      │
      ▼
SPECIALIZED INVESTIGATORS (Application, Database, Dependency analysis)
      │
      ▼
EVIDENCE CORRELATION & COMPETING HYPOTHESES (Strongly Supported / Supported / Inconclusive)
      │
      ▼
DEVIL'S ADVOCATE CHALLENGE (Falsification check & counter-evidence)
      │
      ▼
ROOT CAUSE ASSESSMENT (RCA)
      │
      ▼
RECOVERY ADVISOR (Mitigation strategy & rollback steps)
      │
      ▼
HUMAN APPROVAL GATE (Operator reviews findings & grants permission)
      │
      ▼
RECOVERY SIMULATION (Pre-execution validation & blast radius check)
      │
      ▼
POSTMORTEM & INCIDENT MEMORY (Archival for organizational learning)
```

---

## Incident Scenarios

TRACEIQ includes four realistic, production-plausible synthetic incident scenarios:

| Scenario ID | Title | Root Cause Category | Primary Symptom |
| :--- | :--- | :--- | :--- |
| `bad-deployment` | Bad Deployment / Application Regression | Deployment | Spike in 500 error rate & NullPointerExceptions following a canary release |
| `database-degradation` | Database Degradation | Database | Connection pool exhaustion, lock contention, and high p99 query latency |
| `external-dependency` | External Payment Gateway Failure | Dependency | Upstream 504 Gateway Timeouts and downstream thread starvation |
| `configuration-regression` | Configuration Regression | Configuration | Cache TTL reduction causing stampede and cascading service degradation |

*Note: Scenarios contain realistic background noise, normal baselines, and plausible false leads. Ground truth is strictly isolated for evaluation.*

---

## Repository Structure

```text
TRACEIQ/
├── backend/                  # FastAPI backend service
│   ├── app/
│   │   ├── ai/               # AI layer (LangGraph, providers, schemas, state, planner)
│   │   ├── api/              # REST API routes (/incidents, /investigations, /recovery)
│   │   ├── core/             # Configuration and database engine
│   │   ├── evidence/         # Deterministic telemetry normalization engine
│   │   ├── models/           # SQLAlchemy ORM and Pydantic schemas
│   │   └── services/         # Incident, investigation, recovery, audit services
│   └── tests/                # Pytest suites (unit, integration, AI, scenarios)
├── data/
│   ├── src/generators/       # Telemetry generators (metrics, logs, traces, configs)
│   └── generated/            # Generated synthetic telemetry datasets
├── frontend/                 # React + Vite + TypeScript application
│   ├── src/
│   │   ├── components/       # Workspace UI components (hypotheses, recovery, timeline)
│   │   ├── pages/            # Incidents list & Investigation workspace
│   │   └── services/         # Axios API client
│   └── tests/                # Vitest unit and integration suites
├── scripts/                  # Data generation, seeding, and audit scripts
│   ├── generate_data.py      # Generates synthetic incident datasets
│   ├── validate_data.py      # Validates telemetry schema compliance
│   ├── seed_demo.py          # Seeds database with demo incidents and memories
│   └── audit_scenarios.py    # Autonomous E2E API audit script
├── MASTER.md                 # Project architecture master document
└── AGENTS.md                 # Rules of engagement for AI agents & contributors
```

---

## Getting Started & Execution

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: v18 or higher (with npm)
- **PowerShell** or **Bash**

---

### 1. Telemetry Generation & Validation
Generate the production-plausible scenario datasets and confirm their structural integrity:

```powershell
# From the repository root
python scripts/generate_data.py
python scripts/validate_data.py
```

---

### 2. Database Initialization & Seeding
Populate the SQLite database (`backend/traceiq.db`) with initial incidents, historical incident memories, and baseline records:

```powershell
python scripts/seed_demo.py
```

---

### 3. Running the Backend API
Start the FastAPI backend server using Uvicorn:

```powershell
cd backend

# Set environment paths (PowerShell)
$env:PYTHONPATH="D:\TRACEIQ\data\src;D:\TRACEIQ\backend"
$env:DATA_ROOT="D:\TRACEIQ\data\generated"

# Run server
python -m uvicorn app.main:app --port 8000 --reload
```

The backend API will be accessible at:
- **API Base**: `http://localhost:8000`
- **Swagger Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/v1/health`

---

### 4. Running the Frontend Workspace
In a separate terminal, launch the Vite dev server:

```powershell
cd frontend

# Install dependencies (first time)
npm install

# Start Vite dev server
npm run dev
```

Open your browser at `http://localhost:5173`. The Vite server automatically proxies `/api` calls to `http://localhost:8000`.

---

## Running Tests & Verifications

TRACEIQ maintains an extensive test suite verifying deterministic calculations, AI schemas, fallback mechanisms, and user interactions.

### Backend Tests
Run the complete backend test suite (120 passing tests):

```powershell
cd backend
$env:PYTHONPATH="D:\TRACEIQ\data\src;D:\TRACEIQ\backend"
$env:DATA_ROOT="D:\TRACEIQ\data\generated"

python -m pytest
```

To run only the AI foundation and orchestration tests:
```powershell
python -m pytest tests/ai -v
```

---

### Frontend Tests & Production Build
Run Vitest for frontend component and UX testing:

```powershell
cd frontend
npm test
```

Test production compilation:
```powershell
npm run build
```

---

### End-to-End Verification Audit
With the backend running on port 8000, execute the end-to-end audit script:

```powershell
python scripts/audit_scenarios.py
```

This autonomously audits all 4 scenarios, verifies metric deltas, tests human approval gates, runs recovery simulations, and checks audit log persistence.

---

## AI Configuration & Fallback

The AI layer is configured via environment variables. By default, it operates with a deterministic `mock` provider so that all tests and local development function without requiring live API keys.

| Environment Variable | Allowed Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `AI_ENABLED` | `true`, `false` | `false` | Enables LangGraph AI investigation execution |
| `AI_PROVIDER` | `mock`, `gemini`, `openai`, `anthropic` | `mock` | Selected model provider |
| `AI_MODEL` | string | `mock-reasoner` | Specific LLM model identifier |
| `AI_TEMPERATURE` | float (`0.0` - `2.0`) | `0.0` | Sampling temperature |
| `AI_TIMEOUT_SECONDS` | float | `30.0` | Request timeout before triggering fallback |
| `GEMINI_API_KEY` | string | `None` | Google Gemini API key |
| `OPENAI_API_KEY` | string | `None` | OpenAI API key |
| `ANTHROPIC_API_KEY` | string | `None` | Anthropic Claude API key |

> **Graceful Fallback Guarantee**: If `AI_ENABLED=true` but the provider experiences network timeouts, quota limits, or invalid outputs, TRACEIQ automatically falls back to deterministic hypothesis generation and logs an `ai_investigation_fallback` audit event.

---

## Security & Ground-Truth Isolation

- **Zero Ground-Truth Leakage**: Ground truth keys (`root_cause_service`, `contradictory_lead`, `expected_recovery_action`, `primary_evidence_ids`) exist solely in test evaluation fixtures and are strictly stripped from AI state payloads and prompt inputs.
- **Masked Credentials**: API keys are never written to source code, logged, or exposed via `__repr__` methods.
- **Immutable Audit Trail**: All actions—from investigation start to recovery approval—are recorded with timestamped audit entries.
