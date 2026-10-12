"""
File import endpoints (Excel / CSV) for products, inventory and sales.

All database access goes through the SQLAlchemy ORM - no raw SQL here, as
required by the project rules.

How an import runs
------------------
1. The upload is read and decoded into a DataFrame. A wrong extension or
   undecodable bytes fail with 400 before pandas is involved.
2. Required columns are checked. A missing one fails with 422.
3. Every row is validated in memory. Nothing is written yet.
4. Only then, depending on the strategy:
     - `rollback` (default): any bad row aborts the whole file, 0 rows
       written.
     - `skip`: the good rows are written, the bad ones are reported.

Validating before writing is what makes `rollback` meaningful. With a
row-at-a-time insert there is no "unwritten" state to compare against, and a
file with row 9,001 bad would leave 9,000 rows behind.

Import dates are interpreted as Asia/Ho_Chi_Minh (+07:00) to match the
seeded data - see the timezone note in AGENTS.md. `orders.order_date` is
`timestamptz`, so attaching the offset explicitly is required; a naive
datetime is rejected by PostgreSQL.
"""

import io
from datetime import date, datetime, timedelta, timezone

import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import require_role
from app.database import get_db
from app.import_specs import SUPPORTED_EXTENSIONS, get_spec
from app.models import Category, Inventory, Order, OrderItem, Product, Store
from app.schemas.import_schema import ImportResult, RowError, TemplateInfo

router = APIRouter(prefix="/import", tags=["import"])

HTTP_422_UNPROCESSABLE_CONTENT = 422

# Upload guard rails. A 10 MB CSV of products is roughly 100k rows, far more
# than anyone should insert through a web form in one request.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 20_000
MAX_REPORTED_ERRORS = 100

# Vietnam time, matching how the seeded dataset is stored.
VN_TZ = timezone(timedelta(hours=7))

ORDER_TYPES = {"sale", "purchase"}
ORDER_STATUSES = {"pending", "completed", "cancelled"}
PAYMENT_METHODS = {"cash", "card", "transfer", "ewallet", "other"}

XLSX_MAGIC = b"PK\x03\x04"


