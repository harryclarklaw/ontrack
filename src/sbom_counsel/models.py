"""The normalised internal model shared by every layer.

SBOM ingestion produces :class:`Component` objects. The licensing layer attaches
a :class:`ResolvedLicence`. The policy engine attaches a :class:`Classification`.
The reporting layer consumes :class:`Report`, an aggregate of :class:`ComponentResult`.

Keeping a single, explicit model here is what lets the four layers be developed
and tested independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SourceFormat(str, Enum):
    """Recognised SBOM input formats."""

    CYCLONEDX = "CycloneDX"
    SPDX = "SPDX"


class Posture(str, Enum):
    """Ship-posture for a proprietary, commercially distributed product.

    The numeric severity defines the conservative "worst wins" roll-up: when a
    component or component set carries several postures, the highest severity is
    the one that governs.
    """

    ALLOWED = "allowed"
    REVIEW = "review"
    BLOCKED = "blocked"

    @property
    def severity(self) -> int:
        return {"allowed": 0, "review": 1, "blocked": 2}[self.value]

    @classmethod
    def worst(cls, postures: list[Posture]) -> Posture:
        """Return the most restrictive posture; ALLOWED if the list is empty."""
        if not postures:
            return cls.ALLOWED
        return max(postures, key=lambda p: p.severity)


@dataclass
class Component:
    """A single third-party component, normalised from the source SBOM."""

    name: str
    version: str | None = None
    supplier: str | None = None
    # Raw, unparsed licence strings exactly as found in the SBOM.
    declared_license: str | None = None
    concluded_license: str | None = None
    purl: str | None = None
    bom_ref: str | None = None
    hashes: dict[str, str] = field(default_factory=dict)
    copyright: str | None = None
    # Any embedded licence/attribution text carried in the SBOM, keyed by a label
    # (e.g. an SPDX licence id or "declared"). Never fabricated.
    license_texts: dict[str, str] = field(default_factory=dict)
    # Optional, only surfaced if already present in the SBOM. Never generated.
    vulnerabilities: list[str] = field(default_factory=list)

    @property
    def display_version(self) -> str:
        return self.version or "(no version)"

    @property
    def identifier(self) -> str:
        """A stable, human-meaningful identifier used for sorting and display."""
        return f"{self.name}@{self.version}" if self.version else self.name


@dataclass
class ResolvedLicence:
    """Output of the licensing layer for one component.

    ``expression`` is the normalised SPDX expression actually used for
    classification (concluded licence preferred over declared). ``license_ids``
    and ``exception_ids`` are the atomic SPDX symbols extracted from it.
    """

    raw: str | None
    source_field: str  # "concluded", "declared", or "none"
    expression: str | None
    license_ids: list[str] = field(default_factory=list)
    exception_ids: list[str] = field(default_factory=list)
    unknown_ids: list[str] = field(default_factory=list)
    unresolved: bool = False
    unresolved_reason: str | None = None


@dataclass
class LicenceFinding:
    """Per-licence classification detail, so a compound expression is explainable."""

    license_id: str
    category: str
    posture: Posture
    rule_id: str
    obligations: list[str] = field(default_factory=list)


@dataclass
class AppliedException:
    """Record of a project exception that overrode the computed posture."""

    component: str
    version: str | None
    original_posture: Posture
    override_posture: Posture
    justification: str
    owner: str
    date: str


@dataclass
class Classification:
    """Output of the policy engine for one component."""

    posture: Posture
    category: str
    rule_id: str
    explanation: str
    obligations: list[str] = field(default_factory=list)
    findings: list[LicenceFinding] = field(default_factory=list)
    unresolved: bool = False
    exception: AppliedException | None = None


@dataclass
class ComponentResult:
    """A component together with its resolved licence and classification."""

    component: Component
    licence: ResolvedLicence
    classification: Classification

    @property
    def posture(self) -> Posture:
        return self.classification.posture


@dataclass
class Counts:
    allowed: int = 0
    review: int = 0
    blocked: int = 0

    @property
    def total(self) -> int:
        return self.allowed + self.review + self.blocked


@dataclass
class Report:
    """The full analysis, ready for rendering in any output format."""

    tool_name: str
    tool_version: str
    generated_at: str
    source_path: str
    source_format: SourceFormat
    policy_path: str
    policy_name: str
    exceptions_path: str | None
    overall_posture: Posture
    counts: Counts
    results: list[ComponentResult]
    obligations: list[str] = field(default_factory=list)
    exceptions_applied: list[AppliedException] = field(default_factory=list)
    unresolved: list[ComponentResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
