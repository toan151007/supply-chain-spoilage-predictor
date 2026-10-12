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
from app.schemas.dashboard_schema import (
    AlertsSummaryResponse,
    ExpiringResponse,
    LowStockResponse,
    OverviewResponse,
    RevenuePoint,
    RevenueResponse,
    SeverityCount,
    TopProductResponse,
    TypeCount,
)
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
from app.schemas.order_item_schema import (
    OrderItemCreate,
    OrderItemPage,
    OrderItemRead,
    OrderItemUpdate,
)
from app.schemas.order_schema import (
    OrderCreate,
    OrderDetail,
    OrderItemInput,
    OrderPage,
    OrderRead,
    OrderStatus,
    OrderStatusUpdate,
    OrderType,
    OrderUpdate,
    PaymentMethod,
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
    "AlertsSummaryResponse", "ExpiringResponse", "LowStockResponse",
    "OverviewResponse", "RevenuePoint", "RevenueResponse", "SeverityCount",
    "TopProductResponse", "TypeCount",
    "AlertPage", "AlertRead", "MarkReadRequest", "ResolveRequest",
    "CategoryBrief", "CategoryCreate", "CategoryRead", "CategoryUpdate",
    "ForecastPage", "ForecastRead", "LatestForecast", "LatestForecastList",
    "ExpiringBatch", "ExpiringReport",
    "InventoryCreate", "InventoryPage", "InventoryRead", "InventoryUpdate",
    "Message", "Page",
    "OrderCreate", "OrderDetail", "OrderItemInput", "OrderPage", "OrderRead",
    "OrderStatus", "OrderStatusUpdate", "OrderType", "OrderUpdate",
    "PaymentMethod",
    "OrderItemCreate", "OrderItemPage", "OrderItemRead", "OrderItemUpdate",
    "ProductBase", "ProductBrief", "ProductCreate", "ProductPage",
    "ProductRead", "ProductUpdate",
    "StoreBase", "StoreBrief", "StoreCreate", "StoreRead", "StoreUpdate",
]