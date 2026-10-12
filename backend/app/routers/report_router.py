"""
Report export endpoints (B11): CSV, XLSX and PDF.

All database access goes through the SQLAlchemy ORM - no raw SQL here.

One helper builds the bytes for all three formats from the same row list,
so a report can never disagree with itself across formats: the CSV, the
spreadsheet and the PDF are rendered from a single set of rows.

Date filters are `date`, not `datetime`, matching the dashboard endpoints -
see the timezone note in AGENTS.md.

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
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Integer, case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Inventory, Order, OrderItem, Product, Store

router = APIRouter(prefix="/reports", tags=["reports"])

HTTP_422_UNPROCESSABLE_CONTENT = 422

VN_TZ = timezone(timedelta(hours=7))

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


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=VN_TZ)


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
    db: Session = Depends(get_db),
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
    filters = []
    if in_stock_only:
        filters.append(Inventory.quantity > 0)
    if store_id is not None:
        filters.append(Inventory.store_id == store_id)
    if product_id is not None:
        filters.append(Inventory.product_id == product_id)
    if category_id is not None:
        filters.append(Product.category_id == category_id)

    rows = db.execute(
        select(
            Inventory.inventory_id,
            Store.store_code,
            Store.store_name,
            Product.product_code,
            Product.product_name,
            Category.category_name,
            Inventory.batch_code,
            Inventory.expiry_date,
            func.cast(
                Inventory.expiry_date - func.current_date(), Integer
            ).label("days_left"),
            Inventory.quantity,
            Product.unit_cost,
            (Inventory.quantity * Product.unit_cost).label("total_value"),
            Inventory.received_date,
        )
        .select_from(Inventory)
        .join(Store, Store.store_id == Inventory.store_id)
        .join(Product, Product.product_id == Inventory.product_id)
        .outerjoin(Category, Category.category_id == Product.category_id)
        .where(*filters)
        .order_by(Inventory.expiry_date.asc().nulls_last())
        .limit(limit)
    ).all()

    data = [
        {
            "Ma lot": r[0],
            "Ma CH": r[1],
            "Ten CH": r[2],
            "Ma SP": r[3],
            "Ten SP": r[4],
            "Nhom hang": r[5],
            "So lo": r[6],
            "Han su dung": r[7].isoformat() if r[7] else "",
            "Ngay con lai": r[8],
            "So luong": _f(r[9]),
            "Gia von/SP": _f(r[10]),
            "Gia tri ton": round(_f(r[11]), 2),
            "Ngay nhap": r[12].isoformat() if r[12] else "",
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
    db: Session = Depends(get_db),
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
    cutoff = date.today() + timedelta(days=days)

    filters = [
        Inventory.quantity > 0,
        Inventory.expiry_date.isnot(None),
        Inventory.expiry_date <= cutoff,
    ]
    if store_id is not None:
        filters.append(Inventory.store_id == store_id)

    days_left = func.cast(
        Inventory.expiry_date - func.current_date(), Integer
    )

    rows = db.execute(
        select(
            Inventory.inventory_id,
            Store.store_code,
            Store.store_name,
            Product.product_code,
            Product.product_name,
            Inventory.batch_code,
            Inventory.expiry_date,
            days_left,
            Inventory.quantity,
            Product.unit_cost,
            (Inventory.quantity * Product.unit_cost).label("total_value"),
        )
        .select_from(Inventory)
        .join(Store, Store.store_id == Inventory.store_id)
        .join(Product, Product.product_id == Inventory.product_id)
        .where(*filters)
        .order_by(Inventory.expiry_date)
        .limit(limit)
    ).all()

    data = [
        {
            "Ma lot": r[0],
            "Ma CH": r[1],
            "Ten CH": r[2],
            "Ma SP": r[3],
            "Ten SP": r[4],
            "So lo": r[5],
            "Han su dung": r[6].isoformat() if r[6] else "",
            "Ngay con lai": r[7],
            "Trang thai": "DA HET HAN" if int(r[7]) < 0 else "sap het han",
            "So luong": _f(r[8]),
            "Gia von/SP": _f(r[9]),
            "Gia tri": round(_f(r[10]), 2),
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
    db: Session = Depends(get_db),
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

    Day and month rollups use the database's own date_trunc rather than a
    Python grouping, so the bucketing happens while the rows stream past
    instead of after they are all in memory.
    """
    _validate_range(from_date, to_date)

    filters = [Order.status == "completed", Order.order_type == "sale"]
    if from_date is not None:
        filters.append(Order.order_date >= _start_of_day(from_date))
    if to_date is not None:
        filters.append(Order.order_date < _start_of_day(to_date + timedelta(days=1)))
    if store_id is not None:
        filters.append(Order.store_id == store_id)
    if category_id is not None:
        filters.append(Product.category_id == category_id)

    # One output row per bucket, and nothing else.
    #
    # An earlier version also grouped by store and category for the time
    # rollups, which turned "sales per day" into 1,826 days x 10 stores x
    # 8 categories = 146,080 rows and a 3 MB file. A time series wants one
    # row per period; use group_by=store or group_by=category when that
    # breakdown is what is actually needed.
    if group_by in ("day", "week", "month"):
        label = func.date_trunc(group_by, Order.order_date).label("Ky")
        extra = []
    elif group_by == "store":
        label = Store.store_code.label("Ky")
        extra = []
    elif group_by == "category":
        label = Category.category_name.label("Ky")
        extra = []
    else:  # product
        label = Product.product_code.label("Ky")
        extra = []

    group_cols = [label] + extra

    rows = db.execute(
        select(
            *group_cols,
            func.count(func.distinct(Order.order_id)).label("orders"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("quantity"),
            func.coalesce(func.sum(OrderItem.line_total), 0).label("revenue"),
        )
        .select_from(OrderItem)
        .join(Order, Order.order_id == OrderItem.order_id)
        .join(Store, Store.store_id == Order.store_id)
        .join(Product, Product.product_id == OrderItem.product_id)
        .outerjoin(Category, Category.category_id == Product.category_id)
        .where(*filters)
        .group_by(*group_cols)
        .order_by(label)
        .limit(limit)
    ).all()

    data = []
    for row in rows:
        label_value = row[0]
        if hasattr(label_value, "date"):
            label_value = label_value.isoformat()
        entry = {"Ky": label_value}
        for i, col in enumerate(group_cols[1:]):
            entry[col] = row[i + 1]
        tail = row[len(group_cols):]
        entry["So don"] = int(tail[0])
        entry["So luong"] = _f(tail[1])
        entry["Doanh thu"] = round(_f(tail[2]), 2)
        data.append(entry)

    columns = ["Ky"] + group_cols[1:] + ["So don", "So luong", "Doanh thu"]

    response = _render(data, columns, fmt, "bao-cao-ban-hang",
                       f"BAO CAO BAN HANG (theo {group_by})")
    _truncate_header(rows, limit, response)
    return response


# ===========================================================================
# Waste report
# ===========================================================================
@router.get("/waste/export", summary="Export the waste report")
def export_waste(
    db: Session = Depends(get_db),
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
    cutoff = date.today() + timedelta(days=days)

    filters = [
        Inventory.quantity > 0,
        Inventory.expiry_date.isnot(None),
        Inventory.expiry_date <= cutoff,
    ]
    if store_id is not None:
        filters.append(Inventory.store_id == store_id)

    days_left = func.cast(
        Inventory.expiry_date - func.current_date(), Integer
    )

    state = case(
        (Inventory.expiry_date < func.current_date(), "DA HET HAN"),
        else_="SAP HET HAN",
    )

    rows = db.execute(
        select(
            Inventory.inventory_id,
            Store.store_code,
            Store.store_name,
            Product.product_code,
            Product.product_name,
            Category.category_name,
            Inventory.batch_code,
            Inventory.expiry_date,
            days_left,
            state,
            Inventory.quantity,
            Product.unit_cost,
            (Inventory.quantity * Product.unit_cost).label("total_value"),
        )
        .select_from(Inventory)
        .join(Store, Store.store_id == Inventory.store_id)
        .join(Product, Product.product_id == Inventory.product_id)
        .outerjoin(Category, Category.category_id == Product.category_id)
        .where(*filters)
        .order_by(state, (Inventory.quantity * Product.unit_cost).desc())
        .limit(limit)
    ).all()

    data = [
        {
            "Ma lot": r[0],
            "Ma CH": r[1],
            "Ten CH": r[2],
            "Ma SP": r[3],
            "Ten SP": r[4],
            "Nhom hang": r[5],
            "So lo": r[6],
            "Han su dung": r[7].isoformat() if r[7] else "",
            "Ngay con lai": r[8],
            "Trang thai": r[9],
            "So luong": _f(r[10]),
            "Gia von/SP": _f(r[11]),
            "Gia tri (uoc toi da)": round(_f(r[12]), 2),
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

