"""
Pydantic schemas for the stock transfer workflow (dieu chuyen hang).

Mot yeu cau dieu chuyen quan ly MOT san pham cho MOT cap cua hang, vi vay
khong co bang dong chi tiet. Quy trinh trang thai:

    proposed -> pending -> approved -> in_transit -> received
    proposed | pending -> rejected | cancelled

`quantity` dung float giong cac schema ton kho khac: SQL Server tra DECIMAL,
Pydantic v2 tu doi sang float nen router khong phai ep kieu.
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page
from app.schemas.product_schema import ProductBrief
from app.schemas.store_schema import StoreBrief

TransferStatus = Literal[
    "proposed",
    "pending",
    "approved",
    "in_transit",
    "received",
    "rejected",
    "cancelled",
]

TransferPriority = Literal["low", "normal", "high", "urgent"]


class TransferCreate(BaseModel):
    """Request body for POST /api/v1/transfers."""

    model_config = ConfigDict(from_attributes=True)

    from_store_id: Annotated[int, Field(gt=0)]
    to_store_id: Annotated[int, Field(gt=0)]
    product_id: Annotated[int, Field(gt=0)]
    quantity: Annotated[float, Field(gt=0)]

    # Bat buoc phai chon lo cu the neu kho nguon co nhieu lo khac han dung.
    # De trong thi Stored Procedure tru theo FEFO (lo het han truoc).
    expiry_date: date | None = None

    priority: TransferPriority = "normal"
    reason: Annotated[str | None, Field(max_length=500)] = None
    note: Annotated[str | None, Field(max_length=500)] = None


class TransferDecision(BaseModel):
    """Request body for approve / reject (ly do la tuy chon)."""

    note: Annotated[str | None, Field(max_length=500)] = None


class TransferRead(BaseModel):
    """Response body returned by every transfer endpoint."""

    model_config = ConfigDict(from_attributes=True)

    transfer_id: int
    transfer_code: str

    from_store_id: int
    to_store_id: int
    product_id: int

    quantity: float
    expiry_date: date | None

    status: TransferStatus
    priority: TransferPriority
    reason: str | None = None
    note: str | None = None

    requested_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    shipped_at: datetime | None = None
    completed_at: datetime | None = None

    requested_by_name: str | None = None
    approved_by_name: str | None = None
    rejected_by_name: str | None = None
    shipped_by_name: str | None = None
    received_by_name: str | None = None

    from_store: StoreBrief
    to_store: StoreBrief
    product: ProductBrief


TransferPage = Page[TransferRead]


class TransferSummary(BaseModel):
    """
    Dem so yeu cau theo tung trang thai.

    Frontend dung so nay de ve thanh quy trinh (proposed -> received) va hien
    so luong dang cho duyet. Cac trang thai khong co ban ghi van xuat hien voi
    gia tri 0, nho vay giao dien khong phai tu bu key thieu.
    """

    counts: dict[str, int]
    total: int
    total_quantity: float
    in_transit_quantity: float

