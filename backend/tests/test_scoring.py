from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.scoring_config import ScoringConfig
from backend.app.main import app
from backend.app.models.scoring_models import RiskLevel, SignalStatus
from backend.app.services.dataset_service import DatasetService
from backend.app.services.scoring_service import ScoringService


@pytest.fixture
def scoring_service():
    """Create a ScoringService with a fixed reference date."""
    config = ScoringConfig(reference_date=date(2026, 10, 20))
    return ScoringService(config=config)


@pytest.fixture
def client():
    return TestClient(app)


def test_document_age_thresholds(scoring_service):
    """Test all document age scoring boundaries."""
    # Age <= 30 days: 0 pts
    sig_fresh = scoring_service.evaluate_age_signal({"last_updated": "2026-10-01"})
    assert sig_fresh.status == SignalStatus.EVALUATED
    assert sig_fresh.actual_points == 0.0

    # 31 - 90 days: 5 pts (e.g. 2026-08-01 is 80 days)
    sig_mild = scoring_service.evaluate_age_signal({"last_updated": "2026-08-01"})
    assert sig_mild.status == SignalStatus.EVALUATED
    assert sig_mild.actual_points == 5.0

    # 91 - 180 days: 12 pts (e.g. 2026-06-01 is 141 days)
    sig_mod = scoring_service.evaluate_age_signal({"last_updated": "2026-06-01"})
    assert sig_mod.status == SignalStatus.EVALUATED
    assert sig_mod.actual_points == 12.0

    # 181 - 365 days: 20 pts (e.g. 2026-01-01 is 292 days)
    sig_stale = scoring_service.evaluate_age_signal({"last_updated": "2026-01-01"})
    assert sig_stale.status == SignalStatus.EVALUATED
    assert sig_stale.actual_points == 20.0

    # > 365 days: 30 pts (e.g. 2024-05-01)
    sig_crit = scoring_service.evaluate_age_signal({"last_updated": "2024-05-01"})
    assert sig_crit.status == SignalStatus.EVALUATED
    assert sig_crit.actual_points == 30.0


def test_missing_dates_and_fallback(scoring_service):
    """Test fallback from last_updated to last_reviewed, and unknown when all missing."""
    # last_updated missing, last_reviewed present
    row_fallback = {"last_updated": "", "last_reviewed": "2026-09-01"}
    sig_fallback = scoring_service.evaluate_age_signal(row_fallback)
    assert sig_fallback.status == SignalStatus.EVALUATED
    assert "last_reviewed" in sig_fallback.evidence

    # All dates missing
    row_empty = {"last_updated": "", "last_reviewed": "", "created_date": ""}
    sig_unknown = scoring_service.evaluate_age_signal(row_empty)
    assert sig_unknown.status == SignalStatus.UNKNOWN
    assert sig_unknown.actual_points is None


def test_broken_links_scoring(scoring_service):
    """Test broken links scoring: clean, confirmed, and missing."""
    # Clean check
    clean_sig = scoring_service.evaluate_broken_links_signal({"has_broken_links": False})
    assert clean_sig.status == SignalStatus.EVALUATED
    assert clean_sig.actual_points == 0.0

    # Confirmed broken links
    broken_sig = scoring_service.evaluate_broken_links_signal({"has_broken_links": "True"})
    assert broken_sig.status == SignalStatus.EVALUATED
    assert broken_sig.actual_points == 20.0

    # Missing link data
    unknown_sig = scoring_service.evaluate_broken_links_signal({"has_broken_links": None})
    assert unknown_sig.status == SignalStatus.UNKNOWN
    assert unknown_sig.actual_points is None


def test_deprecated_tools_scoring(scoring_service):
    """Test deprecated tool scoring: clean, confirmed, and missing."""
    clean_sig = scoring_service.evaluate_deprecated_tools_signal({"mentions_deprecated_tool": False})
    assert clean_sig.status == SignalStatus.EVALUATED
    assert clean_sig.actual_points == 0.0

    dep_sig = scoring_service.evaluate_deprecated_tools_signal({"mentions_deprecated_tool": "True"})
    assert dep_sig.status == SignalStatus.EVALUATED
    assert dep_sig.actual_points == 20.0

    unknown_sig = scoring_service.evaluate_deprecated_tools_signal({})
    assert unknown_sig.status == SignalStatus.UNKNOWN
    assert unknown_sig.actual_points is None


def test_contradictions_and_view_trend_unknown_by_default(scoring_service):
    """Test that contradictions and single-window view counts are marked unknown by default."""
    row = {"content_id": "CNT-0001", "page_views_90d": "1500"}
    sig_contra = scoring_service.evaluate_contradictions_signal(row)
    assert sig_contra.status == SignalStatus.UNKNOWN
    assert sig_contra.actual_points is None

    sig_views = scoring_service.evaluate_views_trend_signal(row)
    assert sig_views.status == SignalStatus.UNKNOWN
    assert sig_views.actual_points is None


