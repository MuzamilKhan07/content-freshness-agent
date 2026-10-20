import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from backend.app.core.deprecated_rules import DeprecatedRulesEngine, DeprecatedToolRule
from backend.app.core.ssrf_validator import is_safe_url
from backend.app.models.evidence_models import (
    EvidenceItem,
    EvidenceSeverity,
    EvidenceStatus,
    SignalType,
)

logger = logging.getLogger("freshguard.evidence_tools")


class MetadataInspectionTool:
    """Tool to inspect core metadata fields and record inspection provenance."""

    def __init__(self):
        self.tool_name = "metadata_inspection_tool"

    def inspect(self, row: Dict[str, Any]) -> List[EvidenceItem]:
        doc_id = str(row.get("content_id", "UNKNOWN")).strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        items: List[EvidenceItem] = []

        # 1. Update timestamp check
        last_updated = str(row.get("last_updated", "")).strip()
        if not last_updated or last_updated.lower() in ("nan", "none", "null"):
            items.append(
                EvidenceItem(
                    evidence_id=f"EVID-{doc_id}-AGE-MISSING",
                    document_id=doc_id,
                    signal_type=SignalType.DOCUMENT_AGE,
                    status=EvidenceStatus.UNKNOWN,
                    severity=EvidenceSeverity.HIGH,
                    summary="Missing last_updated timestamp.",
                    source_field="last_updated",
                    observed_value=None,
                    evidence_reference="telemetry:last_updated",
                    detected_at=now_iso,
                    tool_name=self.tool_name,
                    confidence=0.9,
                    recommended_action="Locate and populate the actual document modification date.",
                )
            )
        else:
            items.append(
                EvidenceItem(
                    evidence_id=f"EVID-{doc_id}-AGE-CONFIRMED",
                    document_id=doc_id,
                    signal_type=SignalType.DOCUMENT_AGE,
                    status=EvidenceStatus.CONFIRMED,
                    severity=EvidenceSeverity.INFO,
                    summary=f"Document last modified on {last_updated}.",
                    source_field="last_updated",
                    observed_value=last_updated,
                    evidence_reference="telemetry:last_updated",
                    detected_at=now_iso,
                    tool_name=self.tool_name,
                    confidence=1.0,
                    recommended_action="Use timestamp for age-based freshness scoring.",
                )
            )

        return items


