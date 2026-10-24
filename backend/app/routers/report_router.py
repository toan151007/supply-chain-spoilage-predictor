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
from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error

router = APIRouter(prefix="/reports", tags=["reports"])

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
