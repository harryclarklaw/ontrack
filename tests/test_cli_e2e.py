from __future__ import annotations

import json

import pytest

from sbom_counsel.cli import (
    EXIT_CARGO,
    EXIT_EXCEPTIONS,
    EXIT_GATE_FAILED,
    EXIT_INPUT,
    EXIT_OK,
    EXIT_POLICY,
    main,
)


def _run(args):
    return main(args)


def test_clean_passes_gate(clean_sbom, tmp_path):
    code = _run([str(clean_sbom), "-o", str(tmp_path), "--as-of", "2026-06-06", "--gate"])
    assert code == EXIT_OK
    assert (tmp_path / "licence-risk-report.md").exists()
    assert (tmp_path / "licence-risk-report.html").exists()
    assert (tmp_path / "licence-risk-report.json").exists()
    assert (tmp_path / "NOTICES.txt").exists()
    assert (tmp_path / "NOTICES.md").exists()


def test_mixed_fails_gate_on_blocked(mixed_sbom, tmp_path):
    code = _run([str(mixed_sbom), "-o", str(tmp_path), "--as-of", "2026-06-06", "--gate"])
    assert code == EXIT_GATE_FAILED


def test_gate_on_review_fails_clean_with_no_review(clean_sbom, tmp_path):
    # Clean has no review components, so even gate-on review passes.
    code = _run([str(clean_sbom), "-o", str(tmp_path), "--gate", "--gate-on", "review"])
    assert code == EXIT_OK


def test_gate_on_review_fails_mixed(mixed_sbom, tmp_path):
    code = _run([str(mixed_sbom), "-o", str(tmp_path), "--gate", "--gate-on", "review"])
    assert code == EXIT_GATE_FAILED


def test_no_gate_returns_ok_even_with_blocked(mixed_sbom, tmp_path):
    code = _run([str(mixed_sbom), "-o", str(tmp_path)])
    assert code == EXIT_OK


def test_missing_input_is_usage_error():
    # parser.error raises SystemExit(2) for a usage problem.
    with pytest.raises(SystemExit) as exc:
        _run([])
    assert exc.value.code == 2


def test_input_and_cargo_together_is_usage_error(clean_sbom, tmp_path):
    with pytest.raises(SystemExit) as exc:
        _run([str(clean_sbom), "--cargo-project", str(tmp_path)])
    assert exc.value.code == 2


def test_bad_file_is_input_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    code = _run([str(bad), "-o", str(tmp_path)])
    assert code == EXIT_INPUT


def test_unsupported_format_is_input_error(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"foo": "bar"}))
    code = _run([str(p), "-o", str(tmp_path)])
    assert code == EXIT_INPUT


def test_bad_policy_is_policy_error(clean_sbom, tmp_path):
    bad_policy = tmp_path / "p.yaml"
    bad_policy.write_text("categories: not-a-mapping\n")
    code = _run([str(clean_sbom), "-o", str(tmp_path), "--policy", str(bad_policy)])
    assert code == EXIT_POLICY


def test_bad_exceptions_is_exceptions_error(clean_sbom, tmp_path):
    bad = tmp_path / "e.yaml"
    bad.write_text(
        "exceptions:\n  - component: x\n    posture: allowed\n    owner: a\n    date: '2026'\n"
    )
    code = _run([str(clean_sbom), "-o", str(tmp_path), "--exceptions", str(bad)])
    assert code == EXIT_EXCEPTIONS


def test_cargo_project_without_tool_is_cargo_error(tmp_path):
    # No Cargo.toml / no tool installed -> graceful cargo error, not a crash.
    code = _run(["--cargo-project", str(tmp_path), "-o", str(tmp_path)])
    assert code == EXIT_CARGO


def test_format_selection(clean_sbom, tmp_path):
    code = _run([str(clean_sbom), "-o", str(tmp_path), "-f", "json"])
    assert code == EXIT_OK
    assert (tmp_path / "licence-risk-report.json").exists()
    assert not (tmp_path / "licence-risk-report.md").exists()


def test_json_stdout(clean_sbom, tmp_path, capsys):
    code = _run([str(clean_sbom), "-o", str(tmp_path), "-f", "json", "--json-stdout", "-q"])
    assert code == EXIT_OK
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["schema"] == "sbom-counsel/report/v1"
