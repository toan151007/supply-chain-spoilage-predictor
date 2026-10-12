"""
Pydantic schemas for the dashboard API.

Every figure here is aggregated in SQL, never in Python, so the endpoint
stays fast regardless of how large the tables grow.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class OverviewResponse(BaseModel):
    """
    Headline figures for the dashboard home screen.

    `total_revenue` and `total_inventory_value` are computed from SIMULATED
    prices. The Kaggle dataset has no price column, so prices were assigned
    per product category to make the revenue dashboard work. These numbers
    must not be presented as real figures in the report. See AGENTS.md.

    `total_inventory_value` uses `unit_cost`, not `selling_price`, because
    inventory is valued at cost until the goods are sold.
    """

    total_revenue: float = Field(description="Sum of orders.total_amount (simulated prices)")
    total_orders: int
    total_products: int = Field(description="Active products")
    total_stores: int = Field(description="Active stores")
    total_inventory_value: float = Field(
        description="quantity x unit_cost across all batches"
    )
    total_alerts_unread: int
    generated_at: datetime


class RevenuePoint(BaseModel):
    """One data point on the revenue chart."""

    # Start of the day, week, month or year this point covers.
    period_start: date
    revenue: float
    order_count: int
    total_quantity: float


class RevenueResponse(BaseModel):
    """
    Revenue series aggregated by time bucket.

    Empty buckets are omitted rather than returned as zero, so a sparse
    period does not render as a flat line full of misleading zeros.
    """

    period: str = Field(description="day | week | month | year")
    year: int | None = Field(
        description="Restrict to one calendar year. NULL means all years."
    )
    total_revenue: float
    total_orders: int
    points: list[RevenuePoint]


class TopProductResponse(BaseModel):
    """A product ranked by units sold."""

    product_id: int
    product_code: str
    product_name: str
    unit: str
    total_quantity: float
    total_revenue: float = Field(
        description="Simulated prices - see OverviewResponse"
    )


class LowStockResponse(BaseModel):
    """
    A product-stock pair whose quantity is below its minimum.

    Sourced from view `v_low_stock`, which already applies the
    `SUM(quantity) < min_stock` rule per store and product.
    """

    store_id: int
    product_id: int
    product_code: str
    product_name: str
    unit: str
    total_quantity: float
    min_stock: float
    reorder_point: float | None = None
    shortage: float = Field(description="min_stock minus total_quantity")


class ExpiringResponse(BaseModel):
    """
    A batch that is expired or close to expiry.

    Sourced from view `v_expiring_inventory`, which only covers batches
    within 30 days of today. A larger `days` cannot widen it - the view's
    own WHERE clause is the limit.
    """

    inventory_id: int
    store_id: int
    product_id: int
    product_code: str
    product_name: str
    batch_code: str | None = None
    quantity: float
    expiry_date: date
    days_to_expiry: int = Field(
        description="Negative when already expired"
    )
    stock_value: float
    alert_severity: str = Field(
        description="expired | critical | high | medium | low, computed by the view"
    )


class SeverityCount(BaseModel):
    """One severity bucket with its count."""

    severity: str
    count: int


class TypeCount(BaseModel):
    """One alert type with its count."""

    alert_type: str
    count: int
    unresolved: int


class AlertsSummaryResponse(BaseModel):
    """Alert counts grouped for a dashboard panel."""

    total: int
    unread: int
    unresolved: int
    critical_unread: int = Field(
        description="Unread and critical - what the badge should highlight"
    )
    by_type: list[TypeCount]
    by_severity: list[SeverityCount]