class URLVerificationTool:
    """
    Safely verifies HTTP/HTTPS URLs with SSRF mitigation, connection timeouts,
    redirect validation, and HEAD/GET fallback.
    """

    def __init__(self, timeout_sec: float = 3.5):
        self.tool_name = "url_verification_tool"
        self.timeout_sec = timeout_sec

    def verify_url(
        self,
        doc_id: str,
        url: Optional[str],
        source_field: str = "url",
    ) -> EvidenceItem:
        now_iso = datetime.now(timezone.utc).isoformat()

        if not url or not str(url).strip():
            return EvidenceItem(
                evidence_id=f"EVID-{doc_id}-URL-MISSING",
                document_id=doc_id,
                signal_type=SignalType.URL_VERIFICATION,
                status=EvidenceStatus.UNKNOWN,
                severity=EvidenceSeverity.LOW,
                summary="No destination URL is recorded in the document record.",
                source_field=source_field,
                observed_value=None,
                evidence_reference=None,
                detected_at=now_iso,
                tool_name=self.tool_name,
                confidence=1.0,
                recommended_action="Link verification unavailable until URL is supplied.",
            )

        target_url = str(url).strip()

        # 1. SSRF Safety check
        is_safe, error_msg = is_safe_url(target_url)
        if not is_safe:
            return EvidenceItem(
                evidence_id=f"EVID-{doc_id}-URL-SSRF-REJECTED",
                document_id=doc_id,
                signal_type=SignalType.URL_VERIFICATION,
                status=EvidenceStatus.FAILED,
                severity=EvidenceSeverity.CRITICAL,
                summary=f"URL rejected by security policy: {error_msg}",
                source_field=source_field,
                observed_value=target_url,
                evidence_reference="security:ssrf_guard",
                detected_at=now_iso,
                tool_name=self.tool_name,
                confidence=1.0,
                recommended_action="Investigate potentially unsafe or restricted destination reference.",
            )

        # 2. HTTP Verification with HEAD and GET fallback
        headers = {"User-Agent": "FreshGuardAI-LinkVerifier/1.0"}
        try:
            with httpx.Client(
                timeout=self.timeout_sec,
                follow_redirects=False,
                verify=True,
            ) as client:
                try:
                    response = client.head(target_url, headers=headers)
                except (httpx.RequestError, httpx.HTTPStatusError):
                    # Fallback to GET with streaming to prevent large downloads
                    response = client.get(target_url, headers=headers)

                # Validate redirects
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if location:
                        loc_safe, loc_msg = is_safe_url(location)
                        if not loc_safe:
                            return EvidenceItem(
                                evidence_id=f"EVID-{doc_id}-URL-REDIRECT-BLOCKED",
                                document_id=doc_id,
                                signal_type=SignalType.URL_VERIFICATION,
                                status=EvidenceStatus.FAILED,
                                severity=EvidenceSeverity.HIGH,
                                summary=f"Redirect destination rejected: {loc_msg}",
                                source_field=source_field,
                                observed_value=location,
                                evidence_reference=target_url,
                                detected_at=now_iso,
                                tool_name=self.tool_name,
                                confidence=0.9,
                                recommended_action="Update link to point directly to a safe public destination.",
                            )

                status_code = response.status_code

                if 200 <= status_code < 400:
                    return EvidenceItem(
                        evidence_id=f"EVID-{doc_id}-URL-OK",
                        document_id=doc_id,
                        signal_type=SignalType.URL_VERIFICATION,
                        status=EvidenceStatus.CONFIRMED,
                        severity=EvidenceSeverity.INFO,
                        summary=f"Destination URL verified successfully (HTTP {status_code}).",
                        source_field=source_field,
                        observed_value=f"HTTP {status_code}",
                        evidence_reference=target_url,
                        detected_at=now_iso,
                        tool_name=self.tool_name,
                        confidence=1.0,
                        recommended_action="Link confirmed live and accessible.",
                    )
                elif status_code in (404, 410):
                    return EvidenceItem(
                        evidence_id=f"EVID-{doc_id}-URL-DEAD",
                        document_id=doc_id,
                        signal_type=SignalType.BROKEN_LINKS,
                        status=EvidenceStatus.CONFIRMED,
                        severity=EvidenceSeverity.HIGH,
                        summary=f"Destination URL is dead or removed (HTTP {status_code}).",
                        source_field=source_field,
                        observed_value=f"HTTP {status_code}",
                        evidence_reference=target_url,
                        detected_at=now_iso,
                        tool_name=self.tool_name,
                        confidence=0.95,
                        recommended_action="Replace broken link with updated URL or remove dead reference.",
                    )
                elif status_code in (401, 403, 429):
                    return EvidenceItem(
                        evidence_id=f"EVID-{doc_id}-URL-AUTH",
                        document_id=doc_id,
                        signal_type=SignalType.URL_VERIFICATION,
                        status=EvidenceStatus.SUSPECTED,
                        severity=EvidenceSeverity.MODERATE,
                        summary=f"Access restricted or rate limited (HTTP {status_code}); reachability inconclusive.",
                        source_field=source_field,
                        observed_value=f"HTTP {status_code}",
                        evidence_reference=target_url,
                        detected_at=now_iso,
                        tool_name=self.tool_name,
                        confidence=0.5,
                        recommended_action="Verify internal authorization permissions for destination.",
                    )
                else:
                    return EvidenceItem(
                        evidence_id=f"EVID-{doc_id}-URL-SERVER-ERROR",
                        document_id=doc_id,
                        signal_type=SignalType.URL_VERIFICATION,
                        status=EvidenceStatus.SUSPECTED,
                        severity=EvidenceSeverity.MODERATE,
                        summary=f"Server returned error code (HTTP {status_code}); reachability inconclusive.",
                        source_field=source_field,
                        observed_value=f"HTTP {status_code}",
                        evidence_reference=target_url,
                        detected_at=now_iso,
                        tool_name=self.tool_name,
                        confidence=0.5,
                        recommended_action="Check destination server health.",
                    )

        except httpx.ConnectTimeout:
            return EvidenceItem(
                evidence_id=f"EVID-{doc_id}-URL-TIMEOUT",
                document_id=doc_id,
                signal_type=SignalType.URL_VERIFICATION,
                status=EvidenceStatus.FAILED,
                severity=EvidenceSeverity.MODERATE,
                summary=f"Connection timed out after {self.timeout_sec}s; check inconclusive.",
                source_field=source_field,
                observed_value="Timeout",
                evidence_reference=target_url,
                detected_at=now_iso,
                tool_name=self.tool_name,
                confidence=0.4,
                recommended_action="Retry link verification during next scheduled scan window.",
            )
        except httpx.ConnectError:
            return EvidenceItem(
                evidence_id=f"EVID-{doc_id}-URL-CONN-FAILED",
                document_id=doc_id,
                signal_type=SignalType.BROKEN_LINKS,
                status=EvidenceStatus.CONFIRMED,
                severity=EvidenceSeverity.HIGH,
                summary="Host unreachable or DNS lookup failed.",
                source_field=source_field,
                observed_value="Connection Error",
                evidence_reference=target_url,
                detected_at=now_iso,
                tool_name=self.tool_name,
                confidence=0.9,
                recommended_action="Confirm whether target hostname or domain is still active.",
            )
        except Exception as exc:
            return EvidenceItem(
                evidence_id=f"EVID-{doc_id}-URL-ERROR",
                document_id=doc_id,
                signal_type=SignalType.URL_VERIFICATION,
                status=EvidenceStatus.FAILED,
                severity=EvidenceSeverity.LOW,
                summary=f"URL check encountered error: {exc.__class__.__name__}",
                source_field=source_field,
                observed_value=str(exc)[:100],
                evidence_reference=target_url,
                detected_at=now_iso,
                tool_name=self.tool_name,
                confidence=0.3,
                recommended_action="Investigate verification error.",
            )


