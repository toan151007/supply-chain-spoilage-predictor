"""
Pydantic schemas for the recommendation endpoints (B10).

The numbers in these responses come from MOCK prices and from a forecast
horizon that sits entirely outside the sales history. `reason` exists so the
UI can always explain a recommendation in words rather than showing a bare
number the user has to trust.
"""

from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["high", "medium", "low"]


class ImportRecommendation(BaseModel):
    """How much of a product a store should reorder."""

    product_id: int
    product_code: str
    product_name: str
    category_name: str | None = None
    store_id: int
    store_code: str
    store_name: str

    current_stock: float = Field(description="Units on hand right now")
    expiring_stock: float = Field(
        description="Of current_stock, how much expires within 30 days"
    )
    predicted_demand: float = Field(
        description="Sum of forecast over the forecast horizon"
    )
    safety_stock: float = Field(
        description="reorder_point if set, otherwise min_stock"
    )

    recommended_import_qty: float
    priority: Priority
    reason: str


class ExpiringRecommendation(BaseModel):
    """What to do about a batch that is about to expire."""

    inventory_id: int
    store_id: int
    store_code: str
    store_name: str
    product_id: int
    product_code: str
    product_name: str

    expiry_date: str
    days_to_expiry: int
    quantity: float
    unit_value: float = Field(description="products.unit_cost, a MOCK figure")
    total_value: float

    priority: Priority
    action: Literal["discount", "transfer", "destroy"] = Field(
        description=(
            "discount: sell it now while it still has shelf life. "
            "transfer: move it to a store that sells faster. "
            "destroy: too close to expiry to be worth moving."
        )
    )
    reason: str


class SlowMovingProduct(BaseModel):
    """A product holding capital without moving."""

    product_id: int
    product_code: str
    product_name: str
    category_name: str | None = None

    store_id: int
    store_code: str
    store_name: str

    current_stock: float
    stock_value: float
    units_sold_30d: float
    avg_daily_sales_30d: float
    days_of_cover: float | None = Field(
        description="stock / average daily sales; None when nothing sold"
    )
    priority: Priority
    action: Literal["promotion", "stop_ordering", "reduce_order"] = Field()
    reason: str


class RecommendationSummary(BaseModel):
    """Counts across the whole recommendation set."""

    total: int
    high: int
    medium: int
    low: int
    total_recommended_value: float = Field(
        description="Sum of recommended_import_qty valued at unit_cost"
    )
    notes: list[str] = []
