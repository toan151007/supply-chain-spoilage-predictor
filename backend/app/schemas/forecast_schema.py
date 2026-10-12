"""Pydantic schemas for the forecasts API.

The forecasts table is read-only through the API. Its 3000 rows are produced
by `ai-model/scripts/forecast_next_month.py` using the best model per
product-store pair; accepting manual inserts would pollute the dataset the
model evaluation is based on.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page
from app.schemas.product_schema import ProductBrief
from app.schemas.store_schema import StoreBrief

MODEL_NAME_PATTERN = "^(prophet|xgboost|arima|moving_average|naive)$"


class ForecastRead(BaseModel):
    """Response body for a single forecast row."""

    model_config = ConfigDict(from_attributes=True)

    forecast_id: int
    store_id: int
    product_id: int
    model_name: str
    forecast_date: date
    horizon_days: int
    predicted_quantity: float
    lower_bound: float | None = None
    upper_bound: float | None = None

    # Capped by products.max_stock. The uncapped figure lives in
    # ai-model/outputs/forecast_summary_30d.csv (column `raw_need`).
    recommended_import_qty: float | None = None

    rmse: float | None = None
    mae: float | None = None
    mape: float | None = None
    trained_at: datetime
    created_at: datetime

    store: StoreBrief | None = None
    product: ProductBrief | None = None


class LatestForecast(BaseModel):
    """
    The most recent forecast row for a product-store pair.

    One entry per pair, so the frontend can render a planning table without
    grouping 3000 rows itself.

    Note what this is NOT: the values are for the single most recent
    `forecast_date` (30/01/2018), not a sum across the 30-day horizon. For
    horizon totals use `GET /api/v1/forecasts` and aggregate, or read the
    `raw_need` column in ai-model/outputs/forecast_summary_30d.csv.
    """

    model_config = ConfigDict(from_attributes=True)

    store_id: int
    product_id: int
    model_name: str
    forecast_date: date = Field(description="Most recent forecast date")
    predicted_quantity: float = Field(
        description="Predicted quantity for forecast_date itself"
    )
    lower_bound: float | None = None
    upper_bound: float | None = None
    recommended_import_qty: float | None = None
    store: StoreBrief | None = None
    product: ProductBrief | None = None


ForecastPage = Page[ForecastRead]
LatestForecastList = Page[LatestForecast]

