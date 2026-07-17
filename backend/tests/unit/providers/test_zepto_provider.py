from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.domain.enums import Availability
from app.infrastructure.providers.zepto.provider import ZeptoProvider

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
    html = (FIXTURES / "zepto_product_available.html").read_text()
    await page.set_content(html)
    provider = ZeptoProvider()

    availability = await provider.check_availability_from_page(page)
    price, mrp, discount_pct = await provider.extract_price(page)
    eta_minutes = await provider.extract_eta(page)
    variants = await provider.extract_variants(page)

    assert availability == Availability.AVAILABLE
    assert price == 27.0
    assert mrp == 30.0
    assert discount_pct == 10.0
    assert eta_minutes == 8
    assert variants == ["500 ml"]


@pytest.mark.asyncio
async def test_extracts_out_of_stock_product(page):
    html = (FIXTURES / "zepto_product_out_of_stock.html").read_text()
    await page.set_content(html)
    provider = ZeptoProvider()

    assert (
        await provider.check_availability_from_page(page) == Availability.OUT_OF_STOCK
    )


@pytest.mark.asyncio
async def test_health_check_returns_false_before_initialize():
    provider = ZeptoProvider()
    assert await provider.health_check() is False
