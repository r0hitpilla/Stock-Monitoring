from datetime import datetime, timezone

from app.domain.entities import NotificationContext, Snapshot
from app.domain.enums import Availability, EventType
from app.infrastructure.notifications.formatting import format_message


def test_format_message_includes_keyword_retailer_and_price():
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    context = NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )

    message = format_message(context)

    assert "milk" in message
    assert "Blinkit" in message
    assert "back in stock" in message
    assert "29" in message
