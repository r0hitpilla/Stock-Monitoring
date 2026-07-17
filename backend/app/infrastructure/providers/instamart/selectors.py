"""CSS selectors for scraping Swiggy Instamart's storefront.

These target ``data-testid`` attributes, which are the most robust hook
available on this kind of frontend. Retailer frontends change; if
extraction starts returning ``None`` for fields that should be populated,
the fix is to open the live product page in a browser, inspect the current
DOM, and update ``INSTAMART_SELECTORS`` below. This is expected, ongoing
scraper maintenance, not a defect in the provider logic.

No cart/checkout selectors are ever clicked by this provider — the
``add-to-cart`` selector, where present, is used only as an availability
signal and is never actuated.
"""

INSTAMART_SELECTORS: dict[str, str] = {
    "location_trigger": "[data-testid='select-location']",
    "location_input": "[data-testid='location-search-input']",
    "location_confirm": "[data-testid='location-confirm']",
    "search_result_card": "[data-testid='item-card'] a",
    "product_name": "[data-testid='item-name']",
    "price": "[data-testid='item-price']",
    "mrp": "[data-testid='item-mrp']",
    "eta": "[data-testid='item-eta']",
    "store": "[data-testid='item-store']",
    "image": "[data-testid='item-image'] img",
    "quantity": "[data-testid='item-quantity']",
    "variants": "[data-testid='item-variant']",
    "out_of_stock_badge": "[data-testid='item-out-of-stock']",
    "low_stock_badge": "[data-testid='item-low-stock']",
}
