from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def clean_sbom() -> Path:
    return EXAMPLES / "clean.cdx.json"


@pytest.fixture
def mixed_sbom() -> Path:
    return EXAMPLES / "mixed.spdx.json"
