"""
ORM model cho bang `order_items` - chi tiet dong hang.

⚠️ COT `line_total` LA GENERATED COLUMN trong DB:
    line_total = round(quantity * unit_price * (1 - discount_percent/100), 2)
SQLAlchemy KHONG duoc gan gia tri cho cot nay. Neu gan se bao loi
"cannot insert a non-DEFAULT value into column line_total" hoac
"cannot update a generated column". DB tu tinh - day la uu diem: khong
the nao tinh tay sai khong khop voi cong thuc.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Computed, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderItem(Base):
    """Mot dong san pham trong don hang."""

    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # FK ON DELETE CASCADE - xoa don hang thi dong chi tiet bay theo.
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False
    )
    # FK ON DELETE RESTRICT
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False
    )

    # CHECK (quantity > 0)
    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    # Gia don vi - GIA MO PHONG, xem ghi chu trong Order.
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # CHECK: 0 <= discount_percent <= 100
    discount_percent: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )

    # GENERATED ALWAYS AS ... STORED -> Computed(), khong giu duoc trong
    # Python chi doc. Muon biet gia tri thi SELECT hoac dung OrderItem.line_total
    # sau khi database da tinh.
    line_total: Mapped[float] = mapped_column(
        Numeric(18, 2),
        Computed(
            "round(quantity * unit_price * (1::numeric - discount_percent / 100::numeric), 2)",
            persisted=True,
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ---- Relationships ----
    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")

    def __repr__(self) -> str:
        return (
            f"<OrderItem order={self.order_id} product={self.product_id} "
            f"qty={self.quantity} line_total={self.line_total}>"
        )