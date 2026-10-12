"""
ORM model cho bang `users` - nguoi dung he thong.

LUU Y THIET KE: `expiry_date` KHONG nam o bang nay. Han su dung thuoc ve
lo hang tai cua hang (xem Inventory), khong phai thuoc tinh cua san pham.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Nguoi dung: owner, manager hoac staff."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(150), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # CHECK constraint: owner | manager | staff
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="staff", server_default="staff"
    )

    # FK ON DELETE SET NULL - xoa user khong lam mat don hang hay giao dich.
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.store_id", ondelete="SET NULL"), nullable=True
    )

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
    store: Mapped["Store | None"] = relationship(back_populates="users")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    inventory_transactions: Mapped[list["InventoryTransaction"]] = relationship(
        back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"