"""The extension seam: one :class:`PlatformSpec` per platform, registered in order.

Adding a platform is one module plus one line in ``platforms/__init__.py``. Nothing in
``link.py``, ``chain.py`` or ``deliver.py`` changes, which is the point of keeping the
grammar, the request builders and the payload parsers behind this boundary.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..types import WorkRef

Params = list[tuple[str, str]]
ParseFn = Callable[[str, str, Params], "WorkRef | None"]
CanonicalFn = Callable[[WorkRef], "str | None"]


@dataclass(frozen=True, slots=True)
class PlatformSpec:
    name: str
    hosts: frozenset[str]
    parse: ParseFn
    canonical: CanonicalFn

    def handles(self, host: str) -> bool:
        return host in self.hosts
