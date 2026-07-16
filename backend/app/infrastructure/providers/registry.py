from typing import Callable

from app.domain.ports.provider import BaseRetailProvider, ProviderRegistry


class InMemoryProviderRegistry(ProviderRegistry):
    """In-memory registry that lazily instantiates and caches provider instances."""

    def __init__(self, factories: dict[str, Callable[[], BaseRetailProvider]]) -> None:
        """Initialize the registry with provider factories.

        Args:
            factories: A dict mapping retailer slugs to callable factory functions
                      that create provider instances.
        """
        self._factories = factories
        self._instances: dict[str, BaseRetailProvider] = {}

    def get(self, retailer_slug: str) -> BaseRetailProvider:
        """Get a provider by slug, lazily instantiating and caching it.

        Args:
            retailer_slug: The slug identifying the provider.

        Returns:
            A cached instance of the provider.

        Raises:
            KeyError: If no provider is registered for the given slug.
        """
        if retailer_slug not in self._factories:
            raise KeyError(f"No provider registered for '{retailer_slug}'")
        if retailer_slug not in self._instances:
            self._instances[retailer_slug] = self._factories[retailer_slug]()
        return self._instances[retailer_slug]

    def list_active_slugs(self) -> list[str]:
        """List all slugs of currently instantiated providers.

        Returns:
            A list of slugs for all providers that have been instantiated.
        """
        return list(self._instances.keys())
