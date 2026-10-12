"""
Dashboard aggregation endpoints.

Design notes
------------
* Every figure is computed by PostgreSQL with SUM / COUNT / GROUP BY. No
  row ever reaches Python before it has been aggregated, so these endpoints
  stay fast as the tables grow.
* Read-only views are used where one already does the work
  (`v_low_stock`, `v_expiring_inventory`, `v_product_stock_summary`).
* `Order` and `OrderItem` are mapped ORM classes, so those queries use
  `select()` on real models rather than raw SQL.

⚠️ PRICES ARE SIMULATED
----------------------
The Kaggle dataset has no price column, so prices were assigned per product
category to make a revenue dashboard possible at all. `total_revenue` and
`total_inventory_value` are therefore NOT real money and must not be
presented as such in the report.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, Order, OrderItem, Product, Store
from app.models.views import (
    v_expiring_inventory,
    v_low_stock,
    v_product_stock_summary,
)
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

# PostgreSQL date_trunc units. `week` starts on Monday.
PERIODS = {
    "day": "day",
    "week": "week",
    "month": "month",
    "year": "year",
}

# v_expiring_inventory hardcodes `expiry_date <= CURRENT_DATE + 30`, so a
# bigger window cannot widen the result. Exposing 30 as the maximum keeps
# the API honest instead of silently returning the same rows.
EXPIRING_VIEW_MAX_DAYS = 30

SEVERITY_ORDER = ["critical", "high", "medium", "low"]


@router.get("/overview", response_model=OverviewResponse, summary="Dashboard totals")
def dashboard_overview(db: Session = Depends(get_db)) -> OverviewResponse:
    """
    Headline figures for the home screen.

    Six small aggregate queries rather than one big join, so each stays an
    index-only scan. `total_revenue` uses SUM over `orders` directly -
    summing the same column across a join with `order_items` would multiply
    it by roughly 50, one row per product per order.
    """
    revenue, order_count = db.execute(
        select(
            func.coalesce(func.sum(Order.total_amount), 0),
            func.count(Order.order_id),
        )
    ).one()

    total_products = db.execute(
        select(func.count(Product.product_id)).where(Product.is_active.is_(True))
    ).scalar_one()

    total_stores = db.execute(
        select(func.count(Store.store_id)).where(Store.is_active.is_(True))
    ).scalar_one()

    # The view already multiplies quantity by unit_cost per batch.
    inventory_value = db.execute(
        select(
            func.coalesce(
                func.sum(v_product_stock_summary.c.total_stock_value), 0
            )
        )
    ).scalar_one()

    total_unread = db.execute(
        select(func.count(Alert.alert_id)).where(Alert.is_read.is_(False))
    ).scalar_one()

    return OverviewResponse(
        total_revenue=float(revenue or 0),
        total_orders=int(order_count or 0),
        total_products=int(total_products or 0),
        total_stores=int(total_stores or 0),
        total_inventory_value=float(inventory_value or 0),
        total_alerts_unread=int(total_unread or 0),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/revenue", response_model=RevenueResponse, summary="Revenue over time")
def dashboard_revenue(
    db: Session = Depends(get_db),
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    year: int | None = Query(
        None, ge=1900, le=2999,
        description="Restrict to one calendar year. Omit for all years.",
    ),
) -> RevenueResponse:
    """
    Revenue series grouped into day, week, month or year buckets.

    Uses `date_trunc`, which PostgreSQL supports for all four units. The
    year filter uses a half-open range `[year-01-01, year+1-01-01)` so a
    timestamp exactly at midnight on 1 January is included.

    Buckets with no orders are omitted rather than filled with zero - a gap
    in the data should look like a gap, not a flat sales week.
    """
    bucket = func.date_trunc(PERIODS[period], Order.order_date)

    conditions = []
    if year is not None:
        conditions.append(Order.order_date >= datetime(year, 1, 1))
        conditions.append(Order.order_date < datetime(year + 1, 1, 1))

    rows = db.execute(
        select(
            bucket.label("period_start"),
            func.coalesce(func.sum(Order.total_amount), 0),
            func.count(Order.order_id),
            func.coalesce(func.sum(Order.total_quantity), 0),
        )
        .where(*conditions)
        .group_by(bucket)
        .order_by(bucket)
    ).all()

    points = [
        RevenuePoint(
            period_start=r.period_start.date(),
            revenue=float(r[1] or 0),
            order_count=int(r[2] or 0),
            total_quantity=float(r[3] or 0),
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
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    store_id: int | None = Query(None, gt=0),
    year: int | None = Query(None, ge=1900, le=2999),
) -> list[TopProductResponse]:
    """
    Products ranked by units sold.

    `order_items` holds 912,999 rows, so the join and the GROUP BY both run
    in PostgreSQL. `idx_order_items_product_id` and `idx_orders_store_date`
    keep this from becoming a sequential scan when filtered.

    Ordering is by quantity first. Revenue is reported alongside for context
    but does not drive the ranking, because a cheap high-volume item should
    still rank above an expensive slow one for stock planning.
    """
    conditions = [Order.order_type == "sale"]
    if store_id is not None:
        conditions.append(Order.store_id == store_id)
    if year is not None:
        conditions.append(Order.order_date >= datetime(year, 1, 1))
        conditions.append(Order.order_date < datetime(year + 1, 1, 1))

    rows = db.execute(
        select(
            Product.product_id,
            Product.product_code,
            Product.product_name,
            Product.unit,
            func.coalesce(func.sum(OrderItem.quantity), 0),
            func.coalesce(func.sum(OrderItem.line_total), 0),
        )
        .select_from(OrderItem)
        .join(Order, OrderItem.order_id == Order.order_id)
        .join(Product, OrderItem.product_id == Product.product_id)
        .where(*conditions)
        .group_by(
            Product.product_id,
            Product.product_code,
            Product.product_name,
            Product.unit,
        )
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    ).all()

    return [
        TopProductResponse(
            product_id=r[0],
            product_code=r[1],
            product_name=r[2],
            unit=r[3],
            total_quantity=float(r[4] or 0),
            total_revenue=float(r[5] or 0),
        )
        for r in rows
    ]


@router.get(
    "/low-stock", response_model=list[LowStockResponse],
    summary="Products below minimum stock",
)
def dashboard_low_stock(
    db: Session = Depends(get_db),
    threshold: float = Query(
        20, ge=0,
        description="Only pairs whose shortage reaches this amount",
    ),
    store_id: int | None = Query(None, gt=0),
) -> list[LowStockResponse]:
    """
    Product-stock pairs below their minimum level.

    The view already applies `SUM(quantity) < min_stock` per pair, so this
    endpoint only narrows the result further.

    `threshold` filters on `shortage`, which is `min_stock - total_quantity`
    - how many units are missing, not how many are on hand. Ranking by the
    gap is what a buyer acts on.
    """
    conditions = [v_low_stock.c.shortage >= threshold]
    if store_id is not None:
        conditions.append(v_low_stock.c.store_id == store_id)

    rows = db.execute(
        select(
            v_low_stock.c.store_id,
            v_low_stock.c.product_id,
            v_low_stock.c.product_code,
            v_low_stock.c.product_name,
            v_low_stock.c.unit,
            v_low_stock.c.total_quantity,
            v_low_stock.c.min_stock,
            v_low_stock.c.reorder_point,
            v_low_stock.c.shortage,
        )
        .where(*conditions)
        .order_by(v_low_stock.c.shortage.desc())
    ).all()

    return [
        LowStockResponse(
            store_id=r[0],
            product_id=r[1],
            product_code=r[2],
            product_name=r[3],
            unit=r[4],
            total_quantity=float(r[5] or 0),
            min_stock=float(r[6] or 0),
            reorder_point=float(r[7]) if r[7] is not None else None,
            shortage=float(r[8] or 0),
        )
        for r in rows
    ]


@router.get(
    "/expiring", response_model=list[ExpiringResponse],
    summary="Batches near or past expiry",
)
def dashboard_expiring(
    db: Session = Depends(get_db),
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

    `alert_severity` comes from the view, which maps the date to
    expired / critical / high / medium / low.
    """
    conditions = [v_expiring_inventory.c.days_to_expiry <= days]
    if store_id is not None:
        conditions.append(v_expiring_inventory.c.store_id == store_id)
    if product_id is not None:
        conditions.append(v_expiring_inventory.c.product_id == product_id)

    rows = db.execute(
        select(
            v_expiring_inventory.c.inventory_id,
            v_expiring_inventory.c.store_id,
            v_expiring_inventory.c.product_id,
            v_expiring_inventory.c.product_code,
            v_expiring_inventory.c.product_name,
            v_expiring_inventory.c.batch_code,
            v_expiring_inventory.c.quantity,
            v_expiring_inventory.c.expiry_date,
            v_expiring_inventory.c.days_to_expiry,
            v_expiring_inventory.c.stock_value,
            v_expiring_inventory.c.alert_severity,
        )
        .where(*conditions)
        .order_by(v_expiring_inventory.c.days_to_expiry)
    ).all()

    return [
        ExpiringResponse(
            inventory_id=r[0],
            store_id=r[1],
            product_id=r[2],
            product_code=r[3],
            product_name=r[4],
            batch_code=r[5],
            quantity=float(r[6] or 0),
            expiry_date=r[7],
            days_to_expiry=int(r[8] or 0),
            stock_value=float(r[9] or 0),
            alert_severity=r[10],
        )
        for r in rows
    ]


