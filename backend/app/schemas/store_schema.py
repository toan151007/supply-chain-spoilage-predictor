"""Pydantic schemas for the stores API."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class StoreBase(BaseModel):
    """Fields accepted when creating or updating a store."""

    model_config = ConfigDict(from_attributes=True)

    store_code: Annotated[str, Field(min_length=1, max_length=20)]
    store_name: Annotated[str, Field(min_length=1, max_length=200)]
    address: str | None = None
    phone: Annotated[str | None, Field(max_length=20)] = None

    # Mirrors the database CHECK constraint.
    store_type: str = Field(
        default="convenience_store",
        pattern="^(convenience_store|restaurant|warehouse)$",
    )
    opening_date: date | None = None
    is_active: bool = True


class StoreCreate(StoreBase):
    """Request body for POST /api/v1/stores."""


class StoreUpdate(BaseModel):
    """Request body for PUT /api/v1/stores/{id}. All fields optional."""

    model_config = ConfigDict(from_attributes=True)

    store_code: Annotated[str, Field(min_length=1, max_length=20)] | None = None
    store_name: Annotated[str | None, Field(min_length=1, max_length=200)] = None
    address: str | None = None
    phone: Annotated[str | None, Field(max_length=20)] = None
    store_type: str | None = Field(
        default=None, pattern="^(convenience_store|restaurant|warehouse)$"
    )
    opening_date: date | None = None
    is_active: bool | None = None


class StoreRead(StoreBase):
    """Response body returned by GET endpoints."""

    store_id: int
    created_at: datetime
    updated_at: datetime


class StoreBrief(BaseModel):
    """Minimal store info for embedding in other responses."""

    model_config = ConfigDict(from_attributes=True)

    store_id: int
    store_code: str
    store_name: str