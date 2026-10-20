import logging
import math
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend.app.core.scoring_config import ScoringConfig, default_scoring_config
from backend.app.models.scoring_models import (
    AuditDocumentListResponse,
    AuditRunResponse,
    AuditSummaryResponse,
    RiskLevel,
    ScoredDocument,
    SignalScoreDetail,
    SignalStatus,
)
from backend.app.services.dataset_service import DatasetService, get_dataset_service

logger = logging.getLogger("freshguard.scoring")


class ScoringService:
    """Deterministic, explainable freshness-risk scoring engine."""

    def __init__(
        self,
        dataset_service: Optional[DatasetService] = None,
        config: Optional[ScoringConfig] = None,
    ):
        self._dataset_service = dataset_service or get_dataset_service()
        self.config = config or default_scoring_config
        self._cached_scored_docs: Optional[List[ScoredDocument]] = None
        self._cached_summary: Optional[AuditSummaryResponse] = None
        self._last_audit_time: Optional[str] = None
        self._verified_contradictions: Dict[str, Any] = {}

    def evaluate_age_signal(self, row: Dict[str, Any]) -> SignalScoreDetail:
        """Evaluate document age risk (0-30 points)."""
        max_pts = self.config.weight_age
        ref_date = self.config.reference_date

        date_val = None
        date_field_used = None

        # Prioritize last_updated, fallback to last_reviewed, then created_date
        for field in ("last_updated", "last_reviewed", "created_date"):
            raw_d = str(row.get(field, "")).strip()
            if raw_d and raw_d.lower() not in ("nan", "none", "null", ""):
                try:
                    parsed = datetime.strptime(raw_d, "%Y-%m-%d").date()
                    date_val = parsed
                    date_field_used = field
                    break
                except (ValueError, TypeError):
                    continue

        if not date_val:
            return SignalScoreDetail(
                signal_name="document_age",
                display_name="Document Age & Update Freshness",
                status=SignalStatus.UNKNOWN,
                max_points=max_pts,
                actual_points=None,
                evidence="All timestamp fields (last_updated, last_reviewed, created_date) are missing or invalid.",
                explanation="Document age cannot be evaluated without a reliable timestamp.",
                evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        days_old = (ref_date - date_val).days
        # Safety clamp for future dates
        days_old = max(0, days_old)

        fallback_note = ""
        if date_field_used != "last_updated":
            fallback_note = f" (Note: evaluated using fallback field '{date_field_used}' as last_updated was absent)."

        if days_old <= self.config.age_threshold_fresh:
            pts = self.config.age_points_fresh
            explanation = f"Document updated {days_old} days ago (within 30-day freshness window){fallback_note}."
        elif days_old <= self.config.age_threshold_mild:
            pts = self.config.age_points_mild
            explanation = f"Document updated {days_old} days ago (mild aging, 31-90 days){fallback_note}."
        elif days_old <= self.config.age_threshold_moderate:
            pts = self.config.age_points_moderate
            explanation = f"Document updated {days_old} days ago (moderate aging, 91-180 days){fallback_note}."
        elif days_old <= self.config.age_threshold_stale:
            pts = self.config.age_points_stale
            explanation = f"Document updated {days_old} days ago (significant aging, 181-365 days){fallback_note}."
        else:
            pts = self.config.age_points_critical
            explanation = f"Document updated {days_old} days ago (exceeds 1-year staleness threshold){fallback_note}."

        return SignalScoreDetail(
            signal_name="document_age",
            display_name="Document Age & Update Freshness",
            status=SignalStatus.EVALUATED,
            max_points=max_pts,
            actual_points=pts,
            evidence=f"{date_field_used} = '{date_val.isoformat()}' ({days_old} days elapsed)",
            explanation=explanation,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def evaluate_broken_links_signal(self, row: Dict[str, Any]) -> SignalScoreDetail:
        """Evaluate broken hyperlink risk (0-25 points)."""
        max_pts = self.config.weight_broken_links
        val = row.get("has_broken_links")

        if val is None or str(val).strip() == "" or str(val).lower() in ("nan", "none", "null"):
            return SignalScoreDetail(
                signal_name="broken_links",
                display_name="Hyperlink Reachability",
                status=SignalStatus.UNKNOWN,
                max_points=max_pts,
                actual_points=None,
                evidence="No hyperlink telemetry or crawl records present.",
                explanation="Link integrity check has not been executed or recorded for this document.",
                evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        is_broken = str(val).strip().lower() in ("true", "1", "yes")
        if is_broken:
            pts = self.config.broken_links_confirmed_points
            explanation = "Confirmed dead or broken destination URL(s) detected in link verification check."
        else:
            pts = self.config.broken_links_clean_points
            explanation = "Link verification check confirmed zero broken or unreachable URLs."

        return SignalScoreDetail(
            signal_name="broken_links",
            display_name="Hyperlink Reachability",
            status=SignalStatus.EVALUATED,
            max_points=max_pts,
            actual_points=pts,
            evidence=f"has_broken_links = {is_broken}",
            explanation=explanation,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def evaluate_deprecated_tools_signal(self, row: Dict[str, Any]) -> SignalScoreDetail:
        """Evaluate retired / deprecated software tool mentions (0-20 points)."""
        max_pts = self.config.weight_deprecated_tools
        val = row.get("mentions_deprecated_tool")

        if val is None or str(val).strip() == "" or str(val).lower() in ("nan", "none", "null"):
            return SignalScoreDetail(
                signal_name="deprecated_tools",
                display_name="Deprecated Tool References",
                status=SignalStatus.UNKNOWN,
                max_points=max_pts,
                actual_points=None,
                evidence="No deprecated software catalog check records available.",
                explanation="Document has not been scanned against enterprise retired tooling catalog.",
                evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        has_deprecated = str(val).strip().lower() in ("true", "1", "yes")
        if has_deprecated:
            pts = self.config.deprecated_tool_confirmed_points
            explanation = "Confirmed reference to retired, sunset, or deprecated enterprise tooling."
        else:
            pts = self.config.deprecated_tool_clean_points
            explanation = "Completed software scan detected no references to retired or sunset tools."

        return SignalScoreDetail(
            signal_name="deprecated_tools",
            display_name="Deprecated Tool References",
            status=SignalStatus.EVALUATED,
            max_points=max_pts,
            actual_points=pts,
            evidence=f"mentions_deprecated_tool = {has_deprecated}",
            explanation=explanation,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def evaluate_contradictions_signal(
        self,
        row: Dict[str, Any],
        verified_findings: Optional[Dict[str, Any]] = None,
    ) -> SignalScoreDetail:
        """Evaluate semantic contradictions against newer documents (0-15 points)."""
        max_pts = self.config.weight_contradictions

        # Check if verified findings are supplied (for testing or Phase 5 integration)
        if verified_findings and row.get("content_id") in verified_findings:
            finding = verified_findings[row.get("content_id")]
            count = finding.get("contradiction_count", 0)
            if count > 1:
                pts = self.config.contradiction_multiple_points
                exp = f"Multiple verified semantic contradictions ({count}) detected against newer documents."
            elif count == 1:
                pts = self.config.contradiction_single_points
                exp = "One verified semantic contradiction detected against authoritative newer guidance."
            else:
                pts = self.config.contradiction_clean_points
                exp = "Semantic comparison completed with zero verified contradictions."

            return SignalScoreDetail(
                signal_name="contradictions",
                display_name="Semantic Contradiction Findings",
                status=SignalStatus.EVALUATED,
                max_points=max_pts,
                actual_points=pts,
                evidence=f"findings_count = {count}",
                explanation=exp,
                evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # For Phase 3 default: AI contradiction comparison has not run yet
        return SignalScoreDetail(
            signal_name="contradictions",
            display_name="Semantic Contradiction Findings",
            status=SignalStatus.UNKNOWN,
            max_points=max_pts,
            actual_points=None,
            evidence="AI semantic contradiction comparison scheduled for Phase 5.",
            explanation="Semantic contradiction analysis has not yet been performed across the knowledge corpus.",
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def evaluate_views_trend_signal(self, row: Dict[str, Any]) -> SignalScoreDetail:
        """Evaluate declining reader viewership trend (0-10 points)."""
        max_pts = self.config.weight_declining_views
        views_raw = row.get("page_views_90d")

        # In CSV dataset, only single 90-day aggregate is provided without historical baseline.
        return SignalScoreDetail(
            signal_name="declining_views",
            display_name="Reader Engagement Trend",
            status=SignalStatus.UNKNOWN,
            max_points=max_pts,
            actual_points=None,
            evidence=f"page_views_90d = {views_raw} (single window count, historical baseline absent)",
            explanation="Historical viewership decline cannot be inferred from a single 90-day aggregate without prior telemetry.",
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def score_document(
        self,
        row: Dict[str, Any],
        verified_contradictions: Optional[Dict[str, Any]] = None,
    ) -> ScoredDocument:
        """Calculate explainable score, evidence coverage, risk level, and priority for a record."""
        # 1. Evaluate individual signals
        sig_age = self.evaluate_age_signal(row)
        sig_links = self.evaluate_broken_links_signal(row)
        sig_tools = self.evaluate_deprecated_tools_signal(row)
        sig_contra = self.evaluate_contradictions_signal(row, verified_contradictions)
        sig_views = self.evaluate_views_trend_signal(row)

        signals = {
            "document_age": sig_age,
            "broken_links": sig_links,
            "deprecated_tools": sig_tools,
            "contradictions": sig_contra,
            "declining_views": sig_views,
        }

        # 2. Compute earned points and evaluated maximum
        total_possible_weights = 100.0
        earned_points = 0.0
        evaluated_max_points = 0.0

        for sig in signals.values():
            if sig.status == SignalStatus.EVALUATED and sig.actual_points is not None:
                earned_points += sig.actual_points
                evaluated_max_points += sig.max_points

        # Evidence coverage percentage (e.g. (75 / 100) * 100 = 75%)
        evidence_coverage = round((evaluated_max_points / total_possible_weights) * 100.0, 1)

        # 3. Handle zero or partial evaluations
        if evaluated_max_points == 0.0:
            calculated_score = None
            raw_score = 0.0
            is_provisional = True
            score_status = "unavailable"
            risk_level = RiskLevel.INSUFFICIENT_EVIDENCE
        else:
            raw_score = (earned_points / evaluated_max_points) * 100.0
            calculated_score = int(round(raw_score))

            if evidence_coverage < 100.0:
                is_provisional = True
                score_status = "provisional" if evidence_coverage >= 40.0 else "insufficient_evidence"
            else:
                is_provisional = False
                score_status = "fully_evaluated"

            # Assign risk level
            if score_status == "insufficient_evidence":
                risk_level = RiskLevel.INSUFFICIENT_EVIDENCE
            elif calculated_score >= self.config.threshold_critical:
                risk_level = RiskLevel.CRITICAL
            elif calculated_score >= self.config.threshold_high:
                risk_level = RiskLevel.HIGH
            elif calculated_score >= self.config.threshold_moderate:
                risk_level = RiskLevel.MODERATE
            else:
                risk_level = RiskLevel.LOW

        # 4. Top Contributing Risk Factors
        contributing_factors: List[str] = []
        # Sort evaluated signals with points > 0 descending
        risk_drivers = [
            sig for sig in signals.values()
            if sig.status == SignalStatus.EVALUATED and sig.actual_points and sig.actual_points > 0
        ]
        risk_drivers.sort(key=lambda s: s.actual_points or 0.0, reverse=True)

        for sig in risk_drivers:
            if sig.signal_name == "document_age":
                contributing_factors.append(f"Document age ({int(sig.actual_points)} pts: {sig.evidence})")
            elif sig.signal_name == "broken_links":
                contributing_factors.append(f"Confirmed broken links ({int(sig.actual_points)} pts)")
            elif sig.signal_name == "deprecated_tools":
                contributing_factors.append(f"Deprecated tool mentions ({int(sig.actual_points)} pts)")
            elif sig.signal_name == "contradictions":
                contributing_factors.append(f"Semantic contradiction ({int(sig.actual_points)} pts)")

        if not contributing_factors:
            contributing_factors.append("No active risk factors identified among evaluated signals.")

        # 5. Deterministic Priority Ranking (1 to 6)
        # Order:
        # 1. Critical risk with strong evidence (coverage >= 70%)
        # 2. High risk with strong evidence (coverage >= 70%)
        # 3. High risk with incomplete evidence (< 70%)
        # 4. Moderate risk
        # 5. Low risk
        # 6. Insufficient evidence
        is_strong_evidence = evidence_coverage >= self.config.strong_evidence_coverage_pct

        if risk_level == RiskLevel.CRITICAL and is_strong_evidence:
            priority_rank = 1
            priority_label = "Priority 1 (Critical Risk)"
            priority_explanation = "Immediate remediation required: high calculated risk with strong multi-signal evidence."
        elif risk_level == RiskLevel.HIGH and is_strong_evidence:
            priority_rank = 2
            priority_label = "Priority 2 (High Risk)"
            priority_explanation = "Prompt review needed: elevated risk score backed by verified signals."
        elif risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH) and not is_strong_evidence:
            priority_rank = 3
            priority_label = "Priority 3 (Elevated Risk / Provisional)"
            priority_explanation = "Risk score is provisional due to partial evidence, but triggered signals warrant priority inspection."
        elif risk_level == RiskLevel.MODERATE:
            priority_rank = 4
            priority_label = "Priority 4 (Moderate Risk)"
            priority_explanation = "Scheduled routine review: moderate aging or single minor risk indicator detected."
        elif risk_level == RiskLevel.LOW:
            priority_rank = 5
            priority_label = "Priority 5 (Low Risk / Healthy)"
            priority_explanation = "Currently fresh and healthy based on evaluated signals; monitor in regular cycle."
        else:
            priority_rank = 6
            priority_label = "Priority 6 (Insufficient Evidence)"
            priority_explanation = "Telemetry incomplete: collect missing update dates and link status before assigning definitive rating."

        # 6. Generate Actionable Recommendation
        recommended_action = self._generate_recommended_action(signals, risk_level)

        # Reference values
        ref_score = None
        try:
            if row.get("staleness_score") is not None and str(row.get("staleness_score")).strip() != "":
                ref_score = round(float(str(row.get("staleness_score")).strip()), 4)
        except (ValueError, TypeError):
            pass

        return ScoredDocument(
            content_id=str(row.get("content_id", "UNKNOWN")).strip(),
            title=str(row.get("title", "Untitled Document")).strip(),
            platform=str(row.get("platform", "Unknown")).strip(),
            content_type=str(row.get("content_type", "Unspecified")).strip(),
            subject_area=row.get("subject_area"),
            author=row.get("author"),
            last_updated=row.get("last_updated"),
            last_reviewed=row.get("last_reviewed"),
            calculated_score=calculated_score,
            raw_score=round(raw_score, 2),
            earned_points=earned_points,
            evaluated_max_points=evaluated_max_points,
            evidence_coverage=evidence_coverage,
            is_provisional=is_provisional,
            score_status=score_status,
            risk_level=risk_level,
            priority_rank=priority_rank,
            priority_label=priority_label,
            priority_explanation=priority_explanation,
            top_contributing_factors=contributing_factors,
            recommended_action=recommended_action,
            signal_breakdown=signals,
            reference_staleness_score=ref_score,
            source_recommended_action=row.get("recommended_action"),
            raw_data=row,
        )

    def _generate_recommended_action(
        self,
        signals: Dict[str, SignalScoreDetail],
        risk_level: RiskLevel,
    ) -> str:
        """Deterministic actionable recommendation derived from active evidence."""
        sig_links = signals.get("broken_links")
        sig_tools = signals.get("deprecated_tools")
        sig_age = signals.get("document_age")

        has_broken = sig_links and sig_links.status == SignalStatus.EVALUATED and (sig_links.actual_points or 0) > 0
        has_tools = sig_tools and sig_tools.status == SignalStatus.EVALUATED and (sig_tools.actual_points or 0) > 0
        is_stale = sig_age and sig_age.status == SignalStatus.EVALUATED and (sig_age.actual_points or 0) >= 20.0

        if has_broken and has_tools:
            return "Comprehensive overhaul required: replace dead destination URLs and update references to retired software tooling."
        if has_broken:
            return "Remediate broken links: verify and update or remove dead destination hyperlinks."
        if has_tools:
            return "Tooling review needed: audit and replace mentions of retired software with supported enterprise standards."
        if is_stale:
            return "Subject matter expert review required: document age exceeds standard freshness cycle."
        if risk_level == RiskLevel.INSUFFICIENT_EVIDENCE:
            return "Collect missing telemetry: verify document update history and run link verification."
        return "Content verified fresh: maintain current guidance and schedule next periodic review."

    def run_audit(
        self,
        force_refresh: bool = False,
        verified_contradictions: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ScoredDocument], AuditSummaryResponse]:
        """Execute full scoring audit over inventory dataset."""
        if verified_contradictions is not None:
            self._verified_contradictions = verified_contradictions

        df, _ = self._dataset_service.load_dataset()
        now_iso = datetime.now(timezone.utc).isoformat()

        if df is None or df.empty:
            summary = AuditSummaryResponse(
                total_documents=0,
                scored_documents=0,
                provisional_scores_count=0,
                insufficient_evidence_count=0,
                risk_distribution={
                    "Critical": 0,
                    "High": 0,
                    "Moderate": 0,
                    "Low": 0,
                    "Insufficient Evidence": 0,
                },
                broken_link_documents=0,
                deprecated_tool_documents=0,
                unknown_signals_count=0,
                average_risk_score=0.0,
                last_audit_timestamp=now_iso,
            )
            self._cached_scored_docs = []
            self._cached_summary = summary
            self._last_audit_time = now_iso
            return [], summary

        records = df.to_dict(orient="records")
        scored_list: List[ScoredDocument] = []

        risk_dist = {
            "Critical": 0,
            "High": 0,
            "Moderate": 0,
            "Low": 0,
            "Insufficient Evidence": 0,
        }
        provisional_count = 0
        insufficient_count = 0
        broken_link_docs = 0
        deprecated_tool_docs = 0
        unknown_signals = 0
        score_sum = 0.0
        scored_count = 0

        for r in records:
            doc = self.score_document(r, verified_contradictions=self._verified_contradictions)
            scored_list.append(doc)

            risk_dist[doc.risk_level.value] = risk_dist.get(doc.risk_level.value, 0) + 1

            if doc.is_provisional:
                provisional_count += 1
            if doc.score_status == "insufficient_evidence":
                insufficient_count += 1
            if doc.calculated_score is not None:
                score_sum += doc.calculated_score
                scored_count += 1

            # Signal flags count
            for sig in doc.signal_breakdown.values():
                if sig.status == SignalStatus.UNKNOWN:
                    unknown_signals += 1

            if str(r.get("has_broken_links", "")).strip().lower() in ("true", "1", "yes"):
                broken_link_docs += 1
            if str(r.get("mentions_deprecated_tool", "")).strip().lower() in ("true", "1", "yes"):
                deprecated_tool_docs += 1

        # Sort documents by priority rank (1 is highest), then calculated score DESC
        scored_list.sort(
            key=lambda d: (
                d.priority_rank,
                -(d.calculated_score if d.calculated_score is not None else -1),
                d.content_id,
            )
        )

        avg_score = round(score_sum / scored_count, 1) if scored_count > 0 else 0.0

        summary = AuditSummaryResponse(
            total_documents=len(records),
            scored_documents=scored_count,
            provisional_scores_count=provisional_count,
            insufficient_evidence_count=insufficient_count,
            risk_distribution=risk_dist,
            broken_link_documents=broken_link_docs,
            deprecated_tool_documents=deprecated_tool_docs,
            unknown_signals_count=unknown_signals,
            average_risk_score=avg_score,
            last_audit_timestamp=now_iso,
        )

        self._cached_scored_docs = scored_list
        self._cached_summary = summary
        self._last_audit_time = now_iso

        return scored_list, summary

    def get_audit_summary(self) -> AuditSummaryResponse:
        """Retrieve audit summary, running audit if not yet cached."""
        if self._cached_summary is None:
            _, summary = self.run_audit()
            return summary
        return self._cached_summary

    def get_scored_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        risk_level: Optional[str] = None,
        min_score: Optional[int] = None,
        max_score: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        evidence_status: Optional[str] = None,
    ) -> AuditDocumentListResponse:
        """Query scored documents with pagination, risk filters, score ranges, and sorting."""
        if self._cached_scored_docs is None:
            docs, _ = self.run_audit()
        else:
            docs = self._cached_scored_docs

        filtered = list(docs)

        # 1. Search filter
        if search and search.strip():
            term = search.strip().lower()
            filtered = [
                d for d in filtered
                if term in d.content_id.lower()
                or term in d.title.lower()
                or term in d.platform.lower()
                or term in d.content_type.lower()
                or term in (d.subject_area or "").lower()
                or term in (d.author or "").lower()
            ]

        # 2. Risk level filter
        if risk_level and risk_level.strip() and risk_level.strip().lower() != "all":
            target = risk_level.strip().lower()
            filtered = [d for d in filtered if d.risk_level.value.lower() == target]

        # 3. Minimum score filter
        if min_score is not None:
            filtered = [
                d for d in filtered
                if d.calculated_score is not None and d.calculated_score >= min_score
            ]

        # 4. Maximum score filter
        if max_score is not None:
            filtered = [
                d for d in filtered
                if d.calculated_score is not None and d.calculated_score <= max_score
            ]

        # 5. Evidence status filter (provisional, fully_evaluated, insufficient_evidence)
        if evidence_status and evidence_status.strip() and evidence_status.strip().lower() != "all":
            target_status = evidence_status.strip().lower()
            filtered = [d for d in filtered if d.score_status.lower() == target_status]

        # 6. Sorting
        if sort_by and sort_by.strip():
            f = sort_by.strip().lower()
            reverse = sort_order.strip().lower() == "desc"

            if f in ("score", "calculated_score"):
                filtered.sort(key=lambda d: (d.calculated_score is not None, d.calculated_score or 0), reverse=reverse)
            elif f == "priority":
                filtered.sort(key=lambda d: d.priority_rank, reverse=reverse)
            elif f == "evidence_coverage":
                filtered.sort(key=lambda d: d.evidence_coverage, reverse=reverse)
            elif f == "title":
                filtered.sort(key=lambda d: d.title.lower(), reverse=reverse)
            elif f == "content_id":
                filtered.sort(key=lambda d: d.content_id.lower(), reverse=reverse)
            elif f == "last_updated":
                filtered.sort(key=lambda d: d.last_updated or "", reverse=reverse)

        total_matching = len(filtered)
        total_pages = max(1, math.ceil(total_matching / page_size)) if total_matching > 0 else 0
        current_page = max(1, page)

        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = filtered[start_idx:end_idx]

        available_risks = ["Critical", "High", "Moderate", "Low", "Insufficient Evidence"]

        return AuditDocumentListResponse(
            items=paged_items,
            total=total_matching,
            page=current_page,
            page_size=page_size,
            total_pages=total_pages,
            available_risk_levels=available_risks,
        )

    def get_scored_document_by_id(self, document_id: str) -> Optional[ScoredDocument]:
        """Fetch complete scoring breakdown for a specific document identifier."""
        if self._cached_scored_docs is None:
            docs, _ = self.run_audit()
        else:
            docs = self._cached_scored_docs

        target = document_id.strip().lower()
        for d in docs:
            if d.content_id.strip().lower() == target:
                return d
        return None


# Global singleton provider
_scoring_service_instance: Optional[ScoringService] = None


def get_scoring_service() -> ScoringService:
    """Dependency provider for ScoringService."""
    global _scoring_service_instance
    if _scoring_service_instance is None:
        _scoring_service_instance = ScoringService()
    return _scoring_service_instance
