from datetime import date
from typing import Dict, Tuple
from pydantic import BaseModel, Field


class ScoringConfig(BaseModel):
    """Configurable weights and thresholds for the explainable freshness scoring engine."""

    # Reference evaluation date (defaults to current active timestamp in environment)
    reference_date: date = Field(default=date(2026, 10, 20))

    # Maximum signal weights (sum to 100)
    weight_age: float = Field(default=30.0)
    weight_broken_links: float = Field(default=25.0)
    weight_deprecated_tools: float = Field(default=20.0)
    weight_contradictions: float = Field(default=15.0)
    weight_declining_views: float = Field(default=10.0)

    # Document age brackets (days -> score points)
    age_threshold_fresh: int = Field(default=30, description="<= 30 days: 0 pts")
    age_threshold_mild: int = Field(default=90, description="31-90 days: 5 pts")
    age_threshold_moderate: int = Field(default=180, description="91-180 days: 12 pts")
    age_threshold_stale: int = Field(default=365, description="181-365 days: 20 pts")
    # > 365 days: 30 pts

    age_points_fresh: float = Field(default=0.0)
    age_points_mild: float = Field(default=5.0)
    age_points_moderate: float = Field(default=12.0)
    age_points_stale: float = Field(default=20.0)
    age_points_critical: float = Field(default=30.0)

    # Broken links points
    broken_links_clean_points: float = Field(default=0.0)
    broken_links_confirmed_points: float = Field(default=20.0)
    broken_links_critical_points: float = Field(default=25.0)

    # Deprecated tool points
    deprecated_tool_clean_points: float = Field(default=0.0)
    deprecated_tool_confirmed_points: float = Field(default=20.0)

    # Contradiction points (Phase 5 integration)
    contradiction_clean_points: float = Field(default=0.0)
    contradiction_single_points: float = Field(default=10.0)
    contradiction_multiple_points: float = Field(default=15.0)

    # Risk level boundaries
    threshold_critical: int = Field(default=80)
    threshold_high: int = Field(default=60)
    threshold_moderate: int = Field(default=30)
    threshold_low: int = Field(default=0)

    # Minimum coverage for high-confidence classification
    strong_evidence_coverage_pct: float = Field(default=70.0)


# Default singleton instance
default_scoring_config = ScoringConfig()
