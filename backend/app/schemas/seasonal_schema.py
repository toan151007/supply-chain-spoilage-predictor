"""Pydantic schemas for GET /api/v1/forecasts/seasonal."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SeasonCode = Literal["spring", "summer", "autumn", "winter"]
Recommendation = Literal["import", "neutral", "avoid"]


class SeasonalItem(BaseModel):
    """Mot san pham trong mot mua."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_code: str
    product_name: str
    unit: str | None = None
    category_name: str | None = None

    avg_daily_qty: float = Field(description="Doanh so trung binh/ngay trong mua")
    overall_daily_qty: float = Field(description="Doanh so trung binh/ngay ca nam")
    sample_days: int = Field(description="So ngay co du lieu trong mua")
    season_share: float = Field(description="Ty trong doanh so cua san pham trong mua")
    seasonal_index: float = Field(
        description="Chi so mua vu tuong doi (1.0 = dung muc trung binh)"
    )
    rank_in_season: int = Field(description="Thu hang trong mua, 1 = cao nhat")
    season_products: int = Field(description="So san pham duoc xep hang trong mua")
    recommendation: Recommendation


class SeasonSummary(BaseModel):
    """Toan bo san pham cua mot mua, da chia theo khuyen nghi."""

    model_config = ConfigDict(from_attributes=True)

    season_code: SeasonCode
    season_name: Annotated[str, Field(description="Ten tieng Viet cua mua")]
    months: list[int]
    is_current: bool

    total_products: int
    import_count: int
    avoid_count: int
    neutral_count: int
    avg_index: float | None = None

    import_items: list[SeasonalItem]
    avoid_items: list[SeasonalItem]
    neutral_items: list[SeasonalItem]


class SeasonalForecast(BaseModel):
    """Response body for GET /api/v1/forecasts/seasonal."""

    model_config = ConfigDict(from_attributes=True)

    generated_at: datetime
    data_from: str | None = Field(
        default=None, description="Ngay dau tien cua du lieu lich su (YYYY-MM-DD)"
    )
    data_to: str | None = Field(
        default=None, description="Ngay cuoi cung cua du lieu lich su (YYYY-MM-DD)"
    )
    current_season: SeasonCode
    method: str = Field(description="Giai thich cach tinh chi so mua vu")
    seasons: list[SeasonSummary]
