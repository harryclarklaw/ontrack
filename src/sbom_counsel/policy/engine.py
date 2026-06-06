"""The licence-classification engine: the centre of the tool's value.

Given a component, its resolved SPDX expression, the policy and any exceptions,
this produces a :class:`Classification` whose every part is traceable to a policy
rule. Nothing here is hard-coded judgement; categories, postures and obligations
all come from the policy. The engine's job is to walk the licence expression and
combine the policy's verdicts conservatively.

Combination rules:
* OR (dual licensing): the distributor may elect one branch, so by default the
  least restrictive branch governs (configurable to most restrictive).
* AND: every licence applies, so the most restrictive posture governs and every
  branch's obligations are collected.
* WITH: an SPDX exception may soften or harden the base licence via the policy's
  ``exception_overrides``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from license_expression import AND, OR, LicenseSymbol, LicenseWithExceptionSymbol

from ..models import (
    AppliedException,
    Classification,
    Component,
    LicenceFinding,
    Posture,
    ResolvedLicence,
)
from .exceptions import ExceptionSet
from .loader import Policy

_lock = threading.Lock()


@dataclass
class _Eval:
    """Result of evaluating a sub-expression."""

    posture: Posture
    governing: list[LicenceFinding]  # findings whose obligations and posture apply
    note: str | None = None


def _finding_for_license(license_id: str, policy: Policy) -> LicenceFinding:
    """Classify a single licence id against the policy, recording the rule used."""
    # 1. Exact match.
    cat_key = policy.licenses.get(license_id)
    if cat_key is not None:
        cat = policy.category(cat_key)
        return LicenceFinding(
            license_id=license_id,
            category=cat.key,
            posture=cat.posture,
            rule_id=f"licenses:{license_id}",
            obligations=list(cat.obligations),
        )
    # 2. Pattern (family) match, in policy order.
    for pattern in policy.patterns:
        if license_id.startswith(pattern.prefix):
            cat = policy.category(pattern.category)
            return LicenceFinding(
                license_id=license_id,
                category=cat.key,
                posture=cat.posture,
                rule_id=f"license_patterns:{pattern.id}",
                obligations=list(cat.obligations),
            )
    # 3. Unknown / unrecognised id -> the policy's conservative unknown posture.
    cat = policy.category("unknown")
    return LicenceFinding(
        license_id=license_id,
        category="unknown",
        posture=policy.unknown_posture,
        rule_id="defaults:unknown_posture",
        obligations=list(cat.obligations),
    )


def _finding_with_exception(
    node: LicenseWithExceptionSymbol, policy: Policy
) -> tuple[LicenceFinding, str | None]:
    base_id = node.license_symbol.key
    exc_id = node.exception_symbol.key
    base = _finding_for_license(base_id, policy)
    combined_id = f"{base_id} WITH {exc_id}"
    override = policy.exception_overrides.get(exc_id)
    if override is None:
        # Unknown exception: keep the base licence's posture, but record the WITH.
        return (
            LicenceFinding(
                license_id=combined_id,
                category=base.category,
                posture=base.posture,
                rule_id=base.rule_id,
                obligations=base.obligations,
            ),
            None,
        )
    cat_key = override.category or base.category
    cat = policy.category(cat_key)
    return (
        LicenceFinding(
            license_id=combined_id,
            category=cat.key,
            posture=override.posture,
            rule_id=f"exception_overrides:{exc_id}",
            obligations=list(cat.obligations),
        ),
        override.note,
    )


def _evaluate(node: object, policy: Policy) -> _Eval:
    """Recursively evaluate a parsed licence expression node."""
    if isinstance(node, LicenseWithExceptionSymbol):
        finding, note = _finding_with_exception(node, policy)
        return _Eval(posture=finding.posture, governing=[finding], note=note)

    if isinstance(node, LicenseSymbol):
        finding = _finding_for_license(node.key, policy)
        return _Eval(posture=finding.posture, governing=[finding])

    if isinstance(node, OR):
        children = [_evaluate(arg, policy) for arg in node.args]
        if policy.multi_or == "worst":
            chosen = max(children, key=lambda e: e.posture.severity)
        else:  # best: pick the least restrictive electable branch
            chosen = min(children, key=lambda e: e.posture.severity)
        notes = [c.note for c in children if c.note]
        return _Eval(
            posture=chosen.posture,
            governing=chosen.governing,
            note="; ".join(notes) or None,
        )

    if isinstance(node, AND):
        children = [_evaluate(arg, policy) for arg in node.args]
        postures = [c.posture for c in children]
        posture = (
            Posture.worst(postures)
            if policy.multi_and == "worst"
            else min(children, key=lambda e: e.posture.severity).posture
        )
        governing: list[LicenceFinding] = []
        for c in children:  # every licence in an AND contributes obligations
            governing.extend(c.governing)
        notes = [c.note for c in children if c.note]
        return _Eval(posture=posture, governing=governing, note="; ".join(notes) or None)

    # Should not happen for a well-formed parse; treat conservatively.
    cat = policy.category("unknown")
    return _Eval(
        posture=policy.unknown_posture,
        governing=[
            LicenceFinding(
                license_id=str(node),
                category="unknown",
                posture=policy.unknown_posture,
                rule_id="defaults:unknown_posture",
                obligations=list(cat.obligations),
            )
        ],
    )


def _all_leaf_findings(node: object, policy: Policy) -> list[LicenceFinding]:
    """Every leaf licence finding, for full per-component transparency."""
    if isinstance(node, LicenseWithExceptionSymbol):
        finding, _ = _finding_with_exception(node, policy)
        return [finding]
    if isinstance(node, LicenseSymbol):
        return [_finding_for_license(node.key, policy)]
    if isinstance(node, AND | OR):
        out: list[LicenceFinding] = []
        for arg in node.args:
            out.extend(_all_leaf_findings(arg, policy))
        return out
    return []


def _dedupe_obligations(findings: list[LicenceFinding]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for f in findings:
        for ob in f.obligations:
            if ob not in seen:
                seen.add(ob)
                out.append(ob)
    return out


def _unresolved_classification(policy: Policy, resolved: ResolvedLicence) -> Classification:
    cat = policy.category("unresolved")
    reason = resolved.unresolved_reason or "Licence could not be resolved."
    return Classification(
        posture=policy.unresolved_posture,
        category="unresolved",
        rule_id="defaults:unresolved_posture",
        explanation=(
            f"{reason} Assigned the policy's conservative default for unresolved "
            f"licences ({policy.unresolved_posture.value})."
        ),
        obligations=list(cat.obligations),
        findings=[],
        unresolved=True,
    )


def classify(
    component: Component,
    resolved: ResolvedLicence,
    policy: Policy,
    exceptions: ExceptionSet | None = None,
) -> Classification:
    """Classify one component, then apply any matching project exception."""
    if resolved.unresolved or not resolved.expression:
        classification = _unresolved_classification(policy, resolved)
    else:
        # license-expression's parser is shared; serialise access.
        from ..licensing.resolver import _licensing

        with _lock:
            tree = _licensing().parse(resolved.expression, validate=False, strict=False)
        evaluation = _evaluate(tree, policy)
        findings = _all_leaf_findings(tree, policy)
        governing_rule = (
            evaluation.governing[0].rule_id if evaluation.governing else "defaults:unknown_posture"
        )
        governing_cat = evaluation.governing[0].category if evaluation.governing else "unknown"
        explanation = _build_explanation(resolved, evaluation, policy)
        classification = Classification(
            posture=evaluation.posture,
            category=governing_cat,
            rule_id=governing_rule,
            explanation=explanation,
            obligations=_dedupe_obligations(evaluation.governing),
            findings=findings,
            unresolved=False,
        )

    return _apply_exception(component, classification, exceptions)


def _build_explanation(resolved: ResolvedLicence, evaluation: _Eval, policy: Policy) -> str:
    parts = [
        f"Licence expression '{resolved.expression}' resolved to posture "
        f"'{evaluation.posture.value}'."
    ]
    rules = sorted({f"{f.category} via {f.rule_id}" for f in evaluation.governing})
    if rules:
        parts.append("Governing rule(s): " + "; ".join(rules) + ".")
    if " OR " in (resolved.expression or ""):
        mode = "least" if policy.multi_or == "best" else "most"
        parts.append(f"OR resolved to the {mode} restrictive branch.")
    if evaluation.note:
        parts.append(evaluation.note)
    return " ".join(parts)


def _apply_exception(
    component: Component,
    classification: Classification,
    exceptions: ExceptionSet | None,
) -> Classification:
    if exceptions is None:
        return classification
    rule = exceptions.find(component.name, component.version)
    if rule is None:
        return classification
    applied = AppliedException(
        component=component.name,
        version=component.version,
        original_posture=classification.posture,
        override_posture=rule.posture,
        justification=rule.justification,
        owner=rule.owner,
        date=rule.date,
    )
    classification.exception = applied
    classification.posture = rule.posture
    classification.explanation += (
        f" Exception applied by {rule.owner} on {rule.date}, overriding "
        f"'{applied.original_posture.value}' to '{rule.posture.value}': {rule.justification}"
    )
    return classification
