import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from backend.app.models.dataset import (
    DashboardDistributionsResponse,
    DashboardSummaryResponse,
    DatasetPreviewResponse,
    DatasetStatusResponse,
    DocumentListResponse,
    DocumentRecord,
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
    """Check dataset presence, record count, and column schema."""
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
    """Return a preview of initial dataset records (capped at 10)."""
    return service.get_preview(limit=limit or 10)


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="Paginated document inventory",
)
def list_documents(
    page: int = Query(default=1, ge=1, description="Page number, 1-indexed"),
    page_size: int = Query(default=20, ge=1, le=100, description="Records per page (max 100)"),
    search: Optional[str] = Query(default=None, description="Case-insensitive text search"),
    platform: Optional[str] = Query(default=None, description="Filter by source platform"),
    content_type: Optional[str] = Query(default=None, description="Filter by content type"),
    status: Optional[str] = Query(default=None, description="Filter by status / recommended action"),
    sort_by: Optional[str] = Query(default=None, description="Field to sort by"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$", description="Sort direction (asc/desc)"),
    service: DatasetService = Depends(get_dataset_service),
) -> DocumentListResponse:
    """
    Retrieve paginated knowledge base documents with search, filtering, and sorting.
    """
    try:
        return service.get_documents(
            page=page,
            page_size=page_size,
            search=search,
            platform=platform,
            content_type=content_type,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))


@router.get(
    "/documents/{document_id}",
    response_model=DocumentRecord,
    summary="Get single document details",
)
def get_document(
    document_id: str = Path(..., description="Document content identifier (e.g., CNT-0001)"),
    service: DatasetService = Depends(get_dataset_service),
) -> DocumentRecord:
    """Retrieve complete metadata for a specific document identifier."""
    doc = service.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document with identifier '{document_id}' was not found in the inventory.",
        )
    return doc


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard KPIs overview",
)
def get_dashboard_summary(
    service: DatasetService = Depends(get_dataset_service),
) -> DashboardSummaryResponse:
    """Retrieve high-level enterprise dashboard metrics calculated directly from records."""
    return service.get_dashboard_summary()


@router.get(
    "/dashboard/distributions",
    response_model=DashboardDistributionsResponse,
    summary="Dashboard distribution metrics",
)
def get_dashboard_distributions(
    service: DatasetService = Depends(get_dataset_service),
) -> DashboardDistributionsResponse:
    """Retrieve aggregate distributions for visual cards and charts."""
    return service.get_dashboard_distributions()
