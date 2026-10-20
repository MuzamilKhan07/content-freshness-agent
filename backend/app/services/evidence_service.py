import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from backend.app.models.evidence_models import (
    EvidenceAuditRecord,
    EvidenceAuditRequest,
    EvidenceDocumentResponse,
    EvidenceFindingListResponse,
    EvidenceItem,
    EvidenceSeverity,
    EvidenceStatus,
    EvidenceSummaryResponse,
    SignalType,
)
from backend.app.services.dataset_service import DatasetService, get_dataset_service
from backend.app.services.evidence_tools import (
    DeprecatedToolDetectionTool,
    MetadataInspectionTool,
    MetadataQualityTool,
    URLVerificationTool,
)
from backend.app.services.scoring_service import ScoringService, get_scoring_service

logger = logging.getLogger("freshguard.evidence_service")


class EvidenceCollectionOrchestrator:
    """
    Orchestrates evidence collection tools, aggregates findings,
    maintains audit run history, and updates Phase 3 scoring engine.
    """

    def __init__(
        self,
        dataset_service: Optional[DatasetService] = None,
        scoring_service: Optional[ScoringService] = None,
    ):
        self.dataset_service = dataset_service or get_dataset_service()
        self.scoring_service = scoring_service or get_scoring_service()

        # Tools
        self.meta_tool = MetadataInspectionTool()
        self.url_tool = URLVerificationTool()
        self.dep_tool = DeprecatedToolDetectionTool()
        self.qual_tool = MetadataQualityTool()

        # In-memory persistence
        self._audit_history: Dict[str, EvidenceAuditRecord] = {}
        self._document_evidence_map: Dict[str, List[EvidenceItem]] = {}
        self._latest_summary: Optional[EvidenceSummaryResponse] = None

    def run_evidence_audit(self, req: Optional[EvidenceAuditRequest] = None) -> EvidenceAuditRecord:
        """Execute evidence collection audit across target documents."""
        if req is None:
            req = EvidenceAuditRequest()

        start_time = datetime.now(timezone.utc).isoformat()
        audit_id = f"AUDIT-{uuid.uuid4().hex[:8].upper()}"

        df, _ = self.dataset_service.load_dataset()
        if df is None or df.empty:
            empty_summary = EvidenceSummaryResponse(
                documents_inspected=0,
                checks_attempted=0,
                confirmed_findings=0,
                suspected_findings=0,
                unknown_signals=0,
                failed_checks=0,
                broken_link_findings=0,
                deprecated_reference_findings=0,
                metadata_quality_findings=0,
                audit_start_timestamp=start_time,
                audit_completed_timestamp=start_time,
            )
            record = EvidenceAuditRecord(
                audit_id=audit_id,
                status="completed",
                start_time=start_time,
                completion_time=start_time,
                document_ids=[],
                checks_performed=req.enabled_checks or [],
                summary=empty_summary,
                total_evidence_produced=0,
            )
            self._audit_history[audit_id] = record
            self._latest_summary = empty_summary
            return record

        records = df.to_dict(orient="records")

        # 1. Select eligible documents
        if req.document_ids:
            target_ids = {d.strip().lower() for d in req.document_ids if d.strip()}
            records = [r for r in records if str(r.get("content_id", "")).strip().lower() in target_ids]

        if req.max_documents and req.max_documents > 0:
            records = records[:req.max_documents]

        enabled_checks = set(req.enabled_checks or ["metadata_inspection", "url_verification", "deprecated_tools", "metadata_quality"])
        custom_urls = req.custom_urls or {}

        all_collected_evidence: List[EvidenceItem] = []
        checks_attempted = 0
        confirmed_count = 0
        suspected_count = 0
        unknown_count = 0
        failed_count = 0
        broken_link_count = 0
        deprecated_ref_count = 0
        meta_qual_count = 0

        # Set of verified broken link doc IDs and deprecated tool doc IDs to feed back to scoring engine
        verified_broken_link_docs: Set[str] = set()
        verified_deprecated_tool_docs: Set[str] = set()

        for row in records:
            doc_id = str(row.get("content_id", "UNKNOWN")).strip()
            doc_evidence: List[EvidenceItem] = []
            seen_evidence_ids: Set[str] = set()

            def add_item(item: EvidenceItem):
                nonlocal checks_attempted, confirmed_count, suspected_count, unknown_count, failed_count
                nonlocal broken_link_count, deprecated_ref_count, meta_qual_count

                if item.evidence_id in seen_evidence_ids:
                    return
                seen_evidence_ids.add(item.evidence_id)

                checks_attempted += 1
                if item.status == EvidenceStatus.CONFIRMED:
                    confirmed_count += 1
                elif item.status == EvidenceStatus.SUSPECTED:
                    suspected_count += 1
                elif item.status == EvidenceStatus.UNKNOWN:
                    unknown_count += 1
                elif item.status == EvidenceStatus.FAILED:
                    failed_count += 1

                if item.signal_type in (SignalType.BROKEN_LINKS, SignalType.URL_VERIFICATION) and item.severity in (EvidenceSeverity.HIGH, EvidenceSeverity.CRITICAL):
                    broken_link_count += 1
                    if item.status == EvidenceStatus.CONFIRMED:
                        verified_broken_link_docs.add(doc_id)

                if item.signal_type == SignalType.DEPRECATED_TOOLS and item.severity in (EvidenceSeverity.HIGH, EvidenceSeverity.CRITICAL):
                    deprecated_ref_count += 1
                    if item.status == EvidenceStatus.CONFIRMED:
                        verified_deprecated_tool_docs.add(doc_id)

                if item.signal_type == SignalType.METADATA_QUALITY and item.severity in (EvidenceSeverity.MODERATE, EvidenceSeverity.HIGH, EvidenceSeverity.CRITICAL):
                    meta_qual_count += 1

                doc_evidence.append(item)
                all_collected_evidence.append(item)

            # Tool A: Metadata Inspection
            if "metadata_inspection" in enabled_checks:
                for it in self.meta_tool.inspect(row):
                    add_item(it)

            # Tool B: URL Verification
            if "url_verification" in enabled_checks:
                target_url = custom_urls.get(doc_id) or row.get("url")
                # Also if dataset has broken link flag, verify link telemetry
                url_item = self.url_tool.verify_url(doc_id, target_url)
                add_item(url_item)

            # Tool C: Deprecated Tool Detection
            if "deprecated_tools" in enabled_checks:
                for it in self.dep_tool.detect(row):
                    add_item(it)

            # Tool D: Metadata Quality
            if "metadata_quality" in enabled_checks:
                for it in self.qual_tool.analyze(row):
                    add_item(it)

            # Store in per-document map
            self._document_evidence_map[doc_id] = doc_evidence

        completion_time = datetime.now(timezone.utc).isoformat()

        summary = EvidenceSummaryResponse(
            documents_inspected=len(records),
            checks_attempted=checks_attempted,
            confirmed_findings=confirmed_count,
            suspected_findings=suspected_count,
            unknown_signals=unknown_count,
            failed_checks=failed_count,
            broken_link_findings=broken_link_count,
            deprecated_reference_findings=deprecated_ref_count,
            metadata_quality_findings=meta_qual_count,
            audit_start_timestamp=start_time,
            audit_completed_timestamp=completion_time,
        )

        audit_record = EvidenceAuditRecord(
            audit_id=audit_id,
            status="completed",
            start_time=start_time,
            completion_time=completion_time,
            document_ids=[str(r.get("content_id")) for r in records],
            checks_performed=sorted(list(enabled_checks)),
            summary=summary,
            total_evidence_produced=len(all_collected_evidence),
        )

        self._audit_history[audit_id] = audit_record
        self._latest_summary = summary

        # 2. Trigger scoring engine refresh with verified findings
        self.scoring_service.run_audit()

        return audit_record

    def get_evidence_summary(self) -> EvidenceSummaryResponse:
        """Get latest evidence audit summary, triggering a run if none has occurred yet."""
        if self._latest_summary is None:
            record = self.run_evidence_audit()
            return record.summary
        return self._latest_summary

    def get_document_evidence(self, document_id: str) -> EvidenceDocumentResponse:
        """Return all evidence items collected for a specific document."""
        if not self._document_evidence_map:
            self.run_evidence_audit()

        doc_key = document_id.strip()
        items = self._document_evidence_map.get(doc_key, [])

        # Fetch title from dataset service if possible
        doc = self.dataset_service.get_document_by_id(doc_key)
        title = doc.title if doc else "Document Evidence"

        return EvidenceDocumentResponse(
            document_id=doc_key,
            title=title,
            evidence_count=len(items),
            evidence_items=items,
        )

    def get_audit_by_id(self, audit_id: str) -> Optional[EvidenceAuditRecord]:
        """Fetch audit record by its ID."""
        return self._audit_history.get(audit_id.strip().upper())

    def get_findings(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        signal_type: Optional[str] = None,
        severity: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> EvidenceFindingListResponse:
        """Query paginated individual findings with status and signal filters."""
        if not self._document_evidence_map:
            self.run_evidence_audit()

        all_items: List[EvidenceItem] = []
        for doc_items in self._document_evidence_map.values():
            all_items.extend(doc_items)

        # Filters
        if document_id and document_id.strip():
            target_id = document_id.strip().lower()
            all_items = [it for it in all_items if it.document_id.lower() == target_id]

        if status and status.strip() and status.strip().lower() != "all":
            st_target = status.strip().lower()
            all_items = [it for it in all_items if it.status.value.lower() == st_target]

        if signal_type and signal_type.strip() and signal_type.strip().lower() != "all":
            sig_target = signal_type.strip().lower()
            all_items = [it for it in all_items if it.signal_type.value.lower() == sig_target]

        if severity and severity.strip() and severity.strip().lower() != "all":
            sev_target = severity.strip().lower()
            all_items = [it for it in all_items if it.severity.value.lower() == sev_target]

        total_matching = len(all_items)
        total_pages = max(1, math.ceil(total_matching / page_size)) if total_matching > 0 else 0
        current_page = max(1, page)

        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = all_items[start_idx:end_idx]

        return EvidenceFindingListResponse(
            items=paged_items,
            total=total_matching,
            page=current_page,
            page_size=page_size,
            total_pages=total_pages,
        )


# Global singleton instance provider
_orchestrator_instance: Optional[EvidenceCollectionOrchestrator] = None


def get_evidence_orchestrator() -> EvidenceCollectionOrchestrator:
    """Dependency provider for EvidenceCollectionOrchestrator."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = EvidenceCollectionOrchestrator()
    return _orchestrator_instance
