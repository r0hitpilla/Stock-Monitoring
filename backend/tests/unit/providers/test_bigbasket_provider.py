from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.domain.enums import Availability
from app.infrastructure.providers.bigbasket.provider import BigBasketProvider

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
    html = (FIXTURES / "bigbasket_product_available.html").read_text()
    await page.set_content(html)
    provider = BigBasketProvider()

    availability = await provider.check_availability_from_page(page)
    price, mrp, discount_pct = await provider.extract_price(page)
    quantity_label = await provider.extract_quantity(page)

    assert availability == Availability.AVAILABLE
    assert price == 30.0
    assert mrp == 33.0
    assert discount_pct == 9.1
    assert quantity_label == "500 ml"


@pytest.mark.asyncio
async def test_extracts_out_of_stock_product(page):
    html = (FIXTURES / "bigbasket_product_out_of_stock.html").read_text()
    await page.set_content(html)
    provider = BigBasketProvider()

    assert (
        await provider.check_availability_from_page(page) == Availability.OUT_OF_STOCK
    )


@pytest.mark.asyncio
async def test_health_check_returns_false_before_initialize():
    provider = BigBasketProvider()
    assert await provider.health_check() is False
