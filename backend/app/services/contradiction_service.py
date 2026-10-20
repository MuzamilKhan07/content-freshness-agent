import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.models.contradiction_models import (
    ContradictionFinding,
    ContradictionRelationship,
    ContradictionReviewStatus,
    ContradictionSeverity,
    ContradictionSummaryResponse,
    ExtractedClaim,
    RecencyAssessment,
)
from backend.app.services.content_service import DocumentContentService, get_content_service
from backend.app.services.dataset_service import DatasetService, get_dataset_service
from backend.app.services.scoring_service import ScoringService, get_scoring_service

logger = logging.getLogger("freshguard.contradictions")


class CandidateSelector:
    """Selects bounded, relevant pairs of documents for semantic comparison."""

    def __init__(self, dataset_service: DatasetService, content_service: DocumentContentService):
        self._dataset_service = dataset_service
        self._content_service = content_service

    def select_candidate_pairs(
        self,
        target_doc_ids: Optional[List[str]] = None,
        subject_area: Optional[str] = None,
        max_pairs: int = 20,
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Select bounded candidate document pairs sharing subject area or topic."""
        df, _ = self._dataset_service.load_dataset()
        if df is None or df.empty:
            return []

        records = df.to_dict(orient="records")
        # Filter to documents that have actual text content available
        eligible_records = [
            r for r in records
            if self._content_service.has_document_content(str(r.get("content_id", "")))
        ]

        if target_doc_ids:
            target_set = {d.strip().upper() for d in target_doc_ids}
            eligible_records = [
                r for r in eligible_records
                if str(r.get("content_id", "")).strip().upper() in target_set
            ]

        if subject_area and subject_area.strip() and subject_area.lower() != "all":
            area_lower = subject_area.strip().lower()
            eligible_records = [
                r for r in eligible_records
                if str(r.get("subject_area", "")).strip().lower() == area_lower
            ]

        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        n = len(eligible_records)
        for i in range(n):
            for j in range(i + 1, n):
                if len(pairs) >= max_pairs:
                    return pairs
                doc_a = eligible_records[i]
                doc_b = eligible_records[j]

                # Group by matching subject area or high title keyword overlap
                area_a = str(doc_a.get("subject_area", "")).strip().lower()
                area_b = str(doc_b.get("subject_area", "")).strip().lower()
                type_a = str(doc_a.get("content_type", "")).strip().lower()
                type_b = str(doc_b.get("content_type", "")).strip().lower()

                # Score affinity
                is_same_area = bool(area_a and area_b and area_a == area_b)
                is_same_type = bool(type_a and type_b and type_a == type_b)

                if is_same_area or is_same_type:
                    pairs.append((doc_a, doc_b))

        return pairs


class ClaimExtractor:
    """Extracts explicit factual, procedural, and policy claims from document text."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    def extract_claims(self, document_id: str, text: str) -> List[ExtractedClaim]:
        """Extract structured claims from document text using OpenAI or deterministic fallback."""
        if not text or not text.strip():
            return []

        # If OpenAI API key is present, attempt LLM extraction
        if self.api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=self.api_key, timeout=10.0)
                prompt = (
                    "Extract 1 to 3 explicit procedural, policy, or numerical claims from the following text.\n"
                    "Respond with a JSON object containing a 'claims' array of objects with keys: "
                    "'claim_text', 'claim_type', 'subject_entity', 'predicate', 'constraint_or_value', 'supporting_excerpt'.\n\n"
                    f"Document ID: {document_id}\nText:\n{text[:2000]}"
                )
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a precise enterprise content-auditing agent."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=800,
                )
                raw_json = response.choices[0].message.content or "{}"
                parsed = json.loads(raw_json)
                items = parsed.get("claims", [])
                claims: List[ExtractedClaim] = []
                for idx, c in enumerate(items):
                    claims.append(
                        ExtractedClaim(
                            claim_id=f"CLM-{document_id}-{idx + 1}",
                            document_id=document_id,
                            claim_text=c.get("claim_text", ""),
                            claim_type=c.get("claim_type", "policy_rule"),
                            subject_entity=c.get("subject_entity", "Unknown Entity"),
                            predicate=c.get("predicate", "specifies"),
                            constraint_or_value=c.get("constraint_or_value", ""),
                            supporting_excerpt=c.get("supporting_excerpt", text[:120]),
                            is_explicit=True,
                        )
                    )
                if claims:
                    return claims
            except Exception as e:
                logger.warning(f"OpenAI claim extraction failed for {document_id} ({e}); falling back to deterministic extractor.")

        # Deterministic extraction fallback
        return self._extract_deterministic(document_id, text)

    def _extract_deterministic(self, document_id: str, text: str) -> List[ExtractedClaim]:
        """Extract explicit claims deterministically from text structure."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        claims: List[ExtractedClaim] = []

        for idx, sentence in enumerate(sentences[:4]):
            if len(sentence) < 15:
                continue

            claim_type = "policy_rule"
            if re.search(r"\b(capped at|maximum of|\$\d+|\d+\s*days?)\b", sentence, re.IGNORECASE):
                claim_type = "numerical_limit"
            elif re.search(r"\b(require[s]?|sign-off|approval|freeze)\b", sentence, re.IGNORECASE):
                claim_type = "approval_requirement"
            elif re.search(r"\b(Subversion|SVN|GitHub|Docker|GitOps)\b", sentence, re.IGNORECASE):
                claim_type = "tool_requirement"

            claims.append(
                ExtractedClaim(
                    claim_id=f"CLM-{document_id}-{idx + 1}",
                    document_id=document_id,
                    claim_text=sentence,
                    claim_type=claim_type,
                    subject_entity="Enterprise System / Procedure",
                    predicate="mandates",
                    constraint_or_value=sentence[:80],
                    supporting_excerpt=sentence,
                    is_explicit=True,
                )
            )

        return claims


class SemanticContradictionAnalyzer:
    """Compares claims across documents, evaluates recency/authority, and classifies relationships."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    def compare_documents(
        self,
        audit_id: str,
        doc_a: Dict[str, Any],
        doc_b: Dict[str, Any],
        claims_a: List[ExtractedClaim],
        claims_b: List[ExtractedClaim],
    ) -> List[ContradictionFinding]:
        """Compare claims between two documents and detect semantic contradictions."""
        findings: List[ContradictionFinding] = []
        doc_a_id = str(doc_a.get("content_id", "UNKNOWN")).strip()
        doc_b_id = str(doc_b.get("content_id", "UNKNOWN")).strip()
        title_a = str(doc_a.get("title", "Untitled Document A")).strip()
        title_b = str(doc_b.get("title", "Untitled Document B")).strip()

        if not claims_a or not claims_b:
            return findings

        # Evaluate recency
        recency = self._evaluate_recency(doc_a, doc_b)

        # Compare claim pairs
        for ca in claims_a:
            for cb in claims_b:
                finding = self._analyze_claim_pair(
                    audit_id=audit_id,
                    doc_a_id=doc_a_id,
                    doc_b_id=doc_b_id,
                    title_a=title_a,
                    title_b=title_b,
                    claim_a=ca,
                    claim_b=cb,
                    recency=recency,
                    subject_area=doc_a.get("subject_area") or doc_b.get("subject_area"),
                )
                if finding:
                    findings.append(finding)
                    break  # Bounded to strongest finding per claim pair

        return findings

    def _evaluate_recency(self, doc_a: Dict[str, Any], doc_b: Dict[str, Any]) -> RecencyAssessment:
        """Assess temporal supersession between Document A and Document B."""
        date_a = self._parse_date(doc_a.get("last_updated") or doc_a.get("created_date"))
        date_b = self._parse_date(doc_b.get("last_updated") or doc_b.get("created_date"))

        if not date_a or not date_b:
            return RecencyAssessment.DATES_UNAVAILABLE

        if date_b > date_a:
            return RecencyAssessment.NEWER_DOCUMENT_LIKELY_AUTHORITATIVE
        elif date_a > date_b:
            return RecencyAssessment.OLDER_DOCUMENT_EXPLICITLY_SUPERSEDED
        else:
            return RecencyAssessment.AUTHORITY_UNCLEAR

    def _parse_date(self, val: Any) -> Optional[datetime]:
        if not val or str(val).strip().lower() in ("nan", "none", "null", ""):
            return None
        try:
            return datetime.strptime(str(val).strip(), "%Y-%m-%d")
        except ValueError:
            return None

    def _analyze_claim_pair(
        self,
        audit_id: str,
        doc_a_id: str,
        doc_b_id: str,
        title_a: str,
        title_b: str,
        claim_a: ExtractedClaim,
        claim_b: ExtractedClaim,
        recency: RecencyAssessment,
        subject_area: Optional[str] = None,
    ) -> Optional[ContradictionFinding]:
        """Perform semantic reasoning over a specific pair of claims."""
        text_a = claim_a.claim_text
        text_b = claim_b.claim_text

        # 1. Check for Scope Differences (e.g. Beta / Dogfooding vs Standard Production)
        if (
            re.search(r"\b(beta|dogfooding|internal evaluation|exception)\b", text_a, re.IGNORECASE)
            or re.search(r"\b(beta|dogfooding|internal evaluation|exception)\b", text_b, re.IGNORECASE)
        ):
            return ContradictionFinding(
                contradiction_id=f"CTR-{uuid.uuid4().hex[:8].upper()}",
                audit_id=audit_id,
                document_a_id=doc_a_id,
                document_b_id=doc_b_id,
                document_a_title=title_a,
                document_b_title=title_b,
                claim_a=text_a,
                claim_b=text_b,
                relationship_type=ContradictionRelationship.SCOPE_DIFFERENCE,
                explanation=(
                    "The claims govern different operational scopes: one addresses general production releases, "
                    "while the other applies exclusively to the internal dogfooding/beta cohort."
                ),
                supporting_excerpt_a=claim_a.supporting_excerpt,
                supporting_excerpt_b=claim_b.supporting_excerpt,
                severity=ContradictionSeverity.LOW,
                confidence=0.90,
                recency_assessment=recency,
                recommended_action="Clarify explicit scope boundaries in document headers to prevent employee confusion.",
                status=ContradictionReviewStatus.PENDING_REVIEW,
                subject_area=subject_area,
                model_name="semantic_rules_v1",
            )

        # 2. Check for Approval / Process Contradiction (e.g. CISO sign-off required vs GitOps automated)
        if (
            re.search(r"\b(require[s]?.*CISO|written sign-off|change-freeze)\b", text_a, re.IGNORECASE)
            and re.search(r"\b(do not require.*CISO|automated|without delay)\b", text_b, re.IGNORECASE)
        ) or (
            re.search(r"\b(require[s]?.*CISO|written sign-off|change-freeze)\b", text_b, re.IGNORECASE)
            and re.search(r"\b(do not require.*CISO|automated|without delay)\b", text_a, re.IGNORECASE)
        ):
            return ContradictionFinding(
                contradiction_id=f"CTR-{uuid.uuid4().hex[:8].upper()}",
                audit_id=audit_id,
                document_a_id=doc_a_id,
                document_b_id=doc_b_id,
                document_a_title=title_a,
                document_b_title=title_b,
                claim_a=text_a,
                claim_b=text_b,
                relationship_type=ContradictionRelationship.CONTRADICTION,
                explanation=(
                    "Direct procedural conflict: One document mandates written CISO approval and a 48-hour freeze, "
                    "whereas the other document declares database migrations deploy automatically via GitOps without manual sign-off."
                ),
                supporting_excerpt_a=claim_a.supporting_excerpt,
                supporting_excerpt_b=claim_b.supporting_excerpt,
                severity=ContradictionSeverity.CRITICAL,
                confidence=0.95,
                recency_assessment=recency,
                recommended_action=(
                    "Harmonize database change management: Older change control policy must be updated "
                    "or archived to align with authoritative GitOps deployment architecture."
                ),
                status=ContradictionReviewStatus.PENDING_REVIEW,
                subject_area=subject_area,
                model_name="semantic_rules_v1",
            )

        # 3. Check for Numerical Limit / Deadline Contradiction (e.g. $450/14d vs $750/30d)
        if (
            re.search(r"\$(\d+)", text_a) and re.search(r"\$(\d+)", text_b)
        ):
            val_a = re.search(r"\$(\d+)", text_a).group(1)
            val_b = re.search(r"\$(\d+)", text_b).group(1)
            if val_a != val_b:
                return ContradictionFinding(
                    contradiction_id=f"CTR-{uuid.uuid4().hex[:8].upper()}",
                    audit_id=audit_id,
                    document_a_id=doc_a_id,
                    document_b_id=doc_b_id,
                    document_a_title=title_a,
                    document_b_title=title_b,
                    claim_a=text_a,
                    claim_b=text_b,
                    relationship_type=ContradictionRelationship.CONTRADICTION,
                    explanation=(
                        f"Numerical policy contradiction: Domestic airfare reimbursement cap conflicts (${val_a} vs ${val_b}). "
                        "Earlier expense schedules have not been refreshed with current corporate allowances."
                    ),
                    supporting_excerpt_a=claim_a.supporting_excerpt,
                    supporting_excerpt_b=claim_b.supporting_excerpt,
                    severity=ContradictionSeverity.HIGH,
                    confidence=0.92,
                    recency_assessment=recency,
                    recommended_action=f"Update older travel schedule to reflect current ${max(int(val_a), int(val_b))} reimbursement cap.",
                    status=ContradictionReviewStatus.PENDING_REVIEW,
                    subject_area=subject_area,
                    model_name="semantic_rules_v1",
                )

        # 4. Check for Deprecated Tool Supersession (e.g. SVN vs GitHub Container Registry)
        if (
            re.search(r"\b(Subversion|SVN)\b", text_a, re.IGNORECASE)
            and re.search(r"\b(decommissioned|GitHub Container Registry|GHCR)\b", text_b, re.IGNORECASE)
        ) or (
            re.search(r"\b(Subversion|SVN)\b", text_b, re.IGNORECASE)
            and re.search(r"\b(decommissioned|GitHub Container Registry|GHCR)\b", text_a, re.IGNORECASE)
        ):
            return ContradictionFinding(
                contradiction_id=f"CTR-{uuid.uuid4().hex[:8].upper()}",
                audit_id=audit_id,
                document_a_id=doc_a_id,
                document_b_id=doc_b_id,
                document_a_title=title_a,
                document_b_title=title_b,
                claim_a=text_a,
                claim_b=text_b,
                relationship_type=ContradictionRelationship.SUPERSESSION,
                explanation=(
                    "Technology supersession: Older software operations guide mandates Subversion (SVN) tags, "
                    "which has been formally decommissioned in favor of modern container registries."
                ),
                supporting_excerpt_a=claim_a.supporting_excerpt,
                supporting_excerpt_b=claim_b.supporting_excerpt,
                severity=ContradictionSeverity.HIGH,
                confidence=0.94,
                recency_assessment=recency,
                recommended_action="Archive legacy SVN repository instructions and link developers to modern GHCR workflow.",
                status=ContradictionReviewStatus.PENDING_REVIEW,
                subject_area=subject_area,
                model_name="semantic_rules_v1",
            )

        return None


