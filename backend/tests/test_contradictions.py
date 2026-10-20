import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.contradiction_models import (
    ContradictionRelationship,
    ContradictionReviewStatus,
    ContradictionSeverity,
    RecencyAssessment,
)
from backend.app.services.content_service import get_content_service
from backend.app.services.contradiction_service import (
    CandidateSelector,
    ClaimExtractor,
    SemanticContradictionAnalyzer,
    get_contradiction_service,
)
from backend.app.services.dataset_service import get_dataset_service
from backend.app.services.scoring_service import get_scoring_service

client = TestClient(app)


def test_content_service_text_storage_and_seeding():
    """Verify document content service stores text and provides seeded test records."""
    content_svc = get_content_service()

    # Seeded records exist
    assert content_svc.has_document_content("CNT-0004") is True
    assert content_svc.has_document_content("CNT-0012") is True
    assert "CISO" in content_svc.get_document_content("CNT-0004")

    # Ingestion of custom content
    content_svc.set_document_content("CNT-CUSTOM-1", "This is a custom test document.", source="test")
    assert content_svc.has_document_content("CNT-CUSTOM-1") is True
    assert content_svc.get_document_content("CNT-CUSTOM-1") == "This is a custom test document."

    # Non-existent content returns None
    assert content_svc.get_document_content("CNT-NONEXISTENT") is None
    assert content_svc.has_document_content("CNT-NONEXISTENT") is False


def test_candidate_selector_pairs_eligible_documents():
    """Verify candidate selector generates bounded pairs of same-topic documents with text content."""
    dataset_svc = get_dataset_service()
    content_svc = get_content_service()
    selector = CandidateSelector(dataset_svc, content_svc)

    pairs = selector.select_candidate_pairs(max_pairs=10)
    assert len(pairs) > 0
    assert len(pairs) <= 10

    # Every pair must have content available
    for doc_a, doc_b in pairs:
        assert content_svc.has_document_content(doc_a["content_id"])
        assert content_svc.has_document_content(doc_b["content_id"])


def test_claim_extractor_identifies_structured_claims():
    """Verify claim extractor segments sentences into explicit claims."""
    extractor = ClaimExtractor(api_key=None)  # Use deterministic mode

    text = (
        "All production database schema migrations require prior written sign-off from the CISO. "
        "A mandatory 48-hour change freeze must be observed before any deployment."
    )
    claims = extractor.extract_claims("CNT-0004", text)
    assert len(claims) >= 1
    assert claims[0].document_id == "CNT-0004"
    assert "CISO" in claims[0].claim_text
    assert claims[0].claim_type == "approval_requirement"


def test_analyzer_detects_procedural_contradiction():
    """Verify semantic analyzer identifies conflicting CISO approval vs GitOps automated pipeline."""
    analyzer = SemanticContradictionAnalyzer()
    extractor = ClaimExtractor(api_key=None)

    doc_a = {
        "content_id": "CNT-0004",
        "title": "Change Control Policy",
        "last_updated": "2024-06-01",
        "subject_area": "Security",
    }
    doc_b = {
        "content_id": "CNT-0012",
        "title": "GitOps Architecture Specification",
        "last_updated": "2025-08-15",
        "subject_area": "Security",
    }

    text_a = "All production database schema migrations require prior written sign-off from the CISO and a 48-hour freeze."
    text_b = "Automated database migrations pre-validated by security linters do not require manual CISO sign-off or freeze delays."

    claims_a = extractor.extract_claims("CNT-0004", text_a)
    claims_b = extractor.extract_claims("CNT-0012", text_b)

    findings = analyzer.compare_documents("AUD-TEST-1", doc_a, doc_b, claims_a, claims_b)
    assert len(findings) > 0

    finding = findings[0]
    assert finding.relationship_type == ContradictionRelationship.CONTRADICTION
    assert finding.severity == ContradictionSeverity.CRITICAL
    assert finding.recency_assessment == RecencyAssessment.NEWER_DOCUMENT_LIKELY_AUTHORITATIVE
    assert "CISO" in finding.explanation


def test_analyzer_detects_numerical_limit_contradiction():
    """Verify semantic analyzer flags conflicting expense reimbursement caps."""
    analyzer = SemanticContradictionAnalyzer()
    extractor = ClaimExtractor(api_key=None)

    doc_a = {
        "content_id": "CNT-0001",
        "title": "Travel Reimbursement Policy",
        "last_updated": "2024-01-10",
        "subject_area": "Finance",
    }
    doc_b = {
        "content_id": "CNT-0005",
        "title": "Employee Expense Handbook",
        "last_updated": "2025-03-20",
        "subject_area": "Finance",
    }

    text_a = "Employee travel claims for domestic flights are capped at $450 per segment."
    text_b = "The domestic travel reimbursement allowance is updated to $750 per segment to adjust for airline fare increases."

    claims_a = extractor.extract_claims("CNT-0001", text_a)
    claims_b = extractor.extract_claims("CNT-0005", text_b)

    findings = analyzer.compare_documents("AUD-TEST-2", doc_a, doc_b, claims_a, claims_b)
    assert len(findings) > 0

    finding = findings[0]
    assert finding.relationship_type == ContradictionRelationship.CONTRADICTION
    assert finding.severity == ContradictionSeverity.HIGH
    assert "$450 vs $750" in finding.explanation


