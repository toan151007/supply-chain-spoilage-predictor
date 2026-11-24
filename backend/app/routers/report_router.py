"""
Report export endpoints (B11 / SQL Server Stored Procedure): CSV, XLSX, PDF.

All database access goes through `EXEC dbo.sp_Reports_*`; there is no ORM
query in this file.

One helper builds the bytes for all three formats from the same row list,
so a report can never disagree with itself across formats: the CSV, the
spreadsheet and the PDF are rendered from a single set of rows.

Date filters are `date`, not `datetime`, matching the dashboard endpoints.

Filenames are ASCII and deterministic. A Vietnamese filename in the
`Content-Disposition` header has to be RFC 5987 encoded to survive browsers,
and the frontend already renders Vietnamese labels; sending
`bao-cao-ton-kho.xlsx` keeps the download name safe everywhere.

Excel exports are capped by `MAX_EXPORT_ROWS`. An unfiltered sales report
would otherwise be ~913,000 rows, which builds a multi-hundred-megabyte
workbook in memory and then times out. The cap is reported in a response
header so a client can tell it was truncated rather than silently handing
back partial data.
"""

import io
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pyodbc import Error as PyodbcError

from app.config import settings
from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import require_permission
from app.schemas.spoilage_schema import (
    SpoilageAdviceResponse,
    SpoilageRiskRow,
    SpoilageSummaryResponse,
)
from app.schemas.top_selling_schema import TopSellingRow

# Reports are sensitive and the administrator can switch the right off for a
# manager, so this is checked per request rather than only hidden in the menu.
router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_permission("can_view_report"))],
)

HTTP_422_UNPROCESSABLE_CONTENT = 422

# Guard against building a workbook that will not fit in memory.
MAX_EXPORT_ROWS = 50_000

# PDF gets a much smaller cap. reportlab renders each cell as a Paragraph so
# long text wraps, and that costs roughly 100x a plain string: the waste
# report took 77 s for its ~700 rows and the sales report timed out past
# 120 s. A paginated PDF for tens of thousands of rows is the wrong tool -
# CSV or XLSX is, and the response tells the caller how many rows to expect.
MAX_PDF_ROWS = 1_000

CSV_MEDIA = "text/csv; charset=utf-8"
XLSX_MEDIA = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
PDF_MEDIA = "application/pdf"


def _f(value) -> float:
    return 0.0 if value is None else float(value)


def _validate_range(from_date: date | None, to_date: date | None) -> None:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="from_date must be on or before to_date",
        )


def _filename(stem: str, fmt: str, suffix: str = "") -> str:
    return f"{stem}{suffix}_{date.today().isoformat()}.{fmt}"


def _truncate_header(rows: list, limit: int, response: StreamingResponse) -> None:
    """Tell the client when rows were dropped."""
    response.headers["X-Total-Rows"] = str(len(rows))
    response.headers["X-Truncated"] = "true" if len(rows) > limit else "false"


