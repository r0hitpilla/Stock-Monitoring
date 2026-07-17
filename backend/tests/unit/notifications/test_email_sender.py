from datetime import datetime, timezone

import pytest

from app.domain.entities import DetectionEvent, NotificationChannel, NotificationContext, Snapshot
from app.domain.enums import Availability, EventType, NotificationChannelType
from app.infrastructure.notifications.email import EmailSender


class FakeSmtp:
    sent_messages: list = []

    def __init__(self, host, port):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, username, password):
        pass

    def send_message(self, message):
        FakeSmtp.sent_messages.append(message)


@pytest.mark.asyncio
async def test_email_sender_sends_via_smtp(monkeypatch):
    import smtplib

    FakeSmtp.sent_messages = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)

    sender = EmailSender("smtp.example.com", 587, "user", "pass", "alerts@example.com")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.EMAIL,
        config={"email": "friend@example.com"}, is_verified=True,
    )
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    context = NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )
    event = DetectionEvent(
        id=1, watch_target_id=7, snapshot_id=1, previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
    )

    result = await sender.send(channel, event, context)

    assert result is True
    assert len(FakeSmtp.sent_messages) == 1
    assert FakeSmtp.sent_messages[0]["To"] == "friend@example.com"


@pytest.mark.asyncio
async def test_email_sender_returns_false_without_address():
    sender = EmailSender("smtp.example.com", 587, "user", "pass", "alerts@example.com")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.EMAIL, config={}, is_verified=False
    )
    result = await sender.send(channel, None, None)  # type: ignore[arg-type]
    assert result is False


class RaisingSmtp:
    def __init__(self, host, port):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, username, password):
        import smtplib

        raise smtplib.SMTPAuthenticationError(535, b"bad creds")

    def send_message(self, message):
        raise AssertionError("send_message should not be called when login fails")


@pytest.mark.asyncio
async def test_email_sender_returns_false_on_smtp_exception(monkeypatch):
    import smtplib

    monkeypatch.setattr(smtplib, "SMTP", RaisingSmtp)

    sender = EmailSender("smtp.example.com", 587, "user", "pass", "alerts@example.com")
    channel = NotificationChannel(
        id=1, user_id=10, type=NotificationChannelType.EMAIL,
        config={"email": "friend@example.com"}, is_verified=True,
    )
    snapshot = Snapshot(
        id=1, watch_target_id=7, timestamp=datetime.now(timezone.utc),
        availability=Availability.AVAILABLE, price=29.0, mrp=32.0, discount_pct=9.4,
        eta_minutes=10, store_name="Blinkit Koramangala", image_url=None,
        quantity_label="500 ml", variants=["500 ml"], product_url="https://blinkit.com/prn/milk/123",
    )
    context = NotificationContext(
        keyword="milk", retailer_slug="blinkit", event_type=EventType.STOCK_AVAILABLE, snapshot=snapshot
    )
    event = DetectionEvent(
        id=1, watch_target_id=7, snapshot_id=1, previous_snapshot_id=None,
        event_type=EventType.STOCK_AVAILABLE, created_at=datetime.now(timezone.utc),
    )

    result = await sender.send(channel, event, context)

    assert result is False
