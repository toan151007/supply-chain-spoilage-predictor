"""
ORM model cho bang `orders` - don hang ban ra hoac nhap vao.

Luu y ve doanh thu: cot `total_amount` chua GIA MO PHONG. Dataset
Kaggle chi co so luong, khong co cot gia, nen gia duoc gan theo nhom
hang de dashboard chay duoc. Khi bao cao KHONG trinh bay doanh thu
nay nhu so lieu that - xem AGENTS.md.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    """Don hang: ban ra (sale) hoac dat mua (purchase)."""

    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # FK ON DELETE RESTRICT - khong xoa duoc cua hang con don hang.
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.store_id", ondelete="RESTRICT"), nullable=False
    )

    # CHECK: sale | purchase
    order_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sale", server_default="sale"
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Gia MOC PHONG - xem ghi chu dau file.
    total_amount: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, default=0, server_default="0"
    )
    total_quantity: Mapped[float] = mapped_column(
        Numeric(15, 3), nullable=False, default=0, server_default="0"
    )

    # CHECK: pending | completed | cancelled
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed", server_default="completed"
    )

    # CHECK: cash | card | transfer | ewallet | other
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ---- Relationships ----
    store: Mapped["Store"] = relationship(back_populates="orders")
    user: Mapped["User | None"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",   # xoa don -> xoa chi tiiet
        passive_deletes=True,          # FK ON DELETE CASCADE lo phan xoa
    )

    def __repr__(self) -> str:
        return f"<Order {self.order_code} - {self.total_amount}>"