# ===========================================================================
# Format rendering - one row set, three outputs
# ===========================================================================
def _render(rows: list[dict], columns: list[str], fmt: str, stem: str,
            title: str) -> StreamingResponse:
    """
    Turn rows into a downloadable file.

    `rows` and `columns` are shared by every format so the three downloads
    always carry the same figures.
    """
    frame = pd.DataFrame(rows, columns=columns)

    if fmt == "csv":
        # utf-8-sig so Excel on Windows opens Vietnamese text correctly;
        # without the BOM it renders as mojibake.
        payload = frame.to_csv(index=False).encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(payload),
            media_type=CSV_MEDIA,
            headers={"Content-Disposition":
                     f'attachment; filename="{_filename(stem, "csv")}"'},
        )

    if fmt == "xlsx":
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            frame.to_excel(writer, index=False, sheet_name=stem[:31])
        return StreamingResponse(
            io.BytesIO(buffer.getvalue()),
            media_type=XLSX_MEDIA,
            headers={"Content-Disposition":
                     f'attachment; filename="{_filename(stem, "xlsx")}"'},
        )

    # ---- PDF ----
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    # Landscape once the table gets wide, otherwise the columns crush.
    page = landscape(A4) if len(columns) > 6 else A4
    doc = SimpleDocTemplate(
        buffer, pagesize=page,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title=title,
    )
    styles = getSampleStyleSheet()

    story = [Paragraph(title, styles["Title"]),
             Paragraph(
                 f"Xuat ngay {date.today().isoformat()} · "
                 f"{len(frame)} dong",
                 styles["Normal"],
             ),
             Spacer(1, 6 * mm)]

    if frame.empty:
        story.append(Paragraph("Khong co du lieu de bao cao.", styles["Normal"]))
    else:
        # Capped: see MAX_PDF_ROWS. Saying so on the page beats silently
        # printing a partial report as if it were the whole thing.
        capped = len(frame) > MAX_PDF_ROWS
        shown = frame.head(MAX_PDF_ROWS)

        if capped:
            story.append(Paragraph(
                f"CHI HIEN THI {MAX_PDF_ROWS} DONG DAU TRONG TONG SO "
                f"{len(frame):,} DONG. Hay dung dinh dang CSV hoac XLSX de "
                "lay day du du lieu.",
                styles["Normal"],
            ))
            story.append(Spacer(1, 4 * mm))

        header = [Paragraph(f"<b>{c}</b>", styles["Normal"]) for c in columns]
        body = [
            [Paragraph(_pdf_cell(v), styles["Normal"]) for v in row]
            for row in shown.values.tolist()
        ]
        table = Table([header] + body, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f3f4f6")]),
        ]))
        story.append(table)

    doc.build(story)
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type=PDF_MEDIA,
        headers={"Content-Disposition":
                 f'attachment; filename="{_filename(stem, "pdf")}"'},
    )


def _pdf_cell(value) -> str:
    """Escape a value for reportlab's mini-markup."""
    if value is None:
        return ""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ===========================================================================
