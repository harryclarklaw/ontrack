# Contributing to sbom-counsel

Contributions are welcome. This note covers the essentials.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before opening a pull request

Run the full local check set; CI runs the same:

```bash
python -m pytest        # tests must pass
ruff check src tests    # lint
black --check src tests # formatting (run `black src tests` to fix)
python -m mypy          # type check
```

## Project structure

The code is organised as four independently testable layers, plus the CLI:

- `ingest/` — SBOM parsing and normalisation (CycloneDX, SPDX).
- `licensing/` — SPDX expression resolution.
- `policy/` — policy loading, exceptions, and the classification engine.
- `reporting/` — Markdown, HTML, JSON and notices rendering.

The classification logic must stay **data-driven**: it lives in the policy file,
not in code. If you are tempted to hard-code a licence verdict, add it to the
policy schema instead.

## Guardrails for this tool

This is a legal-adjacent tool. Please preserve these properties in any change:

- **Conservative by default.** Uncertainty must resolve towards `review` or
  `blocked`, never towards `allowed`.
- **Explainable.** Every classification must record the policy rule that produced
  it. Do not add opaque judgements.
- **Never fabricate.** If a licence cannot be resolved, say so. Do not invent
  obligations or licence text.
- **Not legal advice.** Do not add language that implies the tool gives legal
  advice. The disclaimer must remain in every report.

## Adding licences or categories

Prefer editing `src/sbom_counsel/data/default_policy.yaml`. Add a test in
`tests/test_policy.py` that pins the expected category, posture and rule id.

## Changelog

Add an entry under "Unreleased" in `CHANGELOG.md` describing user-visible changes.

## Licence

By contributing you agree that your contributions are licensed under the
Apache License 2.0, consistent with the project licence.
