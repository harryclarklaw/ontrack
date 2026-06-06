"""Load and validate the licence policy.

The policy is external YAML so a lawyer can edit categories, postures and licence
mappings without touching code. This module loads the default shipped policy or a
caller-supplied one, validates it, and exposes typed lookup helpers used by the
engine. Any structural problem raises :class:`PolicyError` with a clear message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from ..errors import PolicyError
from ..models import Posture

DEFAULT_POLICY_RESOURCE = "default_policy.yaml"


@dataclass(frozen=True)
class Category:
    key: str
    description: str
    posture: Posture
    obligations: tuple[str, ...]


@dataclass(frozen=True)
class ExceptionOverride:
    posture: Posture
    category: str | None
    note: str | None


@dataclass(frozen=True)
class Pattern:
    id: str
    prefix: str
    category: str


@dataclass
class Policy:
    name: str
    source_path: str
    scenario: str
    multi_or: str
    multi_and: str
    unresolved_posture: Posture
    unknown_posture: Posture
    categories: dict[str, Category]
    licenses: dict[str, str]
    patterns: list[Pattern]
    exception_overrides: dict[str, ExceptionOverride]
    raw: dict[str, Any] = field(default_factory=dict)

    def category(self, key: str) -> Category:
        cat = self.categories.get(key)
        if cat is None:
            raise PolicyError(
                f"Policy references category '{key}' which is not defined under 'categories'."
            )
        return cat


def _as_posture(value: Any, where: str) -> Posture:
    try:
        return Posture(str(value).strip().lower())
    except ValueError as exc:
        raise PolicyError(
            f"Invalid posture '{value}' at {where}. Expected one of: allowed, review, blocked."
        ) from exc


def _require_mapping(data: Any, where: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise PolicyError(f"Expected a mapping at {where}, found {type(data).__name__}.")
    return data


def default_policy_path() -> Path:
    """Return the on-disk path of the shipped default policy."""
    return Path(str(resources.files("sbom_counsel.data").joinpath(DEFAULT_POLICY_RESOURCE)))


def load_policy(path: str | Path | None = None) -> Policy:
    """Load a policy from ``path``, or the shipped default when ``path`` is None."""
    if path is None:
        resolved = default_policy_path()
    else:
        resolved = Path(path)
        if not resolved.exists():
            raise PolicyError(f"Policy file not found: {resolved}")

    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        raise PolicyError(f"Could not read policy file {resolved}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolicyError(f"Policy file {resolved} is not valid YAML: {exc}") from exc

    data = _require_mapping(data, "the policy root")

    meta = _require_mapping(data.get("meta", {}), "meta")
    settings = _require_mapping(data.get("settings", {}), "settings")
    defaults = _require_mapping(data.get("defaults", {}), "defaults")

    categories_raw = _require_mapping(data.get("categories"), "categories")
    if not categories_raw:
        raise PolicyError("Policy defines no categories; at least one is required.")
    categories: dict[str, Category] = {}
    for key, body in categories_raw.items():
        body = _require_mapping(body, f"categories.{key}")
        obligations = body.get("obligations", []) or []
        if not isinstance(obligations, list):
            raise PolicyError(f"categories.{key}.obligations must be a list.")
        categories[key] = Category(
            key=key,
            description=str(body.get("description", "")).strip(),
            posture=_as_posture(body.get("posture"), f"categories.{key}.posture"),
            obligations=tuple(str(o) for o in obligations),
        )

    licenses_raw = data.get("licenses", {}) or {}
    licenses = _require_mapping(licenses_raw, "licenses")
    license_map: dict[str, str] = {}
    for lic, cat in licenses.items():
        if cat not in categories:
            raise PolicyError(f"licenses['{lic}'] maps to unknown category '{cat}'.")
        license_map[str(lic)] = str(cat)

    patterns: list[Pattern] = []
    for i, p in enumerate(data.get("license_patterns", []) or []):
        p = _require_mapping(p, f"license_patterns[{i}]")
        cat = str(p.get("category", ""))
        if cat not in categories:
            raise PolicyError(f"license_patterns[{i}] maps to unknown category '{cat}'.")
        prefix = str(p.get("prefix", ""))
        if not prefix:
            raise PolicyError(f"license_patterns[{i}] must define a non-empty 'prefix'.")
        patterns.append(Pattern(id=str(p.get("id", f"pattern-{i}")), prefix=prefix, category=cat))

    exc_overrides: dict[str, ExceptionOverride] = {}
    for key, body in (data.get("exception_overrides", {}) or {}).items():
        body = _require_mapping(body, f"exception_overrides.{key}")
        cat = body.get("category")
        if cat is not None and cat not in categories:
            raise PolicyError(f"exception_overrides.{key} maps to unknown category '{cat}'.")
        exc_overrides[str(key)] = ExceptionOverride(
            posture=_as_posture(body.get("posture"), f"exception_overrides.{key}.posture"),
            category=str(cat) if cat is not None else None,
            note=str(body["note"]).strip() if body.get("note") else None,
        )

    unresolved_posture = _as_posture(
        defaults.get("unresolved_posture", "review"), "defaults.unresolved_posture"
    )
    unknown_posture = _as_posture(
        defaults.get("unknown_posture", "review"), "defaults.unknown_posture"
    )
    # The two pseudo-categories must exist so the engine can attach obligations.
    for required in ("unresolved", "unknown"):
        if required not in categories:
            raise PolicyError(f"Policy must define a '{required}' category to describe that case.")

    multi_or = str(settings.get("multi_license_or", "best")).lower()
    multi_and = str(settings.get("multi_license_and", "worst")).lower()
    for name, val in (("multi_license_or", multi_or), ("multi_license_and", multi_and)):
        if val not in ("best", "worst"):
            raise PolicyError(f"settings.{name} must be 'best' or 'worst', found '{val}'.")

    return Policy(
        name=str(meta.get("name", "unnamed policy")),
        source_path=str(resolved),
        scenario=str(meta.get("scenario", "")),
        multi_or=multi_or,
        multi_and=multi_and,
        unresolved_posture=unresolved_posture,
        unknown_posture=unknown_posture,
        categories=categories,
        licenses=license_map,
        patterns=patterns,
        exception_overrides=exc_overrides,
        raw=data,
    )
