import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from backend.app.models.evidence_models import (
    EvidenceAuditRecord,
    EvidenceAuditRequest,
    EvidenceDocumentResponse,
    EvidenceFindingListResponse,
    EvidenceSummaryResponse,
)
from backend.app.services.evidence_service import (
    EvidenceCollectionOrchestrator,
    get_evidence_orchestrator,
)

logger = logging.getLogger("freshguard.evidence_api")
router = APIRouter(prefix="/api/evidence", tags=["Evidence Collection Agent"])


@router.post(
    "/audit",
    response_model=EvidenceAuditRecord,
    summary="Execute evidence collection audit",
)
def run_evidence_audit(
    request: Optional[EvidenceAuditRequest] = None,
    orchestrator: EvidenceCollectionOrchestrator = Depends(get_evidence_orchestrator),
) -> EvidenceAuditRecord:
    """
    Start an evidence collection audit across eligible documents using verification tools.
    Updates the Phase 3 scoring engine with verified findings.
    """
    return orchestrator.run_evidence_audit(request or EvidenceAuditRequest())


@router.get(
    "/summary",
    response_model=EvidenceSummaryResponse,
    summary="Evidence audit summary metrics",
)
def get_evidence_summary(
    orchestrator: EvidenceCollectionOrchestrator = Depends(get_evidence_orchestrator),
) -> EvidenceSummaryResponse:
    """Retrieve aggregate summary counts of checks attempted and evidence gathered."""
    return orchestrator.get_evidence_summary()


@router.get(
    "/documents/{document_id}",
    response_model=EvidenceDocumentResponse,
    summary="Evidence items for a specific document",
)
def get_document_evidence(
    document_id: str = Path(..., description="Document content identifier (e.g., CNT-0001)"),
    orchestrator: EvidenceCollectionOrchestrator = Depends(get_evidence_orchestrator),
) -> EvidenceDocumentResponse:
    """Retrieve all structured evidence items gathered for a specific document."""
    return orchestrator.get_document_evidence(document_id)


@router.get(
    "/findings",
    response_model=EvidenceFindingListResponse,
    summary="Paginated evidence findings catalog",
)
def list_evidence_findings(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Findings per page"),
    status: Optional[str] = Query(default=None, description="Filter by status: confirmed, suspected, unknown, failed"),
    signal_type: Optional[str] = Query(default=None, description="Filter by signal type"),
    severity: Optional[str] = Query(default=None, description="Filter by severity: critical, high, moderate, low, info"),
    document_id: Optional[str] = Query(default=None, description="Filter by document ID"),
    orchestrator: EvidenceCollectionOrchestrator = Depends(get_evidence_orchestrator),
) -> EvidenceFindingListResponse:
    """Query paginated individual evidence records with status and signal filters."""
    return orchestrator.get_findings(
        page=page,
        page_size=page_size,
        status=status,
        signal_type=signal_type,
        severity=severity,
        document_id=document_id,
    )


@router.get(
    "/audits/{audit_id}",
    response_model=EvidenceAuditRecord,
    summary="Lookup specific audit run record",
)
def get_audit_record(
    audit_id: str = Path(..., description="Audit run identifier (e.g., AUDIT-12345678)"),
    orchestrator: EvidenceCollectionOrchestrator = Depends(get_evidence_orchestrator),
) -> EvidenceAuditRecord:
    """Retrieve audit history and tool summary for a given audit execution."""
    record = orchestrator.get_audit_by_id(audit_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Audit execution with ID '{audit_id}' was not found in audit history.",
        )
    return record
