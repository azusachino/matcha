"""Errors shared by the core and its callers."""

from __future__ import annotations


class MatchaError(Exception):
    """Base class, so a bot can catch the whole family."""


class NeedsExpansionError(MatchaError):
    """A short link whose target cannot be derived without a network round trip."""


class PolicyError(MatchaError):
    """A policy was asked for a decision it does not carry.

    Raised by :func:`matcha.deliver.decide` when ``auto_preview`` is ``None``: the bot has
    to state its own product choice rather than inherit one. A :class:`MatchaError`
    subclass on purpose -- ``except MatchaError`` in a bot's sink is where this belongs,
    not an exception escaping that handler.
    """

    def __init__(self, field: str = "auto_preview") -> None:
        super().__init__(f"policy makes no {field} decision; set Policy.{field}")
        self.field = field


class ApiError(MatchaError):
    """A platform answered with a non-zero code; ``code`` is the platform's own."""

    def __init__(self, code: int, message: str = "") -> None:
        super().__init__(f"platform error {code}: {message}".strip())
        self.code = code
        self.message = message
