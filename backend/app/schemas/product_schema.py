"""
Pydantic schemas for the products API.

Separating schemas from ORM models keeps the API contract independent from
the database schema. The API must not leak `password_hash`, internal ids or
database-only columns such as `shelf_life_days` to clients.

Numeric columns come back from PostgreSQL as `Decimal`. Pydantic v2 turns
them into `float` here, so routers never have to convert manually.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryBrief(BaseModel):
    """Minimal category info, embedded in the product response."""

    model_config = ConfigDict(from_attributes=True)

    category_id: int
    category_name: str


class ProductBase(BaseModel):
    """Fields accepted when creating or updating a product."""

    model_config = ConfigDict(from_attributes=True)

    product_code: Annotated[str, Field(min_length=1, max_length=50)]
    product_name: Annotated[str, Field(min_length=1, max_length=255)]
    category_id: Annotated[int, Field(gt=0)]

    unit: Annotated[str, Field(min_length=1, max_length=20)]

    unit_cost: Annotated[float, Field(ge=0)] = 0
    selling_price: Annotated[float, Field(ge=0)] = 0

    # Expiry date is NOT a product attribute - it belongs to a batch at a
    # store. See products table design note.
    shelf_life_days: Annotated[int, Field(gt=0)]

    min_stock: Annotated[float, Field(ge=0)] = 0
    max_stock: Annotated[float | None, Field(gt=0)] = None
    is_perishable: bool = True
    reorder_point: Annotated[float | None, Field(ge=0)] = None
    supplier: Annotated[str | None, Field(max_length=200)] = None
    is_active: bool = True

    @field_validator("max_stock")
    @classmethod
    def _max_at_least_min(cls, v: float | None, info):
        """
        Mirror the database CHECK `chk_stock_range`.

        Validating here gives the client a 422 with a clear field name,
        instead of a raw IntegrityError bubbling up as a 500.
        """
        min_stock = info.data.get("min_stock")
        if v is not None and min_stock is not None and v < min_stock:
            raise ValueError("max_stock must be greater than or equal to min_stock")
        return v


class ProductCreate(ProductBase):
    """Request body for POST /api/v1/products."""


class ProductUpdate(BaseModel):
    """
    Request body for PUT /api/v1/products/{id}.

    Every field is optional so a client can send only what changes.
    Omitted fields keep their current database value.
    """

    model_config = ConfigDict(from_attributes=True)

    product_code: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    product_name: Annotated[str | None, Field(min_length=1, max_length=255)] = None
    category_id: Annotated[int, Field(gt=0)] | None = None
    unit: Annotated[str | None, Field(min_length=1, max_length=20)] = None
    unit_cost: Annotated[float, Field(ge=0)] | None = None
    selling_price: Annotated[float, Field(ge=0)] | None = None
    shelf_life_days: Annotated[int, Field(gt=0)] | None = None
    min_stock: Annotated[float, Field(ge=0)] | None = None
    max_stock: Annotated[float | None, Field(gt=0)] = None
    is_perishable: bool | None = None
    reorder_point: Annotated[float | None, Field(ge=0)] = None
    supplier: Annotated[str | None, Field(max_length=200)] = None
    is_active: bool | None = None


class ProductRead(ProductBase):
    """Response body returned by GET endpoints."""

    product_id: int
    created_at: datetime
    updated_at: datetime
    category: CategoryBrief | None = None


class ProductPage(BaseModel):
    """
    Paginated list response.

    Returning an object instead of a bare list lets the frontend know the
    total count, so it can render pagination controls without a second call.
    """

    total: int = Field(description="Total rows matching the filter")
    page: int
    page_size: int
    pages: int = Field(description="Total number of pages")
    items: list[ProductRead]