"""Swiggy Instamart retailer provider.

Implements :class:`BaseRetailProvider` using Playwright for browser
automation. Extraction methods (``extract_price``, ``extract_eta``,
``extract_store``, ``extract_image``, ``extract_quantity``,
``extract_variants``) and :meth:`InstamartProvider.check_availability_from_page`
operate on an already-loaded :class:`playwright.async_api.Page` and perform
no navigation of their own — this is what makes them unit-testable against
local HTML fixtures instead of the live site.

Navigation methods (``initialize``, ``search_product``, ``get_product``,
``check_availability``, ``health_check``) own all real browser navigation
and network I/O.

This provider never clicks "add to cart," never navigates to checkout, and
never submits any purchase-related form. The presence of an add-to-cart
button is used only as an implicit availability signal via the DOM, never
actuated.
"""

import re
from datetime import datetime, timezone

from playwright.async_api import Browser, Page, Playwright, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability
from app.domain.ports.provider import BaseRetailProvider
from app.infrastructure.providers.instamart.selectors import INSTAMART_SELECTORS

BASE_URL = "https://www.swiggy.com/instamart"


class InstamartProvider(BaseRetailProvider):
    """Retail provider adapter for Swiggy Instamart (swiggy.com/instamart)."""

    slug = "instamart"

    def __init__(self) -> None:
        """Initialize the provider with no active browser session."""
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def initialize(self, location: LocationContext) -> None:
        """Launch a browser and set the delivery location on Instamart.

        Args:
            location: The city/pincode context to set as the delivery
                location, if the location picker UI is presented.
        """
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        page = await self._browser.new_page()
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.click(INSTAMART_SELECTORS["location_trigger"], timeout=5000)
                await page.fill(INSTAMART_SELECTORS["location_input"], location.pincode)
                await page.click(INSTAMART_SELECTORS["location_confirm"], timeout=5000)
            except PlaywrightTimeoutError:
                pass  # location UI may already be set from a saved session
        finally:
            await page.close()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8)
    )
    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        """Search Instamart for products matching a keyword.

        Args:
            keyword: The search term to query.

        Returns:
            A list of product results for each matching search result.
        """
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(
                f"{BASE_URL}/search?query={keyword}",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await page.wait_for_selector(
                INSTAMART_SELECTORS["search_result_card"], timeout=10000
            )
            cards = await page.query_selector_all(INSTAMART_SELECTORS["search_result_card"])
            urls = [await card.get_attribute("href") for card in cards]
            return [await self.get_product(f"{BASE_URL}{url}") for url in urls if url]
        finally:
            await page.close()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8)
    )
    async def get_product(self, product_url: str) -> ProviderProductResult:
        """Fetch and extract full product details from an Instamart product page.

        Args:
            product_url: The absolute URL of the product page.

        Returns:
            A populated :class:`ProviderProductResult` for the product.
        """
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            name_el = await page.query_selector(INSTAMART_SELECTORS["product_name"])
            product_name = (await name_el.inner_text()).strip() if name_el else ""
            availability = await self.check_availability_from_page(page)
            price, mrp, discount_pct = await self.extract_price(page)
            return ProviderProductResult(
                retailer_slug=self.slug,
                keyword=product_name,
                product_name=product_name,
                availability=availability,
                price=price,
                mrp=mrp,
                discount_pct=discount_pct,
                eta_minutes=await self.extract_eta(page),
                store_name=await self.extract_store(page),
                image_url=await self.extract_image(page),
                quantity_label=await self.extract_quantity(page),
                variants=await self.extract_variants(page),
                product_url=product_url,
                scraped_at=datetime.now(timezone.utc),
            )
        finally:
            await page.close()

    async def check_availability(self, product_url: str) -> Availability:
        """Navigate to a product page and determine its availability.

        Args:
            product_url: The absolute URL of the product page.

        Returns:
            The current :class:`Availability` status of the product.
        """
        assert self._browser is not None, "call initialize() first"
        page = await self._browser.new_page()
        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            return await self.check_availability_from_page(page)
        finally:
            await page.close()

    async def check_availability_from_page(self, page: Page) -> Availability:
        """Determine availability from an already-loaded product page.

        Performs no navigation; operates purely on the DOM currently
        loaded into ``page``, which is what makes this method testable
        against local HTML fixtures.

        Args:
            page: An already-loaded Playwright page.

        Returns:
            ``Availability.OUT_OF_STOCK`` if the out-of-stock badge is
            present, ``Availability.LOW_STOCK`` if the low-stock badge is
            present, otherwise ``Availability.AVAILABLE``.
        """
        if await page.query_selector(INSTAMART_SELECTORS["out_of_stock_badge"]):
            return Availability.OUT_OF_STOCK
        if await page.query_selector(INSTAMART_SELECTORS["low_stock_badge"]):
            return Availability.LOW_STOCK
        return Availability.AVAILABLE

    async def extract_price(
        self, page: Page
    ) -> tuple[float | None, float | None, float | None]:
        """Extract price, MRP, and discount percentage from a loaded page.

        Args:
            page: An already-loaded Playwright page.

        Returns:
            A ``(price, mrp, discount_pct)`` tuple. ``discount_pct`` is
            ``round((1 - price / mrp) * 100, 1)`` when both price and a
            truthy mrp are present, otherwise ``None``.
        """
        price = await self._extract_number(page, INSTAMART_SELECTORS["price"])
        mrp = await self._extract_number(page, INSTAMART_SELECTORS["mrp"])
        discount_pct = None
        if price is not None and mrp:
            discount_pct = round((1 - price / mrp) * 100, 1)
        return price, mrp, discount_pct

    async def extract_eta(self, page: Page) -> int | None:
        """Extract the estimated delivery time in minutes from a loaded page.

        Args:
            page: An already-loaded Playwright page.

        Returns:
            The ETA in minutes, or ``None`` if not present/parseable.
        """
        el = await page.query_selector(INSTAMART_SELECTORS["eta"])
        if not el:
            return None
        match = re.search(r"(\d+)", await el.inner_text())
        return int(match.group(1)) if match else None

    async def extract_store(self, page: Page) -> str | None:
        """Extract the fulfilling store's name from a loaded page.

        Args:
            page: An already-loaded Playwright page.

        Returns:
            The store name, or ``None`` if not present.
        """
        el = await page.query_selector(INSTAMART_SELECTORS["store"])
        return (await el.inner_text()).strip() if el else None

    async def extract_image(self, page: Page) -> str | None:
        """Extract the product image URL from a loaded page.

        Args:
            page: An already-loaded Playwright page.

        Returns:
            The image ``src`` URL, or ``None`` if not present.
        """
        el = await page.query_selector(INSTAMART_SELECTORS["image"])
        return await el.get_attribute("src") if el else None

    async def extract_quantity(self, page: Page) -> str | None:
        """Extract the product quantity/size label from a loaded page.

        Args:
            page: An already-loaded Playwright page.

        Returns:
            The quantity label (e.g. "500 ml"), or ``None`` if not present.
        """
        el = await page.query_selector(INSTAMART_SELECTORS["quantity"])
        return (await el.inner_text()).strip() if el else None

    async def extract_variants(self, page: Page) -> list[str]:
        """Extract the list of available product variant labels.

        Args:
            page: An already-loaded Playwright page.

        Returns:
            A list of variant labels; empty if none are present.
        """
        elements = await page.query_selector_all(INSTAMART_SELECTORS["variants"])
        return [(await el.inner_text()).strip() for el in elements]

    async def _extract_number(self, page: Page, selector: str) -> float | None:
        """Extract a numeric value (e.g. a rupee amount) from an element's text.

        Args:
            page: An already-loaded Playwright page.
            selector: The CSS selector for the element containing the number.

        Returns:
            The parsed float value, or ``None`` if the element or a
            parseable number is not present.
        """
        el = await page.query_selector(selector)
        if not el:
            return None
        match = re.search(r"[\d,]+\.?\d*", (await el.inner_text()).replace(",", ""))
        return float(match.group(0)) if match else None

    async def health_check(self) -> bool:
        """Check whether the provider's browser session can reach Instamart.

        Returns:
            ``False`` if the provider hasn't been initialized or the
            health-check navigation times out; ``True`` otherwise.
        """
        if self._browser is None:
            return False
        try:
            page = await self._browser.new_page()
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=10000)
            await page.close()
            return True
        except PlaywrightTimeoutError:
            return False

    async def close(self) -> None:
        """Close the browser and stop the Playwright driver, releasing resources."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
