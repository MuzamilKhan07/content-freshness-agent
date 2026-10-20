import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Path, Query, status

from backend.app.models.remediation_models import (
    CreateRemediationJobRequest,
    DraftRevision,
    RegenerateRevisionRequest,
    RemediationJob,
    RemediationJobListResponse,
    RemediationSummaryResponse,
    ReviewRevisionRequest,
    ValidationResult,
)
from backend.app.services.remediation_service import get_remediation_service

logger = logging.getLogger("freshguard.api.remediation")

remediation_router = APIRouter(prefix="/api/remediation", tags=["AI Remediation Agents"])


@remediation_router.post(
    "/jobs",
    response_model=RemediationJob,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new remediation job for a document",
)
def create_remediation_job(request: CreateRemediationJobRequest) -> RemediationJob:
    """
    Initialize a structured remediation job for an enterprise document.
    Validates document existence and any referenced contradiction or evidence IDs.
    """
    service = get_remediation_service()
    try:
        job = service.create_job(
            document_id=request.document_id,
            remediation_objective=request.remediation_objective,
            source_evidence_ids=request.source_evidence_ids,
            source_contradiction_ids=request.source_contradiction_ids,
            focus_sections=request.focus_sections,
        )
        return job
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Failed to create remediation job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create remediation job: {str(e)}",
        )


@remediation_router.post(
    "/jobs/{remediation_id}/generate",
    response_model=DraftRevision,
    summary="Generate evidence-grounded document revision draft",
)
def generate_remediation_draft(
    remediation_id: str = Path(..., description="Remediation job ID (e.g. REM-CNT-0001-XXXX)"),
) -> DraftRevision:
    """
    Execute Agent B (Revision Agent) and Agent C (Validation Agent) to produce
    a validated document revision proposal with granular change records.
    """
    service = get_remediation_service()
    try:
        draft = service.generate_draft_for_job(remediation_id)
        return draft
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Remediation job '{remediation_id}' not found.",
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Failed to generate draft for job {remediation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Revision generation failed: {str(e)}",
        )


@remediation_router.post(
    "/revisions/{revision_id}/validate",
    response_model=ValidationResult,
    summary="Run independent validation audit on a proposed revision",
)
def validate_revision(
    revision_id: str = Path(..., description="Draft revision ID (e.g. REV-CNT-0001-1-XXXX)"),
) -> ValidationResult:
    """
    Execute Agent C (Validation Agent) to independently verify claims, check for
    omitted requirements, detect remaining active contradictions, and calculate validation status.
    """
    service = get_remediation_service()
    try:
        val_result = service.validate_revision_independently(revision_id)
        return val_result
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Revision '{revision_id}' not found.",
        )
    except Exception as e:
        logger.error(f"Failed to validate revision {revision_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )


@remediation_router.get(
    "/jobs",
    response_model=RemediationJobListResponse,
    summary="List paginated remediation jobs with filters",
)
def list_remediation_jobs(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=15, ge=1, le=100, description="Items per page"),
    document_id: Optional[str] = Query(default=None, description="Filter by target document ID"),
    status: Optional[str] = Query(default=None, description="Filter by job status"),
    validation_status: Optional[str] = Query(default=None, description="Filter by validation outcome"),
    review_status: Optional[str] = Query(default=None, description="Filter by review status"),
) -> RemediationJobListResponse:
    """Retrieve paginated remediation jobs with multi-attribute filtering."""
    service = get_remediation_service()
    items, total, total_pages = service.list_jobs(
        document_id=document_id,
        status=status,
        validation_status=validation_status,
        review_status=review_status,
        page=page,
        page_size=page_size,
    )
    return RemediationJobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@remediation_router.get(
    "/summary",
    response_model=RemediationSummaryResponse,
    summary="Retrieve remediation queue KPIs and aggregate stats",
)
def get_remediation_summary() -> RemediationSummaryResponse:
    """Retrieve aggregate summary metrics across all remediation jobs and revisions."""
    service = get_remediation_service()
    return service.get_summary()


@remediation_router.get(
    "/jobs/{remediation_id}",
    response_model=RemediationJob,
    summary="Retrieve single remediation job details",
)
def get_remediation_job(
    remediation_id: str = Path(..., description="Remediation job ID"),
) -> RemediationJob:
    """Retrieve complete remediation job record including plan, current draft, and validation result."""
    service = get_remediation_service()
    job = service.get_job(remediation_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Remediation job '{remediation_id}' not found.",
        )
    return job


@remediation_router.get(
    "/revisions/{revision_id}",
    response_model=DraftRevision,
    summary="Retrieve single draft revision with side-by-side data and changes",
)
def get_draft_revision(
    revision_id: str = Path(..., description="Draft revision ID"),
) -> DraftRevision:
    """Retrieve full revision proposal, original text, change provenance records, and validation outcome."""
    service = get_remediation_service()
    rev = service.get_revision(revision_id)
    if not rev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft revision '{revision_id}' not found.",
        )
    return rev


@remediation_router.patch(
    "/revisions/{revision_id}/review",
    response_model=DraftRevision,
    summary="Review draft revision (approve, reject, request_changes)",
)
def review_draft_revision(
    revision_id: str = Path(..., description="Draft revision ID"),
    payload: ReviewRevisionRequest = ...,
) -> DraftRevision:
    """
    Record human reviewer decision on a proposed document revision.
    Requires review notes when rejecting or requesting changes.
    Does NOT overwrite the original document or source CSV.
    """
    service = get_remediation_service()
    try:
        updated = service.review_revision(
            revision_id=revision_id,
            action=payload.action,
            review_note=payload.review_note,
            reviewer_name=payload.reviewer_name or "Human Knowledge Manager",
        )
        return updated
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Revision '{revision_id}' not found.",
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Failed to record review for revision {revision_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record review: {str(e)}",
        )


@remediation_router.post(
    "/revisions/{revision_id}/regenerate",
    response_model=DraftRevision,
    summary="Regenerate revision proposal incorporating human auditor feedback",
)
def regenerate_draft_revision(
    revision_id: str = Path(..., description="Draft revision ID to regenerate"),
    payload: RegenerateRevisionRequest = ...,
) -> DraftRevision:
    """
    Generate a new draft revision incorporating specific human feedback while
    preserving previous revisions and complete audit history.
    """
    service = get_remediation_service()
    try:
        new_draft = service.regenerate_revision_with_feedback(
            revision_id=revision_id,
            feedback_notes=payload.feedback_notes,
            focus_areas=payload.focus_areas,
        )
        return new_draft
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Revision '{revision_id}' not found.",
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.error(f"Failed to regenerate revision {revision_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate revision: {str(e)}",
        )
