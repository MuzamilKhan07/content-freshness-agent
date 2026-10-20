from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.dataset_service import DatasetService, get_dataset_service


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test that /api/health returns 200 OK and expected structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data


def test_dataset_status_with_real_data(client):
    """Test /api/dataset/status with the initialized dataset."""
    response = client.get("/api/dataset/status")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["record_count"] == 200
    assert isinstance(data["columns"], list)
    assert len(data["columns"]) == 15
    assert "content_id" in data["columns"]
    assert "title" in data["columns"]


def test_dataset_preview_limits(client):
    """Test that /api/dataset/preview returns at most 10 records."""
    response = client.get("/api/dataset/preview")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["total_records"] == 200
    assert len(data["preview"]) == 10
    assert data["preview_count"] == 10


def test_dashboard_summary_metrics(client):
    """Test /api/dashboard/summary calculates actual values from CSV."""
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_documents"] == 200
    assert data["distinct_platforms"] == 5
    assert data["distinct_content_types"] == 8
    assert data["deprecated_references"] == 54
    assert data["broken_links"] == 40
    assert len(data["platforms_list"]) == 5
    assert "SharePoint" in data["platforms_list"]
    assert "Confluence" in data["platforms_list"]


def test_dashboard_distributions(client):
    """Test /api/dashboard/distributions returns expected aggregates."""
    response = client.get("/api/dashboard/distributions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["by_platform"]) == 5
    assert len(data["by_content_type"]) == 8
    assert len(data["by_reference_score"]) == 5
    assert "deprecated_tool_references" in data["by_signals"]
    assert data["by_signals"]["deprecated_tool_references"] == 54


def test_documents_pagination(client):
    """Test /api/documents default and custom pagination."""
    # Default page size 20
    res = client.get("/api/documents")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 200
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 10
    assert len(data["items"]) == 20

    # Custom page size
    res2 = client.get("/api/documents?page=2&page_size=15")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["page"] == 2
    assert data2["page_size"] == 15
    assert len(data2["items"]) == 15
    assert data2["total_pages"] == 14


def test_documents_search(client):
    """Test case-insensitive text search."""
    res = client.get("/api/documents?search=SharePoint")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    # Every returned item should match the search term in at least one field
    for item in data["items"]:
        combined = f"{item['content_id']} {item['title']} {item['platform']} {item['content_type']}".lower()
        assert "sharepoint" in combined


def test_documents_filters(client):
    """Test filtering by platform and content type."""
    res = client.get("/api/documents?platform=Confluence&content_type=Process Doc")
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["platform"] == "Confluence"
        assert item["content_type"] == "Process Doc"


def test_documents_sorting(client):
    """Test sorting numeric and text columns."""
    res = client.get("/api/documents?sort_by=page_views_90d&sort_order=desc&page_size=5")
    assert res.status_code == 200
    items = res.json()["items"]
    views = [item["page_views_90d"] for item in items]
    assert views == sorted(views, reverse=True)


def test_documents_invalid_sort_field(client):
    """Test that unsupported sort field returns 400 Bad Request."""
    res = client.get("/api/documents?sort_by=invalid_column_name")
    assert res.status_code == 400
    assert "Unsupported sort field" in res.json()["detail"]


def test_document_detail_lookup(client):
    """Test GET /api/documents/{document_id} with real and unknown IDs."""
    res = client.get("/api/documents/CNT-0001")
    assert res.status_code == 200
    data = res.json()
    assert data["content_id"] == "CNT-0001"
    assert data["title"] == "Sample Content Title #1"
    assert "raw_data" in data

    # 404 for unknown ID
    res404 = client.get("/api/documents/DOES-NOT-EXIST")
    assert res404.status_code == 404
    assert "not found" in res404.json()["detail"].lower()


def test_missing_dataset_graceful_handling():
    """Verify that a missing dataset does not crash the endpoints."""
    non_existent_service = DatasetService(dataset_path=Path("non_existent_file.csv"))
    app.dependency_overrides[get_dataset_service] = lambda: non_existent_service
    test_client = TestClient(app)
    try:
        summary_res = test_client.get("/api/dashboard/summary")
        assert summary_res.status_code == 200
        assert summary_res.json()["total_documents"] == 0

        docs_res = test_client.get("/api/documents")
        assert docs_res.status_code == 200
        assert docs_res.json()["total"] == 0
        assert len(docs_res.json()["items"]) == 0

        detail_res = test_client.get("/api/documents/CNT-0001")
        assert detail_res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_no_secrets_in_responses(client):
    """Verify that neither OpenAI keys nor secrets appear in responses."""
    for path in [
        "/api/health",
        "/api/dataset/status",
        "/api/dashboard/summary",
        "/api/dashboard/distributions",
        "/api/documents",
        "/api/documents/CNT-0001",
    ]:
        response = client.get(path)
        content = response.text.lower()
        assert "sk-" not in content
        assert "openai_api_key" not in content
