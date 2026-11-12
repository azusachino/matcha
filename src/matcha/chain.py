"""Running ordered engines, and knowing when a file is actually finished.

The chain is shared by *resolution* and *fetching*. A single engine for one stage and
several for another is how a bot ends up losing links that it could still have saved:
suzuran resolved with yt-dlp alone while downloading with yt-dlp and yutto.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol, TypeVar

from .types import Attempt, ChainResult, Failure, File, Outcome, Reason, Unavailable


class ProbeLike(Protocol):
    """What completeness needs: a byte size and, when known, a duration.

    Bots may pass their own richer probe (for example one that also records whether the
    file parses and yields a name) as long as it keeps these two fields; an injected
    ``expectation`` can then read the extra fields. The members are read-only properties
    on purpose: a frozen dataclass probe has read-only fields, and a writable-attribute
    protocol would reject it while the runtime accepted it.
    """

    @property
    def size_bytes(self) -> int: ...

    @property
    def duration_s(self) -> float | None: ...


@dataclass(frozen=True, slots=True)
class Probe:
    """What a produced file actually is, so a truncated success can be rejected."""

    size_bytes: int
    duration_s: float | None = None


#: Bound once on both sides of ``is_complete``/``run_chain`` so an expectation written
#: for a bot's richer probe stays assignable (see :data:`Expectation`).
_P = TypeVar("_P", bound=ProbeLike)


#: A question about the probe the caller actually produced. A
#: ``Callable[[ProbeLike], bool]`` alias would reject the very expectations the
#: ``is_complete`` docstring advertises: a bot's probe carries more fields, so
#: ``Callable[[_NamedProbe], bool]`` is contravariantly incompatible with a narrower
#: parameter. One TypeVar bound on both the probe and the expectation keeps the
#: annotation honest -- the expectation is only ever called with the probe the same call
#: produced.
Expectation = Callable[[_P], bool]


class Engine(Protocol):
    """One way to obtain the media. The id and version are logged on every attempt."""

    id: str

    def version(self) -> str: ...

    def attempt(self) -> Outcome: ...


class ChainFailed(Exception):
    """No engine produced a complete file; ``attempts`` says what each one said."""

    def __init__(self, attempts: tuple[Attempt, ...]) -> None:
        self.attempts = attempts
        reasons = ", ".join(
            f"{a.engine}:{getattr(a.outcome, 'reason', 'unavailable')}" for a in attempts
        )
        super().__init__(f"every engine failed ({reasons})")

    @property
    def reason(self) -> Reason:
        for attempt in reversed(self.attempts):
            if isinstance(attempt.outcome, Failure):
                return attempt.outcome.reason
        return Reason.EXTRACTOR_FAILED


def is_complete(
    probe: _P,
    expected_duration_s: float | None,
    *,
    tolerance: float = 0.25,
    expectation: Expectation[_P] | None = None,
) -> bool:
    """A file is complete when it exists, is not a stub, and meets the expectation.

    The default expectation is the published duration: a stream that stopped early is a
    failure, not a success, and a file at or below the 1024-byte floor is a stub. A bot
    with a better question ("does it parse and name the work?") passes its own
    ``expectation``; it then owns the whole verdict, including size, so a small but
    valid metadata document is not rejected by a media-file floor. Callers that pass no
    expectation keep the default shape and behavior exactly.
    """
    if expectation is not None:
        return bool(expectation(probe))
    if probe.size_bytes <= 1024:
        return False
    if expected_duration_s and probe.duration_s:
        return probe.duration_s >= expected_duration_s * (1 - tolerance)
    return True


def run_chain(
    engines: Iterable[Engine],
    *,
    probe: Callable[[str], _P] | None = None,
    expected_duration_s: float | None = None,
    expectation: Expectation[_P] | None = None,
    log: Callable[[Attempt], None] | None = None,
) -> ChainResult:
    """Try engines in order; the first complete result wins, every attempt is kept."""
    attempts: list[Attempt] = []
    for engine in engines:
        version = engine.version()
        outcome = engine.attempt()
        attempt = Attempt(engine.id, version, outcome)
        attempts.append(attempt)
        if log is not None:
            log(attempt)
        if isinstance(outcome, File):
            if probe is not None and not is_complete(
                probe(outcome.path),
                expected_duration_s,
                expectation=expectation,
            ):
                continue
            return ChainResult(outcome.path, engine.id, tuple(attempts))
    raise ChainFailed(tuple(attempts))


def fresh_chain(*, out_dir: str, engines: Iterable[Engine]) -> Callable[[], ChainResult]:
    """Bind a chain to one output directory, so callers cannot forget it."""

    def run() -> ChainResult:
        return run_chain(engines)

    run.out_dir = out_dir  # type: ignore[attr-defined]
    return run


__all__ = [
    "ChainFailed",
    "Engine",
    "Expectation",
    "Probe",
    "ProbeLike",
    "Unavailable",
    "is_complete",
    "run_chain",
]
