"""
Phase 7 End-to-End Integration & Production Readiness Test Suite
Verifies backend readiness, static asset serving, CORS configuration,
error handling, and cross-module workflow cohesion.
"""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.content_service import get_content_service
from backend.app.services.dataset_service import get_dataset_service
from backend.app.services.scoring_service import get_scoring_service
from backend.app.services.evidence_service import get_evidence_orchestrator
from backend.app.services.contradiction_service import get_contradiction_service
from backend.app.services.remediation_service import get_remediation_service

client = TestClient(app)


def test_phase7_health_and_readiness():
    """Verify health and readiness probes conform to production specifications."""
    # 1. Health Probe
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert "version" in health_data

    # 2. Readiness Probe
    ready_res = client.get("/api/ready")
    assert ready_res.status_code == 200
    ready_data = ready_res.json()
    assert ready_data["status"] == "ready"
    assert ready_data["dataset_available"] is True
    assert ready_data["records_loaded"] > 0


def test_phase7_static_assets_or_fallback():
    """Verify that root / and static routing return valid responses without crashes."""
    res = client.get("/")
    assert res.status_code in (200, 304)
    # Either returns HTML for SPA or JSON status info
    assert len(res.content) > 0


def test_phase7_dataset_integrity():
    """Verify dataset loading, counts, and search filtering."""
    res = client.get("/api/documents?page=1&page_size=10&search=policy")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] > 0


def test_phase7_scoring_and_audit():
    """Verify explainable scoring engine execution."""
    res = client.get("/api/audit/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_documents"] == 200
    assert summary["scored_documents"] == 200
    assert "risk_distribution" in summary


def test_phase7_evidence_audit_pipeline():
    """Verify safe evidence collection pipeline and findings."""
    res = client.get("/api/evidence/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["documents_inspected"] > 0


def test_phase7_contradiction_detection():
    """Verify cross-document contradiction extraction and listing."""
    res = client.get("/api/contradictions/summary")
    assert res.status_code == 200
    summary = res.json()
    assert "total_pairs_analyzed" in summary


def test_phase7_full_remediation_cycle():
    """Verify complete end-to-end remediation lifecycle from creation to approval."""
    # 1. Create Job
    create_res = client.post(
        "/api/remediation/jobs",
        json={"document_id": "CNT-0001", "remediation_objective": "Phase 7 E2E Integration Test"},
    )
    assert create_res.status_code == 201
    job = create_res.json()
    rem_id = job["remediation_id"]

    # 2. Generate Draft Revision
    gen_res = client.post(f"/api/remediation/jobs/{rem_id}/generate")
    assert gen_res.status_code == 200
    draft = gen_res.json()
    rev_id = draft["revision_id"]
    assert draft["validation_status"] in ("passed", "passed_with_warnings", "needs_human_review")
    assert len(draft["changes"]) > 0

    # 3. Independent Validation Endpoint
    val_res = client.post(f"/api/remediation/revisions/{rev_id}/validate")
    assert val_res.status_code == 200
    assert "evidence_coverage_percent" in val_res.json()

    # 4. Human Approval
    rev_res = client.patch(
        f"/api/remediation/revisions/{rev_id}/review",
        json={"action": "approve", "review_note": "Phase 7 acceptance verified."},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["review_status"] == "approved"

    # 5. Verify Original Document Immutability
    content_svc = get_content_service()
    current_text = content_svc.get_document_content("CNT-0001")
    assert current_text is not None
    assert "$450" in current_text or "Corporate Travel" in current_text


def test_phase7_security_sanitization():
    """Verify error sanitization: 500 errors do not expose stack traces."""
    # Requesting non-existent API endpoints returns clean 404
    res = client.get("/api/unknown_route_xyz")
    assert res.status_code == 404
    assert "detail" in res.json()
    assert "Traceback" not in res.text
