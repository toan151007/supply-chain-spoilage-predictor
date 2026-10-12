"""
Export tat ca ORM models.

Thu tu import co y nghia: cac model duoc import theo thu tu phu thuoc
(Store truoc User vi User tro ve Store). SQLAlchemy giai quyet quan he
khi mapping, nen chi can import het mot lan trong file nay la du.
"""

from app.database import Base

# --- Bang goc / danh muc ---
from app.models.category import Category
from app.models.store import Store

# --- Con nguoi dung & nhom hang ---
from app.models.user import User
from app.models.product import Product

# --- Ban hang ---
from app.models.order import Order
from app.models.order_item import OrderItem

# --- Ton kho ---
from app.models.inventory import Inventory
from app.models.inventory_transaction import InventoryTransaction

# --- Phan tich ---
from app.models.forecast import Forecast
from app.models.alert import Alert

__all__ = [
    "Base",
    "Category",
    "Store",
    "User",
    "Product",
    "Order",
    "OrderItem",
    "Inventory",
    "InventoryTransaction",
    "Forecast",
    "Alert",
]