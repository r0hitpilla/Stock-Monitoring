"""Pure snapshot diffing logic.

Compares a stored Snapshot against a freshly-scraped ProviderProductResult
and returns which state-change events fired.
"""

from app.domain.entities import ProviderProductResult, Snapshot
from app.domain.enums import Availability, EventType


def diff_snapshots(
    previous: Snapshot | None, current: ProviderProductResult
) -> list[EventType]:
    """Compare a previous snapshot with a current result and return fired events.

    Args:
        previous: The previously stored snapshot, or None if this is the first ever check.
        current: The freshly-scraped product result.

    Returns:
        List of EventType events that fired due to the comparison. May be empty if nothing changed.
    """
    events: list[EventType] = []

    previous_availability = (
        previous.availability if previous else Availability.OUT_OF_STOCK
    )

    if previous_availability == Availability.OUT_OF_STOCK and current.availability in (
        Availability.AVAILABLE,
        Availability.LOW_STOCK,
    ):
        events.append(EventType.STOCK_AVAILABLE)
    elif (
        previous_availability in (Availability.AVAILABLE, Availability.LOW_STOCK)
        and current.availability == Availability.OUT_OF_STOCK
    ):
        events.append(EventType.OUT_OF_STOCK)
    elif (
        previous_availability == Availability.AVAILABLE
        and current.availability == Availability.LOW_STOCK
    ):
        events.append(EventType.LOW_STOCK)

    if previous is None:
        return events

    if previous.price != current.price:
        events.append(EventType.PRICE_CHANGED)

    if set(current.variants) - set(previous.variants):
        events.append(EventType.NEW_VARIANT)

    if previous.eta_minutes != current.eta_minutes:
        events.append(EventType.ETA_CHANGED)

    if previous.store_name != current.store_name:
        events.append(EventType.STORE_CHANGED)

    return events