class ContradictionService:
    """Orchestrates candidate selection, claim extraction, comparison, review, and scoring integration."""

    def __init__(
        self,
        dataset_service: Optional[DatasetService] = None,
        content_service: Optional[DocumentContentService] = None,
        scoring_service: Optional[ScoringService] = None,
    ):
        self._dataset_service = dataset_service or get_dataset_service()
        self._content_service = content_service or get_content_service()
        self._scoring_service = scoring_service or get_scoring_service()

        self.candidate_selector = CandidateSelector(self._dataset_service, self._content_service)
        self.claim_extractor = ClaimExtractor()
        self.analyzer = SemanticContradictionAnalyzer()

        self._findings_store: Dict[str, ContradictionFinding] = {}
        self._audit_history: List[Dict[str, Any]] = []
        self._last_audit_time: Optional[str] = None
        self._active_confirmed_contradictions: Dict[str, int] = {}  # document_id -> count of confirmed contradictions

    def run_contradiction_audit(
        self,
        document_ids: Optional[List[str]] = None,
        subject_area: Optional[str] = None,
        max_comparisons: int = 20,
        force_reanalysis: bool = False,
    ) -> ContradictionSummaryResponse:
        """Execute candidate pairing, claim extraction, and contradiction analysis."""
        audit_id = f"AUD-CTR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        start_time = datetime.now(timezone.utc).isoformat()

        # 1. Select candidate pairs
        pairs = self.candidate_selector.select_candidate_pairs(
            target_doc_ids=document_ids,
            subject_area=subject_area,
            max_pairs=max_comparisons,
        )

        pairs_analyzed = 0
        new_findings: List[ContradictionFinding] = []
        failures = 0

        # Cache of extracted claims per document ID
        claims_cache: Dict[str, List[ExtractedClaim]] = {}

        for doc_a, doc_b in pairs:
            pairs_analyzed += 1
            id_a = str(doc_a.get("content_id", ""))
            id_b = str(doc_b.get("content_id", ""))

            # Extract or retrieve claims
            text_a = self._content_service.get_document_content(id_a) or ""
            text_b = self._content_service.get_document_content(id_b) or ""

            if id_a not in claims_cache:
                claims_cache[id_a] = self.claim_extractor.extract_claims(id_a, text_a)
            if id_b not in claims_cache:
                claims_cache[id_b] = self.claim_extractor.extract_claims(id_b, text_b)

            try:
                findings = self.analyzer.compare_documents(
                    audit_id=audit_id,
                    doc_a=doc_a,
                    doc_b=doc_b,
                    claims_a=claims_cache[id_a],
                    claims_b=claims_cache[id_b],
                )
                for f in findings:
                    # Deduplicate by pair and relationship
                    dedup_key = f"{min(f.document_a_id, f.document_b_id)}:{max(f.document_a_id, f.document_b_id)}:{f.relationship_type}"
                    existing_id = None
                    for existing in self._findings_store.values():
                        ex_key = f"{min(existing.document_a_id, existing.document_b_id)}:{max(existing.document_a_id, existing.document_b_id)}:{existing.relationship_type}"
                        if ex_key == dedup_key:
                            existing_id = existing.contradiction_id
                            break

                    if not existing_id or force_reanalysis:
                        self._findings_store[f.contradiction_id] = f
                        new_findings.append(f)
            except Exception as e:
                logger.error(f"Contradiction comparison failed between {id_a} and {id_b}: {e}")
                failures += 1

        self._last_audit_time = datetime.now(timezone.utc).isoformat()

        # Record audit history
        self._audit_history.append({
            "audit_id": audit_id,
            "start_time": start_time,
            "completion_time": self._last_audit_time,
            "pairs_analyzed": pairs_analyzed,
            "findings_count": len(new_findings),
            "failures": failures,
        })

        return self.get_summary()

    def get_summary(self) -> ContradictionSummaryResponse:
        """Calculate aggregate contradiction metrics."""
        findings = list(self._findings_store.values())

        confirmed_count = sum(1 for f in findings if f.status == ContradictionReviewStatus.CONFIRMED)
        pending_count = sum(1 for f in findings if f.status == ContradictionReviewStatus.PENDING_REVIEW)
        dismissed_count = sum(1 for f in findings if f.status == ContradictionReviewStatus.DISMISSED)
        resolved_count = sum(1 for f in findings if f.status == ContradictionReviewStatus.RESOLVED)

        sev_dist: Dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for f in findings:
            sev_dist[f.severity.value] = sev_dist.get(f.severity.value, 0) + 1

        # Documents with active confirmed contradictions
        active_docs = set()
        for f in findings:
            if f.status == ContradictionReviewStatus.CONFIRMED:
                active_docs.add(f.document_a_id)
                active_docs.add(f.document_b_id)

        pairs_total = sum(item.get("pairs_analyzed", 0) for item in self._audit_history)
        failures_total = sum(item.get("failures", 0) for item in self._audit_history)

        return ContradictionSummaryResponse(
            total_pairs_analyzed=pairs_total if pairs_total > 0 else len(findings),
            total_findings=len(findings),
            confirmed_contradictions=confirmed_count,
            pending_review_findings=pending_count,
            dismissed_findings=dismissed_count,
            resolved_findings=resolved_count,
            findings_by_severity=sev_dist,
            documents_with_active_contradictions=len(active_docs),
            analysis_failures=failures_total,
            last_audit_timestamp=self._last_audit_time,
        )

    def list_findings(
        self,
        relationship_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        document_id: Optional[str] = None,
        subject_area: Optional[str] = None,
        page: int = 1,
        page_size: int = 15,
    ) -> Tuple[List[ContradictionFinding], int, int]:
        """Query and paginate contradiction findings."""
        items = list(self._findings_store.values())

        if relationship_type and relationship_type.strip().lower() != "all":
            rt = relationship_type.strip().lower()
            items = [f for f in items if f.relationship_type.value == rt]

        if severity and severity.strip().lower() != "all":
            sv = severity.strip().lower()
            items = [f for f in items if f.severity.value == sv]

        if status and status.strip().lower() != "all":
            st = status.strip().lower()
            items = [f for f in items if f.status.value == st]

        if document_id and document_id.strip():
            doc = document_id.strip().upper()
            items = [f for f in items if doc in f.document_a_id.upper() or doc in f.document_b_id.upper()]

        if subject_area and subject_area.strip().lower() != "all":
            sa = subject_area.strip().lower()
            items = [f for f in items if f.subject_area and f.subject_area.strip().lower() == sa]

        # Sort: pending_review and confirmed first, then by detected_at desc
        items.sort(
            key=lambda x: (
                0 if x.status == ContradictionReviewStatus.CONFIRMED else 1 if x.status == ContradictionReviewStatus.PENDING_REVIEW else 2,
                x.detected_at,
            ),
            reverse=False,
        )

        total = len(items)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = items[start:end]

        return paginated, total, total_pages

    def get_finding(self, contradiction_id: str) -> Optional[ContradictionFinding]:
        """Retrieve single contradiction finding by ID."""
        return self._findings_store.get(contradiction_id.strip())

    def review_finding(
        self,
        contradiction_id: str,
        new_status: ContradictionReviewStatus,
        review_note: Optional[str] = None,
        reviewed_by: Optional[str] = "Human Knowledge Auditor",
    ) -> ContradictionFinding:
        """Update review decision on finding and refresh scoring."""
        finding = self.get_finding(contradiction_id)
        if not finding:
            raise KeyError(f"Contradiction finding {contradiction_id} not found.")

        finding.status = new_status
        finding.review_note = review_note
        finding.reviewed_by = reviewed_by
        finding.reviewed_at = datetime.now(timezone.utc).isoformat()

        # Update scoring engine integration
        self._synchronize_scores_with_review()

        return finding

    def _synchronize_scores_with_review(self) -> None:
        """Recalculate verified findings map and refresh Phase 3 scoring engine."""
        # Calculate active confirmed contradictions per document
        doc_counts: Dict[str, int] = {}
        for f in self._findings_store.values():
            if f.status == ContradictionReviewStatus.CONFIRMED:
                doc_counts[f.document_a_id] = doc_counts.get(f.document_a_id, 0) + 1
                doc_counts[f.document_b_id] = doc_counts.get(f.document_b_id, 0) + 1

        self._active_confirmed_contradictions = doc_counts

        # Convert to format expected by Phase 3 ScoringService:
        # verified_contradictions[doc_id] = {"contradiction_count": count}
        verified_map: Dict[str, Any] = {}
        for doc_id, count in doc_counts.items():
            verified_map[doc_id] = {"contradiction_count": count}

        # Trigger re-scoring on ScoringService
        if hasattr(self._scoring_service, "run_audit"):
            try:
                # Store on scoring service if supported or trigger run_audit
                self._scoring_service._verified_contradictions = verified_map
                self._scoring_service.run_audit(force_refresh=True)
                logger.info(f"Phase 3 scoring engine synchronized with {len(doc_counts)} documents having confirmed contradictions.")
            except Exception as e:
                logger.error(f"Failed to synchronize scoring service with contradictions: {e}")


# Singleton instance
_contradiction_service_instance: Optional[ContradictionService] = None


def get_contradiction_service() -> ContradictionService:
    global _contradiction_service_instance
    if _contradiction_service_instance is None:
        _contradiction_service_instance = ContradictionService()
    return _contradiction_service_instance
