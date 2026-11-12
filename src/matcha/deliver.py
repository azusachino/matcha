"""Whether a resolved link becomes a message or a card.

Policy, not capability, decides. A bot that can upload does not therefore upload: the
rule table is explicit per bot, so a new capacity (a size we happen to know) cannot
silently change behavior. That is why ``auto_preview`` exists as a field instead of
being inferred from whether a plan is available.
"""

from __future__ import annotations

from .types import (
    Capabilities,
    Card,
    Delivery,
    MediaInfo,
    Policy,
    Reason,
    StreamPlan,
    Upload,
)


def decide(
    info: MediaInfo,
    plan: StreamPlan | None,
    caps: Capabilities,
    policy: Policy,
) -> Delivery:
    """Return ``Upload`` when the plan fits the destination, else a ``Card`` with why.

    Order matters: the bot's own choice comes first, then the destination's permission,
    and only then whether a plan exists. A chat that may not preview must hear "no
    access", not "no plan" -- the latter would report a failure to price a download
    that policy had already forbidden.
    """
    if not policy.auto_preview:
        return Card(Reason.MANUAL_POLICY)
    if not caps.preview_allowed:
        return Card(Reason.NO_ACCESS)
    if plan is None:
        return Card(Reason.NO_PLAN)
    if plan.estimated_bytes > caps.max_upload_bytes:
        return Card(Reason.TOO_LARGE)
    return Upload(plan)


def fits_caption(info: MediaInfo, caps: Capabilities) -> bool:
    """A metadata-only card needs no plan; it is always allowed."""
    return True
