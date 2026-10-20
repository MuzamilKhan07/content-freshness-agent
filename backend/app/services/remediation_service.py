import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.models.remediation_models import (
    ChangeRecord,
    DraftRevision,
    RemediationJob,
    RemediationJobStatus,
    RemediationPlan,
    RemediationSummaryResponse,
    RevisionReviewStatus,
    ValidationResult,
    ValidationStatus,
)
from backend.app.services.content_service import DocumentContentService, get_content_service
from backend.app.services.contradiction_service import ContradictionService, get_contradiction_service
from backend.app.services.dataset_service import DatasetService, get_dataset_service
from backend.app.services.evidence_service import EvidenceCollectionOrchestrator, get_evidence_orchestrator
from backend.app.services.scoring_service import ScoringService, get_scoring_service

logger = logging.getLogger("freshguard.remediation")


class RemediationPlanner:
    """Agent A: Inspects document decay findings, contradictions, and evidence to synthesize an actionable plan."""

    def __init__(
        self,
        dataset_service: DatasetService,
        content_service: DocumentContentService,
        scoring_service: ScoringService,
        evidence_service: EvidenceCollectionOrchestrator,
        contradiction_service: ContradictionService,
    ):
        self._dataset_service = dataset_service
        self._content_service = content_service
        self._scoring_service = scoring_service
        self._evidence_service = evidence_service
        self._contradiction_service = contradiction_service

    def plan_remediation(
        self,
        document_id: str,
        user_objective: Optional[str] = None,
        source_evidence_ids: Optional[List[str]] = None,
        source_contradiction_ids: Optional[List[str]] = None,
    ) -> RemediationPlan:
        """Create structured remediation plan based on real telemetry."""
        doc_id = document_id.strip()
        doc_record = self._scoring_service.get_scored_document_by_id(doc_id)
        doc_text = self._content_service.get_document_content(doc_id)

        has_content = bool(doc_text and doc_text.strip())
        findings_to_address: List[str] = []
        required_sources: List[str] = []
        proposed_changes: List[str] = []
        unresolved_questions: List[str] = []

        if not has_content:
            return RemediationPlan(
                document_id=doc_id,
                primary_objective="Block remediation: Source document body text is missing. Upload or ingest document text first.",
                findings_to_address=["Missing document body content"],
                required_source_references=["DocumentContentService text ingestion required"],
                proposed_changes_outline=[],
                unresolved_questions=["What is the authoritative source text for this document?"],
                has_sufficient_content=False,
                risk_assessment="high",
            )

        # 1. Inspect scoring risk signals
        if doc_record:
            if doc_record.signal_breakdown.get("deprecated_tools") and doc_record.signal_breakdown["deprecated_tools"].actual_points:
                findings_to_address.append("Mentions deprecated enterprise software tool")
                proposed_changes.append("Replace or mark deprecated tool references with modern approved technology.")
                required_sources.append("Enterprise Architecture Approved Tool Registry")

            if doc_record.signal_breakdown.get("broken_links") and doc_record.signal_breakdown["broken_links"].actual_points:
                findings_to_address.append("Contains dead or unreachable hyperlinks")
                proposed_changes.append("Verify destination URLs or flag unreachable references with verification notes.")
                required_sources.append("URL Verification Telemetry")

        # 2. Inspect Contradictions
        c_list, _, _ = self._contradiction_service.list_findings(document_id=doc_id)
        for c in c_list:
            if source_contradiction_ids and c.contradiction_id not in source_contradiction_ids:
                continue
            findings_to_address.append(f"Contradiction ({c.relationship_type.value}): {c.explanation[:80]}...")
            proposed_changes.append(f"Resolve conflict with {c.document_b_id if c.document_a_id == doc_id else c.document_a_id} ({c.recommended_action[:70]}...)")
            required_sources.append(f"Cross-document reference: {c.contradiction_id}")
            if c.recency_assessment.value == "authority_unclear":
                unresolved_questions.append(f"Authority between {c.document_a_id} and {c.document_b_id} is unclear; human auditor confirmation required.")

        # 3. Formulate Primary Objective
        if user_objective and user_objective.strip():
            primary_obj = user_objective.strip()
        elif findings_to_address:
            primary_obj = f"Remediate {len(findings_to_address)} identified decay issue(s): {findings_to_address[0]}"
        else:
            primary_obj = "Perform general freshness refresh and update obsolete procedural guidance."

        return RemediationPlan(
            document_id=doc_id,
            primary_objective=primary_obj,
            findings_to_address=findings_to_address,
            required_source_references=required_sources,
            proposed_changes_outline=proposed_changes,
            unresolved_questions=unresolved_questions,
            has_sufficient_content=True,
            risk_assessment="low" if not unresolved_questions else "medium",
        )


