"""
Pydantic schemas for request and response bodies.

Import from the concrete module, for example:
    from app.schemas.product_schema import ProductCreate
"""

from app.schemas.alert_schema import (
    AlertPage,
    AlertRead,
    MarkReadRequest,
    ResolveRequest,
)
from app.schemas.category_schema import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
)
from app.schemas.common import Message, Page
from app.schemas.forecast_schema import (
    ForecastPage,
    ForecastRead,
    LatestForecast,
    LatestForecastList,
)
from app.schemas.inventory_schema import (
    ExpiringBatch,
    ExpiringReport,
    InventoryCreate,
    InventoryPage,
    InventoryRead,
    InventoryUpdate,
)
from app.schemas.product_schema import (
    CategoryBrief,
    ProductBase,
    ProductBrief,
    ProductCreate,
    ProductPage,
    ProductRead,
    ProductUpdate,
)
from app.schemas.store_schema import (
    StoreBase,
    StoreBrief,
    StoreCreate,
    StoreRead,
    StoreUpdate,
)

__all__ = [
    "AlertPage", "AlertRead", "MarkReadRequest", "ResolveRequest",
    "CategoryBrief", "CategoryCreate", "CategoryRead", "CategoryUpdate",
    "ForecastPage", "ForecastRead", "LatestForecast", "LatestForecastList",
    "ExpiringBatch", "ExpiringReport",
    "InventoryCreate", "InventoryPage", "InventoryRead", "InventoryUpdate",
    "Message", "Page",
    "ProductBase", "ProductBrief", "ProductCreate", "ProductPage",
    "ProductRead", "ProductUpdate",
    "StoreBase", "StoreBrief", "StoreCreate", "StoreRead", "StoreUpdate",
]