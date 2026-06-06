"""Resolve a component's raw licence strings to a normalised SPDX expression.

This layer is deliberately thin and delegates the hard problem — parsing SPDX
licence expressions with AND/OR/WITH and compound grouping — to the
``license-expression`` library, which carries the official SPDX licence and
exception lists and works entirely offline.

The rules here are conservative by construction:

* The concluded licence is preferred over the declared licence when present.
* ``NOASSERTION``, an empty value, or an unparseable expression yields an
  *unresolved* result. The policy engine maps unresolved components to the
  policy's conservative default; this layer never guesses a licence.
* Unknown (non-SPDX) identifiers are recorded but do not abort resolution, so a
  ``MIT AND SomePrivate-1.0`` expression still surfaces the MIT obligations while
  flagging the unknown part.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import TYPE_CHECKING

from license_expression import ExpressionError, LicenseSymbol

from ..models import Component, ResolvedLicence

if TYPE_CHECKING:
    from license_expression import Licensing

_NOASSERTION = "NOASSERTION"
_lock = threading.Lock()


@lru_cache(maxsize=1)
def _licensing() -> Licensing:
    """Return a shared SPDX licensing object (construction is relatively costly)."""
    from license_expression import get_spdx_licensing

    return get_spdx_licensing()


def _normalise_known(raw: str) -> str:
    """Map a handful of common deprecated/legacy ids to their current SPDX form.

    Kept intentionally small and explicit; the canonical list lives in
    ``license-expression``. These cover identifiers seen often in real SBOMs that
    pre-date the ``-only`` / ``-or-later`` split.
    """
    legacy = {
        "GPL-2.0": "GPL-2.0-only",
        "GPL-2.0+": "GPL-2.0-or-later",
        "GPL-3.0": "GPL-3.0-only",
        "GPL-3.0+": "GPL-3.0-or-later",
        "LGPL-2.1": "LGPL-2.1-only",
        "LGPL-2.1+": "LGPL-2.1-or-later",
        "LGPL-2.0": "LGPL-2.0-only",
        "LGPL-3.0": "LGPL-3.0-only",
        "LGPL-3.0+": "LGPL-3.0-or-later",
        "AGPL-3.0": "AGPL-3.0-only",
        "AGPL-3.0+": "AGPL-3.0-or-later",
    }
    return legacy.get(raw.strip(), raw.strip())


def resolve(component: Component) -> ResolvedLicence:
    """Resolve a single component's licence to a normalised SPDX expression."""
    concluded = (component.concluded_license or "").strip()
    declared = (component.declared_license or "").strip()

    if concluded and concluded.upper() != _NOASSERTION:
        raw, source = concluded, "concluded"
    elif declared and declared.upper() != _NOASSERTION:
        raw, source = declared, "declared"
    elif concluded.upper() == _NOASSERTION or declared.upper() == _NOASSERTION:
        return ResolvedLicence(
            raw=_NOASSERTION,
            source_field="concluded" if concluded.upper() == _NOASSERTION else "declared",
            expression=None,
            unresolved=True,
            unresolved_reason="Licence is NOASSERTION in the SBOM.",
        )
    else:
        return ResolvedLicence(
            raw=None,
            source_field="none",
            expression=None,
            unresolved=True,
            unresolved_reason="No licence information was found for this component.",
        )

    normalised = _normalise_known(raw)
    licensing = _licensing()
    # license-expression's parser is not documented as thread-safe; guard it.
    with _lock:
        try:
            parsed = licensing.parse(normalised, validate=False, strict=False)
        except (ExpressionError, ValueError) as exc:
            return ResolvedLicence(
                raw=raw,
                source_field=source,
                expression=None,
                unresolved=True,
                unresolved_reason=f"Licence expression could not be parsed: {exc}",
            )

        if parsed is None:
            return ResolvedLicence(
                raw=raw,
                source_field=source,
                expression=None,
                unresolved=True,
                unresolved_reason="Licence expression resolved to nothing.",
            )

        symbols = list(licensing.license_symbols(parsed, unique=True, decompose=True))
        validation = licensing.validate(parsed)

    license_ids: list[str] = []
    exception_ids: list[str] = []
    for sym in symbols:
        if isinstance(sym, LicenseSymbol) and getattr(sym, "is_exception", False):
            exception_ids.append(sym.key)
        else:
            license_ids.append(str(sym))

    unknown = [k for k in license_ids if k in _unknown_keys(validation)]

    return ResolvedLicence(
        raw=raw,
        source_field=source,
        expression=str(parsed),
        license_ids=sorted(set(license_ids)),
        exception_ids=sorted(set(exception_ids)),
        unknown_ids=sorted(set(unknown)),
        unresolved=False,
    )


def _unknown_keys(validation: object) -> set[str]:
    """Extract the unknown licence keys reported by ``Licensing.validate``."""
    keys: set[str] = set()
    for err in getattr(validation, "errors", []) or []:
        # Messages look like: "Unknown license key(s): Foo-1.0, Bar".
        if "Unknown license key" in err:
            _, _, listed = err.partition(":")
            keys.update(k.strip() for k in listed.split(",") if k.strip())
    return keys
