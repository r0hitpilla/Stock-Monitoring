from datetime import datetime, timezone

from app.domain.entities import ProviderProductResult
from app.domain.enums import Availability


def test_provider_product_result_defaults_variants_to_empty_list():
    result = ProviderProductResult(
        retailer_slug="blinkit",
        keyword="milk",
        product_name="Amul Milk 500ml",
        availability=Availability.AVAILABLE,
        price=29.0,
        mrp=32.0,
        discount_pct=9.4,
        eta_minutes=10,
        store_name="Blinkit Koramangala",
        image_url="https://example.com/milk.jpg",
        quantity_label="500 ml",
        product_url="https://blinkit.com/prn/milk/123",
        scraped_at=datetime.now(timezone.utc),
    )

    assert result.variants == []
    assert result.availability is Availability.AVAILABLE
