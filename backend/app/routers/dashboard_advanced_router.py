"""
Advanced dashboard endpoints (B8 / SQL Server Stored Procedure).

All database access goes through `EXEC dbo.sp_Dashboard_*`; there is no ORM
query in this file.

Cost matters here because `order_items` holds 912,999 rows and every one of
these reports would scan it if written naively. Two decisions carry most of
the performance:

1. `revenue-by-store` and `top-stores` aggregate the `orders` table, not the
   line items. An order is the row; its `total_amount` is already the sum of
   its lines. Aggregating 18,260 orders instead of 912,999 lines is ~50x
   less work, and it counts orders correctly - counting view rows would
   report 912,999 "orders".

2. The two endpoints that need line detail (`revenue-by-category`,
   `forecast-vs-actual`) join `order_items` directly rather than reading
   `v_daily_sales`. The view aggregates on
   (store_id, order_date, product_id), but `order_items` carries UNIQUE
   (order_id, product_id) - exactly one line exists per order/product pair,
   so that GROUP BY can only ever return the rows it was given.

Prices are MOCK values assigned per product group - the Kaggle dataset has no
price column. See AGENTS.md; never present these as real money.
"""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
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
    return 0.0 if value is None else float(value)


@router.get(
    "/revenue-by-store",
    response_model=list[RevenueByStore],
    summary="Revenue and order count per store",
)
def revenue_by_store(
    db: DbSession = Depends(get_db),
    from_date: date | None = Query(None, description="Inclusive start day"),
    to_date: date | None = Query(None, description="Inclusive end day"),
) -> list[RevenueByStore]:
    """
    Revenue split by store, largest first.

    `avg_order_value` is revenue divided by order count, not by line count -
    an order containing 50 products is one sale of one basket, and dividing
    by 50 would understate it fiftyfold.
    """
    _validate_range(from_date, to_date)
    try:
        rows = db.rows(
            "sp_Dashboard_RevenueByStore",
            {"FromDate": from_date, "ToDate": to_date, "Limit": None},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return [
        RevenueByStore(
            store_id=r["store_id"],
            store_code=r["store_code"],
            store_name=r["store_name"],
            total_revenue=_f(r["total_revenue"]),
            total_orders=int(r["total_orders"] or 0),
            total_quantity=_f(r["total_quantity"]),
            avg_order_value=_f(r["avg_order_value"]),
        )
        for r in rows
    ]


@router.get(
    "/top-stores",
    response_model=list[RevenueByStore],
    summary="Stores ranked by revenue",
)
def top_stores(
    db: DbSession = Depends(get_db),
    limit: int = Query(5, ge=1, le=100, description="How many stores to return"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
) -> list[RevenueByStore]:
    """
    The highest-revenue stores.

    Shares its procedure with `/revenue-by-store` - the sort and the TOP
    happen in SQL, so asking for 5 rows does not materialise all 10.
    """
    _validate_range(from_date, to_date)
    try:
        rows = db.rows(
            "sp_Dashboard_RevenueByStore",
            {"FromDate": from_date, "ToDate": to_date, "Limit": limit},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return [
        RevenueByStore(
            store_id=r["store_id"],
            store_code=r["store_code"],
            store_name=r["store_name"],
            total_revenue=_f(r["total_revenue"]),
            total_orders=int(r["total_orders"] or 0),
            total_quantity=_f(r["total_quantity"]),
            avg_order_value=_f(r["avg_order_value"]),
        )
        for r in rows
    ]


@router.get(
    "/revenue-by-category",
    response_model=list[RevenueByCategory],
    summary="Revenue split by product category",
)
def revenue_by_category(
    db: DbSession = Depends(get_db),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
) -> list[RevenueByCategory]:
    """
    Revenue per category, largest first.

    `line_total` is the database's generated column, so the procedure uses
    the database's own arithmetic instead of re-implementing the formula.
    The filter mirrors `v_daily_sales` (completed sales only) so the two
    stay consistent. A category with no products (Food) simply does not
    appear - an inner join drops it, which is correct.
    """
    _validate_range(from_date, to_date)
    try:
        rows = db.rows(
            "sp_Dashboard_RevenueByCategory",
            {"FromDate": from_date, "ToDate": to_date},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return [
        RevenueByCategory(
            category_id=r["category_id"],
            category_name=r["category_name"],
            total_revenue=_f(r["total_revenue"]),
            total_quantity=_f(r["total_quantity"]),
            product_count=int(r["product_count"] or 0),
        )
        for r in rows
    ]


@router.get(
    "/inventory-value",
    response_model=list[InventoryValue],
    summary="Stock valuation per store",
)
def inventory_value(
    db: DbSession = Depends(get_db),
    include_empty: bool = Query(
        False, description="Include stores with no stock left"
    ),
) -> list[InventoryValue]:
    """
    Value the remaining stock per store.

    Valued at `products.unit_cost` rather than `selling_price`: this answers
    "what is the stock worth to us", and the cost basis is also the figure
    used for the waste estimate below.

    `expiring_value` is computed in the same aggregate with a conditional
    SUM, so no second query is needed per store.
    """
    try:
        rows = db.rows(
            "sp_Dashboard_InventoryValue", {"IncludeEmpty": 1 if include_empty else 0}
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return [
        InventoryValue(
            store_id=r["store_id"],
            store_code=r["store_code"],
            store_name=r["store_name"],
            total_items=_f(r["total_items"]),
            total_batches=int(r["total_batches"] or 0),
            total_value=_f(r["total_value"]),
            expiring_value=_f(r["expiring_value"]),
        )
        for r in rows
    ]


@router.get(
    "/waste-analysis",
    response_model=dict,
    summary="Expired and expiring stock, with an estimated loss",
)
def waste_analysis(
    db: DbSession = Depends(get_db),
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
    try:
        sets = db.call(
            "sp_Dashboard_WasteAnalysis",
            {"IncludeBatches": 1 if include_batches else 0, "Limit": limit},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    summary_row = sets[0][0] if sets and sets[0] else {}
    expired_rows = sets[1] if len(sets) > 1 else []
    expiring_rows = sets[2] if len(sets) > 2 else []

    summary = WasteSummary(
        expired_batches=int(summary_row.get("expired_batches") or 0),
        expired_items=round(_f(summary_row.get("expired_items")), 3),
        expired_value=round(_f(summary_row.get("expired_value")), 2),
        expiring_batches=int(summary_row.get("expiring_batches") or 0),
        expiring_items=round(_f(summary_row.get("expiring_items")), 3),
        expiring_value=round(_f(summary_row.get("expiring_value")), 2),
        estimated_waste_value=round(
            _f(summary_row.get("estimated_waste_value")), 2
        ),
    )

    payload = {
        **summary.model_dump(),
        "window_days": EXPIRING_WINDOW_DAYS,
        "as_of": date.today().isoformat(),
    }

    def _batch(row: dict, state: str) -> dict:
        return WasteBatch(
            inventory_id=row["inventory_id"],
            store_id=row["store_id"],
            store_name=row["store_name"],
            product_id=row["product_id"],
            product_code=row["product_code"],
            product_name=row["product_name"],
            expiry_date=row["expiry_date"],
            days_to_expiry=int(row["days_to_expiry"] or 0),
            quantity=_f(row["quantity"]),
            value=_f(row["value"]),
            state=state,
        ).model_dump(mode="json")

    if include_batches:
        payload["expired_detail"] = [_batch(r, "expired") for r in expired_rows]
        payload["expiring_detail"] = [
            _batch(r, "expiring_soon") for r in expiring_rows
        ]
    return payload


@router.get(
    "/forecast-vs-actual",
    response_model=ForecastVsActualResponse,
    summary="Compare stored forecasts against actual sales",
)
def forecast_vs_actual(
    db: DbSession = Depends(get_db),
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

    The procedure matches a forecast to its actual by joining `forecasts` to
    `orders`/`order_items` on (store_id, product_id, date) directly rather
    than through `v_daily_sales`, for the same reason as
    `/revenue-by-category`: the view's extra GROUP BY costs a Sort plus a
    GroupAggregate over 912,999 rows and cannot change the result.

    The actual-sales window is CLAMPED to the forecast window. Actual sales
    from outside the forecast horizon can never match a forecast, so
    counting them is both wasted work and a misleading number in the
    response.

    Forecasts exist only for the 30 days after the training cut-off
    (2018-01-01 to 2018-01-30) while sales end at 2017-12-31, so today the
    join matches nothing. That is a property of the dataset, not a failure -
    `matched_rows` will be 0 and the accuracy fields None, with an
    explanation in `message`.

    MAPE is skipped when the actual is 0: |error| / 0 is undefined and
    dividing would produce an infinity that poisons the mean.
    """
    _validate_range(from_date, to_date)

    window_start, window_end = from_date, to_date

    try:
        sets = db.call(
            "sp_Dashboard_ForecastVsActual",
            {
                "ModelName": model_name,
                "FromDate": from_date,
                "ToDate": to_date,
                "ProductId": product_id,
                "StoreId": store_id,
                "IncludeDetail": 1 if include_detail else 0,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    counts = sets[0][0] if sets and sets[0] else {}
    agg = sets[1][0] if len(sets) > 1 and sets[1] else {}
    detail_rows = sets[2] if len(sets) > 2 else []

    forecast_rows = int(counts.get("forecast_rows") or 0)
    actual_rows = int(counts.get("actual_rows") or 0)
    matched_rows = int(counts.get("matched_rows") or 0)

    mape = mae = bias = rmse = None
    zero_actual_rows = 0
    if matched_rows:
        mape = agg.get("mape")
        mae = agg.get("mae")
        bias = agg.get("bias")
        squared = _f(agg.get("squared_error_sum"))
        rmse = squared ** 0.5
        zero_actual_rows = int(agg.get("zero_actual_rows") or 0)

    accuracy = ForecastAccuracy(
        model_name=model_name,
        matched_days=matched_rows,
        mape=round(_f(mape), 4) if mape is not None else None,
        mae=round(_f(mae), 4) if mae is not None else None,
        rmse=round(rmse, 4) if rmse is not None else None,
        bias=round(_f(bias), 4) if bias is not None else None,
    )

    comparison = [
        ForecastComparison(
            store_id=r["store_id"],
            product_id=r["product_id"],
            product_code=r["product_code"],
            product_name=r["product_name"],
            date=r["forecast_date"],
            predicted_quantity=_f(r["predicted_quantity"]),
            actual_quantity=_f(r["actual_quantity"]),
            error=_f(r["error"]),
            abs_percentage_error=round(_f(r["abs_percentage_error"]), 4),
        )
        for r in detail_rows
    ]
    truncated = matched_rows > MAX_COMPARISON_ROWS

    if matched_rows:
        message = f"Compared {matched_rows} row(s) for model '{model_name}'."
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
        forecast_rows=forecast_rows,
        actual_rows=actual_rows,
        matched_rows=matched_rows,
        accuracy=accuracy,
        comparison=comparison,
        comparison_truncated=truncated,
        message=message,
    )
