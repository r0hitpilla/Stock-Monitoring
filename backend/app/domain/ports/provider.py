from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability

Page = Any  # playwright.async_api.Page — kept as Any here to avoid a hard
# infrastructure dependency inside the domain layer


class BaseRetailProvider(ABC):
    """Common contract every retailer adapter must implement."""

    slug: ClassVar[str]

    @abstractmethod
    async def initialize(self, location: LocationContext) -> None:
        """Initialize the provider with a location context."""
        ...

    @abstractmethod
    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        """Search for products matching the given keyword."""
        ...

    @abstractmethod
    async def get_product(self, product_url: str) -> ProviderProductResult:
        """Fetch a product by its URL."""
        ...

    @abstractmethod
    async def check_availability(self, product_url: str) -> Availability:
        """Check if a product is available."""
        ...

    @abstractmethod
    async def extract_price(
        self, page: Page
    ) -> tuple[float | None, float | None, float | None]:
        """Extract price, MRP, and discount percentage from a page."""
        ...

    @abstractmethod
    async def extract_eta(self, page: Page) -> int | None:
        """Extract estimated time of arrival (ETA) in minutes."""
        ...

    @abstractmethod
    async def extract_store(self, page: Page) -> str | None:
        """Extract store name from a page."""
        ...

    @abstractmethod
    async def extract_image(self, page: Page) -> str | None:
        """Extract product image URL from a page."""
        ...

    @abstractmethod
    async def extract_quantity(self, page: Page) -> str | None:
        """Extract product quantity/size from a page."""
        ...

    @abstractmethod
    async def extract_variants(self, page: Page) -> list[str]:
        """Extract product variants from a page."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        ...

    async def close(self) -> None:
        """Release browser resources. Default no-op; override if needed."""
        return None


class ProviderRegistry(ABC):
    """Registry for managing retail provider instances."""

    @abstractmethod
    def get(self, retailer_slug: str) -> BaseRetailProvider:
        """Get a provider by its slug."""
        ...

    @abstractmethod
    def list_active_slugs(self) -> list[str]:
        """List all active provider slugs."""
        ...
