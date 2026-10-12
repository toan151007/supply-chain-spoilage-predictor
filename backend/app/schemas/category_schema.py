"""Pydantic schemas for the categories API."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    """Fields accepted when creating or updating a category."""

    model_config = ConfigDict(from_attributes=True)

    category_name: Annotated[str, Field(min_length=1, max_length=150)]
    description: str | None = None
    # Self-referencing foreign key. NULL means this is a root category.
    parent_category_id: int | None = Field(default=None, gt=0)


class CategoryCreate(CategoryBase):
    """Request body for POST /api/v1/categories."""


class CategoryUpdate(BaseModel):
    """
    Request body for PUT /api/v1/categories/{id}. All fields optional.

    `exclude_unset` on the router means a field left out keeps its current
    value. Sending `parent_category_id: null` explicitly detaches the
    category and makes it a root - that is different from omitting it.
    """

    model_config = ConfigDict(from_attributes=True)

    category_name: Annotated[str | None, Field(min_length=1, max_length=150)] = None
    description: str | None = None
    parent_category_id: int | None = Field(default=None, gt=0)


class CategoryRead(CategoryBase):
    """Response body returned by GET endpoints."""

    category_id: int
    created_at: datetime
    updated_at: datetime


# CategoryBrief is defined once in app/schemas/product_schema.py and
# re-exported from app/schemas/__init__.py.