# ===========================================================================
# Cell coercion helpers
# ===========================================================================
def _is_blank(value) -> bool:
    """True for None, empty string, whitespace and NaN/NaT."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _as_int(value):
    """Coerce to int, or None. Accepts 1.0 from Excel and '1' from CSV."""
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != int(number):
        return None
    return int(number)


def _as_float(value):
    """Coerce to float, or None."""
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_date(value):
    """Coerce to date, or None. Accepts 'YYYY-MM-DD' and Excel datetimes."""
    if _is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value, errors="raise").date()
    except (ValueError, TypeError):
        return None


def _as_datetime(value):
    """Coerce to a timezone-aware datetime in VN_TZ, or None."""
    if _is_blank(value):
        return None
    try:
        parsed = pd.to_datetime(value, errors="raise")
    except (ValueError, TypeError):
        return None
    if pd.isna(parsed):
        return None
    if parsed.tzinfo is None:
        # Naive input is assumed to be local wall-clock time, which is how
        # the seeded orders are stored.
        return parsed.to_pydatetime().replace(tzinfo=VN_TZ)
    return parsed.to_pydatetime()


def _as_str(value) -> str | None:
    """Coerce to a stripped string, or None when blank."""
    if _is_blank(value):
        return None
    return str(value).strip()


# ===========================================================================
# File reading
# ===========================================================================
def _read_upload(upload: UploadFile, resource_type: str) -> pd.DataFrame:
    """
    Decode the upload into a DataFrame.

    Raises 400 for a bad extension, an empty body, a file over the size cap
    or bytes that are not the format the extension promises. All of those
    are client mistakes, so they get 400 rather than 422.
    """
    name = upload.filename or ""
    suffix = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""

    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{suffix or name}'. "
                f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    raw = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty"
        )

    # An .xlsx is a ZIP archive. Catching the mismatch here turns an
    # obscure UnicodeDecodeError from pandas into a message the user can act
    # on ("you renamed a spreadsheet but did not convert it").
    if suffix == ".csv" and raw.startswith(XLSX_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "File is named .csv but its bytes are an Excel (.xlsx) workbook. "
                "Rename it to .xlsx, or re-export it as real CSV."
            ),
        )
    if suffix == ".xlsx" and not raw.startswith(XLSX_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is named .xlsx but is not an Excel workbook.",
        )

    try:
        if suffix == ".csv":
            frame = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
        else:
            frame = pd.read_excel(io.BytesIO(raw), dtype=str)
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "File is not valid UTF-8 text. Re-save the CSV as UTF-8."
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read the file: {type(exc).__name__}: {exc}",
        ) from exc

    if frame.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File has headers but no data rows.",
        )
    if len(frame) > MAX_ROWS:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"File has {len(frame)} rows; the limit is {MAX_ROWS}.",
        )

    # read_csv(dtype=str) keeps whitespace, which would make 'unit ' fail a
    # required-column lookup for no good reason.
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame


def _check_required_columns(frame: pd.DataFrame, spec) -> None:
    present = set(frame.columns)
    missing = [c for c in spec.required if c not in present]
    if missing:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Missing required column(s): {', '.join(missing)}. "
                f"Download the template from /api/v1/import/template/"
                f"{spec.resource_type} for the expected layout."
            ),
        )


# ===========================================================================
# Row validators - return (clean_value, error_message)
# ===========================================================================
def _validate_products(row, db, seen_codes) -> dict:
    """Validate one product row. Returns (values, error)."""
    code = _as_str(row.get("product_code"))
    if not code:
        return None, "product_code is required"
    if code in seen_codes:
        return None, f"product_code '{code}' is duplicated inside the file"
    seen_codes.add(code)

    name = _as_str(row.get("product_name"))
    if not name:
        return None, "product_name is required"

    category_id = _as_int(row.get("category_id"))
    if category_id is None:
        return None, "category_id must be an integer"
    if not db.get(Category, category_id):
        return None, f"category_id {category_id} does not exist"

    unit = _as_str(row.get("unit"))
    if not unit:
        return None, "unit is required"

    unit_cost = _as_float(row.get("unit_cost"))
    if unit_cost is None:
        return None, "unit_cost must be a number"
    if unit_cost < 0:
        return None, "unit_cost must be >= 0"

    selling_price = _as_float(row.get("selling_price"))
    if selling_price is None:
        return None, "selling_price must be a number"
    if selling_price < 0:
        return None, "selling_price must be >= 0"

    shelf_life_days = _as_int(row.get("shelf_life_days"))
    if shelf_life_days is None:
        return None, "shelf_life_days must be an integer"
    if shelf_life_days <= 0:
        return None, "shelf_life_days must be > 0"

    min_stock = _as_float(row.get("min_stock")) or 0.0
    max_stock = _as_float(row.get("max_stock"))

    if max_stock is not None and max_stock < min_stock:
        return None, "max_stock must be >= min_stock"

    return {
        "product_code": code,
        "product_name": name,
        "category_id": category_id,
        "unit": unit,
        "unit_cost": unit_cost,
        "selling_price": selling_price,
        "shelf_life_days": shelf_life_days,
        "min_stock": min_stock,
        "max_stock": max_stock,
        "supplier": _as_str(row.get("supplier")),
    }, None


def _validate_inventory(row, db, seen_lots) -> dict:
    """Validate one inventory (batch) row. Returns (values, error)."""
    product_id = _as_int(row.get("product_id"))
    if product_id is None:
        return None, "product_id must be an integer"
    if not db.get(Product, product_id):
        return None, f"product_id {product_id} does not exist"

    store_id = _as_int(row.get("store_id"))
    if store_id is None:
        return None, "store_id must be an integer"
    if not db.get(Store, store_id):
        return None, f"store_id {store_id} does not exist"

    quantity = _as_float(row.get("quantity"))
    if quantity is None:
        return None, "quantity must be a number"
    if quantity < 0:
        return None, "quantity must be >= 0"

    expiry_date = _as_date(row.get("expiry_date"))
    if expiry_date is None:
        return None, "expiry_date is required (YYYY-MM-DD)"

    # The table has UNIQUE (store_id, product_id, expiry_date).
    lot_key = (store_id, product_id, expiry_date)
    if lot_key in seen_lots:
        return None, (
            f"duplicate batch (store_id={store_id}, product_id={product_id}, "
            f"expiry_date={expiry_date}) inside the file"
        )
    seen_lots.add(lot_key)

    received_date = _as_date(row.get("received_date")) or date.today()

    return {
        "store_id": store_id,
        "product_id": product_id,
        "quantity": quantity,
        "expiry_date": expiry_date,
        "batch_code": _as_str(row.get("batch_code")),
        "received_date": received_date,
    }, None


def _validate_sales(row, db, seen_codes) -> dict:
    """Validate one sales row. Returns (values, error)."""
    order_date = _as_datetime(row.get("order_date"))
    if order_date is None:
        return None, "order_date is required (YYYY-MM-DD or a valid date)"

    store_id = _as_int(row.get("store_id"))
    if store_id is None:
        return None, "store_id must be an integer"
    if not db.get(Store, store_id):
        return None, f"store_id {store_id} does not exist"

    product_id = _as_int(row.get("product_id"))
    if product_id is None:
        return None, "product_id must be an integer"
    if not db.get(Product, product_id):
        return None, f"product_id {product_id} does not exist"

    quantity = _as_float(row.get("quantity"))
    if quantity is None:
        return None, "quantity must be a number"
    if quantity <= 0:
        return None, "quantity must be > 0"

    unit_price = _as_float(row.get("unit_price"))
    if unit_price is None:
        return None, "unit_price must be a number"
    if unit_price < 0:
        return None, "unit_price must be >= 0"

    discount = _as_float(row.get("discount_percent")) or 0.0
    if not 0 <= discount <= 100:
        return None, "discount_percent must be between 0 and 100"

    order_type = _as_str(row.get("order_type")) or "sale"
    if order_type not in ORDER_TYPES:
        return None, f"order_type must be one of {sorted(ORDER_TYPES)}"

    order_status = _as_str(row.get("status")) or "completed"
    if order_status not in ORDER_STATUSES:
        return None, f"status must be one of {sorted(ORDER_STATUSES)}"

    payment = _as_str(row.get("payment_method"))
    if payment is not None and payment not in PAYMENT_METHODS:
        return None, f"payment_method must be one of {sorted(PAYMENT_METHODS)}"

    # A repeated order_code is NOT an error - it is how a multi-line order
    # is expressed, so the lines must all be kept and grouped later in
    # _write_sales. The real conflict (a code that already exists in the
    # database) is checked there, once, with a single query.
    order_code = _as_str(row.get("order_code"))

    return {
        "order_code": order_code,
        "order_date": order_date,
        "store_id": store_id,
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_percent": discount,
        "order_type": order_type,
        "status": order_status,
        "payment_method": payment,
        "customer_name": _as_str(row.get("customer_name")),
    }, None


VALIDATORS = {
    "products": _validate_products,
    "inventory": _validate_inventory,
    "sales": _validate_sales,
}


# ===========================================================================
# Writers
# ===========================================================================
def _write_products(db: Session, rows: list[dict]) -> list[int]:
    """Insert validated product rows. Returns the new primary keys."""
    existing = set(
        db.execute(
            select(Product.product_code).where(
                Product.product_code.in_([r["product_code"] for r in rows])
            )
        ).scalars().all()
    )
    clash = sorted(existing)
    if clash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"product_code already exists in the database: {', '.join(clash)}. "
                "Nothing was imported."
            ),
        )

    created = []
    for values in rows:
        product = Product(**values)
        db.add(product)
        db.flush()  # assign product_id so the response can report it
        created.append(product.product_id)
    return created


def _write_inventory(db: Session, rows: list[dict]) -> list[int]:
    """Insert validated batches. Returns the new inventory_id values."""
    store_ids = {r["store_id"] for r in rows}
    product_ids = {r["product_id"] for r in rows}

    # One query for all existing lots, instead of one per row.
    existing = set(
        db.execute(
            select(
                Inventory.store_id,
                Inventory.product_id,
                Inventory.expiry_date,
            ).where(
                Inventory.store_id.in_(store_ids),
                Inventory.product_id.in_(product_ids),
            )
        ).all()
    )

    clashes = [
        (r["store_id"], r["product_id"], r["expiry_date"])
        for r in rows
        if (r["store_id"], r["product_id"], r["expiry_date"]) in existing
    ]
    if clashes:
        preview = "; ".join(
            f"store={s}, product={p}, expiry={e}" for s, p, e in clashes[:5]
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{len(clashes)} batch(es) already exist in the database "
                f"({preview}). Nothing was imported."
            ),
        )

    created = []
    for values in rows:
        lot = Inventory(**values)
        db.add(lot)
        db.flush()
        created.append(lot.inventory_id)
    return created


def _write_sales(db: Session, rows: list[dict]) -> list[int]:
    """
    Insert sales rows, grouping lines that share an order_code.

    A row without an order_code becomes its own single-line order. Rows are
    keyed by (order_code) when present, otherwise each gets a fresh key so
    it never merges with its neighbour.
    """
    groups: dict[str, list[dict]] = {}
    order_meta: dict[str, dict] = {}
    counter = 0

    for row in rows:
        code = row["order_code"]
        if not code:
            counter += 1
            code = f"IMP-{row['order_date'].strftime('%Y%m%d%H%M%S')}-{counter:06d}"
            row["order_code"] = code
        groups.setdefault(code, []).append(row)
        # The header fields must agree across the lines of one order; the
        # first row wins, which matches how the row is written by hand.
        order_meta.setdefault(
            code,
            {
                "order_date": row["order_date"],
                "store_id": row["store_id"],
                "order_type": row["order_type"],
                "status": row["status"],
                "payment_method": row["payment_method"],
                "customer_name": row["customer_name"],
            },
        )

    # One query for every order_code in the file, not one per code.
    existing_codes = set(
        db.execute(
            select(Order.order_code).where(Order.order_code.in_(list(groups)))
        ).scalars().all()
    )
    if existing_codes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"order_code already exists in the database: "
                f"{', '.join(sorted(existing_codes))}. Nothing was imported."
            ),
        )

    created = []
    for code, lines in groups.items():
        meta = order_meta[code]
        order = Order(
            order_code=code,
            order_date=meta["order_date"],
            store_id=meta["store_id"],
            order_type=meta["order_type"],
            status=meta["status"],
            payment_method=meta["payment_method"],
            customer_name=meta["customer_name"],
            total_amount=0,
            total_quantity=0,
        )
        db.add(order)
        db.flush()

        for line in lines:
            db.add(
                OrderItem(
                    order_id=order.order_id,
                    product_id=line["product_id"],
                    quantity=line["quantity"],
                    unit_price=line["unit_price"],
                    unit_cost=None,
                    discount_percent=line["discount_percent"],
                    # line_total is a generated column - the database owns it.
                )
            )
        created.append(order.order_id)

    # Same pattern as the orders router: flush first because the session
    # runs with autoflush=False, otherwise the SUM reads the old state.
    db.flush()
    for order_id in created:
        total_amount, total_quantity = db.execute(
            select(
                func.coalesce(func.sum(OrderItem.line_total), 0),
                func.coalesce(func.sum(OrderItem.quantity), 0),
            ).where(OrderItem.order_id == order_id)
        ).one()
        order = db.get(Order, order_id)
        order.total_amount = total_amount
        order.total_quantity = total_quantity

    return created


WRITERS = {
    "products": _write_products,
    "inventory": _write_inventory,
    "sales": _write_sales,
}


# ===========================================================================
# Endpoints
# ===========================================================================
def _require_spec(resource_type: str):
    from app.import_specs import IMPORT_SPECS

    spec = IMPORT_SPECS.get(resource_type)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Unknown import type '{resource_type}'. "
                f"Available: {', '.join(sorted(IMPORT_SPECS))}"
            ),
        )
    return spec


def _run_import(
    resource_type: str, frame: pd.DataFrame, spec, strategy: str, db: Session
) -> ImportResult:
    """Validate every row, then write according to the strategy."""
    validator = VALIDATORS[resource_type]
    writer = WRITERS[resource_type]

    seen = set()
    clean_rows: list[dict] = []
    errors: list[RowError] = []

    for offset, (_, row) in enumerate(frame.iterrows()):
        row_number = offset + 1  # 1-based, header excluded
        values, error = validator(row.to_dict(), db, seen)
        if error:
            if len(errors) < MAX_REPORTED_ERRORS:
                errors.append(RowError(row_number=row_number, message=error))
        elif values is None:
            # Defensive: a validator that returns (None, None) would
            # otherwise reach the writer and surface as an unrelated 500.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Validator for {resource_type} returned no values and no "
                    f"error on row {row_number}. This is a bug."
                ),
            )
        else:
            clean_rows.append(values)

    total_rows = len(frame)
    error_rows = total_rows - len(clean_rows)
    errors_truncated = error_rows > len(errors)

    # Any bad row aborts the whole file under the default strategy. That is
    # the safe default: a half-imported catalogue is harder to reason about
    # than no import at all.
    if errors and strategy == "rollback":
        return ImportResult(
            file_name="",
            resource_type=resource_type,
            strategy=strategy,
            total_rows=total_rows,
            success_rows=0,
            error_rows=error_rows,
            errors=errors,
            errors_truncated=errors_truncated,
            created_ids=[],
            message=(
                f"{error_rows} of {total_rows} row(s) failed validation. "
                "Nothing was imported (strategy=rollback). Fix the file and "
                "upload it again."
            ),
        )

    created_ids: list[int] = []
    try:
        created_ids = writer(db, clean_rows)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The database rejected a row that passed validation "
                f"(constraint: {exc.orig}). Nothing was imported."
            ),
        ) from exc

    message = f"Imported {len(created_ids)} record(s)."
    if errors:
        message += (
            f" {error_rows} row(s) were skipped because of the errors listed above."
        )

    return ImportResult(
        file_name="",
        resource_type=resource_type,
        strategy=strategy,
        total_rows=total_rows,
        success_rows=len(clean_rows),
        error_rows=error_rows,
        errors=errors,
        errors_truncated=errors_truncated,
        created_ids=created_ids,
        message=message,
    )


def _import_endpoint(
    resource_type: str, file: UploadFile, strategy: str, db: Session
) -> ImportResult:
    """Shared body for the three upload endpoints."""
    spec = _require_spec(resource_type)
    frame = _read_upload(file, resource_type)
    _check_required_columns(frame, spec)

    result = _run_import(resource_type, frame, spec, strategy, db)
    result.file_name = file.filename or ""
    return result


@router.post(
    "/products", response_model=ImportResult, summary="Import products from a file"
, dependencies=[Depends(require_role('owner', 'manager'))])
def import_products(
    file: UploadFile = File(..., description="CSV or XLSX file"),
    on_error: str = Query(
        "rollback", pattern="^(rollback|skip)$",
        description="rollback: write nothing if any row fails. skip: import the good rows.",
    ),
    db: Session = Depends(get_db),
) -> ImportResult:
    """
    Import products.

    `product_code` must be unique both inside the file and against the
    database; a clash returns 409 and writes nothing.
    """
    return _import_endpoint("products", file, on_error, db)


@router.post(
    "/inventory", response_model=ImportResult, summary="Import stock batches from a file"
, dependencies=[Depends(require_role('owner', 'manager'))])
def import_inventory(
    file: UploadFile = File(..., description="CSV or XLSX file"),
    on_error: str = Query(
        "rollback", pattern="^(rollback|skip)$",
        description="rollback: write nothing if any row fails. skip: import the good rows.",
    ),
    db: Session = Depends(get_db),
) -> ImportResult:
    """
    Import inventory batches.

    (store_id, product_id, expiry_date) is unique in the schema, so a batch
    that already exists returns 409 and writes nothing.
    """
    return _import_endpoint("inventory", file, on_error, db)


@router.post(
    "/sales", response_model=ImportResult, summary="Import sales orders from a file"
, dependencies=[Depends(require_role('owner', 'manager'))])
def import_sales(
    file: UploadFile = File(..., description="CSV or XLSX file"),
    on_error: str = Query(
        "rollback", pattern="^(rollback|skip)$",
        description="rollback: write nothing if any row fails. skip: import the good rows.",
    ),
    db: Session = Depends(get_db),
) -> ImportResult:
    """
    Import sales.

    Rows sharing an `order_code` become one order with several lines. Rows
    without one become a single-line order each. `line_total` is computed by
    the database, and each order's totals are recomputed from its lines -
    the same rule the orders router follows.
    """
    return _import_endpoint("sales", file, on_error, db)


def _template_frame(resource_type: str) -> pd.DataFrame:
    spec = _require_spec(resource_type)
    return pd.DataFrame(spec.sample_rows, columns=spec.columns)


@router.get(
    "/template/{resource_type}",
    summary="Download a CSV or XLSX template with the expected headers",
)
def download_template(
    resource_type: str,
    fmt: str = Query("csv", pattern="^(csv|xlsx)$", description="Output format"),
) -> StreamingResponse:
    """
    Return a ready-to-fill template containing the headers and one or two
    example rows.
    """
    spec = _require_spec(resource_type)
    frame = _template_frame(resource_type)

    if fmt == "csv":
        payload = frame.to_csv(index=False).encode("utf-8-sig")
        return StreamingResponse(
            io.BytesIO(payload),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{spec.filename}"'
            },
        )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=resource_type)
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{spec.filename_stem or spec.resource_type}_template.xlsx"'
        },
    )


@router.get(
    "/types", response_model=list[TemplateInfo], summary="List importable resource types"
)
def list_import_types() -> list[TemplateInfo]:
    """
    Describe every supported import type, so the frontend can build its
    upload UI without hardcoding the column lists.
    """
    from app.import_specs import IMPORT_SPECS

    return [
        TemplateInfo(
            resource_type=spec.resource_type,
            filename=spec.filename,
            format="csv",
            columns=spec.columns,
            required_columns=spec.required,
            description=spec.description,
        )
        for spec in IMPORT_SPECS.values()
    ]
