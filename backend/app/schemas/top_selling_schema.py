"""Response models for the top selling products report."""

from datetime import date

from pydantic import BaseModel


class TopSellingRow(BaseModel):
    """One product and how much of it sold on the requested day."""

    product_id: int
    product_name: str
    product_code: str | None = None
    category_name: str | None = None
    sale_date: date
    total_quantity: float
    total_revenue: float
