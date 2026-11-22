"""
Pydantic schemas for the spoilage risk report.

Every figure is calculated in `sp_Reports_SpoilageRisk` /
`sp_Reports_SpoilageSummary`; this module only describes the response shape so
the frontend cannot drift from the API.

`demand_source` matters when reading the report: only 10 of 50 products have a
Prophet forecast, so the remaining lots use the real 30-day sales rate. A row
with `demand_source = "none"` has neither, and its risk score reflects that no
demand could be measured at all.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class SpoilageRiskRow(BaseModel):
    """One inventory batch in the detail table."""

    inventory_id: int
    batch_code: str | None = None

    store_id: int
    store_code: str
    store_name: str

    product_id: int
    product_code: str
    product_name: str
    unit: str | None = None

    category_id: int | None = None
    category_name: str | None = None

    quantity: float
    unit_cost: float
    stock_value: float

    expiry_date: date
    days_left: int = Field(description="Negative when the batch has expired")

    daily_demand: float = Field(description="Units expected to sell per day")
    demand_source: str = Field(description="forecast | sales | none")
    sellable_qty: float
    unsold_qty: float
    loss_value: float = Field(description="Estimated write-off value at cost")

    risk_score: float = Field(ge=0, le=100)
    risk_level: str = Field(description="safe | warning | high")
    recommended_action: str = Field(
        description="promotion | transfer | inventory_check"
    )
    reason: str


class SpoilageKpi(BaseModel):
    """Headline figures for the four KPI cards."""

    total_stock_qty: float
    total_stock_value: float
    at_risk_qty: float
    at_risk_value: float
    spoilage_rate: float = Field(
        description="at_risk_value / total_stock_value, in percent"
    )
    lots_in_window: int
    lots_to_handle: int
    expired_lots: int
    high_risk_lots: int
    window_days: int


class CategoryRiskPoint(BaseModel):
    """Stacked bar segment for one product category."""

    category_id: int | None = None
    category_name: str | None = None
    safe_count: int
    warning_count: int
    high_count: int
    safe_value: float
    warning_value: float
    high_value: float


class SpoilageTrendPoint(BaseModel):
    """One expiry day on the loss trend line."""

    trend_date: date
    loss_value: float
    total_value: float
    lot_count: int
    handled_rate: float = Field(
        description="Share of the day's expiring value that can still be sold"
    )


class TopRiskLot(BaseModel):
    """A high-risk batch used by the AI summary prompt."""

    product_name: str
    product_code: str
    store_name: str
    batch_code: str | None = None
    quantity: float
    unit: str | None = None
    days_left: int
    risk_score: float
    risk_level: str
    loss_value: float


class SpoilageSummaryResponse(BaseModel):
    """KPI + chart data + the rows behind the AI summary."""

    kpi: SpoilageKpi
    categories: list[CategoryRiskPoint]
    trend: list[SpoilageTrendPoint] = []
    top_risks: list[TopRiskLot]
    generated_at: datetime


class SpoilageAdviceResponse(BaseModel):
    """Free-text recommendations for the report panel."""

    answer: str
    model: str | None = Field(
        default=None,
        description="Gemini model name, 'fallback' or None when not configured",
    )
    generated_at: datetime
