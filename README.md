# FreshGuard AI

> **Agentic Content Freshness and Decay Detection System for Enterprise Knowledge Bases**

FreshGuard AI empowers knowledge managers, onboarding leaders, IT departments, and enterprise content owners to systematically detect stale, rotting, and contradictory documents across knowledge silos.

---

## Phase 1 Overview

Phase 1 establishes a rock-solid, production-grade foundation:
- **FastAPI Backend** with clean modular design (`app/api`, `app/core`, `app/models`, `app/services`), CORS support, structured Pydantic models, and safe error boundary.
- **Dataset Ingestion Engine** that robustly inspects, validates, and previews the knowledge base inventory (`ps11_content_inventory.csv`) preserving source headers and handling missing signals.
- **React 18 + Vite + TypeScript Frontend** built with an enterprise-grade dark theme, real-time backend connection status indicator, inventory metric cards, and responsive record preview table.
- **Automated Test Suite** using `pytest` verifying health status, real dataset ingestion, 10-record preview limiting, missing dataset resilience, and credential exposure prevention.

---

## Project Structure

```text
freshguard-ai/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DatasetPreviewTable.tsx
│   │   │   ├── DatasetWarnings.tsx
│   │   │   ├── Header.tsx
│   │   │   └── MetricsOverview.tsx
│   │   ├── pages/
│   │   │   └── DashboardPage.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── dataset.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── dataset_service.py
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_api.py
│   └── requirements.txt
├── data/
│   └── ps11_content_inventory.csv
├── .env.example
├── .gitignore
├── pytest.ini
└── README.md
```

---

## Quick Start (Windows PowerShell)

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Node.js 18+ & npm 9+ (Tested on Node v24, npm 11)

### 1. Backend Setup

Open a PowerShell terminal at the project root (`e:\FreshGaurd Agent`):

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend\requirements.txt

# Copy environment configuration
Copy-Item .env.example .env
```

### 2. Frontend Setup

In the same or a new terminal:

```powershell
# Navigate to frontend directory
cd frontend

# Install frontend dependencies
npm install

# Return to root directory
cd ..
```

---

## Running the Application

### Terminal 1: Launch Backend Server

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API and Swagger docs will be live at:
- **API Base:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### Terminal 2: Launch Frontend Development Server

```powershell
cd frontend
npm run dev
```
Open your browser at [http://localhost:5173](http://localhost:5173).

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Returns backend service health status, service name, and timestamp |
| `GET` | `/api/dataset/status` | Returns dataset availability, record count, and schema columns |
| `GET` | `/api/dataset/preview` | Returns up to 10 sample records, total record count, and schema |

### Example Responses

#### `GET /api/health`
```json
{
  "status": "healthy",
  "service": "FreshGuard AI Backend",
  "version": "0.1.0",
  "timestamp": "2026-10-20T07:38:11.758257+00:00"
}
```

#### `GET /api/dataset/status`
```json
{
  "available": true,
  "record_count": 200,
  "columns": [
    "content_id", "title", "content_type", "platform", "author",
    "created_date", "last_updated", "last_reviewed", "page_views_90d",
    "linked_from_count", "mentions_deprecated_tool", "has_broken_links",
    "subject_area", "staleness_score", "recommended_action"
  ],
  "warnings": [],
  "file_path": "data/ps11_content_inventory.csv"
}
```

---

## Running Backend Tests

Run the full pytest suite with:

```powershell
.\.venv\Scripts\Activate.ps1
pytest -v
```

Verified test coverage:
1. `test_health_endpoint` — Validates health check payload.
2. `test_dataset_status_with_real_data` — Verifies dataset loading, 200 records loaded, and column presence.
3. `test_dataset_preview_limits` — Verifies preview returns at most 10 records.
4. `test_missing_dataset_graceful_handling` — Verifies graceful fallback and zero crashes when dataset is missing.
5. `test_no_secrets_in_responses` — Verifies that keys or secrets are never exposed in API outputs.

---

## Building Frontend for Production

```powershell
cd frontend
npm run build
```
Generates optimized static assets into `frontend/dist/`.
