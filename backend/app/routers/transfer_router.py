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
from app.dependencies import CurrentUser, require_permission, require_role
from app.schemas.transfer_schema import (
    TransferCreate,
    TransferDecision,
    TransferPage,
    TransferRead,
    TransferStatus,
    TransferSuggestion,
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

MODEL_NAME_PATTERN = "^(prophet|xgboost|arima|moving_average|naive)$"


def _f(value) -> float:
    """Coerce a NUMERIC aggregate to float; None becomes 0.0."""
    return 0.0 if value is None else float(value)


def _vi_num(value: float, digits: int = 0) -> str:
    """Format a number the Vietnamese way: dot thousands, comma decimals."""
    text = f"{value:,.{digits}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def _priority_for_days(days_cover: float) -> str:
    """Map so ngay phu vu con lai sang muc uu tien dieu chuyen."""
    if days_cover < 7:
        return "urgent"
    if days_cover < 14:
        return "high"
    if days_cover < 21:
        return "normal"
    return "low"


URGENCY_LABELS = {
    "CRITICAL": "Khẩn cấp",
    "WARNING": "Cảnh báo",
    "NORMAL": "Bình thường",
}

# Cau ket theo muc khan cap, de nguoi doc biet phai lam gi tiep theo.
URGENCY_CLOSING = {
    "CRITICAL": "Cần chuyển ngay trong hôm nay để tránh đứt gãy chuỗi cung ứng.",
    "WARNING": "Nên điều chuyển trong 1-2 ngày tới để giữ mức phủ an toàn.",
    "NORMAL": "Có thể gom vào chuyến điều chuyển gần nhất, chưa cần gấp.",
}


def _urgency_label(code: str | None) -> str:
    """Ma khan cap (CRITICAL/WARNING/NORMAL) -> nhan tieng Viet."""
    return URGENCY_LABELS.get((code or "").upper(), URGENCY_LABELS["NORMAL"])


def _build_reason(row: dict, urgency: str, numbers: dict) -> str:
    """
    Cau giai thich bang tieng Viet co dau cho moi goi y.

    Bon y: tinh trang cua cua hang nhan, tinh trang cua cua hang gui, khuyen
    nghi cu the (so luong + khoang cach + muc phu sau khi chuyen) va viec can
    lam ngay hay khong. So lieu dung `_vi_num` nen dau phan cach la dau cham.
    """
    unit = numbers["unit"]
    target = numbers["target"]
    to_stock = numbers["to_stock"]
    to_daily = numbers["to_daily"]
    to_cover = numbers["to_cover"]
    from_stock = numbers["from_stock"]
    from_cover = numbers["from_cover"]
    surplus = numbers["surplus"]
    suggested = numbers["suggested"]
    distance = numbers["distance"]

    from_name = row["from_store_name"]
    to_name = row["to_store_name"]
    from_code = row.get("from_store_code") or f"CH{row['from_store_id']}"
    to_code = row.get("to_store_code") or f"CH{row['to_store_id']}"

    parts = [
        f"{to_name} chỉ còn {_vi_num(to_cover, 1)} ngày phủ "
        f"(tồn {_vi_num(to_stock)} {unit}, nhu cầu {_vi_num(to_daily, 1)} {unit}/ngày).",
        f"{from_name} đang dư {_vi_num(surplus)} {unit} so với mức {target} ngày "
        f"(tồn {_vi_num(from_stock)} {unit}, phủ {_vi_num(from_cover, 1)} ngày).",
    ]

    move = f"Nên chuyển {_vi_num(suggested)} {unit} từ {from_code} sang {to_code}"
    if distance is not None:
        move += f" (khoảng {_vi_num(distance, 1)} km)"
    if to_daily > 0:
        after = (to_stock + suggested) / to_daily
        move += f", đưa mức phủ của {to_code} lên khoảng {_vi_num(after, 1)} ngày."
    else:
        move += "."
    parts.append(move)

    parts.append(URGENCY_CLOSING.get(urgency, URGENCY_CLOSING["NORMAL"]))
    return " ".join(parts)


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


# NOTE: `/suggestions` phai khai bao TRUOC `/{transfer_id}` (giong `/summary`).
@router.get(
    "/suggestions",
    response_model=list[TransferSuggestion],
    summary="Goi y dieu chuyen tu AI (du bao vs ton kho)",
)
def transfer_suggestions(
    db: DbSession = Depends(get_db),
    target_days: int = Query(14, ge=1, le=90),
    min_qty: float = Query(1, ge=0),
    limit: int = Query(50, ge=1, le=200),
    model_name: str = Query("prophet", pattern=MODEL_NAME_PATTERN),
) -> list[TransferSuggestion]:
    """
    So sanh nhu cau du bao voi ton kho that cho tung cap (cua hang, san pham)
    va goi y chuyen tu cua hang du thua sang cua hang thieu hut.

    `target_days` la muc phu vu mong muon (ngay). Cua hang co ton kho nhieu
    hon nhu cầu `target_days` ngay bi coi la du, cua hang thap hon la thieu.
    So luong goi y lay phan nho hon giua luong du va luong thieu.

    Mac dinh chi dung du bao Prophet (`model_name=prophet`) de giong voi
    giao dien Dự báo; truyen `model_name=xgboost` khi can so doi chung.
    """
    try:
        rows = db.rows(
            "sp_Transfer_SuggestAI",
            {
                "TargetDays": target_days,
                "MinQty": min_qty,
                "Limit": limit,
                "ModelName": model_name,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    results: list[TransferSuggestion] = []
    for r in rows:
        from_stock = _f(r["from_stock"])
        from_daily = _f(r["from_daily_demand"])
        from_cover = _f(r["from_days_cover"])
        to_stock = _f(r["to_stock"])
        to_daily = _f(r["to_daily_demand"])
        to_cover = _f(r["to_days_cover"])
        surplus = _f(r["surplus_qty"])
        shortage = _f(r["shortage_qty"])
        suggested = _f(r["suggested_qty"])
        unit = (r.get("unit") or "sản phẩm").strip()
        target = int(r["target_days"])
        distance = None if r.get("distance_km") is None else _f(r["distance_km"])
        urgency = (r.get("transfer_urgency") or "").upper()
        if urgency not in URGENCY_LABELS:
            urgency = (
                "CRITICAL" if to_cover < 3
                else "WARNING" if to_cover <= 7
                else "NORMAL"
            )

        reason = _build_reason(
            r,
            urgency,
            {
                "unit": unit,
                "target": target,
                "from_stock": from_stock,
                "from_daily": from_daily,
                "from_cover": from_cover,
                "to_stock": to_stock,
                "to_daily": to_daily,
                "to_cover": to_cover,
                "surplus": surplus,
                "suggested": suggested,
                "distance": distance,
            },
        )

        results.append(
            TransferSuggestion(
                product_id=r["product_id"],
                product_code=r["product_code"],
                product_name=r["product_name"],
                unit=r.get("unit"),
                from_store_id=r["from_store_id"],
                from_store_code=r.get("from_store_code"),
                from_store_name=r["from_store_name"],
                to_store_id=r["to_store_id"],
                to_store_code=r.get("to_store_code"),
                to_store_name=r["to_store_name"],
                from_stock=from_stock,
                from_predicted_qty=_f(r["from_predicted_qty"]),
                from_daily_demand=from_daily,
                from_days_cover=from_cover,
                to_stock=to_stock,
                to_predicted_qty=_f(r["to_predicted_qty"]),
                to_daily_demand=to_daily,
                to_days_cover=to_cover,
                surplus_qty=surplus,
                shortage_qty=shortage,
                suggested_qty=suggested,
                model_name=r["model_name"],
                horizon_days=int(r["horizon_days"]),
                target_days=target,
                priority=_priority_for_days(to_cover),
                reason=reason,
                transfer_urgency=urgency,
                urgency_label=_urgency_label(urgency),
                distance_km=distance,
            )
        )

    return results


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
    dependencies=[
        Depends(require_role(*ANY_STAFF)),
        Depends(require_permission("can_manage_transfer")),
    ],
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
    dependencies=[
        Depends(require_role(*ANY_STAFF)),
        Depends(require_permission("can_manage_transfer")),
    ],
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
    dependencies=[
        Depends(require_role(*MANAGER_ONLY)),
        Depends(require_permission("can_manage_transfer")),
    ],
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
    dependencies=[
        Depends(require_role(*MANAGER_ONLY)),
        Depends(require_permission("can_manage_transfer")),
    ],
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
    dependencies=[
        Depends(require_role(*ANY_STAFF)),
        Depends(require_permission("can_manage_transfer")),
    ],
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
    dependencies=[
        Depends(require_role(*ANY_STAFF)),
        Depends(require_permission("can_manage_transfer")),
    ],
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
    dependencies=[
        Depends(require_role(*ANY_STAFF)),
        Depends(require_permission("can_manage_transfer")),
    ],
)
def complete_transfer(
    transfer_id: int,
    db: DbSession = Depends(get_db),
    user: CurrentUser = None,
) -> dict:
    return _run_action(
        db, "sp_Transfer_Complete", transfer_id, {"UserId": (user or {}).get("user_id")}
    )
