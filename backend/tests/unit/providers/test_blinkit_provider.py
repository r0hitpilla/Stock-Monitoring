from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.domain.enums import Availability
from app.infrastructure.providers.blinkit.provider import BlinkitProvider

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture
async def page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        pg = await browser.new_page()
        yield pg
        await browser.close()


@pytest.mark.asyncio
async def test_extracts_available_product_fields(page):
    html = (FIXTURES / "blinkit_product_available.html").read_text()
    await page.set_content(html)
    provider = BlinkitProvider()

    availability = await provider.check_availability_from_page(page)
    price, mrp, discount_pct = await provider.extract_price(page)
    eta_minutes = await provider.extract_eta(page)
    store_name = await provider.extract_store(page)
    quantity_label = await provider.extract_quantity(page)
    variants = await provider.extract_variants(page)
    image_url = await provider.extract_image(page)

    assert availability == Availability.AVAILABLE
    assert price == 29.0
    assert mrp == 32.0
    assert discount_pct == 9.4
    assert eta_minutes == 10
    assert store_name == "Blinkit Koramangala"
    assert quantity_label == "500 ml"
    assert variants == ["500 ml", "1 L"]
    assert image_url == "https://cdn.blinkit.com/milk.jpg"


@pytest.mark.asyncio
async def test_extracts_out_of_stock_product(page):
    html = (FIXTURES / "blinkit_product_out_of_stock.html").read_text()
    await page.set_content(html)
    provider = BlinkitProvider()

    availability = await provider.check_availability_from_page(page)

    assert availability == Availability.OUT_OF_STOCK


@pytest.mark.asyncio
async def test_health_check_returns_false_before_initialize():
    provider = BlinkitProvider()
    assert await provider.health_check() is False
