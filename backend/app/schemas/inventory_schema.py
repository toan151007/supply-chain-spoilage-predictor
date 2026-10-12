"""Pydantic schemas for the inventory API."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page
from app.schemas.product_schema import ProductBrief
from app.schemas.store_schema import StoreBrief


class InventoryBase(BaseModel):
    """
    Fields accepted when creating or updating a stock batch.

    The database has UNIQUE (store_id, product_id, expiry_date), so a batch
    is identified by that triple rather than by an expiry date alone.
    """

    model_config = ConfigDict(from_attributes=True)

    store_id: Annotated[int, Field(gt=0)]
    product_id: Annotated[int, Field(gt=0)]
    expiry_date: date | None = None
    quantity: Annotated[float, Field(ge=0)] = 0
    received_date: date | None = None
    batch_code: Annotated[str | None, Field(max_length=50)] = None


class InventoryCreate(InventoryBase):
    """Request body for POST /api/v1/inventory."""


class InventoryUpdate(BaseModel):
    """Request body for PUT /api/v1/inventory/{id}. All fields optional."""

    model_config = ConfigDict(from_attributes=True)

    expiry_date: date | None = None
    quantity: Annotated[float | None, Field(ge=0)] = None
    received_date: date | None = None
    batch_code: Annotated[str | None, Field(max_length=50)] = None


class InventoryRead(InventoryBase):
    """Response body returned by GET endpoints."""

    inventory_id: int
    created_at: datetime
    updated_at: datetime

    # `days_to_expiry` is a Python property on the ORM model, computed from
    # `expiry_date`. It is exposed here so the frontend does not have to do
    # the date arithmetic itself.
    days_to_expiry: int | None = None
    store: StoreBrief | None = None
    product: ProductBrief | None = None


class ExpiringBatch(BaseModel):
    """
    Response for the expiring-stock report.

    `days_left` is negative for an already expired batch, which lets the
    frontend colour expired and soon-to-expire rows differently.
    """

    model_config = ConfigDict(from_attributes=True)

    inventory_id: int
    store_id: int
    product_id: int
    expiry_date: date | None
    days_left: int | None
    quantity: float
    product: ProductBrief | None = None


class ExpiringReport(BaseModel):
    """Envelope for the expiring-stock report."""

    days: int = Field(description="Window used for the report")
    as_of: date = Field(description="Date the report was computed")
    total: int
    items: list[ExpiringBatch]


InventoryPage = Page[InventoryRead]

