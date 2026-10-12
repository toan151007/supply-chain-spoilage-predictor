"""
Pydantic schemas for the order-items API (dong chi tiet cua don hang).

`line_total` is a GENERATED ALWAYS AS ... STORED column in PostgreSQL:

    line_total = round(quantity * unit_price * (1 - discount_percent/100), 2)

The database owns that value. It is therefore **read-only** here - it does
not appear in any request schema, and the ORM model declares it with
`Computed(persisted=True)`. After an insert or update the value must be
read back with `db.refresh()` before it is returned to the client.

Numeric columns arrive from PostgreSQL as `Decimal`; Pydantic v2 converts
them to `float` so routers never convert by hand.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page
from app.schemas.product_schema import ProductBrief


class OrderItemCreate(BaseModel):
    """Request body for POST /api/v1/order-items."""

    model_config = ConfigDict(from_attributes=True)

    order_id: Annotated[int, Field(gt=0)]
    product_id: Annotated[int, Field(gt=0)]

    # CHECK (quantity > 0) - mirrors chk_order_items_quantity.
    quantity: Annotated[float, Field(gt=0)]
    # CHECK (unit_price >= 0) - mirrors chk_order_items_unit_price.
    unit_price: Annotated[float, Field(ge=0)]
    unit_cost: Annotated[float | None, Field(ge=0)] = None

    # CHECK (0 <= discount_percent <= 100).
    discount_percent: Annotated[float, Field(ge=0, le=100)] = 0

    # NOTE: `line_total` is intentionally absent. It is computed by the
    # database and must never be sent by a client - an INSERT that carries
    # a value for a generated column fails with
    # "cannot insert a non-DEFAULT value into column line_total".


class OrderItemUpdate(BaseModel):
    """
    Request body for PUT /api/v1/order-items/{id}.

    `order_id` is not updatable. Moving a line between orders would have to
    recalculate the totals of both parents, and it is ambiguous whether the
    move should be rejected if the destination already carries that product.
    Delete the line and create a new one instead.
    """

    model_config = ConfigDict(from_attributes=True)

    product_id: Annotated[int | None, Field(gt=0)] = None
    quantity: Annotated[float | None, Field(gt=0)] = None
    unit_price: Annotated[float | None, Field(ge=0)] = None
    unit_cost: Annotated[float | None, Field(ge=0)] = None
    discount_percent: Annotated[float | None, Field(ge=0, le=100)] = None


class OrderItemRead(BaseModel):
    """Response body returned by the order-items endpoints."""

    model_config = ConfigDict(from_attributes=True)

    order_item_id: int
    order_id: int
    product_id: int
    quantity: float
    unit_price: float
    unit_cost: float | None
    discount_percent: float
    # Always present in responses, always computed by PostgreSQL.
    line_total: float
    created_at: datetime

    # Small product stub: these endpoints can return hundreds of rows and the
    # frontend only needs a code and a label to render the table.
    product: ProductBrief | None = None


OrderItemPage = Page[OrderItemRead]
