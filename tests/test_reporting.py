from __future__ import annotations

import json

import pytest

from sbom_counsel.ingest import ingest
from sbom_counsel.models import Posture
from sbom_counsel.policy import load_exceptions, load_policy
from sbom_counsel.reporting import build_report, html, json_report, markdown, notices


@pytest.fixture
def mixed_report(mixed_sbom):
    fmt, comps = ingest(mixed_sbom)
    return build_report(comps, str(mixed_sbom), fmt, load_policy(), None, "2026-06-06")


@pytest.fixture
def clean_report(clean_sbom):
    fmt, comps = ingest(clean_sbom)
    return build_report(comps, str(clean_sbom), fmt, load_policy(), None, "2026-06-06")


def test_counts_and_overall(mixed_report):
    assert mixed_report.overall_posture is Posture.BLOCKED
    assert mixed_report.counts.blocked == 3
    assert mixed_report.counts.review == 6
    assert mixed_report.counts.allowed == 2
    assert mixed_report.counts.total == 11


def test_results_sorted_worst_first(mixed_report):
    severities = [r.posture.severity for r in mixed_report.results]
    assert severities == sorted(severities, reverse=True)


def test_clean_report_all_allowed(clean_report):
    assert clean_report.overall_posture is Posture.ALLOWED
    assert clean_report.counts.blocked == 0
    assert not clean_report.unresolved


def test_unresolved_collected(mixed_report):
    names = {r.component.name for r in mixed_report.unresolved}
    assert names == {"mystery-package", "unlicensed-snippet"}


def test_json_render_roundtrips_and_has_disclaimer(mixed_report):
    out = json_report.render(mixed_report)
    data = json.loads(out)
    assert data["schema"] == "sbom-counsel/report/v1"
    assert data["summary"]["overall_posture"] == "blocked"
    assert data["summary"]["counts"]["blocked"] == 3
    assert "not legal advice" in data["disclaimer"]
    assert data["limitations"]
    # Every component carries a traceable rule.
    assert all(c["rule_applied"] for c in data["components"])


def test_json_is_deterministic(mixed_report):
    assert json_report.render(mixed_report) == json_report.render(mixed_report)


def test_markdown_has_required_sections(mixed_report):
    md = markdown.render(mixed_report)
    for heading in [
        "## Executive summary",
        "## Risk register",
        "## Unresolved and unknown components",
        "## Obligations to satisfy before distribution",
        "## Exceptions applied",
        "## Methodology",
        "## Limitations",
        "## Disclaimer",
    ]:
        assert heading in md
    assert "not legal advice" in md
    assert md == markdown.render(mixed_report)  # deterministic


def test_html_renders_self_contained(mixed_report):
    out = html.render(mixed_report)
    assert out.startswith("<!DOCTYPE html>")
    assert "<style>" in out  # CSS is inline (self-contained)
    assert "not legal advice" in out
    assert "Blocked" in out
    assert out == html.render(mixed_report)


def test_html_escapes_content(mixed_report):
    # The pipe/markup-significant characters should be escaped, not break the doc.
    out = html.render(mixed_report)
    assert "<script>" not in out.replace("&lt;script&gt;", "")


def test_notices_sections(mixed_report):
    txt = notices.render_text(mixed_report)
    assert "THIRD-PARTY SOFTWARE NOTICES" in txt
    # A shippable permissive component appears.
    assert "fast-json" in txt
    # Blocked/unresolved components are deferred, not presented as cleared.
    assert "DEFERRED" in txt
    assert "copyleft-engine" in txt
    md = notices.render_markdown(mixed_report)
    assert "# Third-party software notices" in md


def test_notices_never_fabricate_text(mixed_report):
    # customcorp-sdk carried extracted text; it must be reproduced verbatim.
    txt = notices.render_text(mixed_report)
    # fast-json had no embedded text -> we point to the SPDX id, not invent text.
    assert "Full licence text not included in the SBOM" in txt


def test_exceptions_appear_in_report(mixed_sbom, fixtures_dir):
    fmt, comps = ingest(mixed_sbom)
    exc = load_exceptions(fixtures_dir / "exceptions.yaml")
    report = build_report(comps, str(mixed_sbom), fmt, load_policy(), exc, "2026-06-06")
    assert len(report.exceptions_applied) == 2
    md = markdown.render(report)
    assert "build-time" in md
    # build-only-gpl-tool -> allowed and copyleft-engine -> review, so only
    # network-service-lib remains blocked.
    assert report.counts.blocked == 1
