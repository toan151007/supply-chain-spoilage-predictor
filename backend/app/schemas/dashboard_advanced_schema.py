"""
Pydantic schemas for the advanced dashboard endpoints (B8).

Date filters here are declared as `date`, not `datetime`. These reports are
day-granularity, and `orders.order_date` is `timestamptz` holding +07:00
wall-clock time - passing a UTC midnight boundary silently drops the first
day of any range (see the timezone note in AGENTS.md). A plain `date` has
no offset to get wrong.
"""

from datetime import date

from pydantic import BaseModel, Field


class RevenueByStore(BaseModel):
    """Revenue and order count for one store."""

    store_id: int
    store_code: str
    store_name: str
    total_revenue: float = Field(description="MOCK price figures - see AGENTS.md")
    total_orders: int
    total_quantity: float
    # total_revenue / total_orders, rounded to 2 decimals.
    avg_order_value: float


class RevenueByCategory(BaseModel):
    """Revenue and quantity for one product category."""

    category_id: int
    category_name: str
    total_revenue: float
    total_quantity: float
    product_count: int = Field(description="Distinct products in this category sold")


class InventoryValue(BaseModel):
    """Stock valuation for one store."""

    store_id: int
    store_code: str
    store_name: str

    total_items: float = Field(description="Sum of inventory.quantity")
    total_batches: int

    # Valued at products.unit_cost (cost basis), not selling_price. The
    # figure answers "what is the stock worth to us", not "what would the
    # shelf price be".
    total_value: float
    expiring_value: float = Field(
        description="Part of total_value expiring within 30 days"
    )


class WasteSummary(BaseModel):
    """Headline waste figures across the whole chain."""

    expired_batches: int
    expired_items: float
    expired_value: float

    expiring_batches: int
    expiring_items: float
    expiring_value: float

    # worst case if every batch at or near expiry were written off
    estimated_waste_value: float = Field(
        description="expired_value + expiring_value, i.e. worst-case write-off"
    )
    currency_note: str = Field(
        default="Gia tri tinh theo products.unit_cost (gia MOC PHONG)"
    )


class WasteBatch(BaseModel):
    """One batch contributing to the waste figures."""

    inventory_id: int
    store_id: int
    store_name: str
    product_id: int
    product_code: str
    product_name: str
    expiry_date: date
    days_to_expiry: int
    quantity: float
    value: float
    state: str = Field(description="expired | expiring_soon | ok")


class ForecastComparison(BaseModel):
    """One (store, product, day) where a forecast and an actual exist."""

    store_id: int
    product_id: int
    product_code: str
    product_name: str
    date: date
    predicted_quantity: float
    actual_quantity: float
    error: float = Field(description="actual - predicted")
    abs_percentage_error: float = Field(
        description="|error| / actual * 100. Undefined when actual is 0, reported as 0."
    )


class ForecastAccuracy(BaseModel):
    """
    Accuracy of a forecast model over the compared window.

    All fields are None when no forecast could be matched to an actual.
    """

    model_name: str
    matched_days: int = Field(
        description="Number of (store, product, day) pairs compared"
    )
    mape: float | None = Field(None, description="Mean absolute percentage error, %")
    mae: float | None = Field(None, description="Mean absolute error, units")
    rmse: float | None = Field(None, description="Root mean squared error, units")
    bias: float | None = Field(
        None, description="Mean signed error; positive means under-forecasting"
    )


class ForecastVsActualResponse(BaseModel):
    """
    Forecast quality for the requested window.

    `comparison` is capped so a 30-day x 10-store x 10-product query cannot
    return 3,000 rows of detail by default. `accuracy` always carries the
    aggregate regardless.
    """

    model_name: str
    from_date: date
    to_date: date

    forecast_rows: int = Field(description="Forecast rows in the window")
    actual_rows: int = Field(description="Actual sales rows in the window")
    matched_rows: int = Field(description="Rows where both exist")

    accuracy: ForecastAccuracy
    comparison: list[ForecastComparison] = []
    comparison_truncated: bool = False

    message: str = ""
