"""
ORM model cho bang `categories` - nhom hang.

Bang nay CO quan he tu tham chieu (parent_category_id tro ve chinh no)
de the hien cau truc phan cap danh muc.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    """Nhom hang, ho tro cau truc phan cap cha-con."""

    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tu tham chieu. FK ON DELETE SET NULL nen xoa cha chi lam muc cha
    # cua cac muc con thanh NULL chu khong xoa mat.
    parent_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # ---- Relationships ----
    # remote_side tro ve cot FK phia "cha". Bat buoc voi quan he tu tham
    # chieu - thieu no SQLAlchemy se khong biet nao la cha, nao la con.
    parent: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="children",
        remote_side="Category.category_id",
        foreign_keys=[parent_category_id],
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        foreign_keys=[parent_category_id],
    )
    products: Mapped[list["Product"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.category_name}>"