# Inventory report
# ===========================================================================
@router.get("/inventory/export", summary="Export the stock report")
def export_inventory(
    db: DbSession = Depends(get_db),
    fmt: str = Query("csv", alias="format", pattern="^(csv|xlsx|pdf)$"),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    category_id: int | None = Query(None, gt=0),
    in_stock_only: bool = Query(True),
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
) -> StreamingResponse:
    """
    Current stock per batch, valued at `products.unit_cost`.

    One row per batch rather than per product+store, because the expiry date
    is what a stock report is actually for - a store holding three batches
    of one product has three different deadlines.
    """
    try:
        rows = db.rows(
            "sp_Reports_Inventory",
            {
                "StoreId": store_id,
                "ProductId": product_id,
                "CategoryId": category_id,
                "InStockOnly": 1 if in_stock_only else 0,
                "Limit": limit,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    data = [
        {
            "Ma lot": r["inventory_id"],
            "Ma CH": r["store_code"],
            "Ten CH": r["store_name"],
            "Ma SP": r["product_code"],
            "Ten SP": r["product_name"],
            "Nhom hang": r["category_name"],
            "So lo": r["batch_code"],
            "Han su dung": r["expiry_date"].isoformat() if r["expiry_date"] else "",
            "Ngay con lai": r["days_left"],
            "So luong": _f(r["quantity"]),
            "Gia von/SP": _f(r["unit_cost"]),
            "Gia tri ton": round(_f(r["total_value"]), 2),
            "Ngay nhap": r["received_date"].isoformat() if r["received_date"] else "",
        }
        for r in rows
    ]
    columns = ["Ma lot", "Ma CH", "Ten CH", "Ma SP", "Ten SP", "Nhom hang",
               "So lo", "Han su dung", "Ngay con lai", "So luong",
               "Gia von/SP", "Gia tri ton", "Ngay nhap"]

    response = _render(data, columns, fmt, "bao-cao-ton-kho",
                       "BAO CAO TON KHO")
    _truncate_header(rows, limit, response)
    return response


# ===========================================================================
# Expiring report
# ===========================================================================
@router.get("/expiring/export", summary="Export the expiring-stock report")
def export_expiring(
    db: DbSession = Depends(get_db),
    fmt: str = Query("csv", alias="format", pattern="^(csv|xlsx|pdf)$"),
    days: int = Query(
        30, ge=1, le=30,
        description="Batches expiring within this many days; capped at 30 "
                    "to match v_expiring_inventory",
    ),
    store_id: int | None = Query(None, gt=0),
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
) -> StreamingResponse:
    """
    Stock at or near expiry, soonest first.

    `days` is capped at 30 because `v_expiring_inventory` hard-codes
    `CURRENT_DATE + 30`; allowing a larger value would silently return the
    same rows and imply the user had seen a wider window than they did.
    """
    try:
        rows = db.rows(
            "sp_Reports_Expiring",
            {"Days": days, "StoreId": store_id, "Limit": limit},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    data = [
        {
            "Ma lot": r["inventory_id"],
            "Ma CH": r["store_code"],
            "Ten CH": r["store_name"],
            "Ma SP": r["product_code"],
            "Ten SP": r["product_name"],
            "So lo": r["batch_code"],
            "Han su dung": r["expiry_date"].isoformat() if r["expiry_date"] else "",
            "Ngay con lai": r["days_left"],
            "Trang thai": "DA HET HAN" if int(r["days_left"] or 0) < 0 else "sap het han",
            "So luong": _f(r["quantity"]),
            "Gia von/SP": _f(r["unit_cost"]),
            "Gia tri": round(_f(r["total_value"]), 2),
        }
        for r in rows
    ]
    columns = ["Ma lot", "Ma CH", "Ten CH", "Ma SP", "Ten SP", "So lo",
               "Han su dung", "Ngay con lai", "Trang thai", "So luong",
               "Gia von/SP", "Gia tri"]

    response = _render(data, columns, fmt, "bao-cao-sap-het-han",
                       "BAO CAO HANG SAP HET HAN")
    _truncate_header(rows, limit, response)
    return response


# ===========================================================================
# Sales report
# ===========================================================================
@router.get("/sales/export", summary="Export the sales report")
def export_sales(
    db: DbSession = Depends(get_db),
    fmt: str = Query("csv", alias="format", pattern="^(csv|xlsx|pdf)$"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    store_id: int | None = Query(None, gt=0),
    category_id: int | None = Query(None, gt=0),
    group_by: str = Query(
        "day", pattern="^(day|week|month|store|category|product)$",
        description="Roll the figures up by this dimension",
    ),
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
) -> StreamingResponse:
    """
    Sales figures rolled up by the requested dimension.

    `order_items` is joined directly rather than through `v_daily_sales`:
    the view carries a redundant GROUP BY that costs a Sort over 912,999
    rows without changing the totals - see the B8 notes in AGENTS.md.

    Day and month rollups use the database's own date arithmetic rather than
    a Python grouping, so the bucketing happens while the rows stream past
    instead of after they are all in memory.
    """
    _validate_range(from_date, to_date)

    try:
        rows = db.rows(
            "sp_Reports_Sales",
            {
                "FromDate": from_date,
                "ToDate": to_date,
                "StoreId": store_id,
                "CategoryId": category_id,
                "GroupBy": group_by,
                "Limit": limit,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    data = [
        {
            "Ky": r["bucket"],
            "So don": int(r["orders"] or 0),
            "So luong": _f(r["quantity"]),
            "Doanh thu": round(_f(r["revenue"]), 2),
        }
        for r in rows
    ]

    columns = ["Ky", "So don", "So luong", "Doanh thu"]

    response = _render(data, columns, fmt, "bao-cao-ban-hang",
                       f"BAO CAO BAN HANG (theo {group_by})")
    _truncate_header(rows, limit, response)
    return response


# ===========================================================================
# Waste report
# ===========================================================================
@router.get("/waste/export", summary="Export the waste report")
def export_waste(
    db: DbSession = Depends(get_db),
    fmt: str = Query("csv", alias="format", pattern="^(csv|xlsx|pdf)$"),
    days: int = Query(
        30, ge=1, le=30, description="Expiring window; capped at 30"
    ),
    store_id: int | None = Query(None, gt=0),
    limit: int = Query(MAX_EXPORT_ROWS, ge=1, le=MAX_EXPORT_ROWS),
) -> StreamingResponse:
    """
    Waste exposure: expired stock plus stock about to expire.

    Adds an `estimated_loss` column per row equal to the whole batch value.
    That is a worst-case figure, not an expected loss - a discount or a
    transfer can recover most of it - and the report says so in the header
    row rather than leaving the reader to assume a total loss.
    """
    try:
        rows = db.rows(
            "sp_Reports_Waste",
            {"Days": days, "StoreId": store_id, "Limit": limit},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    data = [
        {
            "Ma lot": r["inventory_id"],
            "Ma CH": r["store_code"],
            "Ten CH": r["store_name"],
            "Ma SP": r["product_code"],
            "Ten SP": r["product_name"],
            "Nhom hang": r["category_name"],
            "So lo": r["batch_code"],
            "Han su dung": r["expiry_date"].isoformat() if r["expiry_date"] else "",
            "Ngay con lai": r["days_left"],
            "Trang thai": r["state"],
            "So luong": _f(r["quantity"]),
            "Gia von/SP": _f(r["unit_cost"]),
            "Gia tri (uoc toi da)": round(_f(r["total_value"]), 2),
        }
        for r in rows
    ]
    columns = ["Ma lot", "Ma CH", "Ten CH", "Ma SP", "Ten SP", "Nhom hang",
               "So lo", "Han su dung", "Ngay con lai", "Trang thai",
               "So luong", "Gia von/SP", "Gia tri (uoc toi da)"]

    response = _render(data, columns, fmt, "bao-cao-lang-phi",
                       "BAO CAO LANG PHI (uoc toi da)")
    _truncate_header(rows, limit, response)
    return response


# ===========================================================================
# Spoilage risk report (inventory value at risk of being written off)
# ===========================================================================
SPOILAGE_ADVICE_TIMEOUT_SECONDS = 10

SPOILAGE_ADVICE_SYSTEM_PROMPT = (
    "Bạn là chuyên gia quản trị chuỗi cung ứng thực phẩm của FreshChain.\n"
    "Nhiệm vụ: đọc số liệu rủi ro hao hụt bên dưới và viết khuyến nghị hành động.\n"
    "QUY TẮC:\n"
    "1. Chỉ dùng số liệu được cung cấp, không bịa thêm.\n"
    "2. Trả lời bằng tiếng Việt có dấu, 3-5 gạch đầu dòng, mỗi dòng một hành động.\n"
    "3. Nêu con số cụ thể (số lô, giá trị, số ngày còn lại) và thứ tự ưu tiên.\n"
    "4. Không dùng markdown in đậm, không dùng bảng, không mở bài dài dòng.\n"
    "5. Xưng 'Tôi', gọi người đọc là 'Bạn'.\n"
)


def _vi_num(value: float, digits: int = 0) -> str:
    """Format a number the Vietnamese way: dot thousands, comma decimals."""
    text = f"{float(value):,.{digits}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def _risk_reason(row: dict, quantity: float, sellable: float,
                 unsold: float, loss: float, days_left: int) -> str:
    """Build the Vietnamese explanation shown under each risk row."""
    unit = (row.get("unit") or "sản phẩm").strip()
    source = row.get("demand_source") or "none"
    source_label = {
        "forecast": "dự báo Prophet",
        "sales": "bán thực tế 30 ngày",
        "none": "chưa có dữ liệu bán",
    }.get(source, "chưa có dữ liệu bán")

    if days_left < 0:
        return (
            f"Đã hết hạn {abs(days_left)} ngày; toàn bộ {_vi_num(quantity)} {unit} "
            f"({_vi_num(loss)} đ) có nguy cơ thất thoát."
        )
    if days_left == 0:
        return (
            f"Hết hạn hôm nay; {_vi_num(unsold)} {unit} ({_vi_num(loss)} đ) "
            "gần như không kịp bán."
        )
    return (
        f"Còn {days_left} ngày, dự kiến bán được {_vi_num(sellable)}/"
        f"{_vi_num(quantity)} {unit} ({source_label}); ước tính thất thoát "
        f"{_vi_num(unsold)} {unit} ({_vi_num(loss)} đ)."
    )


def _load_spoilage_rows(db: DbSession, days: int, category_id: int | None,
                        store_id: int | None, risk_level: str | None,
                        limit: int) -> list[dict]:
    try:
        return db.rows(
            "sp_Reports_SpoilageRisk",
            {
                "Days": days,
                "CategoryId": category_id,
                "StoreId": store_id,
                "RiskLevel": risk_level,
                "Limit": limit,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc


def _to_risk_row(row: dict) -> SpoilageRiskRow:
    quantity = _f(row["quantity"])
    sellable = _f(row["sellable_qty"])
    unsold = _f(row["unsold_qty"])
    loss = _f(row["loss_value"])
    days_left = int(row["days_left"] or 0)

    return SpoilageRiskRow(
        inventory_id=int(row["inventory_id"]),
        batch_code=row["batch_code"],
        store_id=int(row["store_id"]),
        store_code=row["store_code"],
        store_name=row["store_name"],
        product_id=int(row["product_id"]),
        product_code=row["product_code"],
        product_name=row["product_name"],
        unit=row["unit"],
        category_id=row["category_id"],
        category_name=row["category_name"],
        quantity=round(quantity, 3),
        unit_cost=round(_f(row["unit_cost"]), 2),
        stock_value=round(_f(row["stock_value"]), 2),
        expiry_date=row["expiry_date"],
        days_left=days_left,
        daily_demand=round(_f(row["daily_demand"]), 4),
        demand_source=row["demand_source"],
        sellable_qty=round(sellable, 3),
        unsold_qty=round(unsold, 3),
        loss_value=round(loss, 2),
        risk_score=round(_f(row["risk_score"]), 1),
        risk_level=row["risk_level"],
        recommended_action=row["recommended_action"],
        reason=_risk_reason(row, quantity, sellable, unsold, loss, days_left),
    )


def _load_spoilage_summary(db: DbSession, days: int, category_id: int | None,
                           store_id: int | None) -> dict:
    try:
        sets = db.call(
            "sp_Reports_SpoilageSummary",
            {"Days": days, "CategoryId": category_id, "StoreId": store_id},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    kpi_row = sets[0][0] if sets and sets[0] else {}
    category_rows = sets[1] if len(sets) > 1 else []
    trend_rows = sets[2] if len(sets) > 2 else []
    top_rows = sets[3] if len(sets) > 3 else []

    return {
        "kpi": {
            "total_stock_qty": round(_f(kpi_row.get("total_stock_qty")), 3),
            "total_stock_value": round(_f(kpi_row.get("total_stock_value")), 2),
            "at_risk_qty": round(_f(kpi_row.get("at_risk_qty")), 3),
            "at_risk_value": round(_f(kpi_row.get("at_risk_value")), 2),
            "spoilage_rate": round(_f(kpi_row.get("spoilage_rate")), 2),
            "lots_in_window": int(kpi_row.get("lots_in_window") or 0),
            "lots_to_handle": int(kpi_row.get("lots_to_handle") or 0),
            "expired_lots": int(kpi_row.get("expired_lots") or 0),
            "high_risk_lots": int(kpi_row.get("high_risk_lots") or 0),
            "window_days": int(kpi_row.get("window_days") or days),
        },
        "categories": [
            {
                "category_id": r["category_id"],
                "category_name": r["category_name"],
                "safe_count": int(r["safe_count"] or 0),
                "warning_count": int(r["warning_count"] or 0),
                "high_count": int(r["high_count"] or 0),
                "safe_value": round(_f(r["safe_value"]), 2),
                "warning_value": round(_f(r["warning_value"]), 2),
                "high_value": round(_f(r["high_value"]), 2),
            }
            for r in category_rows
        ],
        "trend": [
            {
                "trend_date": r["trend_date"],
                "loss_value": round(_f(r["loss_value"]), 2),
                "total_value": round(_f(r["total_value"]), 2),
                "lot_count": int(r["lot_count"] or 0),
                "handled_rate": round(_f(r["handled_rate"]), 2),
            }
            for r in trend_rows
        ],
        "top_risks": [
            {
                "product_name": r["product_name"],
                "product_code": r["product_code"],
                "store_name": r["store_name"],
                "batch_code": r["batch_code"],
                "quantity": round(_f(r["quantity"]), 3),
                "unit": r["unit"],
                "days_left": int(r["days_left"] or 0),
                "risk_score": round(_f(r["risk_score"]), 1),
                "risk_level": r["risk_level"],
                "loss_value": round(_f(r["loss_value"]), 2),
            }
            for r in top_rows
        ],
    }


def _fallback_advice(summary: dict) -> str:
    """Deterministic recommendations when Gemini is unavailable."""
    kpi = summary["kpi"]
    lines = [
        f"Tỷ lệ giá trị hàng có nguy cơ hỏng là {_vi_num(kpi['spoilage_rate'], 2)}% "
        f"({_vi_num(kpi['at_risk_value'])} đ trên tổng tồn kho "
        f"{_vi_num(kpi['total_stock_value'])} đ).",
    ]

    if kpi["expired_lots"] > 0:
        lines.append(
            f"- Kiểm kê và xử lý ngay {_vi_num(kpi['expired_lots'])} lô đã hết hạn; "
            "đây là phần không thể cứu được và cần ghi nhận thất thoát."
        )
    if kpi["high_risk_lots"] > 0:
        lines.append(
            f"- Ưu tiên {_vi_num(kpi['high_risk_lots'])} lô nguy cơ cao: chuyển bớt "
            "sang cửa hàng bán nhanh hơn hoặc giảm giá trước khi quá hạn."
        )
    if kpi["lots_to_handle"] > 0:
        lines.append(
            f"- Trong {_vi_num(kpi['lots_in_window'])} lô thuộc khung "
            f"{kpi['window_days']} ngày, có {_vi_num(kpi['lots_to_handle'])} lô cần "
            "xử lý; nên lập danh sách theo thứ tự điểm rủi ro giảm dần."
        )

    if summary["top_risks"]:
        top = summary["top_risks"][0]
        lines.append(
            f"- Lô rủi ro nhất: {top['product_name']} tại {top['store_name']} "
            f"(lô {top['batch_code'] or 'chưa có mã'}), còn {top['days_left']} ngày, "
            f"điểm rủi ro {_vi_num(top['risk_score'], 1)}, ước tính thất thoát "
            f"{_vi_num(top['loss_value'])} đ."
        )

    if summary["categories"]:
        worst = max(summary["categories"], key=lambda c: c["high_count"])
        if worst["high_count"] > 0:
            lines.append(
                f"- Nhóm hàng cần chú ý nhất là {worst['category_name']} với "
                f"{_vi_num(worst['high_count'])} lô nguy cơ cao."
            )

    lines.append(
        "- Tốc độ bán lấy từ dự báo Prophet khi có; các sản phẩm chưa có dự báo "
        "dùng tốc độ bán thực tế 30 ngày gần nhất."
    )
    return "\n".join(lines)


def _build_advice_prompt(summary: dict) -> str:
    kpi = summary["kpi"]
    lines = [
        "SỐ LIỆU RỦI RO HAO HỤT",
        f"- Tổng tồn kho: {_vi_num(kpi['total_stock_qty'])} đơn vị, trị giá "
        f"{_vi_num(kpi['total_stock_value'])} đ.",
        f"- Giá trị có nguy cơ hao hụt: {_vi_num(kpi['at_risk_value'])} đ "
        f"({_vi_num(kpi['spoilage_rate'], 2)}% tổng tồn kho).",
        f"- Khung thời gian: {kpi['window_days']} ngày tới.",
        f"- Số lô cần xử lý: {_vi_num(kpi['lots_to_handle'])}; trong đó "
        f"{_vi_num(kpi['expired_lots'])} lô đã hết hạn và "
        f"{_vi_num(kpi['high_risk_lots'])} lô nguy cơ cao.",
        "TOP LÔ RỦI RO:",
    ]
    for index, item in enumerate(summary["top_risks"], start=1):
        lines.append(
            f"{index}. {item['product_name']} tại {item['store_name']} "
            f"(lô {item['batch_code'] or 'chua co ma'}): còn {item['days_left']} ngày, "
            f"điểm rủi ro {_vi_num(item['risk_score'], 1)}, thất thoát ước tính "
            f"{_vi_num(item['loss_value'])} đ."
        )
    lines.append(
        "\nHãy viết 3-5 khuyến nghị hành động cụ thể, theo thứ tự ưu tiên, "
        "dựa đúng trên số liệu trên."
    )
    return "\n".join(lines)


def _gemini_with_timeout(api_key: str, model_name: str, prompt: str,
                         timeout: float):
    """Call Gemini on a worker thread so a hung SDK cannot block the request."""
    from google import genai

    client = genai.Client(api_key=api_key)
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            client.models.generate_content, model=model_name, contents=prompt
        )
        return future.result(timeout=timeout)
    finally:
        executor.shutdown(wait=False)


@router.get(
    "/spoilage/summary",
    response_model=SpoilageSummaryResponse,
    summary="KPI and chart data for the spoilage risk report",
)
def spoilage_summary(
    db: DbSession = Depends(get_db),
    days: int = Query(30, ge=0, le=365, description="Expiry window in days"),
    category_id: int | None = Query(None, gt=0),
    store_id: int | None = Query(None, gt=0),
) -> SpoilageSummaryResponse:
    summary = _load_spoilage_summary(db, days, category_id, store_id)
    return SpoilageSummaryResponse(**summary, generated_at=datetime.now())


@router.get(
    "/spoilage/advice",
    response_model=SpoilageAdviceResponse,
    summary="AI summary and recommendations for the spoilage report",
)
def spoilage_advice(
    db: DbSession = Depends(get_db),
    days: int = Query(30, ge=0, le=365),
    category_id: int | None = Query(None, gt=0),
    store_id: int | None = Query(None, gt=0),
) -> SpoilageAdviceResponse:
    """
    Build a short action plan from the same numbers the page shows.

    Gemini is best-effort: a missing key, a network error or a timeout falls
    back to deterministic rules, so the panel always has content and the
    request never turns into a 500.
    """
    summary = _load_spoilage_summary(db, days, category_id, store_id)
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        return SpoilageAdviceResponse(
            answer=_fallback_advice(summary),
            model="fallback",
            generated_at=datetime.now(),
        )

    model_name = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
    prompt = SPOILAGE_ADVICE_SYSTEM_PROMPT + "\n" + _build_advice_prompt(summary)

    try:
        response = _gemini_with_timeout(
            api_key, model_name, prompt, SPOILAGE_ADVICE_TIMEOUT_SECONDS
        )
        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates") and response.candidates:
            try:
                text = response.candidates[0].content.parts[0].text
            except Exception:
                text = None
        if text and text.strip():
            return SpoilageAdviceResponse(
                answer=text.strip(),
                model=model_name,
                generated_at=datetime.now(),
            )
    except Exception:
        # A timeout or an API outage must not hide the report behind an error.
        pass

    return SpoilageAdviceResponse(
        answer=_fallback_advice(summary),
        model="fallback",
        generated_at=datetime.now(),
    )


@router.get(
    "/spoilage",
    response_model=list[SpoilageRiskRow],
    summary="Batches at risk of spoilage",
)
def spoilage_detail(
    db: DbSession = Depends(get_db),
    days: int = Query(30, ge=0, le=365, description="Expiry window in days"),
    category_id: int | None = Query(None, gt=0),
    store_id: int | None = Query(None, gt=0),
    risk_level: str | None = Query(None, pattern="^(safe|warning|high)$"),
    limit: int = Query(500, ge=1, le=2000),
) -> list[SpoilageRiskRow]:
    rows = _load_spoilage_rows(
        db, days, category_id, store_id, risk_level, limit
    )
    return [_to_risk_row(row) for row in rows]


@router.get(
    "/spoilage/export",
    summary="Export the spoilage risk report",
)
def export_spoilage(
    db: DbSession = Depends(get_db),
    fmt: str = Query("xlsx", alias="format", pattern="^(csv|xlsx|pdf)$"),
    days: int = Query(30, ge=0, le=365),
    category_id: int | None = Query(None, gt=0),
    store_id: int | None = Query(None, gt=0),
    risk_level: str | None = Query(None, pattern="^(safe|warning|high)$"),
    limit: int = Query(2000, ge=1, le=2000),
) -> StreamingResponse:
    rows = _load_spoilage_rows(
        db, days, category_id, store_id, risk_level, limit
    )

    data = [
        {
            "Ma lo": r["inventory_id"],
            "So lo": r["batch_code"] or "",
            "Ma CH": r["store_code"],
            "Ten CH": r["store_name"],
            "Ma SP": r["product_code"],
            "Ten SP": r["product_name"],
            "Nhom hang": r["category_name"] or "",
            "So luong": round(_f(r["quantity"]), 3),
            "Han su dung": r["expiry_date"].isoformat() if r["expiry_date"] else "",
            "Ngay con lai": int(r["days_left"] or 0),
            "Toc do ban/ngay": round(_f(r["daily_demand"]), 2),
            "Nguon toc do": r["demand_source"],
            "Diem rui ro": round(_f(r["risk_score"]), 1),
            "Muc rui ro": (r["risk_level"] or "").upper(),
            "Gia tri that thoat": round(_f(r["loss_value"]), 2),
            "Goi y xu ly": r["recommended_action"],
        }
        for r in rows
    ]
    columns = ["Ma lo", "So lo", "Ma CH", "Ten CH", "Ma SP", "Ten SP",
               "Nhom hang", "So luong", "Han su dung", "Ngay con lai",
               "Toc do ban/ngay", "Nguon toc do", "Diem rui ro", "Muc rui ro",
               "Gia tri that thoat", "Goi y xu ly"]

    response = _render(data, columns, fmt, "bao-cao-rui-ro-hao-hut",
                       "BAO CAO HANG HOA & RUI RO HAO HUT")
    _truncate_header(rows, limit, response)
    return response


@router.get(
    "/top-selling",
    response_model=list[TopSellingRow],
    summary="Best-selling products of one day",
)
def top_selling(
    db: DbSession = Depends(get_db),
    sale_date: date | None = Query(
        None,
        alias="date",
        description="Sale date (YYYY-MM-DD); defaults to the latest day with sales",
    ),
) -> list[TopSellingRow]:
    """
    Products sold on one day, best sellers first.

    Without `date` the procedure falls back to the latest day that actually
    has completed sales, so the page opens on data instead of an empty today.
    """
    try:
        rows = db.rows("sp_Reports_TopSelling", {"Date": sale_date})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return [
        TopSellingRow(
            product_id=int(row["product_id"]),
            product_name=row["product_name"],
            product_code=row["product_code"],
            category_name=row["category_name"],
            sale_date=row["sale_date"],
            total_quantity=round(_f(row["total_quantity"]), 3),
            total_revenue=round(_f(row["total_revenue"]), 2),
        )
        for row in rows
    ]
