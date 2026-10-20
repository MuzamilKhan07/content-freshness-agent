from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RemediationJobStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    DRAFTING = "drafting"
    VALIDATING = "validating"
    READY_FOR_REVIEW = "ready_for_review"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class RevisionReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ChangeRecord(BaseModel):
    """Substantive modification in document text tied to evidence."""
    change_id: str
    original_text: str
    proposed_text: str
    change_type: str = "factual_correction"  # factual_correction, obsolete_removal, policy_update, procedural_update, clarification
    reason: str
    supporting_evidence_refs: List[str] = Field(default_factory=list)
    validation_outcome: str = "supported"
    requires_human_review: bool = False


class ValidationResult(BaseModel):
    """Independent audit validation findings on the generated draft."""
    validation_status: ValidationStatus = ValidationStatus.NOT_RUN
    supported_claims_count: int = 0
    unsupported_claim_findings: List[str] = Field(default_factory=list)
    remaining_contradiction_refs: List[str] = Field(default_factory=list)
    potentially_omitted_requirements: List[str] = Field(default_factory=list)
    evidence_coverage_percent: float = 0.0
    unresolved_questions: List[str] = Field(default_factory=list)
    validation_summary: str = ""
    validated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validation_timestamp: Optional[str] = None
    validator_name: str = "FreshGuard Independent Validator v1.0"

    def model_post_init(self, __context):
        if not self.validation_timestamp:
            self.validation_timestamp = self.validated_at


class RemediationPlan(BaseModel):
    """Structured remediation plan created by Agent A."""
    document_id: str
    primary_objective: str
    findings_to_address: List[str] = Field(default_factory=list)
    required_source_references: List[str] = Field(default_factory=list)
    proposed_changes_outline: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    has_sufficient_content: bool = True
    risk_assessment: str = "low"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DraftRevision(BaseModel):
    """A proposed document revision with change provenance and review status."""
    revision_id: str
    remediation_id: str
    document_id: str
    revision_number: int = 1
    original_content: str
    proposed_content: str
    revision_summary: str
    changes: List[ChangeRecord] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.NOT_RUN
    validation_result: Optional[ValidationResult] = None
    review_status: RevisionReviewStatus = RevisionReviewStatus.PENDING
    review_note: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RemediationJob(BaseModel):
    """Complete lifecycle record of an AI remediation workflow."""
    remediation_id: str
    document_id: str
    document_title: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "Enterprise Knowledge Auditor"
    status: RemediationJobStatus = RemediationJobStatus.CREATED
    original_content_reference: str = "DocumentContentService"
    risk_score_at_creation: Optional[int] = None
    source_evidence_ids: List[str] = Field(default_factory=list)
    source_contradiction_ids: List[str] = Field(default_factory=list)
    plan: Optional[RemediationPlan] = None
    draft_revision_id: Optional[str] = None
    current_revision_id: Optional[str] = None
    draft_revisions: List[DraftRevision] = Field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    error_summary: Optional[str] = None


class CreateRemediationJobRequest(BaseModel):
    """Payload to start a remediation job."""
    document_id: str
    remediation_objective: Optional[str] = None
    source_evidence_ids: Optional[List[str]] = None
    source_contradiction_ids: Optional[List[str]] = None
    focus_sections: Optional[str] = None


class ReviewRevisionRequest(BaseModel):
    """Payload for human reviewer actions."""
    action: str  # approve, reject, request_changes
    review_note: Optional[str] = None
    reviewer_name: Optional[str] = "Human Knowledge Manager"


class RegenerateRevisionRequest(BaseModel):
    """Payload for requesting AI re-draft with feedback."""
    feedback_notes: str
    focus_areas: Optional[List[str]] = None


class RemediationSummaryResponse(BaseModel):
    """Aggregate statistics for remediation workspace."""
    total_jobs: int
    active_jobs: int
    ready_for_review_jobs: int
    approved_revisions: int
    rejected_revisions: int
    changes_requested_revisions: int
    validation_outcomes: Dict[str, int]
    last_activity_timestamp: Optional[str] = None


class RemediationJobListResponse(BaseModel):
    """Paginated list of remediation jobs."""
    items: List[RemediationJob]
    total: int
    page: int
    page_size: int
    total_pages: int
