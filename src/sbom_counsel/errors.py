"""Exception hierarchy for sbom-counsel.

Every error a user can plausibly trigger (bad input file, unparseable SBOM,
invalid policy, invalid exceptions) is represented here so the CLI can present a
clear, actionable message and a sensible exit code instead of a raw traceback.
"""

from __future__ import annotations


class SbomCounselError(Exception):
    """Base class for all expected, user-facing errors."""


class InputError(SbomCounselError):
    """The input SBOM file is missing, unreadable, or not valid JSON."""


class UnsupportedFormatError(SbomCounselError):
    """The input could not be identified as a supported SBOM format/version."""


class PolicyError(SbomCounselError):
    """The licence policy file is missing, malformed, or internally inconsistent."""


class ExceptionsError(SbomCounselError):
    """The exceptions file is missing, malformed, or has an invalid entry."""


class CargoToolError(SbomCounselError):
    """An optional cargo helper (cargo-about / cargo-deny) failed or is absent."""
