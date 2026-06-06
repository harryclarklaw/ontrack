"""Load and validate the project exceptions file.

An exception grants a specific component (optionally pinned to a version) an
overriding posture, with a recorded justification, owner and date. An exception
without a justification is rejected: an unexplained override is exactly what this
tool exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ..errors import ExceptionsError
from ..models import Posture


@dataclass(frozen=True)
class ExceptionRule:
    component: str
    version: str | None  # None matches any version
    posture: Posture
    justification: str
    owner: str
    date: str

    def matches(self, name: str, version: str | None) -> bool:
        if self.component != name:
            return False
        if self.version is None:
            return True
        return self.version == (version or "")


@dataclass
class ExceptionSet:
    source_path: str
    rules: list[ExceptionRule]

    def find(self, name: str, version: str | None) -> ExceptionRule | None:
        """Return the first matching rule. Version-pinned rules take precedence."""
        pinned = [r for r in self.rules if r.version is not None]
        wildcard = [r for r in self.rules if r.version is None]
        for rule in (*pinned, *wildcard):
            if rule.matches(name, version):
                return rule
        return None


def load_exceptions(path: str | Path | None) -> ExceptionSet | None:
    """Load an exceptions file, or return None when no path is given."""
    if path is None:
        return None
    resolved = Path(path)
    if not resolved.exists():
        raise ExceptionsError(f"Exceptions file not found: {resolved}")
    try:
        data = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ExceptionsError(f"Exceptions file {resolved} is not valid YAML: {exc}") from exc

    if data is None:
        return ExceptionSet(source_path=str(resolved), rules=[])
    if not isinstance(data, dict):
        raise ExceptionsError(
            f"Exceptions file {resolved} must be a mapping with an 'exceptions' list."
        )
    entries = data.get("exceptions", [])
    if not isinstance(entries, list):
        raise ExceptionsError("'exceptions' must be a list.")

    rules: list[ExceptionRule] = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ExceptionsError(f"exceptions[{i}] must be a mapping.")
        component = entry.get("component")
        if not isinstance(component, str) or not component.strip():
            raise ExceptionsError(f"exceptions[{i}] is missing a 'component' name.")
        justification = entry.get("justification")
        if not isinstance(justification, str) or not justification.strip():
            raise ExceptionsError(
                f"exceptions[{i}] (component '{component}') has no 'justification'. "
                "Exceptions without a justification are not permitted."
            )
        owner = entry.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            raise ExceptionsError(f"exceptions[{i}] (component '{component}') has no 'owner'.")
        date = entry.get("date")
        if date is None or not str(date).strip():
            raise ExceptionsError(f"exceptions[{i}] (component '{component}') has no 'date'.")
        posture_raw = entry.get("posture")
        try:
            posture = Posture(str(posture_raw).strip().lower())
        except ValueError as exc:
            raise ExceptionsError(
                f"exceptions[{i}] (component '{component}') has invalid posture "
                f"'{posture_raw}'. Expected allowed, review, or blocked."
            ) from exc
        version = entry.get("version")
        rules.append(
            ExceptionRule(
                component=component.strip(),
                version=str(version).strip() if version not in (None, "") else None,
                posture=posture,
                justification=justification.strip(),
                owner=owner.strip(),
                date=str(date).strip(),
            )
        )
    return ExceptionSet(source_path=str(resolved), rules=rules)