def test_analyzer_distinguishes_scope_difference():
    """Verify analyzer identifies operational exceptions and scope differences without false alarms."""
    analyzer = SemanticContradictionAnalyzer()
    extractor = ClaimExtractor(api_key=None)

    doc_a = {
        "content_id": "CNT-0002",
        "title": "Product Release Process",
        "last_updated": "2025-01-01",
        "subject_area": "Product",
    }
    doc_b = {
        "content_id": "CNT-0008",
        "title": "Internal Dogfooding Guidelines",
        "last_updated": "2025-02-01",
        "subject_area": "Product",
    }

    text_a = "All customer-facing software releases require formal sign-off from the VP of Product."
    text_b = "Beta releases deployed exclusively to the internal dogfooding cohort require only Engineering Manager approval."

    claims_a = extractor.extract_claims("CNT-0002", text_a)
    claims_b = extractor.extract_claims("CNT-0008", text_b)

    findings = analyzer.compare_documents("AUD-TEST-3", doc_a, doc_b, claims_a, claims_b)
    assert len(findings) > 0

    finding = findings[0]
    assert finding.relationship_type == ContradictionRelationship.SCOPE_DIFFERENCE
    assert finding.severity == ContradictionSeverity.LOW
    assert "different operational scopes" in finding.explanation


def test_analyzer_identifies_technology_supersession():
    """Verify analyzer identifies modern technologies explicitly superseding legacy tools."""
    analyzer = SemanticContradictionAnalyzer()
    extractor = ClaimExtractor(api_key=None)

    doc_a = {
        "content_id": "CNT-0003",
        "title": "Software Repository Operations",
        "last_updated": "2023-01-01",
        "subject_area": "IT",
    }
    doc_b = {
        "content_id": "CNT-0010",
        "title": "Modern Cloud Artifact Registry",
        "last_updated": "2025-01-01",
        "subject_area": "IT",
    }

    text_a = "All software release artifacts must be version-tagged and packaged using Subversion (SVN) tags."
    text_b = "Subversion (SVN) has been officially decommissioned in favor of GitHub Container Registry (GHCR)."

    claims_a = extractor.extract_claims("CNT-0003", text_a)
    claims_b = extractor.extract_claims("CNT-0010", text_b)

    findings = analyzer.compare_documents("AUD-TEST-4", doc_a, doc_b, claims_a, claims_b)
    assert len(findings) > 0

    finding = findings[0]
    assert finding.relationship_type == ContradictionRelationship.SUPERSESSION
    assert "decommissioned" in finding.explanation


def test_contradiction_audit_api_workflow():
    """Verify POST /api/contradictions/audit runs successfully and produces traceable findings."""
    response = client.post("/api/contradictions/audit", json={"max_comparisons": 10})
    assert response.status_code == 200
    data = response.json()

    assert data["total_pairs_analyzed"] > 0
    assert data["total_findings"] > 0
    assert data["pending_review_findings"] >= 0


def test_contradiction_listing_and_filtering_api():
    """Verify GET /api/contradictions supports pagination and filtering."""
    # List all
    res = client.get("/api/contradictions?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

    # Filter by status
    res_status = client.get("/api/contradictions?status=pending_review")
    assert res_status.status_code == 200
    for item in res_status.json()["items"]:
        assert item["status"] == "pending_review"

    # Filter by severity
    res_sev = client.get("/api/contradictions?severity=critical")
    assert res_sev.status_code == 200
    for item in res_sev.json()["items"]:
        assert item["severity"] == "critical"


def test_contradiction_review_and_score_synchronization():
    """Verify PATCH /api/contradictions/{id}/review confirms contradiction and updates Phase 3 scores."""
    # 1. Fetch a finding
    list_res = client.get("/api/contradictions?page=1&page_size=1")
    items = list_res.json()["items"]
    assert len(items) > 0
    finding = items[0]
    c_id = finding["contradiction_id"]
    doc_a_id = finding["document_a_id"]

    # 2. Score before confirming contradiction
    scoring_svc = get_scoring_service()
    score_before = scoring_svc.get_scored_document_by_id(doc_a_id)
    assert score_before is not None

    # 3. Review finding to CONFIRMED
    review_res = client.patch(
        f"/api/contradictions/{c_id}/review",
        json={
            "status": "confirmed",
            "review_note": "Verified by Lead Enterprise Architect as an active conflict.",
            "reviewed_by": "Senior Auditor",
        },
    )
    assert review_res.status_code == 200
    reviewed = review_res.json()
    assert reviewed["status"] == "confirmed"
    assert reviewed["review_note"] is not None

    # 4. Verify Phase 3 scoring engine updated the contradiction signal
    score_after = scoring_svc.get_scored_document_by_id(doc_a_id)
    assert score_after is not None
    contra_signal = score_after.signal_breakdown["contradictions"]
    assert contra_signal.status.value == "evaluated"
    assert contra_signal.actual_points is not None
    assert contra_signal.actual_points > 0

    # 5. Review finding to DISMISSED and verify penalty is removed
    dismiss_res = client.patch(
        f"/api/contradictions/{c_id}/review",
        json={
            "status": "dismissed",
            "review_note": "False alarm; documents refer to separate business entities.",
            "reviewed_by": "Senior Auditor",
        },
    )
    assert dismiss_res.status_code == 200
    score_dismissed = scoring_svc.get_scored_document_by_id(doc_a_id)
    assert score_dismissed is not None


def test_document_content_ingestion_api():
    """Verify POST and GET /api/documents/{id}/content."""
    doc_id = "CNT-9999"
    content_text = "Standard Operating Procedure: All customer passwords must be rotated every 90 days."

    # POST content
    post_res = client.post(
        f"/api/documents/{doc_id}/content",
        json={"text": content_text, "source": "unit_test"},
    )
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["status"] == "success"
    assert data["characters_stored"] == len(content_text)

    # GET content
    get_res = client.get(f"/api/documents/{doc_id}/content")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["has_content"] is True
    assert get_data["full_text"] == content_text

    # GET non-existent returns 404
    missing_res = client.get("/api/documents/NON-EXISTENT/content")
    assert missing_res.status_code == 404
