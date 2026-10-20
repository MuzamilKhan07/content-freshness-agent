from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from backend.app.core.deprecated_rules import DeprecatedRulesEngine
from backend.app.core.ssrf_validator import is_safe_url
from backend.app.main import app
from backend.app.models.evidence_models import (
    EvidenceAuditRequest,
    EvidenceSeverity,
    EvidenceStatus,
    SignalType,
)
from backend.app.services.evidence_service import EvidenceCollectionOrchestrator
from backend.app.services.evidence_tools import (
    DeprecatedToolDetectionTool,
    MetadataInspectionTool,
    MetadataQualityTool,
    URLVerificationTool,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_ssrf_validator_blocks_private_and_loopback():
    """Verify that SSRF guard rejects loopback, RFC1918, and cloud metadata."""
    # Loopback
    safe, msg = is_safe_url("http://127.0.0.1:8080/admin")
    assert safe is False
    assert "private" in msg.lower() or "restricted" in msg.lower()

    safe_local, _ = is_safe_url("http://localhost:3000")
    assert safe_local is False

    # Private IP
    safe_priv, _ = is_safe_url("http://192.168.1.50/api")
    assert safe_priv is False

    # Cloud metadata (169.254.169.254)
    safe_meta, _ = is_safe_url("http://169.254.169.254/latest/meta-data/")
    assert safe_meta is False

    # Unsupported protocol
    safe_ftp, _ = is_safe_url("ftp://ftp.example.com/file.txt")
    assert safe_ftp is False


def test_ssrf_validator_permits_public_urls():
    """Verify that public HTTP/HTTPS URLs pass validation."""
    safe_https, _ = is_safe_url("https://www.example.com/docs")
    assert safe_https is True

    safe_http, _ = is_safe_url("http://example.org/guide")
    assert safe_http is True


def test_url_verification_tool_missing_url():
    """Verify that missing URLs are recorded as UNKNOWN rather than failed or clean."""
    tool = URLVerificationTool()
    item = tool.verify_url("DOC-1", None)
    assert item.status == EvidenceStatus.UNKNOWN
    assert item.signal_type == SignalType.URL_VERIFICATION
    assert item.observed_value is None


def test_url_verification_tool_blocks_ssrf_destination():
    """Verify that URL tool emits FAILED evidence with CRITICAL severity for SSRF attempts."""
    tool = URLVerificationTool()
    item = tool.verify_url("DOC-2", "http://169.254.169.254/secret")
    assert item.status == EvidenceStatus.FAILED
    assert item.severity == EvidenceSeverity.CRITICAL
    assert "rejected" in item.summary.lower()


def test_deprecated_tool_detection_rules():
    """Verify rule-based detection for retired software keywords."""
    engine = DeprecatedRulesEngine()
    matches = engine.scan_text("Guide to configuring Skype for Business on Windows 10")
    assert len(matches) == 1
    rule, matched_str = matches[0]
    assert rule.tool_name == "Skype for Business"
    assert "Microsoft Teams" in rule.replacement_guidance

    # Centos match
    centos_match = engine.scan_text("Runbook for deploying to CentOS 7 servers")
    assert len(centos_match) == 1
    assert "Rocky Linux" in centos_match[0][0].replacement_guidance

    # Clean text has no matches
    clean_matches = engine.scan_text("Modern Cloud Architecture on Kubernetes and React")
    assert len(clean_matches) == 0


def test_deprecated_tool_tool_execution():
    """Verify DeprecatedToolDetectionTool produces confirmed evidence when matched."""
    tool = DeprecatedToolDetectionTool()
    row = {
        "content_id": "CNT-TEST-01",
        "title": "Migrating from HipChat to new channels",
        "mentions_deprecated_tool": "True",
    }
    evidence = tool.detect(row)
    assert len(evidence) >= 1
    found = [e for e in evidence if "HipChat" in e.summary]
    assert len(found) == 1
    assert found[0].status == EvidenceStatus.CONFIRMED


def test_metadata_quality_tool_detects_inconsistencies():
    """Verify MetadataQualityTool detects missing titles and inverted dates."""
    tool = MetadataQualityTool()
    row = {
        "content_id": "CNT-TEST-02",
        "title": "Untitled",
        "created_date": "2026-05-01",
        "last_updated": "2024-01-01",  # Inverted: updated before created
    }
    issues = tool.analyze(row)
    assert len(issues) >= 1
    titles = [i for i in issues if i.evidence_id.endswith("QUAL-TITLE")]
    dates = [i for i in issues if i.evidence_id.endswith("DATE-INCONSISTENT")]
    assert len(titles) == 1
    assert len(dates) == 1


def test_evidence_orchestrator_selected_documents():
    """Verify orchestrator runs on a selected document and returns an audit record."""
    orchestrator = EvidenceCollectionOrchestrator()
    req = EvidenceAuditRequest(
        document_ids=["CNT-0001"],
        enabled_checks=["metadata_inspection", "url_verification", "deprecated_tools", "metadata_quality"],
    )
    record = orchestrator.run_evidence_audit(req)
    assert record.status == "completed"
    assert len(record.document_ids) == 1
    assert record.document_ids[0] == "CNT-0001"
    assert record.summary.documents_inspected == 1
    assert record.summary.checks_attempted > 0


def test_evidence_summary_api(client):
    """Test GET /api/evidence/summary returns expected summary metrics."""
    res = client.get("/api/evidence/summary")
    assert res.status_code == 200
    data = res.json()
    assert "documents_inspected" in data
    assert "checks_attempted" in data
    assert "confirmed_findings" in data
    assert "audit_start_timestamp" in data


def test_evidence_documents_lookup_api(client):
    """Test GET /api/evidence/documents/{document_id}."""
    res = client.get("/api/evidence/documents/CNT-0001")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == "CNT-0001"
    assert data["evidence_count"] > 0
    assert len(data["evidence_items"]) > 0


def test_evidence_findings_pagination_and_filtering(client):
    """Test GET /api/evidence/findings with filters."""
    res = client.get("/api/evidence/findings?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert len(data["items"]) == 10
    assert data["total"] > 0

    # Filter by confirmed status
    conf_res = client.get("/api/evidence/findings?status=confirmed")
    assert conf_res.status_code == 200
    for it in conf_res.json()["items"]:
        assert it["status"] == "confirmed"


def test_evidence_audit_history_lookup(client):
    """Test POST /api/evidence/audit followed by GET /api/evidence/audits/{audit_id}."""
    post_res = client.post("/api/evidence/audit", json={"max_documents": 5})
    assert post_res.status_code == 200
    audit_data = post_res.json()
    audit_id = audit_data["audit_id"]

    get_res = client.get(f"/api/evidence/audits/{audit_id}")
    assert get_res.status_code == 200
    assert get_res.json()["audit_id"] == audit_id

    # 404 for unknown audit ID
    res_404 = client.get("/api/evidence/audits/AUDIT-NONEXISTENT")
    assert res_404.status_code == 404
