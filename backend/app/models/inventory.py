"""
ORM model cho bang `inventory` - ton kho hien tai theo lo, theo cua hang.

Day la bang con goc cua he thong chong lang phich: mot san pham tai mot
cua hang co the nhieu lo, moi lo mot ngay het han khac nhau.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Inventory(Base):
    """Ton kho con lai cua mot lo hang tai mot cua hang."""

    __tablename__ = "inventory"

    inventory_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # FK ON DELETE CASCADE - xoa cua hang thi xoa het ton kho cua cua hang do.
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False
    )
    # FK ON DELETE RESTRICT - khong xoa duoc san pham con ton kho.
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False
    )

    # Ngay het han CUA LO NAY - dung cho canh bao va xu ly FIFO.
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    quantity: Mapped[float] = mapped_column(
        Numeric(15, 3), nullable=False, default=0, server_default="0"
    )
    received_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default="CURRENT_DATE"
    )
    batch_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ---- Relationships ----
    store: Mapped["Store"] = relationship(back_populates="inventory")
    product: Mapped["Product"] = relationship(back_populates="inventory")

    # Ngay het han gan nhat - thuong dung de canh bao "sap het han".
    @property
    def days_to_expiry(self) -> int | None:
        """So ngay con lai den han. None neu lo hang khong xac dinh han."""
        if self.expiry_date is None:
            return None
        return (self.expiry_date - date.today()).days

    def __repr__(self) -> str:
        return (
            f"<Inventory store={self.store_id} product={self.product_id} "
            f"qty={self.quantity} expiry={self.expiry_date}>"
        )