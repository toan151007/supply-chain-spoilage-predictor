"""
ORM model cho bang `forecasts` - ket qua du bao nhu cau.

⚠️ DOC `recommended_import_qty` TRUOC KHI BAO CAO:

Cot nay da BI CHAN BOI `max_stock`. Gia tri trong DB khong phan anh
dung nhu cau du bao:
    - Nhu cau thuan (chua cap): 232.397
    - Tong de xuat nhap (sau cap): 7.286
Ly do: seed dat `max_stock` 48-300 trong khi nhu cau Kaggle la
861-2.793/ngay, tuc `max_stock` chi tuong duong 0,5-3 ngay ban.
Day la HAN CHAN DU LIEU, khong phai loi cua mo hinh. Xem AGENTS.md muc
"Quyet dinh KHONG sua" - so 2.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Forecast(Base):
    """Du bao so luong ban theo tung cap san pham x cua hang x ngay."""

    __tablename__ = "forecasts"

    forecast_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # FK ON DELETE CASCADE
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.store_id", ondelete="CASCADE"), nullable=False
    )
    # FK ON DELETE RESTRICT
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id", ondelete="RESTRICT"), nullable=False
    )

    # CHECK: prophet | xgboost | arima | moving_average | naive
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)

    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    # CHECK (horizon_days > 0) - so ngay du bao phia truoc.
    horizon_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    predicted_quantity: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    # Khoang tin cay 95%, dung cho tinh ton kho an toan.
    lower_bound: Mapped[float | None] = mapped_column(Numeric(15, 3), nullable=True)
    upper_bound: Mapped[float | None] = mapped_column(Numeric(15, 3), nullable=True)

    # Xem canh bao dau file.
    recommended_import_qty: Mapped[float | None] = mapped_column(
        Numeric(15, 3), nullable=True
    )

    # Chi so do luoc cua mo hinh tren tap test (M1).
    rmse: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    mae: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    mape: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)

    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ---- Relationships ----
    store: Mapped["Store"] = relationship(back_populates="forecasts")
    product: Mapped["Product"] = relationship(back_populates="forecasts")

    def __repr__(self) -> str:
        return (
            f"<Forecast {self.model_name} store={self.store_id} "
            f"product={self.product_id} date={self.forecast_date} "
            f"h={self.horizon_days} pred={self.predicted_quantity}>"
        )