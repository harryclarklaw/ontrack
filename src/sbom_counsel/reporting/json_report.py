"""Render a :class:`Report` to deterministic, machine-readable JSON.

The JSON carries the same information as the human reports and is the surface a
CI pipeline consumes. Keys are stable and output is sorted where order is not
otherwise meaningful, so the same input always produces byte-identical output.
"""

from __future__ import annotations

import json
from typing import Any

from ..models import ComponentResult, Report
from . import text


def _component_to_dict(r: ComponentResult) -> dict[str, Any]:
    c = r.component
    lic = r.licence
    cls = r.classification
    out: dict[str, Any] = {
        "name": c.name,
        "version": c.version,
        "supplier": c.supplier,
        "purl": c.purl,
        "posture": cls.posture.value,
        "category": cls.category,
        "rule_applied": cls.rule_id,
        "explanation": cls.explanation,
        "licence": {
            "raw": lic.raw,
            "source_field": lic.source_field,
            "expression": lic.expression,
            "license_ids": lic.license_ids,
            "exception_ids": lic.exception_ids,
            "unknown_ids": lic.unknown_ids,
            "unresolved": lic.unresolved,
            "unresolved_reason": lic.unresolved_reason,
        },
        "obligations": cls.obligations,
        "findings": [
            {
                "license_id": f.license_id,
                "category": f.category,
                "posture": f.posture.value,
                "rule_id": f.rule_id,
            }
            for f in cls.findings
        ],
        "unresolved": cls.unresolved,
    }
    if c.hashes:
        out["hashes"] = dict(sorted(c.hashes.items()))
    if c.vulnerabilities:
        out["vulnerabilities"] = sorted(c.vulnerabilities)
    if cls.exception is not None:
        e = cls.exception
        out["exception"] = {
            "original_posture": e.original_posture.value,
            "override_posture": e.override_posture.value,
            "justification": e.justification,
            "owner": e.owner,
            "date": e.date,
        }
    return out


def to_dict(report: Report) -> dict[str, Any]:
    """Build the canonical dictionary form of the report."""
    return {
        "schema": "sbom-counsel/report/v1",
        "tool": {"name": report.tool_name, "version": report.tool_version},
        "generated_at": report.generated_at,
        "source": {"path": report.source_path, "format": report.source_format.value},
        "policy": {"name": report.policy_name, "path": report.policy_path},
        "exceptions_file": report.exceptions_path,
        "summary": {
            "overall_posture": report.overall_posture.value,
            "counts": {
                "blocked": report.counts.blocked,
                "review": report.counts.review,
                "allowed": report.counts.allowed,
                "total": report.counts.total,
            },
        },
        "components": [_component_to_dict(r) for r in report.results],
        "unresolved": [
            {
                "name": r.component.name,
                "version": r.component.version,
                "reason": r.licence.unresolved_reason,
            }
            for r in report.unresolved
        ],
        "obligations": report.obligations,
        "exceptions_applied": [
            {
                "component": e.component,
                "version": e.version,
                "original_posture": e.original_posture.value,
                "override_posture": e.override_posture.value,
                "justification": e.justification,
                "owner": e.owner,
                "date": e.date,
            }
            for e in report.exceptions_applied
        ],
        "notes": report.notes,
        "methodology": text.METHODOLOGY,
        "limitations": text.LIMITATIONS,
        "disclaimer": text.DISCLAIMER,
    }


def render(report: Report) -> str:
    """Render the report as a deterministic JSON string."""
    return json.dumps(to_dict(report), indent=2, ensure_ascii=False, sort_keys=False) + "\n"
