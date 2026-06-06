"""Normalise an SPDX (JSON) document into the internal component model.

Targets SPDX 2.2 and 2.3 (the current 2.x major line). SPDX distinguishes
``licenseConcluded`` from ``licenseDeclared``; both are preserved so the
licensing layer can prefer the concluded value. Text for custom ``LicenseRef-``
identifiers is captured from ``hasExtractedLicensingInfos`` for the notices file.
"""

from __future__ import annotations

import re
from typing import Any

from ..models import Component, SourceFormat

_NOASSERTION = "NOASSERTION"
_NONE = "NONE"
_LICENSE_REF = re.compile(r"LicenseRef-[0-9A-Za-z.\-]+")


def _clean_licence(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v or v.upper() == _NONE:
        return None
    # NOASSERTION is preserved verbatim; the resolver treats it as unresolved.
    return v


def _supplier(pkg: dict[str, Any]) -> str | None:
    for key in ("supplier", "originator"):
        value = pkg.get(key)
        if isinstance(value, str) and value.strip() and value.strip().upper() != _NOASSERTION:
            # SPDX prefixes these with "Organization:" / "Person:"; strip the prefix.
            return value.split(":", 1)[-1].strip() if ":" in value else value.strip()
    return None


def _purl(pkg: dict[str, Any]) -> str | None:
    for ref in pkg.get("externalRefs", []) or []:
        if isinstance(ref, dict) and ref.get("referenceType") == "purl":
            locator = ref.get("referenceLocator")
            if isinstance(locator, str) and locator.strip():
                return locator.strip()
    return None


def _hashes(pkg: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in pkg.get("checksums", []) or []:
        if isinstance(c, dict):
            alg = c.get("algorithm")
            val = c.get("checksumValue")
            if isinstance(alg, str) and isinstance(val, str):
                out[alg] = val
    return out


def _extracted_texts(document: dict[str, Any]) -> dict[str, str]:
    """Map each LicenseRef id to its extracted text, if provided."""
    out: dict[str, str] = {}
    for item in document.get("hasExtractedLicensingInfos", []) or []:
        if not isinstance(item, dict):
            continue
        ref = item.get("licenseId")
        text = item.get("extractedText")
        if isinstance(ref, str) and isinstance(text, str) and text.strip():
            out[ref] = text
    return out


def parse(
    document: dict[str, Any], _source_format: SourceFormat = SourceFormat.SPDX
) -> list[Component]:
    """Convert a parsed SPDX document into a list of components."""
    packages = document.get("packages")
    if not isinstance(packages, list):
        return []
    extracted = _extracted_texts(document)

    components: list[Component] = []
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        name = pkg.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        declared = _clean_licence(pkg.get("licenseDeclared"))
        concluded = _clean_licence(pkg.get("licenseConcluded"))
        version = pkg.get("versionInfo")
        copyright_text = pkg.get("copyrightText")
        if isinstance(copyright_text, str) and copyright_text.strip().upper() == _NOASSERTION:
            copyright_text = None

        # Attach extracted text for any LicenseRef the package references.
        texts: dict[str, str] = {}
        for expr in (declared, concluded):
            if expr:
                for ref in _LICENSE_REF.findall(expr):
                    if ref in extracted:
                        texts[ref] = extracted[ref]

        components.append(
            Component(
                name=name.strip(),
                version=(
                    str(version).strip()
                    if isinstance(version, str | int | float)
                    and str(version).strip()
                    and str(version).strip().upper() != _NOASSERTION
                    else None
                ),
                supplier=_supplier(pkg),
                declared_license=declared,
                concluded_license=concluded,
                purl=_purl(pkg),
                bom_ref=pkg.get("SPDXID") if isinstance(pkg.get("SPDXID"), str) else None,
                hashes=_hashes(pkg),
                copyright=copyright_text if isinstance(copyright_text, str) else None,
                license_texts=texts,
            )
        )
    return components
