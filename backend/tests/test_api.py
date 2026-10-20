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
    assert len(data["columns"]) > 0
    # Expected key columns in ps11_content_inventory.csv
    assert "content_id" in data["columns"]
    assert "title" in data["columns"]
    assert "staleness_score" in data["columns"]
    assert "recommended_action" in data["columns"]


def test_dataset_preview_limits(client):
    """Test that /api/dataset/preview returns at most 10 records and correct summary."""
    response = client.get("/api/dataset/preview")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["total_records"] == 200
    assert len(data["preview"]) == 10
    assert data["preview_count"] == 10
    assert isinstance(data["columns"], list)

    # Verify first record fields
    first_record = data["preview"][0]
    assert "content_id" in first_record
    assert "title" in first_record
    assert first_record["content_id"] == "CNT-0001"


def test_missing_dataset_graceful_handling():
    """Verify that a missing dataset returns available=False and does not crash."""
    non_existent_service = DatasetService(dataset_path=Path("non_existent_file.csv"))
    
    # Override dependency
    app.dependency_overrides[get_dataset_service] = lambda: non_existent_service
    client = TestClient(app)
    try:
        status_res = client.get("/api/dataset/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["available"] is False
        assert status_data["record_count"] == 0
        assert len(status_data["warnings"]) > 0

        preview_res = client.get("/api/dataset/preview")
        assert preview_res.status_code == 200
        preview_data = preview_res.json()
        assert preview_data["available"] is False
        assert preview_data["total_records"] == 0
        assert len(preview_data["preview"]) == 0
    finally:
        app.dependency_overrides.clear()


def test_no_secrets_in_responses(client):
    """Verify that neither OpenAI keys nor secrets appear in responses."""
    for path in ["/api/health", "/api/dataset/status", "/api/dataset/preview"]:
        response = client.get(path)
        content = response.text.lower()
        assert "sk-" not in content
        assert "openai_api_key" not in content
        assert "api_key" not in content
