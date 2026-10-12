"""
Pydantic schemas for request and response bodies.

Import from the concrete module, for example:
    from app.schemas.product_schema import ProductCreate
"""

from app.schemas.product_schema import (
    CategoryBrief,
    ProductBase,
    ProductCreate,
    ProductPage,
    ProductRead,
    ProductUpdate,
)

__all__ = [
    "CategoryBrief",
    "ProductBase",
    "ProductCreate",
    "ProductPage",
    "ProductRead",
    "ProductUpdate",
]