"""Load an SBOM file and auto-detect its format.

We read the JSON once and inspect a few discriminating keys rather than trusting
the file extension. Detection is intentionally narrow: if a document does not
clearly look like CycloneDX or SPDX, we refuse it rather than guess.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..errors import InputError, UnsupportedFormatError
from ..models import SourceFormat


def load_json(path: str | Path) -> dict[str, Any]:
    """Read and parse a JSON file, raising :class:`InputError` on any problem."""
    p = Path(path)
    if not p.exists():
        raise InputError(f"Input file not found: {p}")
    if p.is_dir():
        raise InputError(f"Input path is a directory, not a file: {p}")
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - environment dependent
        raise InputError(f"Could not read input file {p}: {exc}") from exc
    if not text.strip():
        raise InputError(f"Input file is empty: {p}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(
            f"Input file is not valid JSON ({p}): line {exc.lineno}, column {exc.colno}: {exc.msg}. "
            "Only CycloneDX (JSON) and SPDX (JSON) documents are supported."
        ) from exc
    if not isinstance(data, dict):
        raise InputError(
            f"Input file {p} does not contain a JSON object at the top level; "
            "expected a CycloneDX or SPDX document."
        )
    return data


def detect_format(document: dict[str, Any]) -> SourceFormat:
    """Identify the SBOM format from the parsed document."""
    # CycloneDX always carries bomFormat == "CycloneDX".
    if str(document.get("bomFormat", "")).lower() == "cyclonedx":
        return SourceFormat.CYCLONEDX
    # SPDX JSON carries spdxVersion (e.g. "SPDX-2.3") and an SPDXID.
    spdx_version = document.get("spdxVersion")
    if isinstance(spdx_version, str) and spdx_version.upper().startswith("SPDX-"):
        return SourceFormat.SPDX
    # Some CycloneDX exports omit bomFormat but include a specVersion + components.
    if "specVersion" in document and "components" in document:
        return SourceFormat.CYCLONEDX
    raise UnsupportedFormatError(
        "Could not identify the SBOM format. Supported inputs are CycloneDX (JSON), "
        'identified by a "bomFormat": "CycloneDX" field, and SPDX (JSON), '
        'identified by an "spdxVersion": "SPDX-..." field.'
    )
