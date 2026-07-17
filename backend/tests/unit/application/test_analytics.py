from datetime import datetime, timedelta, timezone

from app.application.analytics import compute_availability_summary
from app.domain.entities import DetectionEvent
from app.domain.enums import EventType


def _event(event_type: EventType, minutes_from_start: int, start: datetime) -> DetectionEvent:
    return DetectionEvent(
        id=None, watch_target_id=1, snapshot_id=1, previous_snapshot_id=None,
        event_type=event_type, created_at=start + timedelta(minutes=minutes_from_start),
    )


def test_computes_downtime_and_restock_count_for_closed_outage():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=10)
    events = [
        _event(EventType.OUT_OF_STOCK, 60, start),
        _event(EventType.STOCK_AVAILABLE, 120, start),
    ]

    summary = compute_availability_summary(events, period_start=start, period_end=end)

    assert summary.restock_count == 1
    assert summary.total_downtime_minutes == 60.0
    assert summary.average_downtime_minutes == 60.0
    assert 89.0 < summary.availability_pct < 91.0


def test_trailing_out_of_stock_counts_as_down_until_period_end():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=2)
    events = [_event(EventType.OUT_OF_STOCK, 60, start)]

    summary = compute_availability_summary(events, period_start=start, period_end=end)

    assert summary.total_downtime_minutes == 60.0
    assert summary.restock_count == 0


def test_no_events_means_full_availability():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=1)

    summary = compute_availability_summary([], period_start=start, period_end=end)

    assert summary.availability_pct == 100.0
    assert summary.total_downtime_minutes == 0.0
