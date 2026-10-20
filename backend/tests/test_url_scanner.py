import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_inspect_url_valid_page():
    response = client.post(
        "/api/evidence/inspect-url",
        json={"url": "https://example.com", "check_links": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Example Domain" in data["page_title"]
    assert "broken_links_count" in data
    assert "deprecated_tools_count" in data
    assert "metadata_quality_issues_count" in data
    assert 0 <= data["freshness_score"] <= 100


def test_inspect_url_ssrf_blocked():
    response = client.post(
        "/api/evidence/inspect-url",
        json={"url": "http://127.0.0.1:8000/secret", "check_links": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "SSRF Policy Blocked" in data["error_message"]
    assert data["freshness_score"] == 100.0
    assert data["risk_level"] == "Critical"


def test_inspect_url_cloud_metadata_blocked():
    response = client.post(
        "/api/evidence/inspect-url",
        json={"url": "http://169.254.169.254/latest/meta-data", "check_links": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "SSRF Policy Blocked" in data["error_message"]


def test_import_scanned_url_workflow():
    import_payload = {
        "url": "https://wiki.example.com/legacy-runbook",
        "title": "Legacy Server Runbook",
        "platform": "Internal Wiki",
        "subject_area": "IT Ops",
        "author": "Sysadmin",
        "raw_text": "Please use Skype for Business and deploy to CentOS 7 nodes.",
        "has_broken_links": True,
        "mentions_deprecated_tool": True,
    }
    import_res = client.post("/api/evidence/inspect-url/import", json=import_payload)
    assert import_res.status_code == 200
    res_data = import_res.json()
    assert res_data["status"] == "imported"
    doc_id = res_data["document_id"]
    assert doc_id.startswith("CNT-EXT-")

    # Verify document exists in catalog
    doc_res = client.get(f"/api/documents/{doc_id}")
    assert doc_res.status_code == 200
    doc_data = doc_res.json()
    assert doc_data["title"] == "Legacy Server Runbook"
    assert doc_data["mentions_deprecated_tool"] is True

    # Verify text content exists
    content_res = client.get(f"/api/documents/{doc_id}/content")
    assert content_res.status_code == 200
    content_data = content_res.json()
    assert content_data["has_content"] is True
    assert "Skype for Business" in content_data["full_text"]
