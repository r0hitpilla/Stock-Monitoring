"""CSS selectors for scraping Blinkit's storefront.

These target ``data-test-id`` attributes, which are the most robust hook
available on this kind of frontend. Retailer frontends change; if
extraction starts returning ``None`` for fields that should be populated,
the fix is to open the live product page in a browser, inspect the current
DOM, and update ``BLINKIT_SELECTORS`` below. This is expected, ongoing
scraper maintenance, not a defect in the provider logic.

No cart/checkout selectors are ever clicked by this provider — the
``add-to-cart`` selector, where present, is used only as an availability
signal and is never actuated.
"""

BLINKIT_SELECTORS: dict[str, str] = {
    "location_trigger": "[data-test-id='select-location']",
    "location_input": "[data-test-id='location-search-input']",
    "location_confirm": "[data-test-id='location-confirm']",
    "search_result_card": "[data-test-id='plp-product-card'] a",
    "product_name": "[data-test-id='product-name']",
    "price": "[data-test-id='product-price']",
    "mrp": "[data-test-id='product-mrp']",
    "eta": "[data-test-id='eta']",
    "store": "[data-test-id='store-name']",
    "image": "[data-test-id='product-image'] img",
    "quantity": "[data-test-id='product-quantity']",
    "variants": "[data-test-id='variant-option']",
    "out_of_stock_badge": "[data-test-id='out-of-stock']",
    "low_stock_badge": "[data-test-id='low-stock']",
}
