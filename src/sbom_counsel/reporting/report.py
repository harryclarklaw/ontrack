"""Aggregate per-component results into a :class:`Report`.

This module runs the full pipeline (ingest is done by the caller) over a list of
components: resolve each licence, classify it, then roll the per-component
postures up into an overall release posture and the summary structures the
renderers consume. Ordering is deterministic so reports are reproducible.
"""

from __future__ import annotations

from .. import APP_NAME, __version__
from ..licensing import resolve
from ..models import (
    Component,
    ComponentResult,
    Counts,
    Posture,
    Report,
    SourceFormat,
)
from ..policy import ExceptionSet, Policy, classify


def build_report(
    components: list[Component],
    source_path: str,
    source_format: SourceFormat,
    policy: Policy,
    exceptions: ExceptionSet | None,
    generated_at: str,
) -> Report:
    """Classify every component and assemble the full report."""
    results: list[ComponentResult] = []
    for component in components:
        resolved = resolve(component)
        classification = classify(component, resolved, policy, exceptions)
        results.append(
            ComponentResult(component=component, licence=resolved, classification=classification)
        )

    # Deterministic order: worst posture first, then by name/version.
    results.sort(
        key=lambda r: (
            -r.posture.severity,
            r.component.name.lower(),
            r.component.version or "",
        )
    )

    counts = Counts()
    for r in results:
        if r.posture is Posture.ALLOWED:
            counts.allowed += 1
        elif r.posture is Posture.REVIEW:
            counts.review += 1
        else:
            counts.blocked += 1

    overall = Posture.worst([r.posture for r in results])

    obligations = _collect_obligations(results)
    exceptions_applied = [
        r.classification.exception for r in results if r.classification.exception is not None
    ]
    unresolved = [r for r in results if r.classification.unresolved]
    notes = _collect_notes(results)

    return Report(
        tool_name=APP_NAME,
        tool_version=__version__,
        generated_at=generated_at,
        source_path=source_path,
        source_format=source_format,
        policy_path=policy.source_path,
        policy_name=policy.name,
        exceptions_path=exceptions.source_path if exceptions else None,
        overall_posture=overall,
        counts=counts,
        results=results,
        obligations=obligations,
        exceptions_applied=exceptions_applied,
        unresolved=unresolved,
        notes=notes,
    )


def _collect_obligations(results: list[ComponentResult]) -> list[str]:
    """Union of obligations for components that are shippable (allowed/review).

    Blocked components are excluded: the action there is to resolve the block, not
    to satisfy an obligation. Exceptions that downgrade to allowed/review are kept.
    """
    seen: set[str] = set()
    out: list[str] = []
    for r in results:
        if r.posture is Posture.BLOCKED:
            continue
        for ob in r.classification.obligations:
            if ob not in seen:
                seen.add(ob)
                out.append(ob)
    return out


def _collect_notes(results: list[ComponentResult]) -> list[str]:
    notes: list[str] = []
    any_vulns = any(r.component.vulnerabilities for r in results)
    if any_vulns:
        notes.append(
            "The SBOM carried vulnerability data; it is surfaced in a separate section "
            "for information only. This tool is not a vulnerability scanner."
        )
    return notes
