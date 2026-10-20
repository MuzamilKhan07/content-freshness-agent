from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SignalStatus(str, Enum):
    EVALUATED = "evaluated"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    FAILED = "failed"


class RiskLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"
    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"


class SignalScoreDetail(BaseModel):
    """Detailed explainable breakdown for a single scoring signal."""
    signal_name: str = Field(..., description="Unique signal identifier")
    display_name: str = Field(..., description="Human-readable signal title")
    status: SignalStatus = Field(..., description="Evaluation status")
    max_points: float = Field(..., description="Maximum possible weighted points")
    actual_points: Optional[float] = Field(default=None, description="Earned risk points if evaluated")
    evidence: str = Field(..., description="Concrete factual evidence used")
    explanation: str = Field(..., description="Plain-language justification of score")
    evaluation_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of check")


class ScoredDocument(BaseModel):
    """Document record enriched with calculated freshness-risk score and prioritization."""
    content_id: str = Field(..., description="Unique document ID")
    title: str = Field(..., description="Document title")
    platform: str = Field(..., description="Source platform")
    content_type: str = Field(..., description="Content format / classification")
    subject_area: Optional[str] = Field(default=None, description="Subject domain")
    author: Optional[str] = Field(default=None, description="Author / owner")
    last_updated: Optional[str] = Field(default=None, description="Last update timestamp")
    last_reviewed: Optional[str] = Field(default=None, description="Last review timestamp")

    # Calculated scoring outputs
    calculated_score: Optional[int] = Field(default=None, description="Final freshness-risk score (0-100)")
    raw_score: float = Field(default=0.0, description="Precise unrounded score")
    earned_points: float = Field(default=0.0, description="Sum of points from evaluated signals")
    evaluated_max_points: float = Field(default=0.0, description="Sum of maximum points for evaluated signals")
    evidence_coverage: float = Field(default=0.0, description="Evidence completeness percentage (0-100%)")
    is_provisional: bool = Field(default=True, description="True if evidence is incomplete (<100%)")
    score_status: str = Field(default="provisional", description="provisional | fully_evaluated | insufficient_evidence")
    risk_level: RiskLevel = Field(..., description="Risk categorization")

    # Prioritization and explanations
    priority_rank: int = Field(..., description="Deterministic priority ordering (1 is highest)")
    priority_label: str = Field(..., description="Human-friendly priority description")
    priority_explanation: str = Field(..., description="Specific reason for assigned remediation priority")
    top_contributing_factors: List[str] = Field(default_factory=list, description="Primary drivers of risk score")
    recommended_action: str = Field(..., description="Actionable recommendation based on triggered evidence")

    # Granular signal details
    signal_breakdown: Dict[str, SignalScoreDetail] = Field(default_factory=dict)

    # Reference values preserved from CSV
    reference_staleness_score: Optional[float] = Field(default=None, description="Original baseline score from CSV")
    source_recommended_action: Optional[str] = Field(default=None, description="Original recommendation from CSV")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw source record fields")


class AuditSummaryResponse(BaseModel):
    """High-level risk analytics and score distributions."""
    total_documents: int = Field(..., description="Total documents in inventory")
    scored_documents: int = Field(..., description="Documents successfully evaluated")
    provisional_scores_count: int = Field(..., description="Documents with provisional/partial score")
    insufficient_evidence_count: int = Field(..., description="Documents with insufficient signals")
    risk_distribution: Dict[str, int] = Field(..., description="Counts per RiskLevel category")
    broken_link_documents: int = Field(..., description="Documents with confirmed broken links")
    deprecated_tool_documents: int = Field(..., description="Documents referencing retired tools")
    unknown_signals_count: int = Field(..., description="Count of unevaluated signal instances across dataset")
    average_risk_score: float = Field(default=0.0, description="Average calculated risk score across inventory")
    last_audit_timestamp: str = Field(..., description="Audit completion timestamp")


class AuditDocumentListResponse(BaseModel):
    """Paginated list of scored documents for the audit findings view."""
    items: List[ScoredDocument] = Field(..., description="Scored documents for current page")
    total: int = Field(..., description="Total documents matching query criteria")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total available pages")
    available_risk_levels: List[str] = Field(default_factory=list)


class AuditRunResponse(BaseModel):
    """Result of running or re-running the scoring engine."""
    status: str = Field(default="completed", description="Audit execution status")
    documents_evaluated: int = Field(..., description="Total documents scored in run")
    timestamp: str = Field(..., description="Execution completion timestamp")
    summary: AuditSummaryResponse = Field(..., description="Updated audit summary metrics")
