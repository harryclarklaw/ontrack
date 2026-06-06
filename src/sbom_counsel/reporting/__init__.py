"""Reporting layer: build a report and render it in every output format."""

from __future__ import annotations

from . import html, json_report, markdown, notices
from .report import build_report

__all__ = ["build_report", "markdown", "html", "json_report", "notices"]
