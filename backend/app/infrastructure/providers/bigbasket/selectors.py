"""CSS selectors for scraping BigBasket's storefront.

These target ``data-qa`` attributes, which are the most robust hook
available on this kind of frontend. Retailer frontends change; if
extraction starts returning ``None`` for fields that should be populated,
the fix is to open the live product page in a browser, inspect the current
DOM, and update ``BIGBASKET_SELECTORS`` below. This is expected, ongoing
scraper maintenance, not a defect in the provider logic.

No cart/checkout selectors are ever clicked by this provider — the
``add-to-cart`` selector, where present, is used only as an availability
signal and is never actuated.
"""

BIGBASKET_SELECTORS: dict[str, str] = {
    "location_trigger": "[data-qa='select-location']",
    "location_input": "[data-qa='location-search-input']",
    "location_confirm": "[data-qa='location-confirm']",
    "search_result_card": "[data-qa='product-card'] a",
    "product_name": "[data-qa='product-name']",
    "price": "[data-qa='product-price']",
    "mrp": "[data-qa='product-mrp']",
    "eta": "[data-qa='product-eta']",
    "store": "[data-qa='product-store']",
    "image": "[data-qa='product-image'] img",
    "quantity": "[data-qa='product-quantity']",
    "variants": "[data-qa='product-variant']",
    "out_of_stock_badge": "[data-qa='product-out-of-stock']",
    "low_stock_badge": "[data-qa='product-low-stock']",
}
