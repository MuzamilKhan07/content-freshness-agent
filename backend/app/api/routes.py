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
from backend.app.models.scoring_models import (
    AuditDocumentListResponse,
    AuditRunResponse,
    AuditSummaryResponse,
    ScoredDocument,
)
from backend.app.services.dataset_service import DatasetService, get_dataset_service
from backend.app.services.scoring_service import ScoringService, get_scoring_service

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


# --------------------------------------------------------------------------
# Phase 3 Audit & Explainable Freshness Scoring Endpoints
# --------------------------------------------------------------------------


@router.get(
    "/audit/summary",
    response_model=AuditSummaryResponse,
    summary="Audit risk summary and KPI overview",
)
def get_audit_summary(
    scoring_svc: ScoringService = Depends(get_scoring_service),
) -> AuditSummaryResponse:
    """Return high-level audit summary, risk level counts, and evidence completeness stats."""
    return scoring_svc.get_audit_summary()


@router.get(
    "/audit/documents",
    response_model=AuditDocumentListResponse,
    summary="Prioritized scored documents queue",
)
def get_audit_documents(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Records per page"),
    search: Optional[str] = Query(default=None, description="Search across title, content_id, domain, author"),
    risk_level: Optional[str] = Query(default=None, description="Filter by RiskLevel (Critical, High, Moderate, Low, etc.)"),
    min_score: Optional[int] = Query(default=None, ge=0, le=100, description="Minimum freshness risk score"),
    max_score: Optional[int] = Query(default=None, ge=0, le=100, description="Maximum freshness risk score"),
    sort_by: Optional[str] = Query(default="priority", description="Sort field: priority | score | title | content_id | last_updated"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$", description="Sort direction"),
    evidence_status: Optional[str] = Query(default=None, description="Filter: provisional | fully_evaluated | insufficient_evidence"),
    scoring_svc: ScoringService = Depends(get_scoring_service),
) -> AuditDocumentListResponse:
    """Return paginated list of scored documents ordered deterministically by remediation priority."""
    return scoring_svc.get_scored_documents(
        page=page,
        page_size=page_size,
        search=search,
        risk_level=risk_level,
        min_score=min_score,
        max_score=max_score,
        sort_by=sort_by,
        sort_order=sort_order,
        evidence_status=evidence_status,
    )


@router.get(
    "/audit/documents/{document_id}",
    response_model=ScoredDocument,
    summary="Detailed scoring explanation for a document",
)
def get_audit_document_detail(
    document_id: str = Path(..., description="Document content identifier (e.g., CNT-0001)"),
    scoring_svc: ScoringService = Depends(get_scoring_service),
) -> ScoredDocument:
    """Return complete signal breakdown, evidence, earned points, and recommendation for a document."""
    doc = scoring_svc.get_scored_document_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Scored document with ID '{document_id}' was not found in audit results.",
        )
    return doc


@router.post(
    "/audit/run",
    response_model=AuditRunResponse,
    summary="Trigger freshness audit run",
)
def trigger_audit_run(
    scoring_svc: ScoringService = Depends(get_scoring_service),
) -> AuditRunResponse:
    """Execute full deterministic freshness audit and return completed run summary."""
    docs, summary = scoring_svc.run_audit()
    return AuditRunResponse(
        status="completed",
        documents_evaluated=len(docs),
        timestamp=summary.last_audit_timestamp,
        summary=summary,
    )
