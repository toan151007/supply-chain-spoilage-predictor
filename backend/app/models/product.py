"""
ORM model cho bang `products` - thuoc tinh co dinh cua san pham.

KHONG co `expiry_date` o day. Han su dung thuoc ve lo hang tai cua hang
(xem Inventory), khong phai thuoc tinh cua san pham - da chot trong
AGENTS.md.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    """San pham: ma SKU, ten, gia, han su dung va nguong ton kho."""

    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # FK ON DELETE RESTRICT - khong xoa duoc nhom hang con san pham.
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False
    )

    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_cost: Mapped[float] = mapped_column(
        Numeric(15, 2), nullable=False, default=0, server_default="0"
    )
    selling_price: Mapped[float] = mapped_column(
        Numeric(15, 2), nullable=False, default=0, server_default="0"
    )

    # So ngay san pham giu duoc sau khi nhap. Dung de tinh expiry_date
    # khi tao lo hang moi.
    shelf_life_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # Nguong sinh canh bao tu dong.
    min_stock: Mapped[float] = mapped_column(
        Numeric(15, 3), nullable=False, default=0, server_default="0"
    )
    max_stock: Mapped[float | None] = mapped_column(Numeric(15, 3), nullable=True)
    is_perishable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    reorder_point: Mapped[float | None] = mapped_column(Numeric(15, 3), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ---- Relationships ----
    category: Mapped["Category"] = relationship(back_populates="products")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")
    inventory: Mapped[list["Inventory"]] = relationship(back_populates="product")
    inventory_transactions: Mapped[list["InventoryTransaction"]] = relationship(
        back_populates="product"
    )
    forecasts: Mapped[list["Forecast"]] = relationship(back_populates="product")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"<Product {self.product_code} - {self.product_name}>"