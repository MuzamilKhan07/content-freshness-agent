import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.remediation_models import (
    ChangeRecord,
    DraftRevision,
    RemediationJobStatus,
    RemediationPlan,
    RevisionReviewStatus,
    ValidationStatus,
)
from backend.app.services.content_service import get_content_service
from backend.app.services.remediation_service import (
    DocumentRevisionAgent,
    RemediationPlanner,
    ValidationAgent,
    get_remediation_service,
)
from backend.app.services.scoring_service import get_scoring_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_seed_content():
    """Ensure baseline document content is available for tests."""
    content_svc = get_content_service()
    if not content_svc.has_document_content("CNT-0001"):
        content_svc.set_document_content(
            "CNT-0001",
            "Corporate Travel Policy: Domestic flights capped at $450. Reimbursement within 14 days.",
            source="test_fixture",
        )


# 1. Remediation request validation
def test_create_job_valid_document():
    response = client.post(
        "/api/remediation/jobs",
        json={"document_id": "CNT-0001", "remediation_objective": "Fix travel limits"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["document_id"] == "CNT-0001"
    assert "remediation_id" in data
    assert data["status"] in ("planning", "created", "ready_for_review")


def test_create_job_invalid_document():
    response = client.post(
        "/api/remediation/jobs",
        json={"document_id": "NON-EXISTENT-DOC-9999"},
    )
    assert response.status_code == 400
    assert "does not exist in inventory" in response.json()["detail"]


# 2. Missing document content
def test_missing_document_content_blocks_remediation():
    content_svc = get_content_service()
    # Create doc in scoring service or use an ID with no text
    empty_doc_id = "CNT-9999-EMPTY"
    content_svc._content_store.pop(empty_doc_id, None)

    scoring_svc = get_scoring_service()
    scoring_svc.run_audit()
    scored_res = scoring_svc.get_scored_documents(page=1, page_size=50)
    
    # Pick a document ID from inventory that has no content ingested
    target_id = None
    for d in scored_res.items:
        if not content_svc.has_document_content(d.content_id):
            target_id = d.content_id
            break

    if not target_id:
        target_id = "CNT-0020"
        content_svc._content_store.pop(target_id, None)

    # Creating job when content is missing
    resp = client.post(
        "/api/remediation/jobs",
        json={"document_id": target_id},
    )
    assert resp.status_code == 201
    job = resp.json()
    assert job["plan"]["has_sufficient_content"] is False
    assert job["status"] == "failed"

    # Generating draft on missing content must fail with 400
    gen_resp = client.post(f"/api/remediation/jobs/{job['remediation_id']}/generate")
    assert gen_resp.status_code == 400
    assert "Insufficient source text" in gen_resp.json()["detail"] or "Block remediation" in gen_resp.json()["detail"]


# 3. Missing OpenAI API key / graceful handling
def test_missing_openai_api_key_deterministic_fallback():
    agent = DocumentRevisionAgent(api_key="")
    plan = RemediationPlan(
        document_id="CNT-0001",
        primary_objective="Update airfare cap to $750",
        findings_to_address=["Numerical limit outdated"],
        required_source_references=["CNT-0005:Global Employee Expense Handbook"],
        proposed_changes_outline=["Update $450 to $750"],
        unresolved_questions=[],
        has_sufficient_content=True,
    )
    content = "Corporate Travel Policy: Domestic flights capped at a maximum of $450 per flight segment. All expense reimbursement reports must be submitted within 14 calendar days"
    
    draft = agent.generate_revision(
        remediation_id="REM-TEST-001",
        document_id="CNT-0001",
        original_text=content,
        plan=plan,
    )
    assert draft is not None
    assert "$750" in draft.proposed_content
    assert len(draft.changes) > 0
    assert draft.changes[0].supporting_evidence_refs == ["CNT-0005:Global Employee Expense Handbook"]


# 4. Successful structured draft generation via API
def test_successful_draft_generation_api():
    job_resp = client.post(
        "/api/remediation/jobs",
        json={"document_id": "CNT-0001"},
    )
    assert job_resp.status_code == 201
    rem_id = job_resp.json()["remediation_id"]

    gen_resp = client.post(f"/api/remediation/jobs/{rem_id}/generate")
    assert gen_resp.status_code == 200
    draft = gen_resp.json()
    assert draft["document_id"] == "CNT-0001"
    assert draft["proposed_content"] != ""
    assert isinstance(draft["changes"], list)
    assert draft["validation_status"] in ("passed", "passed_with_warnings", "needs_human_review")


# 5. Malformed model output handling
def test_malformed_model_output_fallback():
    agent = DocumentRevisionAgent(api_key="sk-mock-test-key")
    plan = RemediationPlan(
        document_id="CNT-0001",
        primary_objective="Update flight limit",
        findings_to_address=["Outdated cap"],
        required_source_references=["CNT-0005:Global Employee Expense Handbook"],
        proposed_changes_outline=[],
        has_sufficient_content=True,
    )

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_choice = MagicMock()
        mock_choice.message.content = "INVALID MALFORMED JSON {not_json"
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

        # Should catch JSONDecodeError and safely fall back to deterministic draft without raising
        draft = agent.generate_revision(
            remediation_id="REM-MOCK-001",
            document_id="CNT-0001",
            original_text="Corporate Travel Policy: Domestic flights capped at a maximum of $450 per flight segment. All expense reimbursement reports must be submitted within 14 calendar days",
            plan=plan,
        )
        assert draft is not None
        assert draft.proposed_content != ""


# 6 & 7. Unsupported factual claims & Missing supporting evidence
def test_unsupported_factual_claim_detected():
    validator = ValidationAgent()
    plan = RemediationPlan(
        document_id="CNT-0001",
        primary_objective="Fix limits",
        has_sufficient_content=True,
    )
    # Draft with a change lacking supporting evidence
    draft = DraftRevision(
        revision_id="REV-TEST-UNSUPPORTED",
        remediation_id="REM-TEST-001",
        document_id="CNT-0001",
        original_content="Standard policy requires compliance with rules.",
        proposed_content="Invented policy requires compliance with newly invented $5000 budget.",
        revision_summary="Added random budget limit",
        changes=[
            ChangeRecord(
                change_id="CHG-1",
                original_text="Standard policy",
                proposed_text="Invented policy with $5000 budget",
                change_type="factual_correction",
                reason="Invented claim with no source",
                supporting_evidence_refs=[],  # Missing evidence!
            )
        ],
    )
    result = validator.validate_revision(draft, plan, contradictions=[])
    assert result.validation_status == ValidationStatus.FAILED
    assert len(result.unsupported_claim_findings) > 0
    assert "lacks explicit supporting evidence" in result.unsupported_claim_findings[0]


# 8. Unresolved contradictions detection
def test_unresolved_contradictions_detection():
    validator = ValidationAgent()
    plan = RemediationPlan(document_id="CNT-0001", primary_objective="Test", has_sufficient_content=True)

    mock_contradiction = MagicMock()
    mock_contradiction.claim_a = "Domestic flights capped at a maximum of $450"
    mock_contradiction.recency_assessment = MagicMock(value="newer_document_likely_authoritative")

    draft = DraftRevision(
        revision_id="REV-TEST-CONTRA",
        remediation_id="REM-TEST-001",
        document_id="CNT-0001",
        original_content="Domestic flights capped at a maximum of $450 per segment.",
        proposed_content="Domestic flights capped at a maximum of $450 per segment.",  # Still contains claim_a!
        revision_summary="No changes made",
        changes=[],
    )
    result = validator.validate_revision(draft, plan, contradictions=[mock_contradiction])
    assert result.validation_status == ValidationStatus.FAILED
    assert len(result.remaining_contradiction_refs) > 0


# 9. Validation status classification
def test_validation_status_classification_rules():
    validator = ValidationAgent()
    plan = RemediationPlan(document_id="CNT-0001", primary_objective="Test", has_sufficient_content=True)

    # 1. Passed
    draft_passed = DraftRevision(
        revision_id="REV-PASS",
        remediation_id="REM-1",
        document_id="CNT-0001",
        original_content="Flights max $450. Policy compliance is required.",
        proposed_content="Flights max $750. Policy compliance is required.",
        revision_summary="Updated $450 to $750",
        changes=[
            ChangeRecord(
                change_id="CHG-1",
                original_text="$450",
                proposed_text="$750",
                reason="Align with global expense handbook.",
                supporting_evidence_refs=["CNT-0005:Global Employee Expense Handbook"],
            )
        ],
    )
    res_pass = validator.validate_revision(draft_passed, plan, contradictions=[])
    assert res_pass.validation_status == ValidationStatus.PASSED

    # 2. Needs human review (authority unclear)
    mock_c = MagicMock()
    mock_c.recency_assessment = MagicMock(value="authority_unclear")
    mock_c.claim_a = "Something else not in text"
    res_human = validator.validate_revision(draft_passed, plan, contradictions=[mock_c])
    assert res_human.validation_status == ValidationStatus.NEEDS_HUMAN_REVIEW


# 10. Original content preservation
def test_original_content_preservation_after_draft_and_approval():
    content_svc = get_content_service()
    original_text = content_svc.get_document_content("CNT-0001")
    assert original_text is not None

    # Run job, generate draft, and approve it
    job_resp = client.post("/api/remediation/jobs", json={"document_id": "CNT-0001"})
    rem_id = job_resp.json()["remediation_id"]
    gen_resp = client.post(f"/api/remediation/jobs/{rem_id}/generate")
    rev_id = gen_resp.json()["revision_id"]

    # Approve
    rev_resp = client.patch(
        f"/api/remediation/revisions/{rev_id}/review",
        json={"action": "approve", "review_note": "Looks great, approved."},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["review_status"] == "approved"

    # Original content in content service MUST remain identical!
    current_content = content_svc.get_document_content("CNT-0001")
    assert current_content == original_text


# 11. Revision history tracking
def test_revision_history_regeneration():
    job_resp = client.post("/api/remediation/jobs", json={"document_id": "CNT-0001"})
    rem_id = job_resp.json()["remediation_id"]

    draft_v1 = client.post(f"/api/remediation/jobs/{rem_id}/generate").json()
    assert draft_v1["revision_number"] == 1

    # Request changes on v1
    client.patch(
        f"/api/remediation/revisions/{draft_v1['revision_id']}/review",
        json={"action": "request_changes", "review_note": "Please also clarify receipts window."},
    )

    # Regenerate v2
    regen_resp = client.post(
        f"/api/remediation/revisions/{draft_v1['revision_id']}/regenerate",
        json={"feedback_notes": "Added clarification for receipts window."},
    )
    assert regen_resp.status_code == 200
    draft_v2 = regen_resp.json()
    assert draft_v2["revision_number"] == 2
    assert draft_v2["revision_id"] != draft_v1["revision_id"]

    # Check job history has both revisions
    job_detail = client.get(f"/api/remediation/jobs/{rem_id}").json()
    assert len(job_detail["draft_revisions"]) == 2


# 12 & 13. Approval, rejection, and invalid status transitions
def test_review_status_transitions_and_validations():
    job_resp = client.post("/api/remediation/jobs", json={"document_id": "CNT-0001"})
    rem_id = job_resp.json()["remediation_id"]
    draft = client.post(f"/api/remediation/jobs/{rem_id}/generate").json()
    rev_id = draft["revision_id"]

    # 1. Reject without note should fail (400)
    rej_no_note = client.patch(
        f"/api/remediation/revisions/{rev_id}/review",
        json={"action": "reject", "review_note": ""},
    )
    assert rej_no_note.status_code == 400

    # 2. Reject with valid note succeeds
    rej_valid = client.patch(
        f"/api/remediation/revisions/{rev_id}/review",
        json={"action": "reject", "review_note": "Policy superseded elsewhere; rejected."},
    )
    assert rej_valid.status_code == 200
    assert rej_valid.json()["review_status"] == "rejected"

    # 3. Invalid transition: cannot approve an already rejected revision directly
    invalid_tr = client.patch(
        f"/api/remediation/revisions/{rev_id}/review",
        json={"action": "approve", "review_note": "Trying to approve after rejection"},
    )
    assert invalid_tr.status_code == 400
    assert "terminal status" in invalid_tr.json()["detail"]


# 14. Pagination and filters in list_jobs
def test_list_remediation_jobs_filters():
    resp = client.get("/api/remediation/jobs?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data

    # Filter by document_id
    filtered = client.get("/api/remediation/jobs?document_id=CNT-0001")
    assert filtered.status_code == 200
    for item in filtered.json()["items"]:
        assert "CNT-0001" in item["document_id"]


# 15. Scoring behavior preservation
def test_freshness_score_preserved_after_remediation():
    scoring_svc = get_scoring_service()
    doc_before = scoring_svc.get_scored_document_by_id("CNT-0001")
    score_before = doc_before.calculated_score if doc_before else None

    # Run remediation job
    job_resp = client.post("/api/remediation/jobs", json={"document_id": "CNT-0001"})
    rem_id = job_resp.json()["remediation_id"]
    draft = client.post(f"/api/remediation/jobs/{rem_id}/generate").json()
    client.patch(
        f"/api/remediation/revisions/{draft['revision_id']}/review",
        json={"action": "approve", "review_note": "Approved draft."},
    )

    doc_after = scoring_svc.get_scored_document_by_id("CNT-0001")
    score_after = doc_after.calculated_score if doc_after else None

    # Score MUST NOT be automatically zeroed or artificially lowered
    assert score_before == score_after


# 16. Standalone revision validation endpoint
def test_standalone_validate_endpoint():
    job_resp = client.post("/api/remediation/jobs", json={"document_id": "CNT-0001"})
    rem_id = job_resp.json()["remediation_id"]
    draft = client.post(f"/api/remediation/jobs/{rem_id}/generate").json()
    rev_id = draft["revision_id"]

    val_resp = client.post(f"/api/remediation/revisions/{rev_id}/validate")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert "validation_status" in val_data
    assert "evidence_coverage_percent" in val_data


# 17. Remediation summary KPI endpoint
def test_remediation_summary_endpoint():
    resp = client.get("/api/remediation/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert "total_jobs" in summary
    assert "approved_revisions" in summary
    assert "validation_outcomes" in summary


# 18. Duplicate job handling
def test_duplicate_job_handling():
    resp1 = client.post("/api/remediation/jobs", json={"document_id": "CNT-0001", "remediation_objective": "First pass"})
    assert resp1.status_code == 201
    job1_id = resp1.json()["remediation_id"]

    resp2 = client.post("/api/remediation/jobs", json={"document_id": "CNT-0001", "remediation_objective": "Second pass"})
    assert resp2.status_code == 201
    job2_id = resp2.json()["remediation_id"]

    assert job1_id != job2_id
    # Both jobs exist independently
    j1 = client.get(f"/api/remediation/jobs/{job1_id}").json()
    j2 = client.get(f"/api/remediation/jobs/{job2_id}").json()
    assert j1["plan"]["primary_objective"] == "First pass"
    assert j2["plan"]["primary_objective"] == "Second pass"


# 19. OpenAI API rate limit and timeout handling
def test_openai_api_rate_limit_and_timeout():
    agent = DocumentRevisionAgent(api_key="sk-test-mock-rate-limit")
    plan = RemediationPlan(document_id="CNT-0001", primary_objective="Test timeout", has_sufficient_content=True)

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = TimeoutError("Request timed out after 25s")

        # Must safely catch timeout and fall back to deterministic draft without unhandled crash
        draft = agent.generate_revision(
            remediation_id="REM-TIMEOUT-TEST",
            document_id="CNT-0001",
            original_text="Corporate Travel Policy: Domestic flights capped at a maximum of $450 per flight segment. All expense reimbursement reports must be submitted within 14 calendar days",
            plan=plan,
        )
        assert draft is not None
        assert draft.proposed_content != ""


# 20. Correct linkage between changes and evidence
def test_linkage_between_changes_and_evidence():
    job_resp = client.post("/api/remediation/jobs", json={"document_id": "CNT-0001"})
    rem_id = job_resp.json()["remediation_id"]
    draft = client.post(f"/api/remediation/jobs/{rem_id}/generate").json()

    for chg in draft["changes"]:
        assert chg["original_text"] != ""
        assert chg["proposed_text"] != ""
        assert chg["reason"] != ""
        assert isinstance(chg["supporting_evidence_refs"], list)
        if chg["validation_outcome"] == "supported":
            assert len(chg["supporting_evidence_refs"]) > 0

