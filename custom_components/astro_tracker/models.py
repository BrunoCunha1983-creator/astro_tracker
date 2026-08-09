"""Data models for Astro Tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True, frozen=True)
class AstroEvent:
    """A normalized astronomical event."""

    start: datetime
    end: datetime
    summary: str
    event_type: str
    description: str = ""
    location: str = ""
    attributes: dict[str, Any] | None = None


@dataclass(slots=True)
class AstroTrackerData:
    """Normalized coordinator payload."""

    values: dict[str, Any]
    events: list[AstroEvent]
    source_status: dict[str, str]
