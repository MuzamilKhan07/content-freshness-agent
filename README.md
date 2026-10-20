# FreshGuard AI

> **Agentic Content Freshness and Decay Detection System for Enterprise Knowledge Bases**

FreshGuard AI empowers knowledge managers, onboarding leaders, IT departments, and enterprise content owners to systematically detect stale, rotting, and contradictory documents across enterprise knowledge repositories.

---

## Architecture & Phases

- **Phase 1 (Complete):** Core Foundation, Dataset Ingestion & Validation (`ps11_content_inventory.csv`).
- **Phase 2 (Complete):** Enterprise Content Ingestion & Dashboard:
  - High-Level KPI Summary & Distribution Visualizations
  - Paginated Content Inventory Catalog with Dynamic Filtering, Search, and Column Sorting
  - Slide-Over Document Metadata Inspection Drawer with "Available Evidence" Signals
- **Phase 3 (Upcoming):** Multi-Signal Freshness & Decay Scoring Engine.
- **Phase 4 (Upcoming):** Risk Auditing & Automated Decay Detection.
- **Phase 5 (Upcoming):** Cross-Document Semantic Contradiction Detection.
- **Phase 6 (Upcoming):** Autonomous Remediation Workflows.
- **Phase 7 (Upcoming):** Production Cloud Run Deployment & Automated Scheduling.

---

## Project Structure

```text
freshguard-ai/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ContentInventory.tsx
│   │   │   ├── DashboardOverview.tsx
│   │   │   ├── DatasetPreviewTable.tsx
│   │   │   ├── DatasetWarnings.tsx
│   │   │   ├── DocumentDetailDrawer.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── MetricsOverview.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── TopBar.tsx
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
# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\requirements.txt

# Ensure environment file exists
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

### 2. Frontend Setup

In the same or a new terminal:

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
- **Health Check:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### Terminal 2: Launch React Development Server

```powershell
cd frontend
npm run dev
```
- Open browser at: [http://localhost:5173](http://localhost:5173)

---

## API Endpoints (Phase 1 & Phase 2)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Backend service health, service name, and timestamp |
| `GET` | `/api/dataset/status` | Dataset presence, record count, and schema columns |
| `GET` | `/api/dataset/preview` | Preview of first 10 records (sample) |
| `GET` | `/api/dashboard/summary` | Real calculated KPIs: total docs, platforms, broken links, deprecated tools, missing dates |
| `GET` | `/api/dashboard/distributions` | Aggregate distributions by platform, type, reference score, and signals |
| `GET` | `/api/documents` | Paginated catalog with `search`, `platform`, `content_type`, `status`, `sort_by`, `sort_order` |
| `GET` | `/api/documents/{document_id}` | Complete metadata inspection for a single document |

### Document Query Parameters
- `page` (int, default `1`, min `1`): Page number.
- `page_size` (int, default `20`, max `100`): Documents per page.
- `search` (string, optional): Case-insensitive search across title, content_id, platform, domain, author.
- `platform` (string, optional): Filter by platform (`SharePoint`, `Confluence`, `Google Docs`, `Notion`, `Internal Wiki`).
- `content_type` (string, optional): Filter by type (`Process Doc`, `Runbook`, `Architecture Diagram`, etc.).
- `status` (string, optional): Filter by recommended action.
- `sort_by` (string, optional): Supported fields (`content_id`, `title`, `platform`, `content_type`, `last_updated`, `last_reviewed`, `page_views_90d`, `linked_from_count`, `staleness_score`).
- `sort_order` (string, default `asc`): `asc` or `desc`.

---

## Running Backend Tests

Run the full pytest suite:

```powershell
.\.venv\Scripts\Activate.ps1
pytest -v
```

Verified test suite:
1. `test_health_endpoint`
2. `test_dataset_status_with_real_data`
3. `test_dataset_preview_limits`
4. `test_dashboard_summary_metrics`
5. `test_dashboard_distributions`
6. `test_documents_pagination`
7. `test_documents_search`
8. `test_documents_filters`
9. `test_documents_sorting`
10. `test_documents_invalid_sort_field`
11. `test_document_detail_lookup`
12. `test_missing_dataset_graceful_handling`
13. `test_no_secrets_in_responses`

---

## Building Frontend for Production

```powershell
cd frontend
npm run build
```
Generates optimized static assets into `frontend/dist/`.
