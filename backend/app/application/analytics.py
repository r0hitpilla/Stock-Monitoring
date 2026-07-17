"""Pure business logic for availability and restock analytics."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import DetectionEvent
from app.domain.enums import EventType


@dataclass
class AvailabilitySummary:
    """Aggregate availability/restock metrics for a watch over a period.

    Attributes:
        availability_pct: Percentage of the period the product was in stock.
        restock_count: Number of times the product transitioned back to available.
        total_downtime_minutes: Total minutes spent out of stock in the period.
        average_downtime_minutes: Mean length of each downtime window, in minutes.
    """

    availability_pct: float
    restock_count: int
    total_downtime_minutes: float
    average_downtime_minutes: float


def compute_availability_summary(
    events: list[DetectionEvent], period_start: datetime, period_end: datetime
) -> AvailabilitySummary:
    """Compute availability/restock metrics from a list of detection events.

    Walks OUT_OF_STOCK -> STOCK_AVAILABLE event pairs to build downtime windows.
    An unclosed trailing OUT_OF_STOCK event counts as down until `period_end`.
    This is a pure function with no I/O; callers are responsible for scoping
    `events` to the `[period_start, period_end]` window before calling it.

    Args:
        events: Detection events to analyze. Should already be scoped to the
            period of interest; events outside `[period_start, period_end]`
            are not filtered out by this function.
        period_start: The start of the period being summarized.
        period_end: The end of the period being summarized.

    Returns:
        The computed AvailabilitySummary.
    """
    sorted_events = sorted(events, key=lambda e: e.created_at)

    downtime_periods: list[tuple[datetime, datetime]] = []
    open_outage_start: datetime | None = None
    for event in sorted_events:
        if event.event_type == EventType.OUT_OF_STOCK:
            open_outage_start = event.created_at
        elif (
            event.event_type == EventType.STOCK_AVAILABLE
            and open_outage_start is not None
        ):
            downtime_periods.append((open_outage_start, event.created_at))
            open_outage_start = None
    if open_outage_start is not None:
        downtime_periods.append((open_outage_start, period_end))

    total_downtime_minutes = (
        sum((end - start).total_seconds() for start, end in downtime_periods) / 60
    )
    total_period_minutes = (period_end - period_start).total_seconds() / 60
    availability_pct = (
        100.0
        if total_period_minutes <= 0
        else max(0.0, 100 * (1 - total_downtime_minutes / total_period_minutes))
    )
    restock_count = sum(
        1 for e in sorted_events if e.event_type == EventType.STOCK_AVAILABLE
    )
    average_downtime_minutes = (
        total_downtime_minutes / len(downtime_periods) if downtime_periods else 0.0
    )

    return AvailabilitySummary(
        availability_pct=round(availability_pct, 2),
        restock_count=restock_count,
        total_downtime_minutes=round(total_downtime_minutes, 2),
        average_downtime_minutes=round(average_downtime_minutes, 2),
    )
