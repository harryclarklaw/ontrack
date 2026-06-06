# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-06

Initial release.

### Added
- Ingestion of CycloneDX (JSON, 1.4–1.6) and SPDX (JSON, 2.2–2.3) SBOMs with
  automatic format detection and normalisation into a single internal model.
- Licence resolution to normalised SPDX expressions via `license-expression`,
  handling `AND`, `OR`, `WITH` and compound expressions, with conservative
  treatment of `NOASSERTION`, unknown identifiers and absent licences.
- Data-driven, external YAML licence policy mapping categories to obligations and
  a ship-posture (`allowed` / `review` / `blocked`), with exact-id and licence-family
  matching, SPDX `WITH`-exception overrides, and configurable handling of dual
  (`OR`) and compound (`AND`) licences. Every classification is traceable to a rule.
- Project exceptions with mandatory justification, owner and date, applied after
  classification and audited in the report.
- Reports in Markdown, self-contained HTML and JSON, plus a third-party
  attribution notices file in plain text and Markdown.
- CLI with a CI gate mode and meaningful exit codes; deterministic, offline output.
- Optional Rust convenience wrapper around `cargo-about` / `cargo-deny`.
- Default policy, example SBOMs (clean and mixed), example exceptions, and
  generated example reports.
- Test suite, type checking, linting and formatting configuration, and CI.

[0.1.0]: https://github.com/harryclarklaw/ontrack/releases/tag/v0.1.0
