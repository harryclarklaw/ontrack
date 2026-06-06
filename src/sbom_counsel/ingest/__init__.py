"""SBOM ingestion: load a file, detect its format, normalise to the internal model."""

from __future__ import annotations

from pathlib import Path

from ..models import Component, SourceFormat
from . import cyclonedx, spdx
from .detect import detect_format, load_json


def ingest(path: str | Path) -> tuple[SourceFormat, list[Component]]:
    """Load an SBOM file and return its detected format and normalised components."""
    document = load_json(path)
    fmt = detect_format(document)
    if fmt is SourceFormat.CYCLONEDX:
        return fmt, cyclonedx.parse(document, fmt)
    return fmt, spdx.parse(document, fmt)


__all__ = ["ingest", "detect_format", "load_json", "cyclonedx", "spdx"]
