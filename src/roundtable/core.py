"""Compatibility layer exposing high level helpers."""

from __future__ import annotations

from .scheduler import arrange_seating, assign_topics, build_timeline
from .session import RoundTableSession as RoundTable

__all__ = [
    "arrange_seating",
    "assign_topics",
    "build_timeline",
    "RoundTable",
]
