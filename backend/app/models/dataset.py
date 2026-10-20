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
