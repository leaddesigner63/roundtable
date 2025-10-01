"""Custom exception hierarchy for the roundtable package."""

from __future__ import annotations


class RoundTableError(Exception):
    """Base error for all round table related exceptions."""


class ValidationError(RoundTableError):
    """Raised when input data cannot be validated."""
