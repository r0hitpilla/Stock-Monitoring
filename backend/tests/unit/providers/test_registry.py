import pytest

from app.domain.entities import LocationContext, ProviderProductResult
from app.domain.enums import Availability
from app.domain.ports.provider import BaseRetailProvider
from app.infrastructure.providers.registry import InMemoryProviderRegistry


class FakeProvider(BaseRetailProvider):
    slug = "fake"

    async def initialize(self, location: LocationContext) -> None:
        self.initialized_with = location

    async def search_product(self, keyword: str) -> list[ProviderProductResult]:
        return []

    async def get_product(self, product_url: str) -> ProviderProductResult:
        raise NotImplementedError

    async def check_availability(self, product_url: str) -> Availability:
        return Availability.AVAILABLE

    async def extract_price(self, page):
        return (0.0, 0.0, 0.0)

    async def extract_eta(self, page):
        return None

    async def extract_store(self, page):
        return None

    async def extract_image(self, page):
        return None

    async def extract_quantity(self, page):
        return None

    async def extract_variants(self, page):
        return []

    async def health_check(self) -> bool:
        return True


def test_registry_lazily_instantiates_and_caches_one_instance_per_slug():
    registry = InMemoryProviderRegistry({"fake": FakeProvider})

    first = registry.get("fake")
    second = registry.get("fake")

    assert isinstance(first, FakeProvider)
    assert first is second
    assert registry.list_active_slugs() == ["fake"]


def test_registry_raises_key_error_for_unknown_slug():
    registry = InMemoryProviderRegistry({})

    with pytest.raises(KeyError):
        registry.get("unknown")
