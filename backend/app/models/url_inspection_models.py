from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class InspectUrlRequest(BaseModel):
    url: str = Field(..., description="Target webpage or document URL to inspect")
    check_links: bool = Field(True, description="Whether to probe hyperlinks found on the page")
    max_links_to_check: int = Field(15, ge=1, le=50, description="Max external hyperlinks to check on the page")


class ExtractedLinkResult(BaseModel):
    url: str
    anchor_text: Optional[str] = None
    status_code: Optional[int] = None
    status: str  # "live", "broken", "blocked", "timeout", "unknown"
    error: Optional[str] = None


class DeprecatedToolFinding(BaseModel):
    tool_name: str
    pattern: str
    matched_text: str
    context_excerpt: str
    severity: str = "HIGH"
    recommended_replacement: Optional[str] = None


class MetadataQualityFinding(BaseModel):
    field: str
    issue: str
    severity: str = "MEDIUM"
    observed_value: Optional[str] = None


class UrlInspectionResponse(BaseModel):
    url: str
    status: str  # "success", "error"
    page_title: str
    page_description: Optional[str] = None
    author: Optional[str] = None
    last_modified: Optional[str] = None
    status_code: Optional[int] = None
    character_count: int = 0
    word_count: int = 0

    # Signals
    broken_links_count: int = 0
    total_links_found: int = 0
    links_checked_count: int = 0
    broken_links: List[ExtractedLinkResult] = Field(default_factory=list)
    live_links: List[ExtractedLinkResult] = Field(default_factory=list)

    deprecated_tools_count: int = 0
    deprecated_tools: List[DeprecatedToolFinding] = Field(default_factory=list)

    metadata_quality_issues_count: int = 0
    metadata_quality_issues: List[MetadataQualityFinding] = Field(default_factory=list)

    # Scoring
    freshness_score: float = 0.0
    risk_level: str = "Low"
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)

    text_preview: str = ""
    error_message: Optional[str] = None
    imported_as_document_id: Optional[str] = None


class ImportScannedUrlRequest(BaseModel):
    url: str
    title: str
    platform: Optional[str] = "Web"
    subject_area: Optional[str] = "General"
    author: Optional[str] = None
    raw_text: Optional[str] = None
    has_broken_links: bool = False
    mentions_deprecated_tool: bool = False
