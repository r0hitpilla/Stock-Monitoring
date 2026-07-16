from enum import Enum


class Availability(str, Enum):
    """Product availability status."""

    AVAILABLE = "available"
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"


class EventType(str, Enum):
    """Event types for detection and monitoring."""

    STOCK_AVAILABLE = "stock_available"
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"
    PRICE_CHANGED = "price_changed"
    NEW_VARIANT = "new_variant"
    ETA_CHANGED = "eta_changed"
    STORE_CHANGED = "store_changed"


class NotificationChannelType(str, Enum):
    """Notification delivery channels."""

    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"
    PUSH = "push"
