import logging
import re
import urllib.parse
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import httpx

from backend.app.core.deprecated_rules import DeprecatedRulesEngine
from backend.app.core.ssrf_validator import is_safe_url
from backend.app.models.url_inspection_models import (
    DeprecatedToolFinding,
    ExtractedLinkResult,
    ImportScannedUrlRequest,
    MetadataQualityFinding,
    UrlInspectionResponse,
)
from backend.app.services.dataset_service import DatasetService, get_dataset_service
from backend.app.services.content_service import (
    DocumentContentService,
    get_content_service,
)
from backend.app.services.scoring_service import ScoringService, get_scoring_service

logger = logging.getLogger("freshguard.url_scanner")


class SimpleHtmlExtractor(HTMLParser):
    """Safe, lightweight streaming HTML parser using standard library."""

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.title = ""
        self.description = ""
        self.author = ""
        self.modified_date = ""
        self.links: List[Tuple[str, str]] = []  # (url, anchor_text)
        self.text_chunks: List[str] = []

        self._in_title = False
        self._in_script_or_style = False
        self._current_a_href: Optional[str] = None
        self._current_a_text: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        tag_lower = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag_lower in ("script", "style", "noscript", "svg"):
            self._in_script_or_style = True
            return

        if tag_lower == "title":
            self._in_title = True
        elif tag_lower == "meta":
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            content = attr_dict.get("content", "").strip()

            if name == "description" or prop == "og:description":
                if not self.description:
                    self.description = content
            elif name in ("author", "creator") or prop == "article:author":
                if not self.author:
                    self.author = content
            elif name in ("date", "last-modified", "revised") or prop in (
                "article:modified_time",
                "article:published_time",
                "og:updated_time",
            ):
                if not self.modified_date:
                    self.modified_date = content
        elif tag_lower == "a":
            href = attr_dict.get("href", "").strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                # Resolve relative URL to absolute
                resolved = urllib.parse.urljoin(self.base_url, href)
                self._current_a_href = resolved
                self._current_a_text = []

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg"):
            self._in_script_or_style = False
        elif tag_lower == "title":
            self._in_title = False
        elif tag_lower == "a":
            if self._current_a_href:
                anchor = " ".join(self._current_a_text).strip()
                self.links.append((self._current_a_href, anchor))
                self._current_a_href = None
                self._current_a_text = []

    def handle_data(self, data: str):
        if self._in_script_or_style:
            return
        cleaned = data.strip()
        if not cleaned:
            return

        if self._in_title:
            self.title += " " + cleaned
        else:
            self.text_chunks.append(cleaned)

        if self._current_a_href is not None:
            self._current_a_text.append(cleaned)


