"""Normalise a CycloneDX (JSON) document into the internal component model.

Targets CycloneDX 1.4, 1.5 and 1.6 (the current major line). The component
licence model differs subtly across these versions; the differences are handled
inline and noted. Where a component carries several licence objects without an
explicit SPDX ``expression``, the licences are combined conservatively with
``AND`` so that every licence's obligations are assessed.
"""

from __future__ import annotations

import base64
from typing import Any

from ..models import Component, SourceFormat


def _license_text(license_obj: dict[str, Any]) -> str | None:
    text = license_obj.get("text")
    if not isinstance(text, dict):
        return None
    content = text.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    if str(text.get("encoding", "")).lower() == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except (ValueError, UnicodeDecodeError):
            return None
    return content


def _extract_licences(comp: dict[str, Any]) -> tuple[str | None, dict[str, str]]:
    """Return (declared expression, captured licence texts) for a component."""
    licenses = comp.get("licenses")
    if not isinstance(licenses, list) or not licenses:
        return None, {}

    ids: list[str] = []
    expressions: list[str] = []
    texts: dict[str, str] = {}

    for entry in licenses:
        if not isinstance(entry, dict):
            continue
        # CycloneDX allows either {"expression": "..."} or {"license": {...}}.
        expression = entry.get("expression")
        if isinstance(expression, str) and expression.strip():
            expressions.append(expression.strip())
            continue
        lic = entry.get("license")
        if not isinstance(lic, dict):
            continue
        label = lic.get("id") or lic.get("name")
        if isinstance(label, str) and label.strip():
            ids.append(label.strip())
            captured = _license_text(lic)
            if captured:
                texts[label.strip()] = captured

    # An explicit expression always wins; if several are present, combine with AND.
    if expressions:
        if len(expressions) == 1:
            return expressions[0], texts
        return " AND ".join(f"({e})" if " " in e else e for e in expressions), texts
    if not ids:
        return None, texts
    if len(ids) == 1:
        return ids[0], texts
    # Multiple licence ids without an expression: combine conservatively.
    return " AND ".join(ids), texts


def _supplier(comp: dict[str, Any]) -> str | None:
    supplier = comp.get("supplier")
    if isinstance(supplier, dict):
        name = supplier.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    author = comp.get("author") or comp.get("publisher")
    if isinstance(author, str) and author.strip():
        return author.strip()
    return None


def _hashes(comp: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    hashes = comp.get("hashes")
    if isinstance(hashes, list):
        for h in hashes:
            if isinstance(h, dict):
                alg = h.get("alg")
                content = h.get("content")
                if isinstance(alg, str) and isinstance(content, str):
                    out[alg] = content
    return out


def _vulnerability_map(document: dict[str, Any]) -> dict[str, list[str]]:
    """Map a component bom-ref to any vulnerability ids already in the SBOM."""
    out: dict[str, list[str]] = {}
    vulns = document.get("vulnerabilities")
    if not isinstance(vulns, list):
        return out
    for v in vulns:
        if not isinstance(v, dict):
            continue
        vid = v.get("id")
        if not isinstance(vid, str):
            continue
        for affect in v.get("affects", []) or []:
            if isinstance(affect, dict):
                ref = affect.get("ref")
                if isinstance(ref, str):
                    out.setdefault(ref, []).append(vid)
    return out


def parse(
    document: dict[str, Any], _source_format: SourceFormat = SourceFormat.CYCLONEDX
) -> list[Component]:
    """Convert a parsed CycloneDX document into a list of components."""
    components_raw = document.get("components")
    if not isinstance(components_raw, list):
        return []
    vuln_map = _vulnerability_map(document)

    components: list[Component] = []
    for comp in components_raw:
        if not isinstance(comp, dict):
            continue
        name = comp.get("name")
        if not isinstance(name, str) or not name.strip():
            # A component with no name is unusable; skip it rather than invent one.
            continue
        declared, texts = _extract_licences(comp)
        version = comp.get("version")
        bom_ref = comp.get("bom-ref")
        components.append(
            Component(
                name=name.strip(),
                version=str(version).strip() if version not in (None, "") else None,
                supplier=_supplier(comp),
                declared_license=declared,
                concluded_license=None,
                purl=comp.get("purl") if isinstance(comp.get("purl"), str) else None,
                bom_ref=bom_ref if isinstance(bom_ref, str) else None,
                hashes=_hashes(comp),
                copyright=comp.get("copyright") if isinstance(comp.get("copyright"), str) else None,
                license_texts=texts,
                vulnerabilities=vuln_map.get(bom_ref, []) if isinstance(bom_ref, str) else [],
            )
        )
    return components
