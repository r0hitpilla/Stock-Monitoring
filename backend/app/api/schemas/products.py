from pydantic import BaseModel


class ProductCreateSchema(BaseModel):
    name: str
    keyword: str
    canonical_image_url: str | None = None


class ProductSchema(BaseModel):
    id: int
    name: str
    keyword: str
    canonical_image_url: str | None
