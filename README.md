# sbom-counsel

`sbom-counsel` reads a software bill of materials (SBOM) and produces an
open-source licence-risk report written for a legal reader, together with the
third-party attribution notices file. It answers one question: **can this set of
components be shipped inside a proprietary, commercially distributed product?**

It is a command-line tool and an importable Python library. It runs fully offline
and produces deterministic output.

> **This tool is not legal advice and does not provide it.** Its classifications
> are automated and indicative. They depend entirely on the policy in force and on
> the accuracy of the SBOM, and they do not account for how each component is used,
> linked or distributed. Every report must be reviewed by qualified legal counsel
> before any distribution decision. See [Disclaimer](#disclaimer).

## Why it exists

From 11 December 2027, the EU Cyber Resilience Act will require manufacturers of
products with digital elements placed on the EU market to produce a
machine-readable SBOM (covering at least top-level dependencies) as part of full
compliance. That SBOM is a *security-transparency* artefact. It does not answer
the *intellectual-property* question of whether the licences in that component set
are compatible with shipping closed-source software.

`sbom-counsel` consumes the SBOM a studio already has to generate and adds the
licence-interpretation layer on top. That bridge — from a security artefact to a
shippability assessment a lawyer can read — is the point of the tool.

## What it does

- Ingests a **CycloneDX (JSON)** or **SPDX (JSON)** SBOM, auto-detects the format,
  and normalises it into a single internal model.
- Resolves each component's licence to a normalised **SPDX expression**, correctly
  handling `AND`, `OR`, `WITH` and compound expressions.
- Classifies every component against an **external, editable policy** into a
  category, a set of obligations, and a ship-posture of `allowed`, `review` or
  `blocked`.
- Handles the hard cases conservatively: `NOASSERTION`, unrecognised identifiers
  and components with no licence are surfaced as unresolved or unknown and given
  the policy's conservative default. An unknown licence is never silently treated
  as acceptable.
- Applies project **exceptions** (with a recorded justification, owner and date)
  after classification, and audits them in the report.
- Produces four outputs: a **Markdown** report, a self-contained **HTML** report,
  a machine-readable **JSON** report, and a **third-party notices** file (plain
  text and Markdown).
- Provides a CI **gate mode** with meaningful exit codes.

Every classification records the policy rule that produced it, so a lawyer can
audit exactly why each component was flagged.

## Installation

Requires Python 3.11 or later.

```bash
# From a local checkout
pip install .

# Or, isolated, with pipx
pipx install .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

### Analyse an SBOM

```bash
sbom-counsel path/to/sbom.json -o report-out/
```

This writes into `report-out/`:

| File | Purpose |
| --- | --- |
| `licence-risk-report.md` | The report, for reading and for diffing in review. |
| `licence-risk-report.html` | The same report, self-contained, for emailing. |
| `licence-risk-report.json` | The machine-readable report, for pipelines. |
| `NOTICES.txt`, `NOTICES.md` | The third-party attribution notices. |

### Worked example

The repository ships two example SBOMs and their generated reports under
[`examples/`](examples/).

```bash
# A clean component set: all permissive, gate passes.
sbom-counsel examples/clean.cdx.json -o examples/reports/clean --gate
echo $?   # 0

# A mixed set with copyleft and unresolved components: gate fails.
sbom-counsel examples/mixed.spdx.json --exceptions examples/exceptions.yaml \
    -o examples/reports/mixed --gate
echo $?   # 1
```

The mixed example exercises the hard cases on purpose: a dual `MIT OR Apache-2.0`
licence, a `GPL-2.0-only WITH Classpath-exception-2.0` expression, strong copyleft
(GPL-3.0), network copyleft (AGPL-3.0), weak copyleft (LGPL, MPL), a non-SPDX
`LicenseRef-` identifier, a `NOASSERTION` component, a component with no licence,
and an applied exception. See the generated
[Markdown report](examples/reports/mixed/licence-risk-report.md) and
[notices file](examples/reports/mixed/NOTICES.txt).

### CI gate

```bash
# Fail the build if any component is blocked.
sbom-counsel sbom.json -o out/ --gate

# Stricter: fail if any component is review or worse.
sbom-counsel sbom.json -o out/ --gate --gate-on review
```

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Success; if gating, the gate passed. |
| 1 | The release gate failed. |
| 2 | Command-line usage error. |
| 3 | Input / SBOM-format error. |
| 4 | Policy error. |
| 5 | Exceptions-file error. |
| 6 | Cargo-helper error. |

### Reproducible output

Output is deterministic for a given input. The only varying field is the report
date, which you can pin for byte-identical runs:

```bash
SOURCE_DATE_EPOCH=1717632000 sbom-counsel sbom.json -o out/
# or
sbom-counsel sbom.json -o out/ --as-of 2026-06-06
```

### Rust convenience path (optional)

If you do not already have an SBOM, and you have `cargo-about` or `cargo-deny`
installed, you can gather component data directly from a Cargo project:

```bash
sbom-counsel --cargo-project path/to/rust/project -o out/
```

This is a convenience wrapper only. The SBOM input is the primary,
ecosystem-agnostic route, and is what you should use in CI. If neither cargo tool
is installed the command fails gracefully and points you back at the SBOM path.

### As a library

```python
from sbom_counsel.ingest import ingest
from sbom_counsel.policy import load_policy, load_exceptions
from sbom_counsel.reporting import build_report, json_report

fmt, components = ingest("sbom.json")
report = build_report(
    components, "sbom.json", fmt,
    policy=load_policy(),                 # or load_policy("my-policy.yaml")
    exceptions=load_exceptions(None),     # or a path
    generated_at="2026-06-06",
)
print(report.overall_posture.value)       # "blocked" | "review" | "allowed"
print(json_report.render(report))
```

## The policy file — the lawyer's lever

The classification logic lives entirely in an external YAML policy, not in code. A
lawyer can edit it without touching the source. The shipped default is at
[`src/sbom_counsel/data/default_policy.yaml`](src/sbom_counsel/data/default_policy.yaml);
pass your own with `--policy`.

> The shipped policy contains **conservative defaults intended as a starting
> point**. They are not tuned to your product or jurisdiction and must be reviewed
> by counsel.

The policy maps licence categories to a description, the obligations they trigger,
and a ship-posture. The default categories and postures are:

| Category | Posture | Examples |
| --- | --- | --- |
| Permissive | `allowed` | MIT, BSD-2/3-Clause, Apache-2.0, ISC, Zlib |
| Public domain | `allowed` | CC0-1.0, Unlicense |
| Weak copyleft | `review` | LGPL, MPL-2.0, EPL-2.0 |
| Strong copyleft | `blocked` | GPL-2.0, GPL-3.0 |
| Network copyleft | `blocked` | AGPL-3.0 |
| Non-commercial | `blocked` | CC-BY-NC and variants |
| Share-alike content | `review` | CC-BY-SA |
| Proprietary / custom | `review` | `LicenseRef-*`, commercial terms |
| Unknown / unresolved | `review` (set to `blocked` to be stricter) | NOASSERTION, non-SPDX ids, no licence |

Key parts of the file:

- `categories`: each defines a `description`, `posture` and `obligations` list.
- `licenses`: an exact SPDX-id → category map.
- `license_patterns`: ordered prefix fallbacks for whole licence families
  (e.g. anything starting `AGPL-` → network copyleft). Each carries an id that
  appears in the audit trail.
- `exception_overrides`: SPDX `WITH` exception handling (e.g.
  `Classpath-exception-2.0` softens GPL to `review`).
- `settings.multi_license_or` / `multi_license_and`: how dual/compound licences
  combine. By default an `OR` resolves to the **least restrictive** branch (the
  distributor may elect it) and an `AND` to the **most restrictive**.
- `defaults.unresolved_posture` / `unknown_posture`: the conservative fallback for
  the hard cases. Set either to `blocked` for a stricter gate.

How a component is evaluated: the SPDX expression is parsed; each licence id is
matched against `licenses` then `license_patterns`; an unmatched id uses the
unknown posture; `NOASSERTION`/absent uses the unresolved posture; `OR`/`AND`
branches are combined per the settings above. Every result records the rule id
used, for example `licenses:MIT`, `license_patterns:gpl-family`,
`exception_overrides:Classpath-exception-2.0`, or `defaults:unresolved_posture`.

## The exceptions file

A project exceptions file grants a specific component an overriding posture — for
example a copyleft tool used only at build time and never distributed.

```yaml
exceptions:
  - component: build-only-gpl-tool
    version: "4.4.0"          # optional; omit to match any version
    posture: allowed          # allowed | review | blocked
    justification: >-
      Used only as a build-time code generator; the binary is not distributed.
    owner: general.counsel@example.com
    date: "2026-05-01"
```

Each exception must carry a `justification`, an `owner` and a `date`. **An
exception without a justification is rejected.** Applied exceptions are listed in
the report with their justification, so every override is auditable. Pass the file
with `--exceptions`.

## Known limitations (v1)

- **No linkage analysis.** The tool does not perform static or dynamic linkage
  analysis. Weak-copyleft obligations (LGPL, MPL) depend on how a component is
  linked, which a human must assess. This is the most significant limitation.
- It classifies licence identifiers; it does not read full licence text or detect
  additional terms embedded in a component.
- It is **not a vulnerability scanner**. Where the SBOM already carries
  vulnerability data it is surfaced in a separate, clearly labelled, informational
  section only.
- It does **not** assert CRA compliance or certification. It is a readiness and
  analysis aid.
- Its conclusions are only as good as the SBOM it is given. Components missing from
  the SBOM are invisible to it.
- No GUI, web interface or hosted service; no automated remediation.

## Supported formats

- **CycloneDX JSON**: 1.4, 1.5, 1.6.
- **SPDX JSON**: 2.2, 2.3.

The tool maps these JSON documents directly into its internal model rather than
relying on the heavier official object-model libraries, which keeps ingestion
robust across format minor versions. The genuinely hard problem — parsing SPDX
licence expressions — is delegated to the well-maintained
[`license-expression`](https://github.com/aboutcode-org/license-expression)
library, which carries the SPDX licence list and runs offline.

## Development

```bash
pip install -e ".[dev]"
python -m pytest        # tests
ruff check src tests    # lint
black --check src tests # format
python -m mypy          # type check
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence of this tool

`sbom-counsel` is released under the **Apache License 2.0** — permissive, with an
express patent grant, which is the prudent choice for a publicly released tool.
See [LICENSE](LICENSE).

## Disclaimer

This tool generates automated, indicative classifications by applying a
configurable policy to the licence identifiers found in a supplied SBOM. It is not
legal advice and does not create a lawyer-client relationship. The classifications
depend entirely on the policy in force and on the completeness and accuracy of the
SBOM. They do not account for how each component is actually used, combined, linked
or distributed in your product, and they do not constitute a determination that any
component may or may not be shipped. Before making any distribution decision, the
findings must be reviewed by qualified legal counsel.