def test_provisional_score_and_evidence_coverage(scoring_service):
    """Test normalized provisional score calculation with partial evidence."""
    # Document has age (30 pts), clean links (0 pts), clean tools (0 pts).
    # Evaluated weights = 30 + 25 + 20 = 75. Contradictions (15) and views (10) are unknown.
    row = {
        "content_id": "TEST-01",
        "title": "Test Doc",
        "last_updated": "2024-01-01",  # > 365 days -> 30 pts
        "has_broken_links": "False",    # 0 pts
        "mentions_deprecated_tool": "False",  # 0 pts
    }
    scored = scoring_service.score_document(row)
    assert scored.is_provisional is True
    assert scored.score_status == "provisional"
    assert scored.evidence_coverage == 75.0
    # earned = 30, evaluated_max = 75 -> raw_score = (30/75)*100 = 40.0
    assert scored.calculated_score == 40
    assert scored.risk_level == RiskLevel.MODERATE


def test_high_risk_document_scoring(scoring_service):
    """Test document with stale age, broken links, and deprecated tools reaches Critical risk."""
    row = {
        "content_id": "TEST-CRIT",
        "title": "Critical Stale Doc",
        "last_updated": "2024-01-01",  # 30 pts
        "has_broken_links": "True",    # 20 pts
        "mentions_deprecated_tool": "True",  # 20 pts
    }
    scored = scoring_service.score_document(row)
    # earned = 30 + 20 + 20 = 70. evaluated_max = 75.
    # raw_score = (70/75) * 100 = 93.33 -> 93
    assert scored.calculated_score == 93
    assert scored.risk_level == RiskLevel.CRITICAL
    assert scored.priority_rank == 1  # Critical with strong evidence (75% >= 70%)


def test_document_with_zero_signals(scoring_service):
    """Test behavior when a document has zero evaluatable signals."""
    row = {
        "content_id": "TEST-EMPTY",
        "title": "Empty Signals Doc",
        "last_updated": "",
        "has_broken_links": None,
        "mentions_deprecated_tool": None,
    }
    scored = scoring_service.score_document(row)
    assert scored.calculated_score is None
    assert scored.evidence_coverage == 0.0
    assert scored.score_status == "unavailable"
    assert scored.risk_level == RiskLevel.INSUFFICIENT_EVIDENCE
    assert scored.priority_rank == 6


def test_audit_run_and_summary_endpoint(client):
    """Test POST /api/audit/run and GET /api/audit/summary."""
    run_res = client.post("/api/audit/run")
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "completed"
    assert run_data["documents_evaluated"] == 200

    sum_res = client.get("/api/audit/summary")
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["total_documents"] == 200
    assert summary["scored_documents"] == 200
    assert summary["broken_link_documents"] == 40
    assert summary["deprecated_tool_documents"] == 54
    assert "Critical" in summary["risk_distribution"]
    assert "High" in summary["risk_distribution"]
    assert "Moderate" in summary["risk_distribution"]
    assert "Low" in summary["risk_distribution"]


def test_audit_documents_pagination_and_filters(client):
    """Test GET /api/audit/documents pagination, filtering, and sorting."""
    # Default paginated response
    res = client.get("/api/audit/documents?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 200
    assert len(data["items"]) == 10
    assert data["total_pages"] == 20

    # Priority order: top item should have priority_rank 1 or 2
    first_item = data["items"][0]
    assert first_item["priority_rank"] in (1, 2)
    assert "signal_breakdown" in first_item

    # Filter by risk level
    crit_res = client.get("/api/audit/documents?risk_level=Critical")
    assert crit_res.status_code == 200
    for item in crit_res.json()["items"]:
        assert item["risk_level"] == "Critical"

    # Search filter
    search_res = client.get("/api/audit/documents?search=SharePoint")
    assert search_res.status_code == 200
    assert search_res.json()["total"] > 0


def test_audit_document_detail_and_404(client):
    """Test GET /api/audit/documents/{id}."""
    res = client.get("/api/audit/documents/CNT-0001")
    assert res.status_code == 200
    data = res.json()
    assert data["content_id"] == "CNT-0001"
    assert "signal_breakdown" in data
    assert "document_age" in data["signal_breakdown"]
    assert "broken_links" in data["signal_breakdown"]
    assert "deprecated_tools" in data["signal_breakdown"]
    assert "evidence_coverage" in data

    # 404 for unknown document
    res_404 = client.get("/api/audit/documents/NON-EXISTENT-ID")
    assert res_404.status_code == 404
