"""
Pydantic schemas for the orders API (don hang).

`orders.total_amount` and `orders.total_quantity` are ordinary columns, not
generated ones, so nothing in the database keeps them in step with
`order_items`. They are **denormalised counters maintained by this API**:
every write to a line recalculates them from
`SUM(line_total)` and `SUM(quantity)` over the parent order.

Prices are MOCK values - the Kaggle dataset has no price column. See the
module docstring in `app/models/order.py` and AGENTS.md; never present these
figures as real revenue.

Numeric columns arrive from PostgreSQL as `Decimal`; Pydantic v2 converts
them to `float` so routers never convert by hand.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import Page
from app.schemas.order_item_schema import OrderItemRead
from app.schemas.store_schema import StoreBrief

# Mirrors the database CHECK constraints, so a bad value produces a 422
# naming the field instead of an IntegrityError surfacing as a 500.
OrderType = Literal["sale", "purchase"]
OrderStatus = Literal["pending", "completed", "cancelled"]
PaymentMethod = Literal["cash", "card", "transfer", "ewallet", "other"]


class OrderItemInput(BaseModel):
    """
    One line supplied inline when creating an order.

    Same rules as `OrderItemCreate` minus `order_id`: the parent is the
    order being created, and the database generates `line_total`.
    """

    model_config = ConfigDict(from_attributes=True)

    product_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[float, Field(gt=0)]
    unit_price: Annotated[float, Field(ge=0)]
    unit_cost: Annotated[float | None, Field(ge=0)] = None
    discount_percent: Annotated[float, Field(ge=0, le=100)] = 0


class OrderCreate(BaseModel):
    """Request body for POST /api/v1/orders."""

    model_config = ConfigDict(from_attributes=True)

    # `order_code` has a UNIQUE constraint; duplicates come back as 409.
    order_code: Annotated[str, Field(min_length=1, max_length=50)]

    store_id: Annotated[int, Field(gt=0)]
    order_type: OrderType = "sale"
    order_date: datetime | None = Field(
        None, description="Defaults to now() when omitted"
    )
    status: OrderStatus = "pending"
    payment_method: PaymentMethod | None = None
    customer_name: Annotated[str | None, Field(max_length=150)] = None
    user_id: Annotated[int | None, Field(gt=0)] = None
    note: Annotated[str | None, Field(max_length=2000)] = None

    # At least one line. An order with no lines has no business meaning here:
    # every seeded order carries exactly 50 lines, and `total_amount` would
    # stay at 0 with nothing to explain it.
    items: Annotated[list[OrderItemInput], Field(min_length=1, max_length=500)]

    @field_validator("items")
    @classmethod
    def _reject_duplicate_products(cls, items: list[OrderItemInput]):
        """
        Reject duplicate products inside one payload.

        The table has UNIQUE (order_id, product_id), so the database would
        reject the whole insert with a generic IntegrityError. Catching it
        here turns that into a 422 that names the offending product.
        """
        seen: set[int] = set()
        for line in items:
            if line.product_id in seen:
                raise ValueError(
                    f"product_id {line.product_id} appears more than once; "
                    "combine the quantities into a single line"
                )
            seen.add(line.product_id)
        return items


class OrderUpdate(BaseModel):
    """
    Request body for PUT /api/v1/orders/{id}.

    Lines are not updatable here - use /api/v1/order-items. The endpoint
    also refuses to touch an order that is completed or cancelled; see the
    router for the reasoning.
    """

    model_config = ConfigDict(from_attributes=True)

    order_code: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    store_id: Annotated[int | None, Field(gt=0)] = None
    order_type: OrderType | None = None
    order_date: datetime | None = None
    payment_method: PaymentMethod | None = None
    customer_name: Annotated[str | None, Field(max_length=150)] = None
    user_id: Annotated[int | None, Field(gt=0)] = None
    note: Annotated[str | None, Field(max_length=2000)] = None


class OrderStatusUpdate(BaseModel):
    """Request body for PUT /api/v1/orders/{id}/status."""

    model_config = ConfigDict(from_attributes=True)

    status: OrderStatus


class OrderRead(BaseModel):
    """
    Response body for order rows.

    `line_count` and `total_items` are derived from `order_items` and are
    not columns on the table:

    - `line_count`  - number of detail rows
    - `total_items` - sum of quantity across those rows
    """

    model_config = ConfigDict(from_attributes=True)

    order_id: int
    order_code: str
    store_id: int
    order_type: str
    order_date: datetime
    total_amount: float
    total_quantity: float
    status: str
    payment_method: str | None
    customer_name: str | None
    user_id: int | None
    note: str | None
    created_at: datetime
    updated_at: datetime

    line_count: int = 0
    total_items: float = 0

    store: StoreBrief | None = None


class OrderDetail(OrderRead):
    """
    Order plus its lines.

    Only returned by the detail endpoint and by /{id}/items consumers that
    need the parent, never by the list endpoint - a page of 20 orders each
    carrying 50 lines would be a 1,000-row response.
    """

    items: list[OrderItemRead] = []


OrderPage = Page[OrderRead]