class UrlScannerService:
    """Service to safely inspect, extract, and audit external URLs and webpages."""

    def __init__(
        self,
        dataset_service: Optional[DatasetService] = None,
        content_service: Optional[DocumentContentService] = None,
        scoring_service: Optional[ScoringService] = None,
    ):
        self.dep_engine = DeprecatedRulesEngine()
        self.dataset_service = dataset_service or get_dataset_service()
        self.content_service = content_service or get_content_service()
        self.scoring_service = scoring_service or get_scoring_service()

    def inspect_url(
        self,
        target_url: str,
        check_links: bool = True,
        max_links_to_check: int = 15,
    ) -> UrlInspectionResponse:
        """Inspect a webpage URL, extracting broken links, deprecated tools, and metadata quality."""
        cleaned_url = target_url.strip()
        if not cleaned_url.startswith(("http://", "https://")):
            cleaned_url = "https://" + cleaned_url

        # 1. SSRF Safety Check
        is_safe, error_msg = is_safe_url(cleaned_url)
        if not is_safe:
            return UrlInspectionResponse(
                url=cleaned_url,
                status="error",
                page_title="Security Blocked",
                error_message=f"SSRF Policy Blocked: {error_msg}",
                freshness_score=100.0,
                risk_level="Critical",
            )

        # 2. Fetch HTML content
        headers = {
            "User-Agent": "FreshGuardAI-ContentAuditor/1.0 (+https://github.com/khan007913/content-freshness-agent)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(
                timeout=6.0,
                follow_redirects=True,
                headers=headers,
                verify=True,
            ) as client:
                resp = client.get(cleaned_url)
                status_code = resp.status_code

                if status_code >= 400:
                    return UrlInspectionResponse(
                        url=cleaned_url,
                        status="error",
                        status_code=status_code,
                        page_title=f"HTTP {status_code} Error",
                        error_message=f"Web server returned HTTP {status_code}",
                        freshness_score=90.0,
                        risk_level="Critical",
                        broken_links_count=1,
                    )

                html_text = resp.text[:1_000_000]  # Max 1MB
                last_modified_header = resp.headers.get("last-modified")

        except Exception as e:
            logger.warning(f"Failed to fetch URL {cleaned_url}: {e}")
            return UrlInspectionResponse(
                url=cleaned_url,
                status="error",
                page_title="Connection Failed",
                error_message=f"Network error: {str(e)}",
                freshness_score=95.0,
                risk_level="Critical",
            )

        # 3. Parse HTML
        parser = SimpleHtmlExtractor(base_url=cleaned_url)
        try:
            parser.feed(html_text)
        except Exception as e:
            logger.debug(f"HTML parsing note: {e}")

        page_title = parser.title.strip() or "Untitled Webpage"
        page_description = parser.description.strip() or None
        page_author = parser.author.strip() or None
        last_modified = parser.modified_date.strip() or last_modified_header or None

        visible_text = " ".join(parser.text_chunks)
        char_count = len(visible_text)
        word_count = len(visible_text.split())

        # 4. Scan for Deprecated Tools
        deprecated_findings: List[DeprecatedToolFinding] = []
        rule_hits = self.dep_engine.scan_text(f"{page_title}\n{visible_text}")
        for hit in rule_hits:
            deprecated_findings.append(
                DeprecatedToolFinding(
                    tool_name=hit.rule.tool_name,
                    pattern=hit.rule.pattern,
                    matched_text=hit.matched_text,
                    context_excerpt=hit.context_excerpt,
                    severity="HIGH",
                    recommended_replacement=f"Migrate to modern supported platform: {', '.join(hit.rule.replacements)}",
                )
            )

        # 5. Probe extracted links for broken URLs
        total_links_found = len(parser.links)
        broken_links: List[ExtractedLinkResult] = []
        live_links: List[ExtractedLinkResult] = []
        links_checked = 0

        if check_links and parser.links:
            # Deduplicate by destination URL
            unique_links: Dict[str, str] = {}
            for link_url, anchor in parser.links:
                if link_url not in unique_links and link_url != cleaned_url:
                    unique_links[link_url] = anchor

            targets = list(unique_links.items())[:max_links_to_check]
            links_checked = len(targets)

            with httpx.Client(timeout=3.5, follow_redirects=True, headers=headers) as link_client:
                for l_url, l_anchor in targets:
                    link_safe, _ = is_safe_url(l_url)
                    if not link_safe:
                        broken_links.append(
                            ExtractedLinkResult(
                                url=l_url,
                                anchor_text=l_anchor or None,
                                status="blocked",
                                error="SSRF restricted address",
                            )
                        )
                        continue

                    try:
                        # Try HEAD first
                        head_resp = link_client.head(l_url)
                        code = head_resp.status_code
                        if code in (404, 410):
                            broken_links.append(
                                ExtractedLinkResult(
                                    url=l_url,
                                    anchor_text=l_anchor or None,
                                    status_code=code,
                                    status="broken",
                                    error=f"Dead link (HTTP {code})",
                                )
                            )
                        elif code < 400:
                            live_links.append(
                                ExtractedLinkResult(
                                    url=l_url,
                                    anchor_text=l_anchor or None,
                                    status_code=code,
                                    status="live",
                                )
                            )
                        else:
                            # Verify with GET
                            get_resp = link_client.get(l_url)
                            if get_resp.status_code in (404, 410):
                                broken_links.append(
                                    ExtractedLinkResult(
                                        url=l_url,
                                        anchor_text=l_anchor or None,
                                        status_code=get_resp.status_code,
                                        status="broken",
                                        error=f"Dead link (HTTP {get_resp.status_code})",
                                    )
                                )
                            else:
                                live_links.append(
                                    ExtractedLinkResult(
                                        url=l_url,
                                        anchor_text=l_anchor or None,
                                        status_code=get_resp.status_code,
                                        status="live" if get_resp.status_code < 400 else "warning",
                                    )
                                )
                    except Exception as err:
                        broken_links.append(
                            ExtractedLinkResult(
                                url=l_url,
                                anchor_text=l_anchor or None,
                                status="unreachable",
                                error=str(err),
                            )
                        )

        # 6. Metadata Quality Checks
        quality_issues: List[MetadataQualityFinding] = []
        if not page_title or page_title == "Untitled Webpage":
            quality_issues.append(
                MetadataQualityFinding(
                    field="title",
                    issue="Missing or generic HTML title tag",
                    severity="HIGH",
                )
            )

        if not last_modified:
            quality_issues.append(
                MetadataQualityFinding(
                    field="last_modified",
                    issue="No publication or last-modified date found in headers or meta tags",
                    severity="MEDIUM",
                )
            )

        if not page_author:
            quality_issues.append(
                MetadataQualityFinding(
                    field="author",
                    issue="No author or team ownership attribute found",
                    severity="LOW",
                )
            )

        if word_count < 40:
            quality_issues.append(
                MetadataQualityFinding(
                    field="content_length",
                    issue=f"Extremely thin content ({word_count} words extracted)",
                    severity="HIGH",
                )
            )

        # 7. Calculate Deterministic Freshness Score (0-100)
        # Weights:
        # Age: 30 max (if last modified is available and >180 days, or 15 pts if date is unknown)
        # Broken links: 25 max (20 pts if confirmed broken links)
        # Deprecated tools: 20 max (20 pts if confirmed tool hit)
        # Metadata quality: 15 max (5 pts per issue up to 15)
        # Contradictions: 10 max (0 by default on single doc)

        earned_pts = 0.0
        score_breakdown: Dict[str, Any] = {}

        # Broken links signal
        if broken_links:
            bl_pts = min(25.0, 15.0 + (len(broken_links) * 5.0))
            earned_pts += bl_pts
            score_breakdown["broken_links"] = {"points": bl_pts, "max": 25, "reason": f"{len(broken_links)} broken links found"}
        else:
            score_breakdown["broken_links"] = {"points": 0, "max": 25, "reason": "No broken links found"}

        # Deprecated tools signal
        if deprecated_findings:
            dt_pts = 20.0
            earned_pts += dt_pts
            score_breakdown["deprecated_tools"] = {"points": dt_pts, "max": 20, "reason": f"{len(deprecated_findings)} deprecated software references"}
        else:
            score_breakdown["deprecated_tools"] = {"points": 0, "max": 20, "reason": "Clean of deprecated tools"}

        # Metadata quality signal
        if quality_issues:
            mq_pts = min(15.0, len(quality_issues) * 5.0)
            earned_pts += mq_pts
            score_breakdown["metadata_quality"] = {"points": mq_pts, "max": 15, "reason": f"{len(quality_issues)} metadata quality issues"}
        else:
            score_breakdown["metadata_quality"] = {"points": 0, "max": 15, "reason": "Complete metadata"}

        # Age signal
        if last_modified:
            score_breakdown["document_age"] = {"points": 10.0, "max": 30, "reason": f"Published/Modified date detected: {last_modified}"}
            earned_pts += 10.0
        else:
            score_breakdown["document_age"] = {"points": 15.0, "max": 30, "reason": "Date unknown; provisional aging penalty applied"}
            earned_pts += 15.0

        freshness_score = round(min(100.0, earned_pts), 1)
        if freshness_score >= 70:
            risk_level = "Critical"
        elif freshness_score >= 50:
            risk_level = "High"
        elif freshness_score >= 30:
            risk_level = "Moderate"
        else:
            risk_level = "Low"

        text_preview = visible_text[:600] + ("..." if len(visible_text) > 600 else "")

        return UrlInspectionResponse(
            url=cleaned_url,
            status="success",
            page_title=page_title,
            page_description=page_description,
            author=page_author,
            last_modified=last_modified,
            status_code=status_code,
            character_count=char_count,
            word_count=word_count,
            broken_links_count=len(broken_links),
            total_links_found=total_links_found,
            links_checked_count=links_checked,
            broken_links=broken_links,
            live_links=live_links,
            deprecated_tools_count=len(deprecated_findings),
            deprecated_tools=deprecated_findings,
            metadata_quality_issues_count=len(quality_issues),
            metadata_quality_issues=quality_issues,
            freshness_score=freshness_score,
            risk_level=risk_level,
            score_breakdown=score_breakdown,
            text_preview=text_preview,
        )

    def import_scanned_url_to_catalog(self, req: ImportScannedUrlRequest) -> str:
        """
        Imports an inspected webpage into the active inventory catalog and content store.
        Returns the created document_id.
        """
        doc_id = f"CNT-EXT-{uuid.uuid4().hex[:6].upper()}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Add to dataset in-memory DataFrame
        df, _ = self.dataset_service.load_dataset()
        new_row = {
            "content_id": doc_id,
            "title": req.title or "Imported Web Document",
            "content_type": "Web Article",
            "platform": req.platform or "Web",
            "author": req.author or "External Web Author",
            "created_date": now_iso,
            "last_updated": now_iso,
            "last_reviewed": now_iso,
            "page_views_90d": 100,
            "linked_from_count": 1,
            "mentions_deprecated_tool": req.mentions_deprecated_tool,
            "has_broken_links": req.has_broken_links,
            "subject_area": req.subject_area or "General",
            "staleness_score": 50,
            "recommended_action": "Review scanned web content and remediate identified decay.",
        }

        self.dataset_service.add_document_record(new_row)

        # 2. Add text content into DocumentContentService
        raw_text = req.raw_text or f"Source URL: {req.url}\n\nTitle: {req.title}"
        self.content_service.set_document_content(
            document_id=doc_id,
            text=raw_text,
            source=f"url_import:{req.url}",
        )

        # 3. Trigger scoring update
        try:
            self.scoring_service.run_audit()
        except Exception as e:
            logger.debug(f"Scoring update after import note: {e}")

        logger.info(f"Successfully imported external URL {req.url} as document {doc_id}")
        return doc_id


_scanner_singleton: Optional[UrlScannerService] = None


def get_url_scanner_service() -> UrlScannerService:
    global _scanner_singleton
    if _scanner_singleton is None:
        _scanner_singleton = UrlScannerService()
    return _scanner_singleton
