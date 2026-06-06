from __future__ import annotations

from sbom_counsel.licensing import resolve
from sbom_counsel.models import Component


def _resolve(declared=None, concluded=None):
    return resolve(
        Component(name="x", version="1", declared_license=declared, concluded_license=concluded)
    )


def test_simple_licence():
    r = _resolve(declared="MIT")
    assert not r.unresolved
    assert r.expression == "MIT"
    assert r.license_ids == ["MIT"]
    assert r.source_field == "declared"


def test_concluded_preferred_over_declared():
    r = _resolve(declared="GPL-3.0-only", concluded="MIT")
    assert r.expression == "MIT"
    assert r.source_field == "concluded"


def test_dual_or_expression():
    r = _resolve(declared="MIT OR Apache-2.0")
    assert set(r.license_ids) == {"MIT", "Apache-2.0"}
    assert "OR" in r.expression


def test_with_exception():
    r = _resolve(declared="GPL-2.0-only WITH Classpath-exception-2.0")
    assert r.license_ids == ["GPL-2.0-only"]
    assert r.exception_ids == ["Classpath-exception-2.0"]


def test_compound_and_or():
    r = _resolve(declared="(MIT OR GPL-3.0-only) AND BSD-3-Clause")
    assert set(r.license_ids) == {"MIT", "GPL-3.0-only", "BSD-3-Clause"}


def test_noassertion_is_unresolved():
    r = _resolve(declared="NOASSERTION")
    assert r.unresolved
    assert "NOASSERTION" in r.unresolved_reason


def test_no_licence_is_unresolved():
    r = _resolve()
    assert r.unresolved
    assert "No licence" in r.unresolved_reason


def test_unknown_identifier_flagged():
    r = _resolve(declared="FooBar-1.0")
    assert not r.unresolved
    assert r.unknown_ids == ["FooBar-1.0"]


def test_legacy_gpl_normalised():
    assert _resolve(declared="GPL-2.0").expression == "GPL-2.0-only"
    assert _resolve(declared="GPL-3.0+").expression == "GPL-3.0-or-later"
    assert _resolve(declared="LGPL-2.1").expression == "LGPL-2.1-only"


def test_unparseable_expression_is_unresolved():
    r = _resolve(declared="MIT AND AND OR")
    assert r.unresolved
    assert "could not be parsed" in r.unresolved_reason
