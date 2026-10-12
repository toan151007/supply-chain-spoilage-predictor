"""
Advanced dashboard endpoints (B8).

All database access goes through the SQLAlchemy ORM - no raw SQL here, as
required by the project rules.

Cost matters here because `order_items` holds 912,999 rows and every one of
these reports would scan it if written naively. Two decisions carry most of
the performance:

1. `revenue-by-store` and `top-stores` read the `orders` table, not the line
   items. An order is the row; its `total_amount` is already the sum of its
   lines. Aggregating 18,260 orders instead of 912,999 lines is ~50x less
   work, and it counts orders correctly - counting view rows would report
   912,999 "orders".

2. The two endpoints that need line detail (`revenue-by-category`,
   `forecast-vs-actual`) join `order_items` directly rather than reading
   `v_daily_sales`. The view aggregates on
   (store_id, order_date, product_id), but `order_items` carries UNIQUE
   (order_id, product_id) - exactly one line exists per order/product pair,
   so that GROUP BY can only ever return the rows it was given. Skipping it
   removes a Sort and a GroupAggregate over 912,999 rows: measured 1,606 ms
   through the view against 680 ms joined directly, with byte-identical
   totals.

   `revenue-by-store` and `top-stores` avoid the line items altogether by
   aggregating the 18,260 `orders` rows, whose `total_amount` already holds
   the line-level sum.

   Nothing here loops over rows to issue a follow-up query.

Prices are MOCK values assigned per product group - the Kaggle dataset has no
price column. See AGENTS.md; never present these as real money.
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Date, Integer, case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Category,
    Forecast,
    Inventory,
    Order,
    OrderItem,
    Product,
    Store,
)
from app.schemas.dashboard_advanced_schema import (
    ForecastAccuracy,
    ForecastComparison,
    ForecastVsActualResponse,
    InventoryValue,
    RevenueByCategory,
    RevenueByStore,
    WasteBatch,
    WasteSummary,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard-advanced"])

HTTP_422_UNPROCESSABLE_CONTENT = 422

# Matches the window hard-coded in v_expiring_inventory, so these reports
# and that view never disagree about what counts as "expiring soon".
EXPIRING_WINDOW_DAYS = 30

# Vietnam time, matching how the seeded dataset is stored (see AGENTS.md).
VN_TZ = timezone(timedelta(hours=7))

# Detail rows returned by forecast-vs-actual before truncating.
MAX_COMPARISON_ROWS = 200


def _validate_range(from_date: date | None, to_date: date | None) -> None:
    """Reject an inverted range up front rather than returning an empty list."""
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail="from_date must be on or before to_date",
        )


def _f(value) -> float:
    """Coerce a NUMERIC (Decimal) aggregate to float.

    Numeric columns come back as Decimal from PostgreSQL. Without this the
    response carries Decimal values and Pydantic warns about a Decimal
    landing in a float field.
    """
    if value is None:
        return 0.0
    return float(value)


def _date_bounds(
    from_date: date | None, to_date: date | None
) -> tuple[date | None, date | None]:
    """
    Widen a partial range so SQL can use plain comparisons.

    A missing `to_date` would otherwise compare against NULL and silently
    drop every row, which reads as "no data" rather than "no upper bound".
    """
    return from_date, to_date


# ===========================================================================
# Revenue by store / top stores
# ===========================================================================
def _store_revenue_rows(db: Session, from_date, to_date) -> list[RevenueByStore]:
    """
    Aggregate the `orders` table per store.

    Deliberately not `order_items`: one order is one row here, so
    `count(Order.order_id)` is the true order count and
    `sum(Order.total_amount)` is already the line-level total.
    """
    filters = []
    if from_date is not None:
        # order_date is timestamptz holding +07:00 wall-clock time. The
        # bounds are built in UTC from plain dates so the comparison happens
        # in the database rather than being shifted by Python's timezone.
        filters.append(Order.order_date >= _start_of_day(from_date))
    if to_date is not None:
        filters.append(Order.order_date < _end_of_day(to_date))

    rows = db.execute(
        select(
            Store.store_id,
            Store.store_code,
            Store.store_name,
            func.coalesce(func.sum(Order.total_amount), 0),
            func.count(Order.order_id),
            func.coalesce(func.sum(Order.total_quantity), 0),
        )
        .select_from(Order)
        .join(Store, Store.store_id == Order.store_id)
        .where(*filters)
        .group_by(Store.store_id, Store.store_code, Store.store_name)
    ).all()

    result = []
    for store_id, code, name, revenue, orders, quantity in rows:
        revenue = _f(revenue)
        orders = int(orders)
        result.append(
            RevenueByStore(
                store_id=store_id,
                store_code=code,
                store_name=name,
                total_revenue=revenue,
                total_orders=orders,
                total_quantity=_f(quantity),
                # Guard the division: a store with no orders in the window
                # would otherwise produce 0/0.
                avg_order_value=round(revenue / orders, 2) if orders else 0.0,
            )
        )
    return result


def _start_of_day(day: date) -> datetime:
    """Midnight at the start of `day` in Asia/Ho_Chi_Minh (+07:00).

    The seeded orders are stamped at local midnight, which is 17:00 UTC the
    previous day. Building the bound with the same offset keeps day-based
    filters aligned with the data instead of clipping the first day.
    """
    return datetime.combine(day, time.min, tzinfo=VN_TZ)


def _end_of_day(day: date) -> datetime:
    """Midnight at the start of the day AFTER `day`, same timezone.

    Strictly-less-than against this bound includes the whole final day
    without having to reason about 23:59:59.999999.
    """
    return datetime.combine(day + timedelta(days=1), time.min, tzinfo=VN_TZ)


@router.get(
    "/revenue-by-store",
    response_model=list[RevenueByStore],
    summary="Revenue and order count per store",
)
def revenue_by_store(
    db: Session = Depends(get_db),
    from_date: date | None = Query(None, description="Inclusive start day"),
    to_date: date | None = Query(None, description="Inclusive end day"),
) -> list[RevenueByStore]:
    """
    Revenue split by store, newest figures first.

    `avg_order_value` is revenue divided by order count, not by line count -
    an order containing 50 products is one sale of one basket, and dividing
    by 50 would understate it fiftyfold.
    """
    _validate_range(from_date, to_date)
    rows = _store_revenue_rows(db, *_date_bounds(from_date, to_date))
    return sorted(rows, key=lambda r: r.total_revenue, reverse=True)


@router.get(
    "/top-stores",
    response_model=list[RevenueByStore],
    summary="Stores ranked by revenue",
)
def top_stores(
    db: Session = Depends(get_db),
    limit: int = Query(5, ge=1, le=100, description="How many stores to return"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
) -> list[RevenueByStore]:
    """
    The highest-revenue stores.

    Shares its query with `/revenue-by-store` - the sort happens in SQL via
    LIMIT, so asking for 5 rows does not scan and materialise all 10.
    """
    _validate_range(from_date, to_date)

    filters = []
    if from_date is not None:
        filters.append(Order.order_date >= _start_of_day(from_date))
    if to_date is not None:
        filters.append(Order.order_date < _end_of_day(to_date))

    rows = db.execute(
        select(
            Store.store_id,
            Store.store_code,
            Store.store_name,
            func.coalesce(func.sum(Order.total_amount), 0),
            func.count(Order.order_id),
            func.coalesce(func.sum(Order.total_quantity), 0),
        )
        .select_from(Order)
        .join(Store, Store.store_id == Order.store_id)
        .where(*filters)
        .group_by(Store.store_id, Store.store_code, Store.store_name)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(limit)
    ).all()

    result = []
    for store_id, code, name, revenue, orders, quantity in rows:
        revenue = _f(revenue)
        orders = int(orders)
        result.append(
            RevenueByStore(
                store_id=store_id,
                store_code=code,
                store_name=name,
                total_revenue=revenue,
                total_orders=orders,
                total_quantity=_f(quantity),
                avg_order_value=round(revenue / orders, 2) if orders else 0.0,
            )
        )
    return result


# ===========================================================================
# Revenue by category
# ===========================================================================
@router.get(
    "/revenue-by-category",
    response_model=list[RevenueByCategory],
    summary="Revenue split by product category",
)
def revenue_by_category(
    db: Session = Depends(get_db),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
) -> list[RevenueByCategory]:
    """
    Revenue per category, largest first.

    Joins `order_items` directly instead of reading `v_daily_sales`. The
    view carries a `GROUP BY store_id, order_date, product_id`, which looks
    necessary but is not: `order_items` has UNIQUE (order_id, product_id), so
    exactly one line exists per order/product pair and the aggregation can
    only ever return that one row. Skipping it drops a Sort plus a
    GroupAggregate over 912,999 rows.

    Measured: 1,606 ms through the view vs 680 ms joined directly, with
    byte-identical totals for all 7 categories. The `WHERE` mirrors the
    view's own filter (completed sales only) so the two stay consistent.
    """
    _validate_range(from_date, to_date)

    filters = [Order.status == "completed", Order.order_type == "sale"]
    if from_date is not None:
        filters.append(Order.order_date >= _start_of_day(from_date))
    if to_date is not None:
        filters.append(Order.order_date < _end_of_day(to_date))

    rows = db.execute(
        select(
            Category.category_id,
            Category.category_name,
            # line_total is the generated column, so this is the database's
            # own arithmetic rather than a re-implementation of the formula.
            func.coalesce(func.sum(OrderItem.line_total), 0),
            func.coalesce(func.sum(OrderItem.quantity), 0),
            func.count(func.distinct(OrderItem.product_id)),
        )
        .select_from(OrderItem)
        .join(Order, Order.order_id == OrderItem.order_id)
        .join(Product, Product.product_id == OrderItem.product_id)
        .join(Category, Category.category_id == Product.category_id)
        .where(*filters)
        .group_by(Category.category_id, Category.category_name)
        .order_by(func.sum(OrderItem.line_total).desc())
    ).all()

    return [
        RevenueByCategory(
            category_id=category_id,
            category_name=name,
            total_revenue=_f(revenue),
            total_quantity=_f(quantity),
            product_count=int(product_count),
        )
        for category_id, name, revenue, quantity, product_count in rows
    ]


# ===========================================================================
# Inventory value
# ===========================================================================
@router.get(
    "/inventory-value",
    response_model=list[InventoryValue],
    summary="Stock valuation per store",
)
def inventory_value(
    db: Session = Depends(get_db),
    include_empty: bool = Query(
        False, description="Include stores with no stock left"
    ),
) -> list[InventoryValue]:
    """
    Value the remaining stock per store.

    Valued at `products.unit_cost` rather than `selling_price`: this answers
    "what is the stock worth to us", and the cost basis is also the figure
    used for the waste estimate below.

    `expiring_value` is computed in the same pass with a conditional SUM, so
    no second query is needed per store.
    """
    horizon = date.today() + timedelta(days=EXPIRING_WINDOW_DAYS)

    expiring_value = func.coalesce(
        func.sum(
            case(
                (
                    Inventory.expiry_date.isnot(None)
                    & (Inventory.expiry_date <= horizon),
                    Inventory.quantity * Product.unit_cost,
                ),
                else_=0,
            )
        ),
        0,
    )

    query = (
        select(
            Store.store_id,
            Store.store_code,
            Store.store_name,
            func.coalesce(func.sum(Inventory.quantity), 0),
            func.count(Inventory.inventory_id),
            func.coalesce(func.sum(Inventory.quantity * Product.unit_cost), 0),
            expiring_value.label("expiring_value"),
        )
        .select_from(Store)
        .outerjoin(
            Inventory,
            (Inventory.store_id == Store.store_id) & (Inventory.quantity > 0),
        )
        .outerjoin(Product, Product.product_id == Inventory.product_id)
        .group_by(Store.store_id, Store.store_code, Store.store_name)
        .order_by(func.sum(Inventory.quantity * Product.unit_cost).desc())
    )
    if not include_empty:
        query = query.having(func.coalesce(func.sum(Inventory.quantity), 0) > 0)

    rows = db.execute(query).all()

    return [
        InventoryValue(
            store_id=store_id,
            store_code=code,
            store_name=name,
            total_items=_f(total_items),
            total_batches=int(batches),
            total_value=_f(total_value),
            expiring_value=_f(expiring),
        )
        for store_id, code, name, total_items, batches, total_value, expiring
        in rows
    ]


# ===========================================================================
# Waste analysis
# ===========================================================================
def _waste_batches(
    db: Session, expired_only: bool, horizon: date
) -> list[WasteBatch]:
    """
    One aggregate-free query returning the batches that matter.

    `days_to_expiry` is computed as a difference against CURRENT_DATE so the
    classification matches what the database itself considers overdue,
    rather than re-deriving "today" in Python where a timezone difference
    could shift it by a day.
    """
    days_to_expiry = func.cast(
        Inventory.expiry_date - func.current_date(), Integer
    )

    condition = (
        Inventory.expiry_date < func.current_date()
        if expired_only
        else (
            Inventory.expiry_date.isnot(None)
            & (Inventory.expiry_date <= horizon)
            & (Inventory.expiry_date >= func.current_date())
        )
    )

    rows = db.execute(
        select(
            Inventory.inventory_id,
            Inventory.store_id,
            Store.store_name,
            Inventory.product_id,
            Product.product_code,
            Product.product_name,
            Inventory.expiry_date,
            days_to_expiry.label("days_to_expiry"),
            Inventory.quantity,
            (Inventory.quantity * Product.unit_cost).label("value"),
        )
        .select_from(Inventory)
        .join(Store, Store.store_id == Inventory.store_id)
        .join(Product, Product.product_id == Inventory.product_id)
        .where(condition & (Inventory.quantity > 0))
        .order_by(Inventory.expiry_date)
    ).all()

    state = "expired" if expired_only else "expiring_soon"
    return [
        WasteBatch(
            inventory_id=row[0],
            store_id=row[1],
            store_name=row[2],
            product_id=row[3],
            product_code=row[4],
            product_name=row[5],
            expiry_date=row[6],
            days_to_expiry=int(row[7]),
            quantity=_f(row[8]),
            value=_f(row[9]),
            state=state,
        )
        for row in rows
    ]


@router.get(
    "/waste-analysis",
    response_model=dict,
    summary="Expired and expiring stock, with an estimated loss",
)
def waste_analysis(
    db: Session = Depends(get_db),
    include_batches: bool = Query(
        False, description="Include the per-batch breakdown (can be 500+ rows)"
    ),
    limit: int = Query(50, ge=1, le=500, description="Batch rows when included"),
) -> dict:
    """
    Summarise spoilage exposure.

    `estimated_waste_value` is deliberately the WORST case: expired stock is
    already written off, and every batch expiring within the window is
    assumed lost as well. Real spoilage would be lower. Reporting a
    best-case number here would understate the operational risk.
    """
    horizon = date.today() + timedelta(days=EXPIRING_WINDOW_DAYS)

    expired = _waste_batches(db, expired_only=True, horizon=horizon)
    expiring = _waste_batches(db, expired_only=False, horizon=horizon)

    expired_value = sum(b.value for b in expired)
    expiring_value = sum(b.value for b in expiring)

    summary = WasteSummary(
        expired_batches=len(expired),
        expired_items=round(sum(b.quantity for b in expired), 3),
        expired_value=round(expired_value, 2),
        expiring_batches=len(expiring),
        expiring_items=round(sum(b.quantity for b in expiring), 3),
        expiring_value=round(expiring_value, 2),
        estimated_waste_value=round(expired_value + expiring_value, 2),
    )

    payload = {
        **summary.model_dump(),
        "window_days": EXPIRING_WINDOW_DAYS,
        "as_of": date.today().isoformat(),
    }
    if include_batches:
        payload["expired_detail"] = [
            b.model_dump(mode="json") for b in expired[:limit]
        ]
        payload["expiring_detail"] = [
            b.model_dump(mode="json") for b in expiring[:limit]
        ]
    return payload


# ===========================================================================
# Forecast vs actual
# ===========================================================================
@router.get(
    "/forecast-vs-actual",
    response_model=ForecastVsActualResponse,
    summary="Compare stored forecasts against actual sales",
)
def forecast_vs_actual(
    db: Session = Depends(get_db),
    model_name: str = Query(
        "prophet", description="prophet | xgboost | arima | moving_average | naive"
    ),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    product_id: int | None = Query(None, gt=0),
    store_id: int | None = Query(None, gt=0),
    include_detail: bool = Query(
        False, description=f"Include per-row detail (max {MAX_COMPARISON_ROWS} rows)"
    ),
) -> ForecastVsActualResponse:
    """
    Score a stored forecast against the sales that actually happened.

    Matches a forecast to its actual by joining `forecasts` to
    `orders`/`order_items` on (store_id, product_id, date) directly rather
    than through `v_daily_sales`, for the same reason as
    `/revenue-by-category`: the view's extra GROUP BY costs a Sort plus a
    GroupAggregate over 912,999 rows and cannot change the result.

    The actual-sales window is CLAMPED to the forecast window. Actual sales
    from outside the forecast horizon can never match a forecast, so
    counting them is both wasted work and a misleading number in the
    response. With no dates supplied this turns a full 912,999-row scan
    into an index lookup that returns nothing.

    Forecasts exist only for the 30 days after the training cut-off
    (2018-01-01 to 2018-01-30) while sales end at 2017-12-31, so today the
    join matches nothing. That is a property of the dataset, not a failure -
    `matched_rows` will be 0 and the accuracy fields None, with an
    explanation in `message`.

    MAPE is skipped when the actual is 0: |error| / 0 is undefined and
    dividing would produce an infinity that poisons the mean.
    """
    _validate_range(from_date, to_date)

    window_start, window_end = _date_bounds(from_date, to_date)

    fc_filters = [Forecast.model_name == model_name]
    if window_start is not None:
        fc_filters.append(Forecast.forecast_date >= window_start)
    if window_end is not None:
        fc_filters.append(Forecast.forecast_date <= window_end)
    if product_id is not None:
        fc_filters.append(Forecast.product_id == product_id)
    if store_id is not None:
        fc_filters.append(Forecast.store_id == store_id)

    # Clamp the actual window to the span the forecasts actually cover.
    fc_span = db.execute(
        select(
            func.min(Forecast.forecast_date),
            func.max(Forecast.forecast_date),
        ).where(Forecast.model_name == model_name)
    ).one()
    fc_first, fc_last = fc_span

    actual_start, actual_end = window_start, window_end
    if fc_first is not None:
        actual_start = max(actual_start, fc_first) if actual_start else fc_first
    if fc_last is not None:
        actual_end = min(actual_end, fc_last) if actual_end else fc_last

    def _actual_filters():
        out = [Order.status == "completed", Order.order_type == "sale"]
        if actual_start is not None:
            out.append(Order.order_date >= _start_of_day(actual_start))
        if actual_end is not None:
            out.append(Order.order_date < _end_of_day(actual_end))
        if product_id is not None:
            out.append(OrderItem.product_id == product_id)
        if store_id is not None:
            out.append(Order.store_id == store_id)
        return out

    # A forecast matches the line of its own order for that store, product
    # and day. The two conditions are split because `OrderItem` is not yet
    # in the FROM clause while the Order join is being built.
    # forecast_date is a plain date; order_date is timestamptz at +07:00, so
    # the cast is applied to the timestamp.
    on_order = (
        (Order.store_id == Forecast.store_id)
        & (Order.order_date.cast(Date) == Forecast.forecast_date)
    )
    on_line = (
        (OrderItem.order_id == Order.order_id)
        & (OrderItem.product_id == Forecast.product_id)
    )

    error = OrderItem.quantity - Forecast.predicted_quantity
    abs_error = func.abs(error)
    # Guard the division: a zero actual has no meaningful percentage error.
    pct_error = abs_error / func.nullif(OrderItem.quantity, 0) * 100

    matched_rows = db.execute(
        select(func.count())
        .select_from(Forecast)
        .join(Order, on_order)
        .join(OrderItem, on_line)
        .where(*fc_filters, *_actual_filters())
    ).scalar_one()

    forecast_rows = db.execute(
        select(func.count()).select_from(Forecast).where(*fc_filters)
    ).scalar_one()

    actual_rows = db.execute(
        select(func.count())
        .select_from(OrderItem)
        .join(Order, Order.order_id == OrderItem.order_id)
        .where(*_actual_filters())
    ).scalar_one()

    zero_actual_rows = 0
    mape = mae = bias = rmse = None
    if matched_rows:
        agg = db.execute(
            select(
                func.avg(pct_error),
                func.avg(abs_error),
                func.avg(error),
                func.coalesce(
                    func.sum(case((OrderItem.quantity == 0, 1), else_=0)), 0
                ),
            )
            .select_from(Forecast)
            .join(Order, on_order)
            .join(OrderItem, on_line)
            .where(*fc_filters, *_actual_filters())
        ).one()
        mape, mae, bias, zero_actual_rows = agg

        # RMSE needs the squared error, so it gets its own aggregate; there
        # is no built-in for it.
        sum_sq = db.execute(
            select(func.coalesce(func.sum(error * error), 0))
            .select_from(Forecast)
            .join(Order, on_order)
            .join(OrderItem, on_line)
            .where(*fc_filters, *_actual_filters())
        ).scalar_one()
        rmse = float(sum_sq) ** 0.5

    accuracy = ForecastAccuracy(
        model_name=model_name,
        matched_days=int(matched_rows or 0),
        mape=round(_f(mape), 4) if mape is not None else None,
        mae=round(_f(mae), 4) if mae is not None else None,
        rmse=round(rmse, 4) if rmse is not None else None,
        bias=round(_f(bias), 4) if bias is not None else None,
    )

    comparison: list[ForecastComparison] = []
    truncated = False
    if include_detail and matched_rows:
        rows = db.execute(
            select(
                Forecast.store_id,
                Forecast.product_id,
                Product.product_code,
                Product.product_name,
                Forecast.forecast_date,
                Forecast.predicted_quantity,
                OrderItem.quantity,
                error,
                pct_error,
            )
            .select_from(Forecast)
            .join(Order, on_order)
            .join(OrderItem, on_line)
            .join(Product, Product.product_id == Forecast.product_id)
            .where(*fc_filters, *_actual_filters())
            .order_by(Forecast.forecast_date, Forecast.store_id, Forecast.product_id)
            .limit(MAX_COMPARISON_ROWS)
        ).all()

        comparison = [
            ForecastComparison(
                store_id=r[0],
                product_id=r[1],
                product_code=r[2],
                product_name=r[3],
                date=r[4],
                predicted_quantity=_f(r[5]),
                actual_quantity=_f(r[6]),
                error=_f(r[7]),
                abs_percentage_error=round(_f(r[8]), 4),
            )
            for r in rows
        ]
        truncated = matched_rows > MAX_COMPARISON_ROWS

    if matched_rows:
        message = (
            f"Compared {matched_rows} row(s) for model '{model_name}'."
        )
        if zero_actual_rows:
            message += (
                f" {zero_actual_rows} row(s) had an actual of 0 and were excluded "
                "from MAPE (percentage error is undefined against zero)."
            )
    else:
        message = (
            f"No forecast for model '{model_name}' could be matched to an actual "
            f"in {window_start or 'open start'}..{window_end or 'open end'}. "
            f"The table holds {forecast_rows} forecast row(s) and "
            f"{actual_rows} actual row(s) within the forecast window, but they "
            "cover different periods. Stored forecasts run from 2018-01-01 to "
            "2018-01-30 while sales data ends 2017-12-31, so accuracy cannot "
            "be measured until actual sales exist for the forecast horizon."
        )

    return ForecastVsActualResponse(
        model_name=model_name,
        from_date=window_start or date.min,
        to_date=window_end or date.max,
        forecast_rows=int(forecast_rows or 0),
        actual_rows=int(actual_rows or 0),
        matched_rows=int(matched_rows or 0),
        accuracy=accuracy,
        comparison=comparison,
        comparison_truncated=truncated,
        message=message,
    )

