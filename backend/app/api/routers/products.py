from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user_id, get_session
from app.api.schemas.products import ProductCreateSchema, ProductSchema
from app.domain.ports.repositories import ProductRepository
from app.infrastructure.db.repositories import SqlAlchemyProductRepository

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def get_product_repository(
    session: AsyncSession = Depends(get_session),
) -> ProductRepository:
    return SqlAlchemyProductRepository(session)


@router.post("", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreateSchema,
    user_id: int = Depends(get_current_user_id),
    repo: ProductRepository = Depends(get_product_repository),
) -> ProductSchema:
    product = await repo.create(
        user_id, body.name, body.keyword, body.canonical_image_url
    )
    return ProductSchema(
        id=product.id,
        name=product.name,
        keyword=product.keyword,
        canonical_image_url=product.canonical_image_url,
    )


@router.get("", response_model=list[ProductSchema])
async def list_products(
    user_id: int = Depends(get_current_user_id),
    repo: ProductRepository = Depends(get_product_repository),
) -> list[ProductSchema]:
    products = await repo.list_for_user(user_id)
    return [
        ProductSchema(
            id=p.id,
            name=p.name,
            keyword=p.keyword,
            canonical_image_url=p.canonical_image_url,
        )
        for p in products
    ]


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    repo: ProductRepository = Depends(get_product_repository),
) -> None:
    product = await repo.get_by_id(product_id)
    if product is None or product.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    await repo.delete(product_id)
