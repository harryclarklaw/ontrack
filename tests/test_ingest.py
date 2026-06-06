from __future__ import annotations

import json

import pytest

from sbom_counsel.errors import InputError, UnsupportedFormatError
from sbom_counsel.ingest import ingest
from sbom_counsel.ingest.detect import detect_format, load_json
from sbom_counsel.models import SourceFormat


def test_detect_cyclonedx_and_spdx(clean_sbom, mixed_sbom):
    assert detect_format(load_json(clean_sbom)) is SourceFormat.CYCLONEDX
    assert detect_format(load_json(mixed_sbom)) is SourceFormat.SPDX


def test_detect_cyclonedx_without_bomformat():
    assert detect_format({"specVersion": "1.5", "components": []}) is SourceFormat.CYCLONEDX


def test_detect_unsupported_raises():
    with pytest.raises(UnsupportedFormatError):
        detect_format({"hello": "world"})


def test_load_json_missing_file(tmp_path):
    with pytest.raises(InputError, match="not found"):
        load_json(tmp_path / "nope.json")


def test_load_json_directory(tmp_path):
    with pytest.raises(InputError, match="directory"):
        load_json(tmp_path)


def test_load_json_empty(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("")
    with pytest.raises(InputError, match="empty"):
        load_json(p)


def test_load_json_malformed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not valid")
    with pytest.raises(InputError, match="not valid JSON"):
        load_json(p)


def test_load_json_not_object(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]")
    with pytest.raises(InputError, match="JSON object"):
        load_json(p)


def test_cyclonedx_expression_and_purl(clean_sbom):
    fmt, comps = ingest(clean_sbom)
    assert fmt is SourceFormat.CYCLONEDX
    serde = next(c for c in comps if c.name == "serde")
    assert serde.declared_license == "MIT OR Apache-2.0"
    assert serde.purl == "pkg:cargo/serde@1.0.197"
    assert serde.supplier == "serde authors"


def test_cyclonedx_edgecases(fixtures_dir):
    fmt, comps = ingest(fixtures_dir / "cdx_edgecases.json")
    by_name = {c.name: c for c in comps}
    # A component with no name is skipped, not invented.
    assert "9.9.9" not in by_name
    assert len(comps) == 3
    # Multiple licence objects without an expression combine conservatively with AND.
    assert by_name["multi-licence-lib"].declared_license == "MIT AND BSD-3-Clause"
    # Base64 licence text is decoded and captured.
    assert by_name["base64-text-lib"].license_texts["MIT"] == "Copyright (c) Acme"
    assert by_name["base64-text-lib"].hashes == {"SHA-256": "abc123"}
    # Vulnerability data already in the SBOM is surfaced.
    assert by_name["vulnerable-lib"].vulnerabilities == ["CVE-2024-0001"]


def test_spdx_concluded_declared_and_noassertion(mixed_sbom):
    fmt, comps = ingest(mixed_sbom)
    assert fmt is SourceFormat.SPDX
    by_name = {c.name: c for c in comps}
    # NOASSERTION is preserved as-is for the resolver to treat as unresolved.
    assert by_name["mystery-package"].concluded_license == "NOASSERTION"
    # Supplier prefix ("Organization:") is stripped.
    assert by_name["fast-json"].supplier == "FastJSON Project"
    # purl is read from externalRefs.
    assert by_name["fast-json"].purl == "pkg:cargo/fast-json@2.4.0"
    # A package with no licence fields at all yields no licence.
    assert by_name["unlicensed-snippet"].declared_license is None
    assert by_name["unlicensed-snippet"].concluded_license is None


def test_spdx_extracted_licence_text(mixed_sbom):
    fmt, comps = ingest(mixed_sbom)
    sdk = next(c for c in comps if c.name == "customcorp-sdk")
    assert "LicenseRef-CustomCorp" in sdk.license_texts
    assert "CustomCorp Commercial License" in sdk.license_texts["LicenseRef-CustomCorp"]


def test_unsupported_top_level(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"foo": "bar"}))
    with pytest.raises(UnsupportedFormatError):
        ingest(p)
