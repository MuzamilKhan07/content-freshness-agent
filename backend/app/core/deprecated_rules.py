import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DeprecatedToolRule(BaseModel):
    rule_id: str = Field(..., description="Unique rule identifier")
    tool_name: str = Field(..., description="Canonical name of the deprecated software")
    pattern: str = Field(..., description="Regular expression pattern with word boundaries")
    replacement_guidance: str = Field(..., description="Recommended enterprise replacement")
    deprecation_category: str = Field(default="Retired Software", description="Category or domain")
    severity: str = Field(default="high", description="Default finding severity")


# Standard enterprise retired tools catalog
DEFAULT_DEPRECATED_RULES: List[DeprecatedToolRule] = [
    DeprecatedToolRule(
        rule_id="DEP-001",
        tool_name="Skype for Business",
        pattern=r"\b(skype\s+for\s+business|lync)\b",
        replacement_guidance="Migrate meeting links and communications to Microsoft Teams.",
        deprecation_category="Communication",
        severity="high",
    ),
    DeprecatedToolRule(
        rule_id="DEP-002",
        tool_name="HipChat",
        pattern=r"\bhipchat\b",
        replacement_guidance="Replace team channels and webhook integrations with Slack or MS Teams.",
        deprecation_category="Communication",
        severity="high",
    ),
    DeprecatedToolRule(
        rule_id="DEP-003",
        tool_name="Internet Explorer",
        pattern=r"\b(internet\s+explorer|ie11|ie\s*11)\b",
        replacement_guidance="Direct internal users to modern Chromium-based browsers (Edge, Chrome).",
        deprecation_category="Browser / Client",
        severity="moderate",
    ),
    DeprecatedToolRule(
        rule_id="DEP-004",
        tool_name="AngularJS (v1.x)",
        pattern=r"\b(angularjs|angular\s*1\.[0-9]+)\b",
        replacement_guidance="Upgrade legacy frontend components to modern Angular (v17+) or React.",
        deprecation_category="Frontend Framework",
        severity="high",
    ),
    DeprecatedToolRule(
        rule_id="DEP-005",
        tool_name="CentOS Linux 7/8",
        pattern=r"\b(centos\s*(?:7|8)|centos\s+linux\s*(?:7|8))\b",
        replacement_guidance="Migrate servers and deployment runbooks to Rocky Linux, AlmaLinux, or RHEL 9.",
        deprecation_category="Operating System",
        severity="critical",
    ),
    DeprecatedToolRule(
        rule_id="DEP-006",
        tool_name="Python 2.x",
        pattern=r"\bpython\s*2(?:\.[0-9]+)?\b",
        replacement_guidance="Upgrade scripts and utility runbooks to Python 3.10+.",
        deprecation_category="Runtime / Language",
        severity="critical",
    ),
    DeprecatedToolRule(
        rule_id="DEP-007",
        tool_name="Subversion (SVN)",
        pattern=r"\b(subversion|svn\s+checkout|svn\s+commit)\b",
        replacement_guidance="Migrate version control workflows and repository references to Git / GitHub Enterprise.",
        deprecation_category="VCS",
        severity="high",
    ),
    DeprecatedToolRule(
        rule_id="DEP-008",
        tool_name="Adobe Flash",
        pattern=r"\b(adobe\s+flash|flash\s+player|\.swf)\b",
        replacement_guidance="Re-author interactive learning content or diagrams using modern HTML5 standards.",
        deprecation_category="Media / Plugin",
        severity="critical",
    ),
    DeprecatedToolRule(
        rule_id="DEP-009",
        tool_name="Team Foundation Server (TFS)",
        pattern=r"\b(tfs|team\s+foundation\s+server)\b",
        replacement_guidance="Update build pipeline guidance and project boards to Azure DevOps or GitHub Actions.",
        deprecation_category="CI/CD / ALM",
        severity="moderate",
    ),
    DeprecatedToolRule(
        rule_id="DEP-010",
        tool_name="Confluence Server (On-Premises)",
        pattern=r"\bconfluence\s+server\b",
        replacement_guidance="Point links and administration steps to Confluence Cloud / Data Center.",
        deprecation_category="Knowledge Platform",
        severity="moderate",
    ),
]


class DeprecatedRulesEngine:
    """Pre-compiles regex patterns for efficient case-insensitive token boundary detection."""

    def __init__(self, rules: Optional[List[DeprecatedToolRule]] = None):
        self.rules = rules or DEFAULT_DEPRECATED_RULES
        self._compiled: List[tuple] = [
            (rule, re.compile(rule.pattern, re.IGNORECASE))
            for rule in self.rules
        ]

    def scan_text(self, text: str) -> List[tuple]:
        """
        Scan string for deprecated tool rules.
        Returns list of (rule, matched_substring).
        """
        if not text or not isinstance(text, str):
            return []

        matches = []
        for rule, regex in self._compiled:
            match = regex.search(text)
            if match:
                matches.append((rule, match.group(0)))
        return matches
