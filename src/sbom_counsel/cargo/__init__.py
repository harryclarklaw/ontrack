"""Optional convenience wrapper around cargo-about / cargo-deny for Rust projects.

This is a convenience path only. The primary, ecosystem-agnostic route is to feed
the tool a CycloneDX or SPDX SBOM. This module shells out to ``cargo-about`` or
``cargo-deny`` (whichever is present) to gather component licence data from a
Cargo project directory, then normalises it into the same internal model.

Everything here is best-effort and fails gracefully: if the tool is not
installed, or returns nothing usable, a :class:`CargoToolError` is raised with a
clear message and the user is pointed back at the SBOM path. No network access is
performed by this module itself; the underlying cargo tools may require it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..errors import CargoToolError
from ..models import Component

# A cargo-about handlebars template that emits one JSON object describing every
# licence and the crates that use it. We parse this back into components.
_ABOUT_TEMPLATE = """{
  "licenses": [
  {{#each licenses}}
    {
      "id": {{#if id}}"{{id}}"{{else}}null{{/if}},
      "name": {{json name}},
      "used_by": [
      {{#each used_by}}
        { "name": {{json crate.name}}, "version": {{json crate.version}} }{{#unless @last}},{{/unless}}
      {{/each}}
      ]
    }{{#unless @last}},{{/unless}}
  {{/each}}
  ]
}
"""

_ABOUT_CONFIG = "accepted = []\n"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=600, check=False
        )
    except FileNotFoundError as exc:
        raise CargoToolError(f"Command not found: {cmd[0]}.") from exc
    except subprocess.TimeoutExpired as exc:
        raise CargoToolError(f"{' '.join(cmd)} timed out after 600s.") from exc


def available_tool(preferred: str = "auto") -> str | None:
    """Return which cargo helper is available ('about', 'deny') or None."""
    have_about = shutil.which("cargo-about") is not None
    have_deny = shutil.which("cargo-deny") is not None
    if preferred == "about":
        return "about" if have_about else None
    if preferred == "deny":
        return "deny" if have_deny else None
    if have_about:
        return "about"
    if have_deny:
        return "deny"
    return None


def run_cargo_about(project_dir: str | Path) -> list[Component]:
    """Gather components via ``cargo about generate`` with a JSON template."""
    project = Path(project_dir)
    if not (project / "Cargo.toml").exists():
        raise CargoToolError(f"No Cargo.toml found in {project}; not a Cargo project.")
    if shutil.which("cargo-about") is None:
        raise CargoToolError(
            "cargo-about is not installed. Install it with 'cargo install cargo-about', "
            "or use the SBOM input path instead."
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        template_file = tmp_path / "about.hbs"
        config_file = tmp_path / "about.toml"
        template_file.write_text(_ABOUT_TEMPLATE, encoding="utf-8")
        config_file.write_text(_ABOUT_CONFIG, encoding="utf-8")
        proc = _run(
            ["cargo", "about", "generate", "-c", str(config_file), str(template_file)],
            cwd=project,
        )
    if proc.returncode != 0:
        raise CargoToolError(
            "cargo-about failed:\n" + (proc.stderr.strip() or proc.stdout.strip() or "no output")
        )
    return _parse_about_output(proc.stdout)


def _parse_about_output(stdout: str) -> list[Component]:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CargoToolError(f"Could not parse cargo-about output as JSON: {exc}") from exc

    # Invert licence -> crates into crate -> licence ids.
    crate_licences: dict[tuple[str, str], list[str]] = {}
    for lic in data.get("licenses", []) or []:
        lic_id = lic.get("id") or lic.get("name")
        if not lic_id:
            continue
        for used in lic.get("used_by", []) or []:
            key = (str(used.get("name", "")).strip(), str(used.get("version", "")).strip())
            if key[0]:
                crate_licences.setdefault(key, []).append(str(lic_id))

    components: list[Component] = []
    for (name, version), ids in sorted(crate_licences.items()):
        unique = sorted(set(ids))
        expression = unique[0] if len(unique) == 1 else " AND ".join(unique)
        components.append(
            Component(
                name=name,
                version=version or None,
                declared_license=expression,
                purl=f"pkg:cargo/{name}@{version}" if version else f"pkg:cargo/{name}",
            )
        )
    return components


def run_cargo_deny(project_dir: str | Path) -> list[Component]:
    """Gather components via ``cargo deny list`` (JSON output)."""
    project = Path(project_dir)
    if not (project / "Cargo.toml").exists():
        raise CargoToolError(f"No Cargo.toml found in {project}; not a Cargo project.")
    if shutil.which("cargo-deny") is None:
        raise CargoToolError(
            "cargo-deny is not installed. Install it with 'cargo install cargo-deny', "
            "or use the SBOM input path instead."
        )
    proc = _run(["cargo", "deny", "list", "--format", "json", "--layout", "crate"], cwd=project)
    if proc.returncode != 0:
        raise CargoToolError(
            "cargo-deny failed:\n" + (proc.stderr.strip() or proc.stdout.strip() or "no output")
        )
    return _parse_deny_output(proc.stdout)


def _parse_deny_output(stdout: str) -> list[Component]:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CargoToolError(f"Could not parse cargo-deny output as JSON: {exc}") from exc

    components: list[Component] = []
    # cargo-deny crate layout: { "crate name version": { "licenses": [...] }, ... }
    if isinstance(data, dict):
        for key, body in sorted(data.items()):
            name, _, version = str(key).rpartition(" ")
            name = name.strip() or str(key)
            licences: list[object] = []
            if isinstance(body, dict):
                licences = body.get("licenses", []) or list(body.keys())
            expr = None
            if licences:
                unique = sorted({str(x) for x in licences})
                expr = unique[0] if len(unique) == 1 else " AND ".join(unique)
            components.append(
                Component(name=name, version=version.strip() or None, declared_license=expr)
            )
    return components


def gather_components(project_dir: str | Path, tool: str = "auto") -> tuple[str, list[Component]]:
    """Gather components using the selected (or first available) cargo tool."""
    chosen = available_tool(tool)
    if chosen is None:
        raise CargoToolError(
            "Neither cargo-about nor cargo-deny is available. Install one, or use the "
            "SBOM input path (the primary, recommended route)."
        )
    if chosen == "about":
        return "cargo-about", run_cargo_about(project_dir)
    return "cargo-deny", run_cargo_deny(project_dir)


__all__ = ["gather_components", "available_tool", "run_cargo_about", "run_cargo_deny"]
