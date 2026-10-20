import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.models.contradiction_models import (
    ContradictionAuditRequest,
    ContradictionFinding,
    ContradictionListResponse,
    ContradictionReviewRequest,
    ContradictionSummaryResponse,
    DocumentContentPayload,
)
from backend.app.services.content_service import get_content_service
from backend.app.services.contradiction_service import get_contradiction_service

logger = logging.getLogger("freshguard.api.contradictions")

contradiction_router = APIRouter(prefix="/api", tags=["Contradiction Detection Agent"])


@router_post := contradiction_router.post(
    "/contradictions/audit",
    response_model=ContradictionSummaryResponse,
    summary="Start an AI contradiction detection audit across candidate document pairs",
)
def trigger_contradiction_audit(request: ContradictionAuditRequest = ContradictionAuditRequest()):
    service = get_contradiction_service()
    try:
        summary = service.run_contradiction_audit(
            document_ids=request.document_ids,
            subject_area=request.subject_area,
            max_comparisons=request.max_comparisons,
            force_reanalysis=request.force_reanalysis,
        )
        return summary
    except Exception as e:
        logger.error(f"Error during contradiction audit execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contradiction audit execution failed: {str(e)}",
        )


@contradiction_router.get(
    "/contradictions/summary",
    response_model=ContradictionSummaryResponse,
    summary="Retrieve aggregate summary of cross-document contradiction findings",
)
def get_contradictions_summary():
    service = get_contradiction_service()
    return service.get_summary()


@contradiction_router.get(
    "/contradictions",
    response_model=ContradictionListResponse,
    summary="Retrieve paginated list of contradiction findings with optional filters",
)
def list_contradictions(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=15, ge=1, le=100, description="Items per page"),
    relationship_type: Optional[str] = Query(default=None, description="Filter by relationship classification"),
    severity: Optional[str] = Query(default=None, description="Filter by severity level"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by review status"),
    document_id: Optional[str] = Query(default=None, description="Filter by associated document ID"),
    subject_area: Optional[str] = Query(default=None, description="Filter by subject area"),
):
    service = get_contradiction_service()
    items, total, total_pages = service.list_findings(
        relationship_type=relationship_type,
        severity=severity,
        status=status_filter,
        document_id=document_id,
        subject_area=subject_area,
        page=page,
        page_size=page_size,
    )

    return ContradictionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@contradiction_router.get(
    "/contradictions/{contradiction_id}",
    response_model=ContradictionFinding,
    summary="Retrieve full detail of a specific contradiction finding",
)
def get_contradiction_detail(contradiction_id: str):
    service = get_contradiction_service()
    finding = service.get_finding(contradiction_id)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contradiction finding '{contradiction_id}' not found.",
        )
    return finding


@contradiction_router.patch(
    "/contradictions/{contradiction_id}/review",
    response_model=ContradictionFinding,
    summary="Review and update the status of a contradiction finding (confirm, dismiss, resolve)",
)
def review_contradiction(contradiction_id: str, request: ContradictionReviewRequest):
    service = get_contradiction_service()
    try:
        updated = service.review_finding(
            contradiction_id=contradiction_id,
            new_status=request.status,
            review_note=request.review_note,
            reviewed_by=request.reviewed_by,
        )
        return updated
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contradiction finding '{contradiction_id}' not found.",
        )
    except Exception as e:
        logger.error(f"Failed to review contradiction {contradiction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update review status: {str(e)}",
        )


# Content ingestion and retrieval endpoints
@contradiction_router.post(
    "/documents/{document_id}/content",
    summary="Ingest or update text content for an enterprise document",
)
def ingest_document_content(document_id: str, payload: DocumentContentPayload):
    content_service = get_content_service()
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text payload cannot be empty.",
        )

    content_service.set_document_content(
        document_id=document_id,
        text=payload.text,
        source=payload.source or "manual_ingestion",
    )

    return {
        "status": "success",
        "document_id": document_id.strip(),
        "characters_stored": len(payload.text.strip()),
        "source": payload.source or "manual_ingestion",
    }


@contradiction_router.get(
    "/documents/{document_id}/content",
    summary="Retrieve stored text content for an enterprise document",
)
def get_document_content(document_id: str):
    content_service = get_content_service()
    text = content_service.get_document_content(document_id)
    if text is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No text content has been ingested for document '{document_id}'.",
        )

    meta = content_service.get_content_metadata(document_id)
    return {
        "document_id": document_id.strip(),
        "has_content": True,
        "character_count": len(text),
        "source": meta.get("source") if meta else "unknown",
        "text_preview": text[:300] + ("..." if len(text) > 300 else ""),
        "full_text": text,
    }
