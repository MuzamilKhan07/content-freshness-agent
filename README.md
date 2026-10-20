# FreshGuard AI

> **Agentic Content Freshness and Decay Detection System for Enterprise Knowledge Bases**

FreshGuard AI empowers knowledge managers, onboarding leaders, IT departments, and enterprise content owners to systematically detect stale, rotting, and contradictory documents across enterprise knowledge repositories.

---

## Architecture & Phases

- **Phase 1 (Complete):** Core Foundation, Dataset Ingestion & Validation (`ps11_content_inventory.csv`).
- **Phase 2 (Complete):** Enterprise Content Ingestion & Inventory Dashboard with Pagination, Search, and Filtering.
- **Phase 3 (Complete):** Explainable Freshness Scoring Engine & Prioritized Remediation Queue:
  - Deterministic 0–100 risk scoring with granular signal attribution.
  - Transparent evidence coverage and provisional score tracking.
  - Priority-ranked remediation queue with plain-language explanations.
  - Slide-over Score Explanation Inspector detailing formula calculations and recommended actions.
- **Phase 4 (Upcoming):** Evidence Collection Agent & Automated Scans.
- **Phase 5 (Upcoming):** Cross-Document Semantic Contradiction Detection.
- **Phase 6 (Upcoming):** Autonomous Remediation Workflows.
- **Phase 7 (Upcoming):** Cloud Run Production Deployment & Automated Scheduling.

---

## Phase 3 Freshness Scoring Engine

### Multi-Signal Scoring Weights (100 Points Total)

| Signal | Maximum Points | Status in Phase 3 | Evaluation Logic |
|---|---:|---|---|
| **Document Age** | 30 | Evaluated | Evaluated from `last_updated` (fallback to `last_reviewed`/`created_date`). &le;30d: 0 pts, 31–90d: 5 pts, 91–180d: 12 pts, 181–365d: 20 pts, >365d: 30 pts. |
| **Broken Hyperlinks** | 25 | Evaluated | Evaluated from `has_broken_links`. Clean: 0 pts, Confirmed dead links: 20 pts. |
| **Deprecated Tool References** | 20 | Evaluated | Evaluated from `mentions_deprecated_tool`. Clean: 0 pts, Confirmed retired software mention: 20 pts. |
| **Semantic Contradictions** | 15 | Unknown | Scheduled for Phase 5 (Cross-document LLM contradiction detection). |
| **Declining Viewership** | 10 | Unknown | In inventory CSV, only a single 90-day count is present without longitudinal history. Kept honestly as unknown. |

### Provisional Scoring & Evidence Coverage

Because contradiction checks (Phase 5) and view trend baselines are scheduled for future phases, the engine evaluates available signals (75% theoretical coverage) and produces a normalized provisional score:

$$\text{Provisional Score} = \left(\frac{\text{Earned Points}}{\text{Evaluated Maximum Points}}\right) \times 100$$

- Fully preserved raw earned points and denominator.
- Distinctly labeled as `Provisional` in both API responses and UI cards.
- Unknown signals are kept visibly distinct from clean signals.

### Risk Classification Thresholds

- **Critical Risk:** 80–100 points
- **High Risk:** 60–79 points
- **Moderate Risk:** 30–59 points
- **Low Risk:** 0–29 points
- **Insufficient Evidence:** Evaluated weight coverage < 40%

### Deterministic Prioritization Hierarchy

1. **Priority 1 (Critical Risk):** Critical score backed by strong evidence (&ge;70% coverage).
2. **Priority 2 (High Risk):** High score backed by strong evidence (&ge;70% coverage).
3. **Priority 3 (Elevated Risk / Provisional):** High score with partial evidence.
4. **Priority 4 (Moderate Risk):** Moderate aging or single minor risk signal.
5. **Priority 5 (Low Risk / Healthy):** Document is verified fresh and healthy.
6. **Priority 6 (Insufficient Evidence):** Telemetry incomplete; requires further data collection.

---

## Quick Start (Windows PowerShell)

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Node.js 18+ & npm 9+ (Tested on Node v24, npm 11)

### 1. Backend Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

### 2. Frontend Setup

```powershell
cd frontend
npm install
cd ..
```

---

## Running the Application

### Terminal 1: Launch FastAPI Backend Server

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **API Base:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Terminal 2: Launch React Development Server

```powershell
cd frontend
npm run dev
```
- Open browser at: [http://localhost:5173](http://localhost:5173)

---

## API Endpoints (Phases 1, 2 & 3)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Backend service health, version, and server timestamp |
| `GET` | `/api/dataset/status` | Ingestion status, available columns, and record count |
| `GET` | `/api/dashboard/summary` | Dashboard KPIs (total docs, platforms, broken links, deprecated tools) |
| `GET` | `/api/dashboard/distributions` | Aggregate distributions by platform, type, baseline score, and signals |
| `GET` | `/api/documents` | Paginated catalog with `search`, `platform`, `content_type`, `sort_by` |
| `GET` | `/api/documents/{document_id}` | Complete metadata inspection for a single document |
| `GET` | `/api/audit/summary` | Audit risk summary: Critical, High, Moderate, Low counts and coverage |
| `GET` | `/api/audit/documents` | Prioritized remediation queue with search, risk level, min/max score filters |
| `GET` | `/api/audit/documents/{document_id}` | Full scoring explanation: formula, signal breakdown, and recommended action |
| `POST` | `/api/audit/run` | Execute/re-run deterministic freshness audit against loaded records |

---

## Running Automated Backend Tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest -v
```
All 24 automated tests cover Phase 1, Phase 2, and Phase 3 functionality:
- Age thresholds (&le;30, 31–90, 91–180, 181–365, >365 days).
- Broken link scoring (clean, confirmed, missing).
- Deprecated tool scoring (clean, confirmed, missing).
- Contradiction and view trend unknown handling.
- Provisional score normalization and evidence coverage.
- Priority rank ordering (1 to 6).
- Zero records and missing data resilience.
- Security checks confirming zero exposed API keys.
