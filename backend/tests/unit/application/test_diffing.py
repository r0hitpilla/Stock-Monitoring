from datetime import datetime, timezone

from app.application.diffing import diff_snapshots
from app.domain.entities import ProviderProductResult, Snapshot
from app.domain.enums import Availability, EventType


def _snapshot(**overrides) -> Snapshot:
    base = dict(
        id=1,
        watch_target_id=1,
        timestamp=datetime.now(timezone.utc),
        availability=Availability.OUT_OF_STOCK,
        price=29.0,
        mrp=32.0,
        discount_pct=9.4,
        eta_minutes=10,
        store_name="Blinkit Koramangala",
        image_url=None,
        quantity_label="500 ml",
        variants=["500 ml"],
        product_url="https://blinkit.com/prn/milk/123",
    )
    base.update(overrides)
    return Snapshot(**base)


def _result(**overrides) -> ProviderProductResult:
    base = dict(
        retailer_slug="blinkit",
        keyword="milk",
        product_name="Amul Milk 500ml",
        availability=Availability.AVAILABLE,
        price=29.0,
        mrp=32.0,
        discount_pct=9.4,
        eta_minutes=10,
        store_name="Blinkit Koramangala",
        image_url=None,
        quantity_label="500 ml",
        variants=["500 ml"],
        product_url="https://blinkit.com/prn/milk/123",
        scraped_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return ProviderProductResult(**base)


def test_first_ever_snapshot_that_is_in_stock_emits_stock_available():
    events = diff_snapshots(None, _result(availability=Availability.AVAILABLE))
    assert events == [EventType.STOCK_AVAILABLE]


def test_out_of_stock_to_available_emits_stock_available():
    previous = _snapshot(availability=Availability.OUT_OF_STOCK)
    events = diff_snapshots(previous, _result(availability=Availability.AVAILABLE))
    assert EventType.STOCK_AVAILABLE in events


def test_available_to_out_of_stock_emits_out_of_stock():
    previous = _snapshot(availability=Availability.AVAILABLE)
    events = diff_snapshots(previous, _result(availability=Availability.OUT_OF_STOCK))
    assert events == [EventType.OUT_OF_STOCK]


def test_price_change_emits_price_changed():
    previous = _snapshot(availability=Availability.AVAILABLE, price=29.0)
    events = diff_snapshots(
        previous, _result(availability=Availability.AVAILABLE, price=25.0)
    )
    assert events == [EventType.PRICE_CHANGED]


def test_new_variant_emits_new_variant():
    previous = _snapshot(availability=Availability.AVAILABLE, variants=["500 ml"])
    events = diff_snapshots(
        previous,
        _result(availability=Availability.AVAILABLE, variants=["500 ml", "1 L"]),
    )
    assert events == [EventType.NEW_VARIANT]


def test_no_changes_emits_no_events():
    previous = _snapshot(availability=Availability.AVAILABLE)
    events = diff_snapshots(previous, _result(availability=Availability.AVAILABLE))
    assert events == []
