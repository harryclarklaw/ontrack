"""Command-line interface for sbom-counsel.

Two audiences are served here: a lawyer who runs it once and reads the report,
and an engineer who runs it in CI as a release gate. The first is served by the
written reports; the second by ``--gate`` and the exit codes below.

Exit codes:
    0  success; if gating, the gate passed
    1  the release gate failed (a component met or exceeded the gate threshold)
    2  command-line usage error
    3  input / SBOM-format error
    4  policy error
    5  exceptions-file error
    6  cargo-helper error
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import APP_NAME, __version__
from .errors import (
    CargoToolError,
    ExceptionsError,
    InputError,
    PolicyError,
    UnsupportedFormatError,
)
from .ingest import ingest
from .models import Component, Posture, SourceFormat
from .policy import load_exceptions, load_policy
from .reporting import build_report, html, json_report, markdown, notices

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_USAGE = 2
EXIT_INPUT = 3
EXIT_POLICY = 4
EXIT_EXCEPTIONS = 5
EXIT_CARGO = 6

_ALL_FORMATS = ["md", "html", "json", "notices"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=(
            "Analyse an SBOM for open-source licence risk and produce a "
            "legal-reader report plus a third-party notices file. Not legal advice."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")

    src = parser.add_argument_group("input (choose one)")
    src.add_argument(
        "input", nargs="?", help="Path to a CycloneDX (JSON) or SPDX (JSON) SBOM file."
    )
    src.add_argument(
        "--cargo-project",
        metavar="DIR",
        help="Instead of an SBOM, gather components from a Cargo project using "
        "cargo-about/cargo-deny (convenience path; requires the tool installed).",
    )
    src.add_argument(
        "--cargo-tool",
        choices=["auto", "about", "deny"],
        default="auto",
        help="Which cargo helper to use with --cargo-project (default: auto).",
    )

    cfg = parser.add_argument_group("policy and exceptions")
    cfg.add_argument(
        "--policy", metavar="FILE", help="Licence policy YAML (default: the shipped policy)."
    )
    cfg.add_argument("--exceptions", metavar="FILE", help="Project exceptions YAML (optional).")

    out = parser.add_argument_group("output")
    out.add_argument(
        "-o",
        "--output-dir",
        default="sbom-counsel-out",
        metavar="DIR",
        help="Directory for generated reports (default: ./sbom-counsel-out).",
    )
    out.add_argument(
        "-f",
        "--format",
        action="append",
        choices=[*_ALL_FORMATS, "all"],
        help="Output format(s) to write; repeatable. Default: all.",
    )
    out.add_argument(
        "--basename",
        default="licence-risk-report",
        help="Base filename for the report files (default: licence-risk-report).",
    )
    out.add_argument(
        "--json-stdout",
        action="store_true",
        help="Also write the JSON report to stdout (for pipelines).",
    )
    out.add_argument(
        "--as-of",
        metavar="DATE",
        help="Pin the report date (e.g. 2026-06-06) for reproducible output. "
        "Defaults to SOURCE_DATE_EPOCH if set, else today (UTC).",
    )

    gate = parser.add_argument_group("CI gate")
    gate.add_argument(
        "--gate",
        action="store_true",
        help="Gate mode: exit non-zero if any component meets the gate threshold.",
    )
    gate.add_argument(
        "--gate-on",
        choices=["blocked", "review"],
        default="blocked",
        help="Gate threshold: 'blocked' fails on blocked only; 'review' fails on "
        "review or worse (default: blocked).",
    )

    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress output.")
    return parser


def _generated_at(as_of: str | None) -> str:
    if as_of:
        return as_of
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.strip().isdigit():
        return datetime.fromtimestamp(int(epoch), tz=UTC).strftime("%Y-%m-%d")
    return datetime.now(tz=UTC).strftime("%Y-%m-%d")


def _resolve_formats(values: list[str] | None) -> list[str]:
    if not values or "all" in values:
        return list(_ALL_FORMATS)
    # Preserve canonical order, drop duplicates.
    return [f for f in _ALL_FORMATS if f in set(values)]


def _load_components(args: argparse.Namespace) -> tuple[str, SourceFormat, list[Component]]:
    if args.cargo_project:
        from .cargo import gather_components

        tool, components = gather_components(args.cargo_project, args.cargo_tool)
        return f"{tool}:{args.cargo_project}", SourceFormat.CYCLONEDX, components
    fmt, components = ingest(args.input)
    return args.input, fmt, components


def _gate_failures(report_results: list, threshold: Posture) -> list:
    return [r for r in report_results if r.posture.severity >= threshold.severity]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input and not args.cargo_project:
        parser.error("provide an SBOM file, or use --cargo-project DIR")
    if args.input and args.cargo_project:
        parser.error("provide either an SBOM file or --cargo-project, not both")

    def log(msg: str) -> None:
        if not args.quiet:
            print(msg, file=sys.stderr)

    try:
        source_path, source_format, components = _load_components(args)
    except (InputError, UnsupportedFormatError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    except CargoToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_CARGO

    if not components:
        print(
            "error: the input contained no components to analyse. Confirm the SBOM "
            "lists components (CycloneDX 'components' / SPDX 'packages').",
            file=sys.stderr,
        )
        return EXIT_INPUT

    try:
        policy = load_policy(args.policy)
    except PolicyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_POLICY

    try:
        exceptions = load_exceptions(args.exceptions)
    except ExceptionsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_EXCEPTIONS

    report = build_report(
        components=components,
        source_path=source_path,
        source_format=source_format,
        policy=policy,
        exceptions=exceptions,
        generated_at=_generated_at(args.as_of),
    )

    formats = _resolve_formats(args.format)
    out_dir = Path(args.output_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: could not create output directory {out_dir}: {exc}", file=sys.stderr)
        return EXIT_INPUT

    written: list[Path] = []
    base = args.basename
    if "md" in formats:
        written.append(_write(out_dir / f"{base}.md", markdown.render(report)))
    if "html" in formats:
        written.append(_write(out_dir / f"{base}.html", html.render(report)))
    if "json" in formats:
        written.append(_write(out_dir / f"{base}.json", json_report.render(report)))
    if "notices" in formats:
        written.append(_write(out_dir / "NOTICES.txt", notices.render_text(report)))
        written.append(_write(out_dir / "NOTICES.md", notices.render_markdown(report)))

    for p in written:
        log(f"wrote {p}")
    log(
        f"overall posture: {report.overall_posture.value} "
        f"(blocked={report.counts.blocked}, review={report.counts.review}, "
        f"allowed={report.counts.allowed})"
    )

    if args.json_stdout:
        sys.stdout.write(json_report.render(report))

    if args.gate:
        threshold = Posture.BLOCKED if args.gate_on == "blocked" else Posture.REVIEW
        failures = _gate_failures(report.results, threshold)
        if failures:
            log(f"gate failed: {len(failures)} component(s) at or above '{args.gate_on}'.")
            for r in failures:
                log(f"  {r.component.identifier}: {r.posture.value}")
            return EXIT_GATE_FAILED
        log(f"gate passed: no component at or above '{args.gate_on}'.")

    return EXIT_OK


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
