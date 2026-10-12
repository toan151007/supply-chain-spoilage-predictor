"""
ORM model cho bang `stores` - cua hang / chi nhanh trong chuoi ban le.

Day la bang goc cua phan ma nhanh: moi du lieu khac deu tro ve store_id.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Store(Base):
    """Cua hang trong chuoi ban le hoac F&B."""

    __tablename__ = "stores"

    store_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    store_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    store_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # CHECK constraint: convenience_store | restaurant | warehouse
    store_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="convenience_store", server_default="convenience_store"
    )
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # Trigger trg_stores_updated tu gan updated_at trong DB,
    # khong can cap nhat thu cong trong Python.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ---- Relationships ----
    # KHONG dat cascade o phia nay. Quan he cha-con phai khai bao
    # `passive_deletes` o phia "con" de tranh SQLAlchemy gui lenh DELETE
    # thu cong cho tung dong con - cau truc FK cua DB da lo phan xoa hien du.
    users: Mapped[list["User"]] = relationship(back_populates="store")
    orders: Mapped[list["Order"]] = relationship(back_populates="store")
    inventory: Mapped[list["Inventory"]] = relationship(back_populates="store")
    inventory_transactions: Mapped[list["InventoryTransaction"]] = relationship(
        back_populates="store"
    )
    forecasts: Mapped[list["Forecast"]] = relationship(back_populates="store")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="store")

    def __repr__(self) -> str:
        return f"<Store {self.store_code} - {self.store_name}>"