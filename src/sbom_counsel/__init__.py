"""sbom-counsel: open-source licence-risk analysis for software bills of materials.

The tool ingests a CycloneDX or SPDX SBOM, classifies every component against an
editable licence policy, and produces a legal-reader report plus a third-party
attribution notices file. It answers one question: can this component set be
shipped in a proprietary, commercially distributed product?

This is not legal advice. See the disclaimer in every generated report.
"""

from __future__ import annotations

# Single source of truth for the tool's identity. Rename here to rebrand.
APP_NAME = "sbom-counsel"
APP_TITLE = "sbom-counsel"
__version__ = "0.1.0"

__all__ = ["APP_NAME", "APP_TITLE", "__version__"]
