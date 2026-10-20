from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="healthy", description="Backend service health status")
    service: str = Field(default="FreshGuard AI Backend", description="Service name")
    version: str = Field(default="0.1.0", description="API version")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Current server timestamp (UTC)"
    )


class DatasetStatusResponse(BaseModel):
    """Dataset status report schema."""
    available: bool = Field(..., description="Whether the dataset file exists and is accessible")
    record_count: int = Field(default=0, description="Total number of records in dataset")
    columns: List[str] = Field(default_factory=list, description="Available dataset column names")
    warnings: List[str] = Field(default_factory=list, description="Non-sensitive dataset notices or warnings")
    file_path: Optional[str] = Field(default=None, description="Relative dataset path if found")


class DatasetPreviewResponse(BaseModel):
    """Dataset preview response schema (up to 10 records)."""
    available: bool = Field(..., description="Whether the dataset is available for preview")
    total_records: int = Field(default=0, description="Total number of records in dataset")
    preview_count: int = Field(default=0, description="Number of preview records returned")
    columns: List[str] = Field(default_factory=list, description="Available dataset column names")
    preview: List[Dict[str, Any]] = Field(default_factory=list, description="Sample records (max 10)")
    warnings: List[str] = Field(default_factory=list, description="Any warnings encountered during reading")


class DocumentRecord(BaseModel):
    """Normalized schema for a knowledge base inventory document."""
    content_id: str = Field(..., description="Unique document identifier")
    title: str = Field(default="Untitled", description="Document title")
    content_type: str = Field(default="Unspecified", description="Document category or type")
    platform: str = Field(default="Unknown", description="Source knowledge system or repository")
    author: Optional[str] = Field(default=None, description="Document author or maintainer")
    created_date: Optional[str] = Field(default=None, description="Creation date (YYYY-MM-DD)")
    last_updated: Optional[str] = Field(default=None, description="Last updated date (YYYY-MM-DD)")
    last_reviewed: Optional[str] = Field(default=None, description="Last reviewed date (YYYY-MM-DD)")
    page_views_90d: Optional[int] = Field(default=None, description="Page views over the trailing 90 days")
    linked_from_count: Optional[int] = Field(default=None, description="Number of incoming internal links")
    mentions_deprecated_tool: bool = Field(default=False, description="Flag indicating mention of retired tools")
    has_broken_links: bool = Field(default=False, description="Flag indicating dead or broken URLs")
    subject_area: Optional[str] = Field(default=None, description="Subject domain / department")
    staleness_score: Optional[float] = Field(default=None, description="Existing reference score from source CSV")
    recommended_action: Optional[str] = Field(default=None, description="Existing recommended workflow action")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Complete unedited record fields")


class DocumentListResponse(BaseModel):
    """Paginated document inventory response."""
    items: List[DocumentRecord] = Field(..., description="Document records for current page")
    total: int = Field(..., description="Total records matching filter criteria")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Page size applied")
    total_pages: int = Field(..., description="Total pages available")
    available_platforms: List[str] = Field(default_factory=list, description="Unique platforms available in dataset")
    available_content_types: List[str] = Field(default_factory=list, description="Unique content types in dataset")


class DashboardSummaryResponse(BaseModel):
    """Aggregated KPIs for enterprise dashboard overview."""
    total_documents: int = Field(..., description="Total indexed documents")
    distinct_platforms: int = Field(..., description="Count of distinct source platforms")
    distinct_content_types: int = Field(..., description="Count of distinct content types")
    missing_update_dates: int = Field(..., description="Documents missing last_updated timestamp")
    deprecated_references: int = Field(..., description="Documents referencing deprecated tooling")
    broken_links: int = Field(..., description="Documents with broken links detected")
    missing_metadata_count: int = Field(..., description="Documents missing one or more metadata attributes")
    platforms_list: List[str] = Field(default_factory=list, description="List of all platforms")
    content_types_list: List[str] = Field(default_factory=list, description="List of all content types")


class DistributionItem(BaseModel):
    """Single distribution bucket."""
    label: str = Field(..., description="Bucket or category label")
    count: int = Field(..., description="Count of documents in this category")
    percentage: float = Field(..., description="Percentage of total (0-100)")


class DashboardDistributionsResponse(BaseModel):
    """Aggregate distribution arrays suitable for frontend charts."""
    by_platform: List[DistributionItem] = Field(default_factory=list)
    by_content_type: List[DistributionItem] = Field(default_factory=list)
    by_reference_score: List[DistributionItem] = Field(default_factory=list)
    by_recommended_action: List[DistributionItem] = Field(default_factory=list)
    by_signals: Dict[str, int] = Field(default_factory=dict)
