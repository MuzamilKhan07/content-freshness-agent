from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContradictionRelationship(str, Enum):
    CONTRADICTION = "contradiction"
    SUPERSESSION = "supersession"
    COMPLEMENTARY = "complementary"
    SCOPE_DIFFERENCE = "scope_difference"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ContradictionSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecencyAssessment(str, Enum):
    NEWER_DOCUMENT_LIKELY_AUTHORITATIVE = "newer_document_likely_authoritative"
    OLDER_DOCUMENT_EXPLICITLY_SUPERSEDED = "older_document_explicitly_superseded"
    AUTHORITY_UNCLEAR = "authority_unclear"
    DATES_UNAVAILABLE = "dates_unavailable"


class ContradictionReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class ExtractedClaim(BaseModel):
    """Structured claim extracted from a document."""
    claim_id: str
    document_id: str
    claim_text: str
    claim_type: str = "policy_rule"  # procedure_step, policy_rule, approval_requirement, numerical_limit, tool_requirement
    subject_entity: str
    predicate: str
    constraint_or_value: str
    supporting_excerpt: str
    source_location: Optional[str] = None
    is_explicit: bool = True


class ContradictionFinding(BaseModel):
    """Complete contradiction finding linking two documents."""
    contradiction_id: str
    audit_id: str
    document_a_id: str
    document_b_id: str
    document_a_title: str
    document_b_title: str
    claim_a: str
    claim_b: str
    relationship_type: ContradictionRelationship
    explanation: str
    supporting_excerpt_a: str
    supporting_excerpt_b: str
    source_location_a: Optional[str] = None
    source_location_b: Optional[str] = None
    severity: ContradictionSeverity = ContradictionSeverity.MEDIUM
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    recency_assessment: RecencyAssessment = RecencyAssessment.AUTHORITY_UNCLEAR
    recommended_action: str
    status: ContradictionReviewStatus = ContradictionReviewStatus.PENDING_REVIEW
    review_note: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    subject_area: Optional[str] = None
    model_name: Optional[str] = None


class ContradictionAuditRequest(BaseModel):
    """Request parameters for running contradiction audit."""
    document_ids: Optional[List[str]] = None
    subject_area: Optional[str] = None
    max_comparisons: int = Field(default=20, ge=1, le=100)
    force_reanalysis: bool = False


class ContradictionSummaryResponse(BaseModel):
    """High-level summary of contradiction audit findings."""
    total_pairs_analyzed: int
    total_findings: int
    confirmed_contradictions: int
    pending_review_findings: int
    dismissed_findings: int
    resolved_findings: int
    findings_by_severity: Dict[str, int]
    documents_with_active_contradictions: int
    analysis_failures: int
    last_audit_timestamp: Optional[str] = None


class ContradictionListResponse(BaseModel):
    """Paginated response for contradiction findings."""
    items: List[ContradictionFinding]
    total: number if False else int
    page: int
    page_size: int
    total_pages: int


class ContradictionReviewRequest(BaseModel):
    """Request payload for updating review status."""
    status: ContradictionReviewStatus
    review_note: Optional[str] = None
    reviewed_by: Optional[str] = "Human Knowledge Auditor"


class DocumentContentPayload(BaseModel):
    """Payload for ingesting document text."""
    text: str
    source: Optional[str] = "manual_ingestion"
