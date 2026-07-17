"""Database seeding utilities."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import RetailerModel

SUPPORTED_RETAILERS: list[tuple[str, str]] = [
    ("blinkit", "Blinkit"),
    ("zepto", "Zepto"),
    ("instamart", "Swiggy Instamart"),
    ("bigbasket", "BigBasket"),
]


async def ensure_retailers_seeded(session: AsyncSession) -> None:
    """Idempotent upsert of supported retailers by slug.

    Args:
        session: The SQLAlchemy async session.
    """
    existing = (await session.execute(select(RetailerModel.slug))).scalars().all()
    existing_slugs = set(existing)
    for slug, name in SUPPORTED_RETAILERS:
        if slug not in existing_slugs:
            session.add(RetailerModel(slug=slug, name=name, is_active=True))
    await session.commit()
