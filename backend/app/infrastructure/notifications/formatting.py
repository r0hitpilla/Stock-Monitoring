"""Message formatting for notifications."""

from app.domain.entities import NotificationContext
from app.domain.enums import EventType

_EVENT_LABELS = {
    EventType.STOCK_AVAILABLE: "back in stock",
    EventType.OUT_OF_STOCK: "out of stock",
    EventType.LOW_STOCK: "running low",
    EventType.PRICE_CHANGED: "price changed",
    EventType.NEW_VARIANT: "a new variant available",
    EventType.ETA_CHANGED: "a changed delivery time",
    EventType.STORE_CHANGED: "a changed fulfilling store",
}


def format_message(context: NotificationContext) -> str:
    """Format a notification message from context.

    Args:
        context: The notification context containing message details.

    Returns:
        A formatted message string.
    """
    label = _EVENT_LABELS[context.event_type]
    price_part = f" — ₹{context.snapshot.price:.0f}" if context.snapshot.price is not None else ""
    return f"{context.keyword} on {context.retailer_slug.title()} is now {label}{price_part}."
