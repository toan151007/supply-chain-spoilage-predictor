"""
Dashboard aggregation endpoints (B5 / SQL Server Stored Procedure).

Design notes
------------
* Every figure is computed by SQL Server with SUM / COUNT / GROUP BY inside
  a stored procedure. No row reaches Python before it has been aggregated.
* Read-only views are used where one already does the work
  (`v_low_stock`, `v_expiring_inventory`, `v_product_stock_summary`).
* All access goes through `EXEC dbo.sp_Dashboard_*`; there is no ORM query
  in this file.

WARNING - PRICES ARE SIMULATED
------------------------------
The Kaggle dataset has no price column, so prices were assigned per product
category to make a revenue dashboard possible at all. `total_revenue` and
`total_inventory_value` are therefore NOT real money and must not be
presented as such in the report.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.schemas.dashboard_schema import (
    AlertsSummaryResponse,
    ExpiringResponse,
    LowStockResponse,
    OverviewResponse,
    RevenuePoint,
    RevenueResponse,
    SeverityCount,
    TopProductResponse,
    TypeCount,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# v_expiring_inventory hardcodes `expiry_date <= CURRENT_DATE + 30`, so a
# bigger window cannot widen the result. Exposing 30 as the maximum keeps
# the API honest instead of silently returning the same rows.
EXPIRING_VIEW_MAX_DAYS = 30

SEVERITY_ORDER = ["critical", "high", "medium", "low"]


def _f(value) -> float:
    return 0.0 if value is None else float(value)


@router.get("/overview", response_model=OverviewResponse, summary="Dashboard totals")
def dashboard_overview(db: DbSession = Depends(get_db)) -> OverviewResponse:
    """
    Headline figures for the home screen, aggregated in one procedure.

    `total_revenue` sums `orders.total_amount` directly - summing the same
    column across a join with `order_items` would multiply it by roughly 50,
    one row per product per order.
    """
    try:
        row = db.one("sp_Dashboard_Overview") or {}
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return OverviewResponse(
        total_revenue=_f(row.get("total_revenue")),
        total_orders=int(row.get("total_orders") or 0),
        total_products=int(row.get("total_products") or 0),
        total_stores=int(row.get("total_stores") or 0),
        total_inventory_value=_f(row.get("total_inventory_value")),
        total_alerts_unread=int(row.get("total_alerts_unread") or 0),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/revenue", response_model=RevenueResponse, summary="Revenue over time")
def dashboard_revenue(
    db: DbSession = Depends(get_db),
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    year: int | None = Query(
        None, ge=1900, le=2999,
        description="Restrict to one calendar year. Omit for all years.",
    ),
) -> RevenueResponse:
    """
    Revenue series grouped into day, week, month or year buckets.

    Buckets with no orders are omitted rather than filled with zero - a gap
    in the data should look like a gap, not a flat sales week.

    `year=2017` still returns one point per bucket inside 2017; the filter
    narrows the range, it does not collapse the range into a single bucket.
    """
    try:
        rows = db.rows("sp_Dashboard_Revenue", {"Period": period, "Year": year})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    points = [
        RevenuePoint(
            period_start=r["period_start"],
            revenue=_f(r["revenue"]),
            order_count=int(r["order_count"] or 0),
            total_quantity=_f(r["total_quantity"]),
        )
        for r in rows
    ]

    return RevenueResponse(
        period=period,
        year=year,
        total_revenue=sum(p.revenue for p in points),
        total_orders=sum(p.order_count for p in points),
        points=points,
    )


@router.get(
    "/top-products", response_model=list[TopProductResponse],
    summary="Best selling products",
)
def dashboard_top_products(
    db: DbSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    store_id: int | None = Query(None, gt=0),
    year: int | None = Query(None, ge=1900, le=2999),
) -> list[TopProductResponse]:
    """
    Products ranked by units sold.

    Ordering is by quantity first. Revenue is reported alongside for context
    but does not drive the ranking, because a cheap high-volume item should
    still rank above an expensive slow one for stock planning.
    """
    try:
        rows = db.rows(
            "sp_Dashboard_TopProducts",
            {"Limit": limit, "StoreId": store_id, "Year": year},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return [
        TopProductResponse(
            product_id=r["product_id"],
            product_code=r["product_code"],
            product_name=r["product_name"],
            unit=r["unit"],
            total_quantity=_f(r["total_quantity"]),
            total_revenue=_f(r["total_revenue"]),
        )
        for r in rows
    ]


@router.get(
    "/low-stock", response_model=list[LowStockResponse],
    summary="Products below minimum stock",
)
def dashboard_low_stock(
    db: DbSession = Depends(get_db),
    threshold: float = Query(
        20, ge=0,
        description="Only pairs whose shortage reaches this amount",
    ),
    store_id: int | None = Query(None, gt=0),
) -> list[LowStockResponse]:
    """
    Product-stock pairs below their minimum level.

    The view already applies `SUM(quantity) < min_stock` per pair, so this
    procedure only narrows the result further.

    `threshold` filters on `shortage`, which is `min_stock - total_quantity`
    - how many units are missing, not how many are on hand. Ranking by the
    gap is what a buyer acts on.
    """
    try:
        rows = db.rows(
            "sp_Dashboard_LowStock",
            {"Threshold": threshold, "StoreId": store_id},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return [
        LowStockResponse(
            store_id=r["store_id"],
            product_id=r["product_id"],
            product_code=r["product_code"],
            product_name=r["product_name"],
            unit=r["unit"],
            total_quantity=_f(r["total_quantity"]),
            min_stock=_f(r["min_stock"]),
            reorder_point=_f(r["reorder_point"]) if r["reorder_point"] is not None else None,
            shortage=_f(r["shortage"]),
        )
        for r in rows
    ]


@router.get(
    "/expiring", response_model=list[ExpiringResponse],
    summary="Batches near or past expiry",
)
def dashboard_expiring(
    db: DbSession = Depends(get_db),
    days: int = Query(
        7, ge=0, le=EXPIRING_VIEW_MAX_DAYS,
        description="Window in days, capped by the view",
    ),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
) -> list[ExpiringResponse]:
    """
    Batches expiring within the window, plus those already expired.

    `days = 0` returns only batches whose expiry date has passed, which is
    the cleanup view. Expired rows carry a negative `days_to_expiry`.

    The upper bound is 30 because `v_expiring_inventory` filters on
    `expiry_date <= CURRENT_DATE + 30` in its own WHERE clause. Passing
    more than 30 would silently return the same rows, so it is rejected
    with 422 instead.
    """
    try:
        rows = db.rows(
            "sp_Dashboard_Expiring",
            {"Days": days, "StoreId": store_id, "ProductId": product_id},
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    return [
        ExpiringResponse(
            inventory_id=r["inventory_id"],
            store_id=r["store_id"],
            product_id=r["product_id"],
            product_code=r["product_code"],
            product_name=r["product_name"],
            batch_code=r["batch_code"],
            quantity=_f(r["quantity"]),
            expiry_date=r["expiry_date"],
            days_to_expiry=int(r["days_to_expiry"] or 0),
            stock_value=_f(r["stock_value"]),
            alert_severity=r["alert_severity"],
        )
        for r in rows
    ]


@router.get(
    "/alerts-summary", response_model=AlertsSummaryResponse,
    summary="Alert counts by type and severity",
)
def dashboard_alerts_summary(
    db: DbSession = Depends(get_db),
    store_id: int | None = Query(None, gt=0),
) -> AlertsSummaryResponse:
    """
    Alert counts for a dashboard panel.

    The procedure returns three result sets - totals, counts by type and
    counts by severity - so the panel never pulls 518 full rows into Python
    just to call `len()`.

    Severity is ordered critical first so the UI shows the worst first, and
    missing buckets are filled with zero so the UI always renders all four.
    """
    try:
        sets = db.call("sp_Dashboard_AlertsSummary", {"StoreId": store_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    totals = sets[0][0] if sets and sets[0] else {}
    by_type_rows = sets[1] if len(sets) > 1 else []
    by_sev_rows = sets[2] if len(sets) > 2 else []

    severity_map = {r["severity"]: int(r["total"] or 0) for r in by_sev_rows}
    by_severity = [
        SeverityCount(severity=sev, count=severity_map.get(sev, 0))
        for sev in SEVERITY_ORDER
    ]

    return AlertsSummaryResponse(
        total=int(totals.get("total") or 0),
        unread=int(totals.get("unread") or 0),
        unresolved=int(totals.get("unresolved") or 0),
        critical_unread=int(totals.get("critical_unread") or 0),
        by_type=[
            TypeCount(
                alert_type=r["alert_type"],
                count=int(r["total"] or 0),
                unresolved=int(r["unresolved"] or 0),
            )
            for r in by_type_rows
        ],
        by_severity=by_severity,
    )
