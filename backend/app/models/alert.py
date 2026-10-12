"""
ORM model cho bang `alerts` - canh bao ton kho va chong lang phich.

Chu y ve i18n: cot `title` luu KEY i18n chu khong luu van ban tieng Viet,
vi du `alert.title.EXPIRED`. Ban dich nam o `backend/app/i18n/vi.json`.
Ly do: du an ho tro da ngon ngu, neu luu van ban trong DB thi phai
cap nhat lai toan bo du lieu moi khi doi ngon ngu.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Alert(Base):
    """Canh bao: het han, ton kho thap, ton kho cao, bat thuong du bao."""

    __tablename__ = "alerts"

    alert_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # FK ON DELETE CASCADE. Nullable: canh bao bat buoc phai gan store
    # hay khong vi du bao chung toan he thong.
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.product_id", ondelete="CASCADE"), nullable=True
    )

    # CHECK: expiring_soon | expired | low_stock | over_stock | forecast_anomaly
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # CHECK: low | medium | high | critical
    severity: Mapped[str] = mapped_column(
        String(10), nullable=False, default="low", server_default="low"
    )

    # Chua KEY i18n, khong chua van ban - xem ghi chu dau file.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Han cua lo hang gay ra canh bao. NULL voi canh bao ton kho.
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_stock: Mapped[float | None] = mapped_column(Numeric(15, 3), nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Numeric(15, 3), nullable=True)

    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_resolved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ⚠️ CHECK (chk_alert_resolved_at) rang buoc hai truong nay phai
    # nhat quan: da xu ly thi resolved_at phai khac NULL, chua xu ly
    # thi resolved_at phai NULL. DB se tu chan du truong khong nhat quan.
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ---- Relationships ----
    store: Mapped["Store | None"] = relationship(back_populates="alerts")
    product: Mapped["Product | None"] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert {self.alert_type} ({self.severity}) - {self.title}>"