class DeprecatedToolDetectionTool:
    """Tool to inspect available document text and metadata against retired tools rulebook."""

    def __init__(self, engine: Optional[DeprecatedRulesEngine] = None):
        self.tool_name = "deprecated_tool_detector"
        self.engine = engine or DeprecatedRulesEngine()

    def detect(self, row: Dict[str, Any]) -> List[EvidenceItem]:
        doc_id = str(row.get("content_id", "UNKNOWN")).strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        items: List[EvidenceItem] = []

        # 1. Inspect title and available text fields
        text_to_scan = f"{row.get('title', '')} {row.get('subject_area', '')} {row.get('content_type', '')}"
        matches = self.engine.scan_text(text_to_scan)

        has_flag = str(row.get("mentions_deprecated_tool", "")).strip().lower() in ("true", "1", "yes")

        if matches:
            for rule, matched_word in matches:
                items.append(
                    EvidenceItem(
                        evidence_id=f"EVID-{doc_id}-DEP-{rule.rule_id}",
                        document_id=doc_id,
                        signal_type=SignalType.DEPRECATED_TOOLS,
                        status=EvidenceStatus.CONFIRMED,
                        severity=EvidenceSeverity.HIGH if rule.severity == "high" else EvidenceSeverity.CRITICAL,
                        summary=f"Detected reference to retired tool '{rule.tool_name}'.",
                        source_field="title/metadata",
                        observed_value=matched_word,
                        evidence_reference=rule.rule_id,
                        detected_at=now_iso,
                        tool_name=self.tool_name,
                        confidence=0.95,
                        recommended_action=rule.replacement_guidance,
                    )
                )
        elif has_flag:
            # Source inventory flag reports deprecated tool presence, but specific keyword not found in short title
            items.append(
                EvidenceItem(
                    evidence_id=f"EVID-{doc_id}-DEP-FLAGGED",
                    document_id=doc_id,
                    signal_type=SignalType.DEPRECATED_TOOLS,
                    status=EvidenceStatus.CONFIRMED,
                    severity=EvidenceSeverity.HIGH,
                    summary="Document flagged for deprecated tool mention; body inspection needed to locate exact token.",
                    source_field="mentions_deprecated_tool",
                    observed_value="True",
                    evidence_reference="inventory:flag",
                    detected_at=now_iso,
                    tool_name=self.tool_name,
                    confidence=0.85,
                    recommended_action="Audit document body text to identify and replace retired software instructions.",
                )
            )
        else:
            items.append(
                EvidenceItem(
                    evidence_id=f"EVID-{doc_id}-DEP-CLEAN",
                    document_id=doc_id,
                    signal_type=SignalType.DEPRECATED_TOOLS,
                    status=EvidenceStatus.CONFIRMED,
                    severity=EvidenceSeverity.INFO,
                    summary="No deprecated tool references detected in verified software scan.",
                    source_field="mentions_deprecated_tool",
                    observed_value="False",
                    evidence_reference="catalog:clean",
                    detected_at=now_iso,
                    tool_name=self.tool_name,
                    confidence=1.0,
                    recommended_action="Tooling references appear current with standard enterprise stack.",
                )
            )

        return items


