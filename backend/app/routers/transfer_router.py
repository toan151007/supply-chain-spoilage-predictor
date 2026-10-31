"""
Router cho nghiep vu dieu chuyen hang giua cua hang (stock transfer).

Quy trinh trang thai (khop CHECK constraint trong database):

    proposed -> pending -> approved -> in_transit -> received
    proposed | pending -> rejected | cancelled

Phan quyen:
- staff duoc tao de xuat, gui duyet, huy, xac nhan giao (ship) va nhan hang.
- owner/manager duoc duyet hoac tu choi.
- Khi `received`, Stored Procedure tu tru kho nguon (FEFO) va cong kho dich
  trong CUNG mot transaction, kem 2 dong inventory_transactions.

Router nay khong tu tinh toan gi: moi thao tac chi la mot lan goi
`EXEC dbo.sp_Transfer_...`. Loi nghiep vu 50001-50005 duoc map sang HTTP
trong `app.database.map_sqlserver_error`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import CurrentUser, require_role
from app.schemas.transfer_schema import (
    TransferCreate,
    TransferDecision,
    TransferPage,
    TransferRead,
    TransferStatus,
    TransferSummary,
)

router = APIRouter(prefix="/transfers", tags=["transfers"])

# Trang thai theo dung thu tu hien thi tren thanh quy trinh.
STATUS_ORDER = [
    "proposed",
    "pending",
    "approved",
    "in_transit",
    "received",
    "rejected",
    "cancelled",
]

ANY_STAFF = ("owner", "manager", "staff")
MANAGER_ONLY = ("owner", "manager")


def _to_read(row: dict) -> dict:
    """Ghep cac cot phang cua SP thanh object long (from_store/to_store/product)."""
    row = dict(row)
    row["from_store"] = {
        "store_id": row.get("from_store_id"),
        "store_code": row.get("from_store_code"),
        "store_name": row.get("from_store_name"),
    }
    row["to_store"] = {
        "store_id": row.get("to_store_id"),
        "store_code": row.get("to_store_code"),
        "store_name": row.get("to_store_name"),
    }
    row["product"] = {
        "product_id": row.get("product_id"),
        "product_code": row.get("product_code"),
        "product_name": row.get("product_name"),
    }
    return row


def _get_row(db: DbSession, transfer_id: int) -> dict:
    """Doc mot yeu cau; SP nem 50001 (-> 404) khi khong ton tai."""
    try:
        row = db.one("sp_Transfer_Get", {"TransferId": transfer_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer request {transfer_id} not found",
        )
    return _to_read(row)


def _run_action(
    db: DbSession, sp_name: str, transfer_id: int, params: dict | None = None
) -> dict:
    """
    Goi mot SP chuyen trang thai va tra ve dong vua cap nhat.

    Moi SP trong nhom nay deu `EXEC sp_Transfer_Get` sau khi COMMIT, nen
    result set dau tien chinh la dong day du.
    """
    payload = {"TransferId": transfer_id}
    if params:
        payload.update(params)
    try:
        row = db.one(sp_name, payload)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transfer request {transfer_id} not found",
        )
    return _to_read(row)


# NOTE: `/summary` phai khai bao TRUOC `/{transfer_id}`, neu khong FastAPI se
# co gang parse chuoi "summary" thanh int va tra 422.
@router.get(
    "/summary",
    response_model=TransferSummary,
    summary="Dem yeu cau dieu chuyen theo trang thai",
)
def transfer_summary(db: DbSession = Depends(get_db)) -> TransferSummary:
    try:
        sets = db.call("sp_Transfer_Summary")
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    counts = {code: 0 for code in STATUS_ORDER}
    for row in sets[0] if sets else []:
        code = row.get("status")
        if code in counts:
            counts[code] = int(row.get("total") or 0)

    totals = (sets[1][0] if len(sets) > 1 and sets[1] else {}) or {}
    return TransferSummary(
        counts=counts,
        total=int(totals.get("total") or 0),
        total_quantity=float(totals.get("total_quantity") or 0),
        in_transit_quantity=float(totals.get("in_transit_quantity") or 0),
    )


@router.get("", response_model=TransferPage, summary="Danh sach yeu cau dieu chuyen")
def list_transfers(
    db: DbSession = Depends(get_db),
    status_filter: TransferStatus | None = Query(None, alias="status"),
    from_store_id: int | None = Query(None, gt=0),
    to_store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    search: Annotated[str | None, Query(max_length=255)] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TransferPage:
    try:
        sets = db.call(
            "sp_Transfer_List",
            {
                "Status": status_filter,
                "FromStoreId": from_store_id,
                "ToStoreId": to_store_id,
                "ProductId": product_id,
                "Search": search,
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = [_to_read(row) for row in (sets[1] if len(sets) > 1 else [])]
    pages = (total + page_size - 1) // page_size
    return TransferPage(
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{transfer_id}", response_model=TransferRead, summary="Chi tiet yeu cau")
def get_transfer(transfer_id: int, db: DbSession = Depends(get_db)) -> dict:
    return _get_row(db, transfer_id)


@router.post(
    "",
    response_model=TransferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tao yeu cau dieu chuyen",
    dependencies=[Depends(require_role(*ANY_STAFF))],
)
def create_transfer(
    payload: TransferCreate,
    db: DbSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    data = payload.model_dump()
    try:
        row = db.one(
            "sp_Transfer_Create",
            {
                "FromStoreId": data["from_store_id"],
                "ToStoreId": data["to_store_id"],
                "ProductId": data["product_id"],
                "Quantity": data["quantity"],
                "ExpiryDate": data["expiry_date"],
                "Priority": data["priority"],
                "Reason": data["reason"],
                "Note": data["note"],
                "RequestedBy": (user or {}).get("user_id"),
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transfer was created but could not be read back",
        )
    return _to_read(row)


@router.post(
    "/{transfer_id}/submit",
    response_model=TransferRead,
    summary="Gui yeu cau cho quan ly duyet",
    dependencies=[Depends(require_role(*ANY_STAFF))],
)
def submit_transfer(
    transfer_id: int,
    db: DbSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    return _run_action(
        db, "sp_Transfer_Submit", transfer_id, {"UserId": (user or {}).get("user_id")}
    )


@router.post(
    "/{transfer_id}/approve",
    response_model=TransferRead,
    summary="Duyet yeu cau dieu chuyen",
    dependencies=[Depends(require_role(*MANAGER_ONLY))],
)
def approve_transfer(
    transfer_id: int,
    payload: TransferDecision | None = None,
    db: DbSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    return _run_action(
        db,
        "sp_Transfer_Approve",
        transfer_id,
        {
            "ApprovedBy": (user or {}).get("user_id"),
            "Note": (payload.note if payload else None),
        },
    )


@router.post(
    "/{transfer_id}/reject",
    response_model=TransferRead,
    summary="Tu choi yeu cau dieu chuyen",
    dependencies=[Depends(require_role(*MANAGER_ONLY))],
)
def reject_transfer(
    transfer_id: int,
    payload: TransferDecision | None = None,
    db: DbSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    return _run_action(
        db,
        "sp_Transfer_Reject",
        transfer_id,
        {
            "RejectedBy": (user or {}).get("user_id"),
            "Reason": (payload.note if payload else None),
        },
    )


@router.post(
    "/{transfer_id}/cancel",
    response_model=TransferRead,
    summary="Huy yeu cau dieu chuyen",
    dependencies=[Depends(require_role(*ANY_STAFF))],
)
def cancel_transfer(
    transfer_id: int,
    db: DbSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    return _run_action(
        db, "sp_Transfer_Cancel", transfer_id, {"UserId": (user or {}).get("user_id")}
    )


@router.post(
    "/{transfer_id}/ship",
    response_model=TransferRead,
    summary="Xac nhan xuat kho, hang dang tren duong",
    dependencies=[Depends(require_role(*ANY_STAFF))],
)
def ship_transfer(
    transfer_id: int,
    db: DbSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    return _run_action(
        db, "sp_Transfer_Ship", transfer_id, {"ShippedBy": (user or {}).get("user_id")}
    )


@router.post(
    "/{transfer_id}/complete",
    response_model=TransferRead,
    summary="Xac nhan da nhan hang, cap nhat kho hai ben",
    dependencies=[Depends(require_role(*ANY_STAFF))],
)
def complete_transfer(
    transfer_id: int,
    db: DbSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    return _run_action(
        db, "sp_Transfer_Complete", transfer_id, {"UserId": (user or {}).get("user_id")}
    )