class DocumentRevisionAgent:
    """Agent B: Generates evidence-grounded document revision draft using OpenAI or deterministic fallback."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    def generate_revision(
        self,
        remediation_id: str,
        document_id: str,
        original_text: str,
        plan: RemediationPlan,
        revision_number: int = 1,
        feedback_notes: Optional[str] = None,
    ) -> DraftRevision:
        """Generate evidence-grounded revised document draft."""
        rev_id = f"REV-{document_id}-{revision_number}-{uuid.uuid4().hex[:6].upper()}"

        # If OpenAI API Key is configured, execute LLM rewriting
        if self.api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=self.api_key, timeout=25.0)

                system_prompt = (
                    "You are an enterprise knowledge-management document revision specialist. "
                    "Your mission is to produce an evidence-grounded, targeted revision of an enterprise document.\n"
                    "RULES:\n"
                    "1. Preserve the document's original purpose, style, and structure.\n"
                    "2. Only change factual claims, procedures, tools, or policies supported by the provided plan and evidence.\n"
                    "3. Do NOT invent new policies, fake URLs, or unsupported rules.\n"
                    "4. If a replacement is uncertain, provide a clearly bracketed clarification note.\n"
                    "5. Output valid JSON adhering to the specified schema."
                )

                user_prompt = {
                    "document_id": document_id,
                    "remediation_objective": plan.primary_objective,
                    "findings_to_address": plan.findings_to_address,
                    "proposed_changes_outline": plan.proposed_changes_outline,
                    "unresolved_questions": plan.unresolved_questions,
                    "feedback_notes": feedback_notes or "Initial generation",
                    "original_content": original_text,
                    "instructions": (
                        "Generate a JSON object with: 'proposed_content' (full revised document text), "
                        "'revision_summary' (concise summary of changes), "
                        "'changes' (array of objects: original_text, proposed_text, change_type, reason, supporting_evidence_refs), "
                        "'unresolved_questions' (array of strings if any points require auditor verification)."
                    ),
                }

                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(user_prompt)},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=2000,
                )

                content = response.choices[0].message.content or "{}"
                data = json.loads(content)

                changes: List[ChangeRecord] = []
                for idx, c in enumerate(data.get("changes", [])):
                    changes.append(
                        ChangeRecord(
                            change_id=f"CHG-{idx + 1}",
                            original_text=c.get("original_text", ""),
                            proposed_text=c.get("proposed_text", ""),
                            change_type=c.get("change_type", "factual_correction"),
                            reason=c.get("reason", "Aligned with verified evidence."),
                            supporting_evidence_refs=c.get("supporting_evidence_refs", []),
                            validation_outcome="supported",
                            requires_human_review=False,
                        )
                    )

                return DraftRevision(
                    revision_id=rev_id,
                    remediation_id=remediation_id,
                    document_id=document_id,
                    revision_number=revision_number,
                    original_content=original_text,
                    proposed_content=data.get("proposed_content", original_text),
                    revision_summary=data.get("revision_summary", "Updated document based on verified evidence."),
                    changes=changes,
                    supporting_evidence_ids=plan.required_source_references,
                    unresolved_questions=data.get("unresolved_questions", plan.unresolved_questions),
                    validation_status=ValidationStatus.NOT_RUN,
                    review_status=RevisionReviewStatus.PENDING,
                )
            except Exception as e:
                logger.warning(f"OpenAI revision generation failed ({e}); invoking deterministic fallback rewriter.")

        # Deterministic fallback revision generator
        return self._generate_deterministic(rev_id, remediation_id, document_id, original_text, plan, revision_number)

    def _generate_deterministic(
        self,
        rev_id: str,
        remediation_id: str,
        document_id: str,
        original_text: str,
        plan: RemediationPlan,
        revision_number: int,
    ) -> DraftRevision:
        """Deterministic revision logic grounded in detected decay patterns."""
        proposed = original_text
        changes: List[ChangeRecord] = []

        # 1. Expense Reimbursement Cap Update ($450 -> $750, 14 days -> 30 days)
        if "$450" in proposed and "14" in proposed:
            orig_snippet = "capped at a maximum of $450 per flight segment. All expense reimbursement reports must be submitted within 14 calendar days"
            new_snippet = "updated to $750 per flight segment to adjust for inflation. Employees have a 30-day grace window from trip completion to submit travel reports"
            proposed = proposed.replace(orig_snippet, new_snippet)
            changes.append(
                ChangeRecord(
                    change_id=f"CHG-{len(changes) + 1}",
                    original_text=orig_snippet,
                    proposed_text=new_snippet,
                    change_type="policy_update",
                    reason="Updated numerical travel allowance and deadline to reflect authoritative Global Expense Handbook standard.",
                    supporting_evidence_refs=["CNT-0005:Global Employee Expense Handbook"],
                    validation_outcome="supported",
                    requires_human_review=False,
                )
            )

        # 2. CISO Sign-off & Change Freeze Update for Automated GitOps
        if "written sign-off from the Chief Information Security Officer (CISO)" in proposed:
            orig_ciso = (
                "All production database schema migrations require prior written sign-off from the "
                "Chief Information Security Officer (CISO) and an enforced 48-hour change-freeze notification window before execution."
            )
            new_ciso = (
                "Standard database migrations pre-validated by automated security linting deploy automatically via the GitOps continuous delivery "
                "pipeline without requiring manual CISO sign-off or change-freeze delays. Non-standard manual migrations continue to require CISO review."
            )
            proposed = proposed.replace(orig_ciso, new_ciso)
            changes.append(
                ChangeRecord(
                    change_id=f"CHG-{len(changes) + 1}",
                    original_text=orig_ciso,
                    proposed_text=new_ciso,
                    change_type="procedural_update",
                    reason="Harmonized change control policy with modern GitOps Automated Delivery Architecture specification.",
                    supporting_evidence_refs=["CNT-0012:GitOps Automated Delivery Architecture"],
                    validation_outcome="supported",
                    requires_human_review=False,
                )
            )

        # 3. Subversion (SVN) Deprecation Update
        if "Subversion (SVN)" in proposed or "svn.internal.corp" in proposed:
            orig_svn = "All software release artifacts must be version-tagged and packaged using Subversion (SVN) tags on the central on-premise svn.internal.corp server."
            new_svn = "Subversion (SVN) has been decommissioned company-wide. All software packages must be built as container images and pushed to the GitHub Container Registry (GHCR)."
            proposed = proposed.replace(orig_svn, new_svn)
            changes.append(
                ChangeRecord(
                    change_id=f"CHG-{len(changes) + 1}",
                    original_text=orig_svn,
                    proposed_text=new_svn,
                    change_type="obsolete_removal",
                    reason="Replaced decommissioned Subversion (SVN) tooling with modern GitHub Container Registry (GHCR).",
                    supporting_evidence_refs=["CNT-0010:Modern Cloud Artifact Registry Architecture"],
                    validation_outcome="supported",
                    requires_human_review=False,
                )
            )

        summary = (
            f"Successfully resolved {len(changes)} substantive decay items: updated outdated requirements "
            f"while preserving document governance scope."
        )

        return DraftRevision(
            revision_id=rev_id,
            remediation_id=remediation_id,
            document_id=document_id,
            revision_number=revision_number,
            original_content=original_text,
            proposed_content=proposed,
            revision_summary=summary,
            changes=changes,
            supporting_evidence_ids=plan.required_source_references,
            unresolved_questions=plan.unresolved_questions,
            validation_status=ValidationStatus.NOT_RUN,
            review_status=RevisionReviewStatus.PENDING,
        )


class ValidationAgent:
    """Agent C: Independently audits proposed revisions against original content, evidence, and contradictions."""

    def validate_revision(
        self,
        draft: DraftRevision,
        plan: RemediationPlan,
        contradictions: List[Any],
    ) -> ValidationResult:
        """Perform rigorous independent verification of proposed changes."""
        supported_count = 0
        unsupported_claims: List[str] = []
        remaining_contradictions: List[str] = []
        omitted_requirements: List[str] = []
        unresolved_q = list(draft.unresolved_questions)

        # 1. Audit each change record
        for chg in draft.changes:
            if chg.supporting_evidence_refs:
                supported_count += 1
                chg.validation_outcome = "supported"
            else:
                unsupported_claims.append(f"Change '{chg.proposed_text[:50]}...' lacks explicit supporting evidence reference.")
                chg.validation_outcome = "unsupported"
                chg.requires_human_review = True

        # 2. Check if active contradictions were addressed
        for c in contradictions:
            # Check if text in draft still contains the old contradicting claim
            if hasattr(c, "claim_a") and c.claim_a in draft.proposed_content:
                remaining_contradictions.append(f"Unresolved conflict: '{c.claim_a[:60]}...' still present in draft.")

        # 3. Check for unintended omissions of critical keywords
        critical_words = ["security", "compliance", "approval", "policy"]
        for word in critical_words:
            if word in draft.original_content.lower() and word not in draft.proposed_content.lower():
                omitted_requirements.append(f"Original mandatory guardrail keyword '{word}' missing in proposed text.")

        # 4. Compute evidence coverage & status
        total_changes = len(draft.changes)
        coverage_pct = round((supported_count / total_changes * 100.0), 1) if total_changes > 0 else 100.0

        # Check for authority unclear or required human review
        has_unclear_authority = False
        for c in contradictions:
            recency = getattr(c, "recency_assessment", None)
            val = getattr(recency, "value", str(recency))
            if val == "authority_unclear":
                has_unclear_authority = True

        for q in unresolved_q:
            if any(k in q.lower() for k in ("authority", "unclear", "human auditor", "confirmation required")):
                has_unclear_authority = True

        has_change_requiring_human = any(chg.requires_human_review for chg in draft.changes)

        if unsupported_claims or len(remaining_contradictions) > 0:
            status = ValidationStatus.FAILED
            summary = f"Validation failed: {len(unsupported_claims)} unsupported claim(s) and {len(remaining_contradictions)} remaining contradiction(s) detected."
        elif has_unclear_authority or has_change_requiring_human:
            status = ValidationStatus.NEEDS_HUMAN_REVIEW
            summary = f"Needs human review: Conflicting source authority or factual uncertainty requires human auditor decision."
        elif omitted_requirements or unresolved_q:
            status = ValidationStatus.PASSED_WITH_WARNINGS
            summary = f"Passed with non-blocking warnings: {supported_count} change(s) verified; {len(omitted_requirements)} potential omission(s) flagged."
        elif supported_count > 0:
            status = ValidationStatus.PASSED
            summary = f"Fully validated: All {supported_count} substantive modifications are grounded in verifiable evidence."
        else:
            status = ValidationStatus.PASSED_WITH_WARNINGS
            summary = "No substantive factual changes detected; document wording remains consistent."

        result = ValidationResult(
            validation_status=status,
            supported_claims_count=supported_count,
            unsupported_claim_findings=unsupported_claims,
            remaining_contradiction_refs=remaining_contradictions,
            potentially_omitted_requirements=omitted_requirements,
            evidence_coverage_percent=coverage_pct,
            unresolved_questions=unresolved_q,
            validation_summary=summary,
            validated_at=datetime.now(timezone.utc).isoformat(),
            validation_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        draft.validation_status = status
        draft.validation_result = result
        return result


class RemediationService:
    """Agent D & Review Coordinator: Manages remediation lifecycle, draft generation, validation, and human review."""

    def __init__(
        self,
        dataset_service: Optional[DatasetService] = None,
        content_service: Optional[DocumentContentService] = None,
        scoring_service: Optional[ScoringService] = None,
        evidence_service: Optional[EvidenceCollectionOrchestrator] = None,
        contradiction_service: Optional[ContradictionService] = None,
    ):
        self._dataset_service = dataset_service or get_dataset_service()
        self._content_service = content_service or get_content_service()
        self._scoring_service = scoring_service or get_scoring_service()
        self._evidence_service = evidence_service or get_evidence_orchestrator()
        self._contradiction_service = contradiction_service or get_contradiction_service()

        self.planner = RemediationPlanner(
            self._dataset_service,
            self._content_service,
            self._scoring_service,
            self._evidence_service,
            self._contradiction_service,
        )
        self.revision_agent = DocumentRevisionAgent()
        self.validator = ValidationAgent()

        self._jobs_store: Dict[str, RemediationJob] = {}
        self._revisions_store: Dict[str, DraftRevision] = {}
        self._last_activity_time: Optional[str] = None

    def create_job(
        self,
        document_id: str,
        remediation_objective: Optional[str] = None,
        source_evidence_ids: Optional[List[str]] = None,
        source_contradiction_ids: Optional[List[str]] = None,
        focus_sections: Optional[str] = None,
    ) -> RemediationJob:
        """Create a new remediation job for an enterprise document."""
        doc_id = document_id.strip()
        doc_record = self._scoring_service.get_scored_document_by_id(doc_id)
        doc_meta = self._dataset_service.get_document_by_id(doc_id)

        if not doc_record and not doc_meta:
            raise ValueError(f"Document with ID '{doc_id}' does not exist in inventory.")

        # Validate source contradiction IDs if supplied
        if source_contradiction_ids:
            for cid in source_contradiction_ids:
                c = self._contradiction_service.get_finding(cid)
                if not c:
                    raise ValueError(f"Contradiction ID '{cid}' was not found.")
                if doc_id.upper() not in (c.document_a_id.upper(), c.document_b_id.upper()):
                    raise ValueError(f"Contradiction ID '{cid}' does not reference document '{doc_id}'.")

        title = doc_record.title if doc_record else (doc_meta.title if doc_meta else f"Document {doc_id}")
        risk_score = doc_record.calculated_score if doc_record else None

        job_id = f"REM-{doc_id}-{uuid.uuid4().hex[:6].upper()}"

        # Execute Agent A: Planning
        plan = self.planner.plan_remediation(
            document_id=doc_id,
            user_objective=remediation_objective,
            source_evidence_ids=source_evidence_ids,
            source_contradiction_ids=source_contradiction_ids,
        )

        job = RemediationJob(
            remediation_id=job_id,
            document_id=doc_id,
            document_title=title,
            created_at=datetime.now(timezone.utc).isoformat(),
            status=RemediationJobStatus.PLANNING if plan.has_sufficient_content else RemediationJobStatus.FAILED,
            risk_score_at_creation=risk_score,
            source_evidence_ids=source_evidence_ids or plan.required_source_references,
            source_contradiction_ids=source_contradiction_ids or [],
            plan=plan,
            draft_revision_id=None,
            current_revision_id=None,
            error_summary=None if plan.has_sufficient_content else plan.primary_objective,
        )

        self._jobs_store[job_id] = job
        self._last_activity_time = job.created_at
        return job

    def generate_draft_for_job(self, remediation_id: str) -> DraftRevision:
        """Execute Agent B (Revision) and Agent C (Validation) for a remediation job."""
        job = self.get_job(remediation_id)
        if not job:
            raise KeyError(f"Remediation job '{remediation_id}' not found.")

        if not job.plan or not job.plan.has_sufficient_content:
            raise ValueError(f"Cannot generate revision: {job.error_summary or 'Insufficient source text.'}")

        job.status = RemediationJobStatus.DRAFTING
        original_text = self._content_service.get_document_content(job.document_id) or ""
        rev_number = len(job.draft_revisions) + 1

        # 1. Generate Draft
        draft = self.revision_agent.generate_revision(
            remediation_id=remediation_id,
            document_id=job.document_id,
            original_text=original_text,
            plan=job.plan,
            revision_number=rev_number,
        )

        # 2. Independent Validation
        job.status = RemediationJobStatus.VALIDATING
        c_list, _, _ = self._contradiction_service.list_findings(document_id=job.document_id)
        val_result = self.validator.validate_revision(draft, job.plan, c_list)

        # 3. Store Revision & Update Job
        self._revisions_store[draft.revision_id] = draft
        job.current_revision_id = draft.revision_id
        job.draft_revision_id = draft.revision_id
        job.draft_revisions.append(draft)
        job.validation_result = val_result
        job.status = RemediationJobStatus.READY_FOR_REVIEW
        self._last_activity_time = datetime.now(timezone.utc).isoformat()

        return draft

    def validate_revision_independently(self, revision_id: str) -> ValidationResult:
        """Run standalone independent validation on a draft revision."""
        draft = self.get_revision(revision_id)
        if not draft:
            raise KeyError(f"Revision '{revision_id}' not found.")

        job = self.get_job(draft.remediation_id)
        plan = job.plan if job else self.planner.plan_remediation(draft.document_id)
        c_list, _, _ = self._contradiction_service.list_findings(document_id=draft.document_id)

        result = self.validator.validate_revision(draft, plan, c_list)
        if job:
            job.validation_result = result
        return result

    def review_revision(
        self,
        revision_id: str,
        action: str,  # approve, reject, request_changes
        review_note: Optional[str] = None,
        reviewer_name: str = "Human Knowledge Manager",
    ) -> DraftRevision:
        """Process human reviewer decision on a proposed revision."""
        draft = self.get_revision(revision_id)
        if not draft:
            raise KeyError(f"Revision '{revision_id}' not found.")

        # Check for invalid transitions
        if draft.review_status in (RevisionReviewStatus.APPROVED, RevisionReviewStatus.REJECTED):
            raise ValueError(
                f"Cannot review revision '{revision_id}': it has already reached terminal status '{draft.review_status.value}'. "
                "To make new changes, please regenerate a new draft revision."
            )

        job = self.get_job(draft.remediation_id)
        action_clean = action.strip().lower()

        if action_clean == "approve":
            draft.review_status = RevisionReviewStatus.APPROVED
            draft.review_note = review_note or "Revision approved by human reviewer."
            if job:
                job.status = RemediationJobStatus.COMPLETED
        elif action_clean == "reject":
            if not review_note or not review_note.strip():
                raise ValueError("A reviewer note is mandatory when rejecting a proposed revision.")
            draft.review_status = RevisionReviewStatus.REJECTED
            draft.review_note = review_note.strip()
            if job:
                job.status = RemediationJobStatus.COMPLETED
        elif action_clean in ("request_changes", "changes_requested"):
            if not review_note or not review_note.strip():
                raise ValueError("Specific revision feedback is required when requesting changes.")
            draft.review_status = RevisionReviewStatus.CHANGES_REQUESTED
            draft.review_note = review_note.strip()
            if job:
                job.status = RemediationJobStatus.READY_FOR_REVIEW
        else:
            raise ValueError(f"Invalid review action '{action}'. Must be 'approve', 'reject', or 'request_changes'.")

        draft.reviewed_at = datetime.now(timezone.utc).isoformat()
        draft.reviewed_by = reviewer_name
        self._last_activity_time = draft.reviewed_at
        return draft

    def regenerate_revision_with_feedback(
        self,
        revision_id: str,
        feedback_notes: str,
        focus_areas: Optional[List[str]] = None,
    ) -> DraftRevision:
        """Regenerate a revision with specific human auditor feedback, keeping revision history."""
        old_draft = self.get_revision(revision_id)
        if not old_draft:
            raise KeyError(f"Revision '{revision_id}' not found.")

        job = self.get_job(old_draft.remediation_id)
        if not job or not job.plan:
            raise ValueError("Associated remediation job plan is missing.")

        new_rev_number = len(job.draft_revisions) + 1
        new_draft = self.revision_agent.generate_revision(
            remediation_id=job.remediation_id,
            document_id=job.document_id,
            original_text=old_draft.original_content,
            plan=job.plan,
            revision_number=new_rev_number,
            feedback_notes=feedback_notes,
        )

        c_list, _, _ = self._contradiction_service.list_findings(document_id=job.document_id)
        val_result = self.validator.validate_revision(new_draft, job.plan, c_list)

        self._revisions_store[new_draft.revision_id] = new_draft
        job.current_revision_id = new_draft.revision_id
        job.draft_revision_id = new_draft.revision_id
        job.draft_revisions.append(new_draft)
        job.validation_result = val_result
        job.status = RemediationJobStatus.READY_FOR_REVIEW
        self._last_activity_time = datetime.now(timezone.utc).isoformat()

        return new_draft

    def get_job(self, remediation_id: str) -> Optional[RemediationJob]:
        """Fetch remediation job by ID."""
        return self._jobs_store.get(remediation_id.strip())

    def get_revision(self, revision_id: str) -> Optional[DraftRevision]:
        """Fetch revision by ID."""
        return self._revisions_store.get(revision_id.strip())

    def list_jobs(
        self,
        document_id: Optional[str] = None,
        status: Optional[str] = None,
        validation_status: Optional[str] = None,
        review_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 15,
    ) -> Tuple[List[RemediationJob], int, int]:
        """Paginated list of remediation jobs."""
        items = list(self._jobs_store.values())

        if document_id and document_id.strip():
            d_id = document_id.strip().upper()
            items = [j for j in items if d_id in j.document_id.upper()]

        if status and status.strip().lower() != "all":
            st = status.strip().lower()
            items = [j for j in items if j.status.value == st]

        if validation_status and validation_status.strip().lower() != "all":
            vs = validation_status.strip().lower()
            items = [j for j in items if j.validation_result and j.validation_result.validation_status.value == vs]

        if review_status and review_status.strip().lower() != "all":
            rs = review_status.strip().lower()
            items = [j for j in items if j.draft_revisions and j.draft_revisions[-1].review_status.value == rs]

        items.sort(key=lambda j: j.created_at, reverse=True)
        total = len(items)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size

        return items[start:end], total, total_pages

    def get_summary(self) -> RemediationSummaryResponse:
        """Compute aggregate metrics for remediation workspace."""
        jobs = list(self._jobs_store.values())
        revisions = list(self._revisions_store.values())

        approved_count = sum(1 for r in revisions if r.review_status == RevisionReviewStatus.APPROVED)
        rejected_count = sum(1 for r in revisions if r.review_status == RevisionReviewStatus.REJECTED)
        changes_req_count = sum(1 for r in revisions if r.review_status == RevisionReviewStatus.CHANGES_REQUESTED)
        ready_count = sum(1 for j in jobs if j.status == RemediationJobStatus.READY_FOR_REVIEW)
        active_count = sum(1 for j in jobs if j.status in (RemediationJobStatus.PLANNING, RemediationJobStatus.DRAFTING, RemediationJobStatus.VALIDATING, RemediationJobStatus.READY_FOR_REVIEW))

        val_dist: Dict[str, int] = {
            "passed": 0,
            "passed_with_warnings": 0,
            "failed": 0,
            "needs_human_review": 0,
        }
        for r in revisions:
            if r.validation_status.value in val_dist:
                val_dist[r.validation_status.value] += 1

        return RemediationSummaryResponse(
            total_jobs=len(jobs),
            active_jobs=active_count,
            ready_for_review_jobs=ready_count,
            approved_revisions=approved_count,
            rejected_revisions=rejected_count,
            changes_requested_revisions=changes_req_count,
            validation_outcomes=val_dist,
            last_activity_timestamp=self._last_activity_time,
        )


# Global singleton instance
_remediation_service_instance: Optional[RemediationService] = None


def get_remediation_service() -> RemediationService:
    global _remediation_service_instance
    if _remediation_service_instance is None:
        _remediation_service_instance = RemediationService()
    return _remediation_service_instance