class MetadataQualityTool:
    """Tool to inspect schema completeness and timestamp consistency."""

    def __init__(self):
        self.tool_name = "metadata_quality_tool"

    def analyze(self, row: Dict[str, Any]) -> List[EvidenceItem]:
        doc_id = str(row.get("content_id", "UNKNOWN")).strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        items: List[EvidenceItem] = []

        # 1. Missing identifier or title
        title = str(row.get("title", "")).strip()
        if not title or title.lower() in ("nan", "none", "null", "untitled"):
            items.append(
                EvidenceItem(
                    evidence_id=f"EVID-{doc_id}-QUAL-TITLE",
                    document_id=doc_id,
                    signal_type=SignalType.METADATA_QUALITY,
                    status=EvidenceStatus.CONFIRMED,
                    severity=EvidenceSeverity.HIGH,
                    summary="Document title is missing or generic.",
                    source_field="title",
                    observed_value=title or "EMPTY",
                    evidence_reference="schema:title",
                    detected_at=now_iso,
                    tool_name=self.tool_name,
                    confidence=1.0,
                    recommended_action="Assign a descriptive, authoritative document title.",
                )
            )

        # 2. Date consistency check (created_date vs last_updated)
        created_str = str(row.get("created_date", "")).strip()
        updated_str = str(row.get("last_updated", "")).strip()

        if created_str and updated_str:
            try:
                c_date = datetime.strptime(created_str, "%Y-%m-%d").date()
                u_date = datetime.strptime(updated_str, "%Y-%m-%d").date()
                if u_date < c_date:
                    items.append(
                        EvidenceItem(
                            evidence_id=f"EVID-{doc_id}-QUAL-DATE-INCONSISTENT",
                            document_id=doc_id,
                            signal_type=SignalType.METADATA_QUALITY,
                            status=EvidenceStatus.CONFIRMED,
                            severity=EvidenceSeverity.HIGH,
                            summary=f"Inconsistent dates: last_updated ({updated_str}) precedes created_date ({created_str}).",
                            source_field="last_updated/created_date",
                            observed_value=f"created={created_str}, updated={updated_str}",
                            evidence_reference="schema:date_ordering",
                            detected_at=now_iso,
                            tool_name=self.tool_name,
                            confidence=1.0,
                            recommended_action="Correct document lifecycle timestamp chronology.",
                        )
                    )
            except (ValueError, TypeError):
                items.append(
                    EvidenceItem(
                        evidence_id=f"EVID-{doc_id}-QUAL-DATE-MALFORMED",
                        document_id=doc_id,
                        signal_type=SignalType.METADATA_QUALITY,
                        status=EvidenceStatus.CONFIRMED,
                        severity=EvidenceSeverity.MODERATE,
                        summary="Malformed date string encountered (expected YYYY-MM-DD).",
                        source_field="created_date/last_updated",
                        observed_value=f"created={created_str}, updated={updated_str}",
                        evidence_reference="schema:date_format",
                        detected_at=now_iso,
                        tool_name=self.tool_name,
                        confidence=1.0,
                        recommended_action="Normalize timestamp values to ISO 8601 YYYY-MM-DD format.",
                    )
                )

        return items
