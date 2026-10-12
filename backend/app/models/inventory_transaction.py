"""
ORM model cho bang `inventory_transactions` - nhat ky bien dong ton kho.

⚠️ VAI TRO TRONG DU AN - DOC FILE NAY TRUOC KHI DUNG:

Bang nay la NHAT KY KIEM TOAN bien dong kho. No phuc vu:
  - Phan tich ton kho (san pham di duoc bao nhieu, khi nao)
  - Canh bao het han (v_expiring_inventory, fn_generate_inventory_alerts)
  - Chon lo hang theo FIFO khi xuat hang
  - Thong ke lang phich (cac giao dich disposal)

NO KHONG PHAI DU LIEU DAU VAO CHO MO HINH DU BAO.
Dau vao du bao duy nhat la view `v_daily_sales`, dung tu
`orders` + `order_items`. Xem AGENTS.md muc "Quyet dinh thiet ke da chot".
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InventoryTransaction(Base):
    """Mot lan nhap, xuat, dieu chinhenhang hoac huy hang."""

    __tablename__ = "inventory_transactions"

    transaction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False
    )

    # Ghi lai han cua lo hang ma giao dich nay lien quan. NULL neu khong
    # xac dinh duoc lo hang cu the.
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # CHECK constraint: import | export | adjustment | disposal
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # CHECK (quantity > 0) - so luong luon duong. Chieu cua giao dich
    # duoc quyet dinh boi transaction_type chu khong phai dau am.
    quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # CHECK: manual | order | import_excel
    reference_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True, default="manual", server_default="manual"
    )
    # ID tham chieu tuyet doi theo reference_type:
    #   manual -> inventory_id (am cho disposal de tach khong gian khoa)
    #   order  -> order_id
    reference_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ---- Relationships ----
    store: Mapped["Store"] = relationship(back_populates="inventory_transactions")
    product: Mapped["Product"] = relationship(back_populates="inventory_transactions")
    user: Mapped["User | None"] = relationship(back_populates="inventory_transactions")

    def __repr__(self) -> str:
        return (
            f"<InventoryTransaction {self.transaction_type} "
            f"store={self.store_id} product={self.product_id} qty={self.quantity}>"
        )