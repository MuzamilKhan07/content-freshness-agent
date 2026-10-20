from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceStatus(str, Enum):
    CONFIRMED = "confirmed"
    SUSPECTED = "suspected"
    UNKNOWN = "unknown"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class EvidenceSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INFO = "info"


class SignalType(str, Enum):
    DOCUMENT_AGE = "document_age"
    BROKEN_LINKS = "broken_links"
    DEPRECATED_TOOLS = "deprecated_tools"
    METADATA_QUALITY = "metadata_quality"
    URL_VERIFICATION = "url_verification"
    CONTRADICTIONS = "contradictions"


class EvidenceItem(BaseModel):
    """Normalized structured evidence record produced by investigative tools."""
    evidence_id: str = Field(..., description="Unique evidence identifier")
    document_id: str = Field(..., description="Associated document identifier")
    signal_type: SignalType = Field(..., description="Category of signal being evaluated")
    status: EvidenceStatus = Field(..., description="Evaluation confidence / status")
    severity: EvidenceSeverity = Field(..., description="Severity of the detected finding")
    summary: str = Field(..., description="Concise plain-language finding explanation")
    source_field: str = Field(..., description="CSV column or input source investigated")
    observed_value: Optional[str] = Field(default=None, description="Actual observed value safely formatted")
    evidence_reference: Optional[str] = Field(default=None, description="Traceable rule ID, HTTP URL, or telemetry key")
    detected_at: str = Field(..., description="ISO detection timestamp")
    tool_name: str = Field(..., description="Tool or agent component that produced the finding")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Calibrated confidence level")
    recommended_action: str = Field(..., description="Immediate next step recommended by the evidence")


class EvidenceAuditRequest(BaseModel):
    """Parameters for initiating an evidence collection audit run."""
    document_ids: Optional[List[str]] = Field(default=None, description="Explicit list of document IDs to audit (all if None)")
    max_documents: Optional[int] = Field(default=None, ge=1, le=500, description="Cap on documents evaluated")
    enabled_checks: Optional[List[str]] = Field(
        default=["metadata_inspection", "url_verification", "deprecated_tools", "metadata_quality"],
        description="List of verification tools to run",
    )
    custom_urls: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional mapping of document_id -> target URL to safely verify",
    )


class EvidenceSummaryResponse(BaseModel):
    """Summary metrics of evidence gathered across documents."""
    documents_inspected: int = Field(default=0)
    checks_attempted: int = Field(default=0)
    confirmed_findings: int = Field(default=0)
    suspected_findings: int = Field(default=0)
    unknown_signals: int = Field(default=0)
    failed_checks: int = Field(default=0)
    broken_link_findings: int = Field(default=0)
    deprecated_reference_findings: int = Field(default=0)
    metadata_quality_findings: int = Field(default=0)
    audit_start_timestamp: str = Field(...)
    audit_completed_timestamp: str = Field(...)


class EvidenceDocumentResponse(BaseModel):
    """All evidence items associated with a specific document."""
    document_id: str = Field(...)
    title: str = Field(...)
    evidence_count: int = Field(...)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)


class EvidenceFindingListResponse(BaseModel):
    """Paginated list of individual evidence findings."""
    items: List[EvidenceItem] = Field(...)
    total: int = Field(...)
    page: int = Field(...)
    page_size: int = Field(...)
    total_pages: int = Field(...)


class EvidenceAuditRecord(BaseModel):
    """Historical audit run record."""
    audit_id: str = Field(...)
    status: str = Field(default="completed")
    start_time: str = Field(...)
    completion_time: str = Field(...)
    document_ids: List[str] = Field(default_factory=list)
    checks_performed: List[str] = Field(default_factory=list)
    summary: EvidenceSummaryResponse = Field(...)
    total_evidence_produced: int = Field(default=0)
