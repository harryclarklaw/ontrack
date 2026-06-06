from __future__ import annotations

import textwrap

import pytest

from sbom_counsel.errors import ExceptionsError, PolicyError
from sbom_counsel.licensing import resolve
from sbom_counsel.models import Component, Posture
from sbom_counsel.policy import classify, load_exceptions, load_policy


@pytest.fixture
def policy():
    return load_policy()


def _classify(policy, declared=None, concluded=None, name="x", version="1", exceptions=None):
    comp = Component(
        name=name, version=version, declared_license=declared, concluded_license=concluded
    )
    return classify(comp, resolve(comp), policy, exceptions)


def test_default_policy_loads(policy):
    assert "MIT" in policy.licenses
    assert policy.unresolved_posture is Posture.REVIEW


def test_permissive_allowed(policy):
    c = _classify(policy, declared="MIT")
    assert c.posture is Posture.ALLOWED
    assert c.category == "permissive"
    assert c.rule_id == "licenses:MIT"
    assert c.obligations


def test_strong_copyleft_blocked(policy):
    assert _classify(policy, declared="GPL-3.0-only").posture is Posture.BLOCKED


def test_network_copyleft_blocked(policy):
    assert _classify(policy, declared="AGPL-3.0-only").posture is Posture.BLOCKED


def test_weak_copyleft_review(policy):
    assert _classify(policy, declared="LGPL-2.1-or-later").posture is Posture.REVIEW


def test_dual_or_picks_least_restrictive(policy):
    # MIT OR GPL-3.0 -> distributor may elect MIT -> allowed.
    c = _classify(policy, declared="MIT OR GPL-3.0-only")
    assert c.posture is Posture.ALLOWED


def test_and_picks_most_restrictive(policy):
    c = _classify(policy, declared="MIT AND GPL-3.0-only")
    assert c.posture is Posture.BLOCKED


def test_with_exception_softens(policy):
    c = _classify(policy, declared="GPL-2.0-only WITH Classpath-exception-2.0")
    assert c.posture is Posture.REVIEW
    assert c.rule_id == "exception_overrides:Classpath-exception-2.0"


def test_unknown_identifier_review(policy):
    c = _classify(policy, declared="Weird-Custom-9.9")
    assert c.posture is Posture.REVIEW
    assert c.category == "unknown"


def test_licenseref_pattern(policy):
    c = _classify(policy, declared="LicenseRef-Acme")
    assert c.category == "proprietary-commercial"
    assert c.rule_id == "license_patterns:license-ref-family"


def test_unresolved_conservative_default(policy):
    c = _classify(policy, declared="NOASSERTION")
    assert c.unresolved
    assert c.posture is Posture.REVIEW
    assert c.rule_id == "defaults:unresolved_posture"


def test_every_result_has_a_rule(policy):
    for expr in ["MIT", "GPL-3.0-only", "NOASSERTION", "Weird-1.0", "MIT OR Apache-2.0"]:
        c = _classify(policy, declared=expr)
        assert c.rule_id
        assert c.explanation


# --- exceptions ---


def test_exception_overrides_and_is_recorded(policy, fixtures_dir):
    exc = load_exceptions(fixtures_dir / "exceptions.yaml")
    c = _classify(
        policy,
        declared="GPL-3.0-or-later",
        name="build-only-gpl-tool",
        version="4.4.0",
        exceptions=exc,
    )
    assert c.posture is Posture.ALLOWED
    assert c.exception is not None
    assert c.exception.original_posture is Posture.BLOCKED
    assert "build-time" in c.exception.justification


def test_exception_version_pin(policy, fixtures_dir):
    exc = load_exceptions(fixtures_dir / "exceptions.yaml")
    # Wrong version -> no exception applies.
    c = _classify(
        policy,
        declared="GPL-3.0-or-later",
        name="build-only-gpl-tool",
        version="9.9.9",
        exceptions=exc,
    )
    assert c.posture is Posture.BLOCKED
    assert c.exception is None


def test_exception_wildcard_version(policy, fixtures_dir):
    exc = load_exceptions(fixtures_dir / "exceptions.yaml")
    c = _classify(
        policy,
        declared="GPL-3.0-only",
        name="copyleft-engine",
        version="any-version",
        exceptions=exc,
    )
    assert c.posture is Posture.REVIEW
    assert c.exception is not None


def test_exception_missing_justification_rejected(tmp_path):
    p = tmp_path / "exc.yaml"
    p.write_text(textwrap.dedent("""
        exceptions:
          - component: foo
            posture: allowed
            owner: a@b.com
            date: "2026-01-01"
    """))
    with pytest.raises(ExceptionsError, match="justification"):
        load_exceptions(p)


def test_exception_missing_owner_rejected(tmp_path):
    p = tmp_path / "exc.yaml"
    p.write_text(textwrap.dedent("""
        exceptions:
          - component: foo
            posture: allowed
            justification: because
            date: "2026-01-01"
    """))
    with pytest.raises(ExceptionsError, match="owner"):
        load_exceptions(p)


def test_exception_bad_posture_rejected(tmp_path):
    p = tmp_path / "exc.yaml"
    p.write_text(textwrap.dedent("""
        exceptions:
          - component: foo
            posture: maybe
            justification: because
            owner: a@b.com
            date: "2026-01-01"
    """))
    with pytest.raises(ExceptionsError, match="posture"):
        load_exceptions(p)


# --- policy validation ---


def test_policy_invalid_posture(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text(textwrap.dedent("""
        categories:
          permissive:
            posture: sometimes
          unknown:
            posture: review
          unresolved:
            posture: review
        licenses: {}
    """))
    with pytest.raises(PolicyError, match="Invalid posture"):
        load_policy(p)


def test_policy_unknown_category_mapping(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text(textwrap.dedent("""
        categories:
          permissive:
            posture: allowed
          unknown:
            posture: review
          unresolved:
            posture: review
        licenses:
          MIT: nonexistent
    """))
    with pytest.raises(PolicyError, match="unknown category"):
        load_policy(p)


def test_policy_requires_unresolved_category(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text(textwrap.dedent("""
        categories:
          permissive:
            posture: allowed
          unknown:
            posture: review
        licenses: {}
    """))
    with pytest.raises(PolicyError, match="unresolved"):
        load_policy(p)


def test_policy_or_worst_setting(tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text(textwrap.dedent("""
        settings:
          multi_license_or: worst
        categories:
          permissive:
            posture: allowed
          strong-copyleft:
            posture: blocked
          unknown:
            posture: review
          unresolved:
            posture: review
        licenses:
          MIT: permissive
          GPL-3.0-only: strong-copyleft
    """))
    policy = load_policy(p)
    c = _classify(policy, declared="MIT OR GPL-3.0-only")
    assert c.posture is Posture.BLOCKED  # worst branch governs under this policy
