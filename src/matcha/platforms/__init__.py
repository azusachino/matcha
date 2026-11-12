"""Registered platform specs, in match order."""

from __future__ import annotations

from . import bilibili, youtube
from .base import PlatformSpec

REGISTRY: tuple[PlatformSpec, ...] = (
    bilibili.SPEC,
    youtube.SPEC,
)


def find(host: str) -> PlatformSpec | None:
    for spec in REGISTRY:
        if spec.handles(host):
            return spec
    return None


def spec_for(name: str) -> PlatformSpec | None:
    for spec in REGISTRY:
        if spec.name == name:
            return spec
    return None


def names() -> tuple[str, ...]:
    return tuple(spec.name for spec in REGISTRY)
