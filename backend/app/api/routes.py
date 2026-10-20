import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query

from backend.app.models.dataset import (
    DatasetPreviewResponse,
    DatasetStatusResponse,
    HealthResponse,
)
from backend.app.services.dataset_service import DatasetService, get_dataset_service

logger = logging.getLogger("freshguard.api")
router = APIRouter(prefix="/api", tags=["FreshGuard AI"])


@router.get("/health", response_model=HealthResponse, summary="Backend health check")
def health_check() -> HealthResponse:
    """Return application health status and server metadata."""
    return HealthResponse(
        status="healthy",
        service="FreshGuard AI Backend",
        version="0.1.0",
    )


@router.get(
    "/dataset/status",
    response_model=DatasetStatusResponse,
    summary="Dataset availability and metadata",
)
def get_dataset_status(
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetStatusResponse:
    """
    Check dataset presence, record count, and column schema.
    Returns graceful status without crashing if dataset is missing or malformed.
    """
    return service.get_status()


@router.get(
    "/dataset/preview",
    response_model=DatasetPreviewResponse,
    summary="Preview up to 10 dataset records",
)
def get_dataset_preview(
    limit: Optional[int] = Query(
        default=10,
        ge=1,
        le=10,
        description="Number of records to preview (max 10)",
    ),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetPreviewResponse:
    """
    Returns a limited preview of the initial dataset records (capped at 10),
    along with total records count and column schema.
    """
    return service.get_preview(limit=limit or 10)