@router.get(
    "/alerts-summary", response_model=AlertsSummaryResponse,
    summary="Alert counts by type and severity",
)
def dashboard_alerts_summary(
    db: Session = Depends(get_db),
    store_id: int | None = Query(None, gt=0),
) -> AlertsSummaryResponse:
    """
    Alert counts for a dashboard panel.

    Three aggregates rather than one query returning all alerts: the panel
    needs counts, and pulling 518 full rows into Python just to call
    `len()` would be wasteful.

    Severity is ordered critical first so the UI shows the worst first.
    """
    conditions = []
    if store_id is not None:
        conditions.append(Alert.store_id == store_id)

    totals = db.execute(
        select(
            func.count(Alert.alert_id),
            func.coalesce(
                func.sum(case((Alert.is_read.is_(False), 1), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((Alert.is_resolved.is_(False), 1), else_=0)), 0
            ),
            func.coalesce(
                func.sum(
                    case(
                        (Alert.is_read.is_(False) & (Alert.severity == "critical"), 1),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(*conditions)
    ).one()

    by_type_rows = db.execute(
        select(
            Alert.alert_type,
            func.count(Alert.alert_id),
            func.coalesce(
                func.sum(case((Alert.is_resolved.is_(False), 1), else_=0)), 0
            ),
        )
        .where(*conditions)
        .group_by(Alert.alert_type)
        .order_by(Alert.alert_type)
    ).all()

    by_sev_rows = db.execute(
        select(Alert.severity, func.count(Alert.alert_id))
        .where(*conditions)
        .group_by(Alert.severity)
    ).all()

    severity_map = {row[0]: int(row[1]) for row in by_sev_rows}
    # Fill the zero buckets so the UI always renders all four levels.
    by_severity = [
        SeverityCount(severity=sev, count=severity_map.get(sev, 0))
        for sev in SEVERITY_ORDER
    ]

    return AlertsSummaryResponse(
        total=int(totals[0] or 0),
        unread=int(totals[1] or 0),
        unresolved=int(totals[2] or 0),
        critical_unread=int(totals[3] or 0),
        by_type=[
            TypeCount(
                alert_type=r[0],
                count=int(r[1]),
                unresolved=int(r[2]),
            )
            for r in by_type_rows
        ],
        by_severity=by_severity,
    )