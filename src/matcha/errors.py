"""Errors shared by the core and its callers."""

from __future__ import annotations


class MatchaError(Exception):
    """Base class, so a bot can catch the whole family."""


class NeedsExpansionError(MatchaError):
    """A short link whose target cannot be derived without a network round trip."""


class ApiError(MatchaError):
    """A platform answered with a non-zero code; ``code`` is the platform's own."""

    def __init__(self, code: int, message: str = "") -> None:
        super().__init__(f"platform error {code}: {message}".strip())
        self.code = code
        self.message = message
