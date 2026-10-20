import logging
from typing import Dict, List, Optional

logger = logging.getLogger("freshguard.content")


class DocumentContentService:
    """Manages raw text and excerpts for enterprise knowledge base documents."""

    def __init__(self):
        self._content_store: Dict[str, Dict[str, str]] = {}
        self._seed_sample_content()

    def set_document_content(self, document_id: str, text: str, source: str = "manual_ingestion") -> None:
        """Store or update text content for a document."""
        doc_id = document_id.strip()
        self._content_store[doc_id] = {
            "text": text.strip(),
            "source": source,
        }
        logger.info(f"Ingested text content for document {doc_id} ({len(text)} characters, source: {source})")

    def get_document_content(self, document_id: str) -> Optional[str]:
        """Retrieve stored text content for a document if available."""
        doc_id = document_id.strip()
        record = self._content_store.get(doc_id)
        if record:
            return record.get("text")
        return None

    def has_document_content(self, document_id: str) -> bool:
        """Check if document has text content available."""
        doc_id = document_id.strip()
        return doc_id in self._content_store and bool(self._content_store[doc_id].get("text"))

    def get_content_metadata(self, document_id: str) -> Optional[Dict[str, str]]:
        """Get content storage metadata."""
        return self._content_store.get(document_id.strip())

    def list_documents_with_content(self) -> List[str]:
        """List all document IDs that have text content loaded."""
        return list(self._content_store.keys())

    def _seed_sample_content(self) -> None:
        """Seed realistic enterprise document texts for candidate comparison."""
        seeds = {
            # Security Pair 1: Direct Procedure Contradiction & Supersession
            "CNT-0004": {
                "source": "seed_security_policy",
                "text": (
                    "Enterprise Production Change Control Policy (Section 4.2 - Database Migrations):\n"
                    "All production database schema migrations require prior written sign-off from the "
                    "Chief Information Security Officer (CISO) and an enforced 48-hour change-freeze notification "
                    "window before execution. Under no circumstances may an automated pipeline bypass manual CISO approval."
                ),
            },
            "CNT-0012": {
                "source": "seed_security_architecture",
                "text": (
                    "GitOps Automated Delivery Architecture Specification (Section 8.1):\n"
                    "Under the modern GitOps continuous deployment architecture, automated database migrations "
                    "pre-validated by the enterprise security linting engine do not require manual CISO sign-off "
                    "or change-freeze delays. Migrations apply automatically upon pull request merge into the production branch."
                ),
            },

            # Finance Pair 2: Numerical Limits & Deadline Contradiction
            "CNT-0001": {
                "source": "seed_finance_travel",
                "text": (
                    "Corporate Travel and Expense Policy (Schedule B - Air Travel):\n"
                    "Employee travel expense claims for domestic flights are capped at a maximum of $450 per flight segment. "
                    "All expense reimbursement reports must be submitted within 14 calendar days of trip completion. "
                    "Receipts submitted after 14 days will be rejected by corporate payroll."
                ),
            },
            "CNT-0005": {
                "source": "seed_finance_expense",
                "text": (
                    "Global Employee Expense Handbook (Air Travel Standard):\n"
                    "The domestic travel reimbursement allowance is updated to $750 per flight segment to adjust for "
                    "airline fare increases. Employees have a 30-day grace window from trip completion to submit travel reports."
                ),
            },

            # Product Pair 3: Scope Difference (Enterprise Release vs Beta Cohort)
            "CNT-0002": {
                "source": "seed_product_process",
                "text": (
                    "Standard Product Release Governance Process:\n"
                    "All customer-facing software releases require formal sign-off from the VP of Product and Lead Architect "
                    "prior to staging deployment. Production release flags must be toggled on by the central operations team."
                ),
            },
            "CNT-0008": {
                "source": "seed_product_beta",
                "text": (
                    "Customer Dogfooding & Beta Program Guidelines:\n"
                    "Beta releases deployed exclusively to the internal employee dogfooding cohort require only Engineering Manager "
                    "approval and do not require VP of Product sign-off. These guidelines apply strictly to pre-release evaluation rings."
                ),
            },

            # IT Tooling Pair 4: Deprecated Tool Supersession
            "CNT-0003": {
                "source": "seed_it_wiki",
                "text": (
                    "Software Repository Operations Standard:\n"
                    "All software release artifacts must be version-tagged and packaged using Subversion (SVN) tags on the "
                    "central on-premise svn.internal.corp server. Developers must commit release branches to SVN."
                ),
            },
            "CNT-0010": {
                "source": "seed_it_modern",
                "text": (
                    "Modern Cloud Artifact Registry Architecture:\n"
                    "Subversion (SVN) has been officially decommissioned across all engineering organizations. "
                    "All software packages must be built as container images and pushed to the GitHub Container Registry (GHCR)."
                ),
            },
        }

        for doc_id, data in seeds.items():
            self._content_store[doc_id] = data


# Global singleton instance
_content_service_instance: Optional[DocumentContentService] = None


def get_content_service() -> DocumentContentService:
    global _content_service_instance
    if _content_service_instance is None:
        _content_service_instance = DocumentContentService()
    return _content_service_instance
