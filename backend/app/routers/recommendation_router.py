"""
Recommendation endpoints (B10): reorder, expiring stock, slow movers.

All database access goes through the SQLAlchemy ORM - no raw SQL here.

The anchor date is the most important decision in this module. Sales data
ends 2017-12-31 and the forecast horizon is January 2018, so "the last 30
days" has to mean the last 30 days *of available data*, not the last 30 days
before today. Anchoring on `CURRENT_DATE` would put the window in 2026,
find zero sales for every product, and report the entire catalogue as
dead stock. `_data_anchor_date` reads the real maximum sale date instead.

A second consequence of that gap: the recommended quantities are not
actionable in a real sense. The forecast covers a period for which no actual
demand will ever be observed from this dataset, and current stock is seeded
against `max_stock` values that are 0.5-3 days of sales (see AGENTS.md). The
maths below is correct; the inputs make the output hypothetical. That is
stated in each `reason` string so the number never travels without its
caveat.
"""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Integer, case, func, select
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
from app.schemas.recommendation_schema import (
    ExpiringRecommendation,
    ImportRecommendation,
    RecommendationSummary,
    SlowMovingProduct,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

HTTP_422_UNPROCESSABLE_CONTENT = 422

VN_TZ = timezone(timedelta(hours=7))

# Window used for the "recent sales" side of both recommendations.
DEFAULT_LOOKBACK_DAYS = 30

# Stock expiring within this many days is counted as at-risk and cannot
# count as usable cover. Matches v_expiring_inventory's hard-coded window.
EXPIRY_RISK_DAYS = 30

# Expiring batches get a recommendation inside this window.
DEFAULT_EXPIRING_WINDOW_DAYS = 7

# Slow-moving thresholds.
SLOW_MOVING_MAX_UNITS = 5        # fewer than this sold in the window
SLOW_MOVING_MIN_STOCK = 50       # while holding at least this much


def _f(value) -> float:
    """Coerce a NUMERIC aggregate to float; None becomes 0.0."""
    return 0.0 if value is None else float(value)


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=VN_TZ)


def _data_anchor_date(db: Session) -> date:
    """
    The most recent day that actually has SOLD.

    Two filters matter here, and dropping either one breaks the module:

    - Anchoring on CURRENT_DATE would put the window in 2026, find no sales
      at all, and report the entire catalogue as dead stock.
    - Anchoring on the newest order of any status is just as wrong. A
      single draft order created "now" carries today's date, so creating one
      would drag the anchor forward and silently zero every sales figure in
      the recommendations. Only completed sales count.

    Returns today when there is no completed sales history at all, which
    keeps the query well-formed and surfaces an empty result rather than an
    error.
    """
    latest = db.execute(
        select(func.max(Order.order_date))
        .where(Order.status == "completed", Order.order_type == "sale")
    ).scalar_one()
    if latest is None:
        return date.today()
    return latest.date() if isinstance(latest, datetime) else latest


def _priority_for(value: float, high: float, medium: float) -> str:
    """Map a magnitude onto high / medium / low."""
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return "low"


# ===========================================================================
# GET /recommendations/import
# ===========================================================================
@router.get(
    "/import",
    response_model=list[ImportRecommendation],
    summary="Recommended reorder quantity per store and product",
)
def recommend_import(
    db: Session = Depends(get_db),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    min_qty: float = Query(0, ge=0, description="Hide rows at or below this"),
    limit: int = Query(200, ge=1, le=1000),
) -> list[ImportRecommendation]:
    """
    recommended_import_qty = max(0, predicted_demand - usable_stock + safety_stock)

    `usable_stock` deliberately EXCLUDES stock expiring within 30 days. Stock
    that will be written off cannot cover demand, and counting it would make
    a store holding 500 units of about-to-expire product look over-supplied
    when it is in fact about to be empty.

    `safety_stock` prefers `reorder_point` and falls back to `min_stock`,
    because that is the level the product table itself treats as the floor.

    Only pairs that have a forecast are considered, so the result covers the
    10 products and 10 stores in the forecasts table rather than all 50 x 10
    combinations. Note that products 13, 28 and 45 have forecasts for only 9
    stores - see AGENTS.md.
    """
    anchor = _data_anchor_date(db)

    # Forecast horizon read from the data rather than assumed to be 30 days.
    horizon_start, horizon_end = db.execute(
        select(func.min(Forecast.forecast_date), func.max(Forecast.forecast_date))
    ).one()
    horizon_days = (
        (horizon_end - horizon_start).days + 1
        if horizon_start and horizon_end
        else 0
    )

    # 1. Demand: sum the forecast across the horizon, per store+product.
    fc_filters = []
    if store_id is not None:
        fc_filters.append(Forecast.store_id == store_id)
    if product_id is not None:
        fc_filters.append(Forecast.product_id == product_id)

    demand_rows = db.execute(
        select(
            Forecast.store_id,
            Forecast.product_id,
            func.sum(Forecast.predicted_quantity),
            func.sum(Forecast.lower_bound),
            func.sum(Forecast.upper_bound),
        )
        .where(*fc_filters)
        .group_by(Forecast.store_id, Forecast.product_id)
    ).all()

    if not demand_rows:
        return []

    store_ids = {r[0] for r in demand_rows}
    product_ids = {r[1] for r in demand_rows}

    # 2. Stock on hand, split into usable and at-risk.
    # The CASE keeps the two sums in one pass over the rows. A NULL
    # expiry_date falls to else_=0, which is right: an undated batch has no
    # expiry risk and counts entirely as usable.
    risk_cutoff = date.today() + timedelta(days=EXPIRY_RISK_DAYS)
    stock_rows = db.execute(
        select(
            Inventory.store_id,
            Inventory.product_id,
            func.coalesce(func.sum(Inventory.quantity), 0),
            func.coalesce(
                func.sum(
                    case(
                        (Inventory.expiry_date <= risk_cutoff, Inventory.quantity),
                        else_=0,
                    )
                ),
                0,
            ),
        )
        .where(
            Inventory.store_id.in_(store_ids),
            Inventory.product_id.in_(product_ids),
            Inventory.quantity > 0,
        )
        .group_by(Inventory.store_id, Inventory.product_id)
    ).all()

    stock = {(s, p): (total, at_risk) for s, p, total, at_risk in stock_rows}

    # 3. Product and store metadata, in one query each.
    products = {
        p.product_id: p
        for p in db.execute(
            select(Product).where(Product.product_id.in_(product_ids))
        ).scalars().all()
    }
    categories = {
        c.category_id: c
        for c in db.execute(
            select(Category).where(
                Category.category_id.in_(
                    [p.category_id for p in products.values()]
                )
            )
        ).scalars().all()
    }
    stores = {
        s.store_id: s
        for s in db.execute(
            select(Store).where(Store.store_id.in_(store_ids))
        ).scalars().all()
    }

    results = []
    for s_id, p_id, predicted, lower, upper in demand_rows:
        product = products.get(p_id)
        store = stores.get(s_id)
        if product is None or store is None:
            continue

        predicted = _f(predicted)
        current_stock, at_risk = stock.get((s_id, p_id), (0.0, 0.0))
        current_stock = _f(current_stock)
        at_risk = _f(at_risk)

        usable_stock = max(0.0, current_stock - at_risk)
        safety = _f(
            product.reorder_point
            if product.reorder_point is not None
            else product.min_stock
        )

        recommended = max(0.0, predicted - usable_stock + safety)

        if recommended <= min_qty:
            continue

        # Thresholds are relative to the forecast itself: a gap equal to a
        # whole day's forecast is a normal refill, several times that is a
        # stockout risk.
        per_day = predicted / horizon_days if horizon_days else predicted
        high, medium = per_day * 7, per_day * 2
        priority = _priority_for(recommended, high, medium)

        reasons = [
            f"Du bao {horizon_days} ngay: {predicted:,.0f} san pham",
            f"ton kho hien tai {current_stock:,.0f}, dung duoc {usable_stock:,.0f}",
        ]
        if at_risk > 0:
            reasons.append(
                f"{at_risk:,.0f} san pham het han trong {EXPIRY_RISK_DAYS} ngay "
                "khong tinh vao ton kho dung duoc"
            )
        if safety > 0:
            reasons.append(f"ton kho an toan {safety:,.0f}")
        if lower is not None and upper is not None:
            reasons.append(
                f"khoang du bao [{_f(lower):,.0f} - {_f(upper):,.0f}]"
            )
        reasons.append(
            "GIA TRI DON HANG GIA MOC PHONG; du bao phu thang 01/2018 trong khi "
            "du lieu ban hang chi den 31/12/2017 nen day la so hinh THU NGHIEM"
        )

        results.append(
            ImportRecommendation(
                product_id=p_id,
                product_code=product.product_code,
                product_name=product.product_name,
                category_name=(
                    categories[product.category_id].category_name
                    if product.category_id in categories
                    else None
                ),
                store_id=s_id,
                store_code=store.store_code,
                store_name=store.store_name,
                current_stock=current_stock,
                expiring_stock=at_risk,
                predicted_demand=round(predicted, 3),
                safety_stock=safety,
                recommended_import_qty=round(recommended, 3),
                priority=priority,
                reason=" | ".join(reasons),
            )
        )

    results.sort(key=lambda r: r.recommended_import_qty, reverse=True)
    return results[:limit]


# ===========================================================================
# GET /recommendations/expiring
# ===========================================================================
@router.get(
    "/expiring",
    response_model=list[ExpiringRecommendation],
    summary="Recommended actions for batches about to expire",
)
def recommend_expiring(
    db: Session = Depends(get_db),
    days: int = Query(
        DEFAULT_EXPIRING_WINDOW_DAYS, ge=1, le=EXPIRY_RISK_DAYS,
        description="Include batches expiring within this many days",
    ),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    min_value: float = Query(
        0, ge=0, description="Hide batches worth less than this at cost"
    ),
    limit: int = Query(200, ge=1, le=1000),
) -> list[ExpiringRecommendation]:
    """
    Rank at-risk batches by what they are worth, most valuable first.

    The action follows the shelf life left, not the value:
      - more than half the window left -> discount, there is time to sell
      - less than half -> transfer, no time to sell but time to move
      - already expired or expiring within 2 days -> destroy, too late for
        either and moving it would only shift the loss to another store
    """
    today = date.today()
    cutoff = today + timedelta(days=days)
    halfway = today + timedelta(days=days // 2)

    filters = [
        Inventory.quantity > 0,
        Inventory.expiry_date.isnot(None),
        Inventory.expiry_date <= cutoff,
    ]
    if store_id is not None:
        filters.append(Inventory.store_id == store_id)
    if product_id is not None:
        filters.append(Inventory.product_id == product_id)

    days_left = func.cast(
        Inventory.expiry_date - func.current_date(), Integer
    )

    rows = db.execute(
        select(
            Inventory.inventory_id,
            Inventory.store_id,
            Store.store_code,
            Store.store_name,
            Inventory.product_id,
            Product.product_code,
            Product.product_name,
            Inventory.expiry_date,
            days_left.label("days_to_expiry"),
            Inventory.quantity,
            Product.unit_cost,
            (Inventory.quantity * Product.unit_cost).label("total_value"),
        )
        .select_from(Inventory)
        .join(Store, Store.store_id == Inventory.store_id)
        .join(Product, Product.product_id == Inventory.product_id)
        .where(*filters)
        .order_by((Inventory.quantity * Product.unit_cost).desc())
        .limit(limit)
    ).all()

    results = []
    for row in rows:
        # Unpack by name. Reading row[10] when the tuple has twelve columns
        # is a silent way to report the unit cost as the batch total, which
        # is exactly the bug this replaced.
        (
            inventory_id,
            store_id,
            store_code,
            store_name,
            product_id,
            product_code,
            product_name,
            expiry_date,
            days_left,
            quantity,
            unit_cost,
            total_value,
        ) = row

        total_value = _f(total_value)
        if total_value < min_value:
            continue

        d_left = int(days_left)

        if d_left < 0:
            action = "destroy"
            reason = f"DA HET HAN {abs(d_left)} ngay truoc - phai tieu huy"
        elif d_left <= 2:
            action = "destroy"
            reason = (
                f"Con {d_left} ngay - qua ngan de giam gia hay chuyen kho, "
                "gia bang dich khi con ban duoc o cho khac"
            )
        elif expiry_date <= halfway:
            action = "transfer"
            reason = (
                f"Con {d_left} ngay - chuyen sang cua hang ban nhanh hon, "
                "giam gia se khong du thoi gian ban het"
            )
        else:
            action = "discount"
            reason = (
                f"Con {d_left} ngay - giam gia de ban nhanh truoc khi het han"
            )

        priority = _priority_for(total_value, 10_000_000, 1_000_000)

        results.append(
            ExpiringRecommendation(
                inventory_id=inventory_id,
                store_id=store_id,
                store_code=store_code,
                store_name=store_name,
                product_id=product_id,
                product_code=product_code,
                product_name=product_name,
                expiry_date=expiry_date.isoformat(),
                days_to_expiry=d_left,
                quantity=_f(quantity),
                unit_value=_f(unit_cost),
                total_value=round(total_value, 2),
                priority=priority,
                action=action,
                reason=reason,
            )
        )

    return results


# ===========================================================================
# GET /recommendations/slow-moving
# ===========================================================================
@router.get(
    "/slow-moving",
    response_model=list[SlowMovingProduct],
    summary="Products holding stock that is not selling",
)
def recommend_slow_moving(
    db: Session = Depends(get_db),
    days: int = Query(
        DEFAULT_LOOKBACK_DAYS, ge=1, le=365,
        description="Lookback window, measured back from the last day with sales",
    ),
    store_id: int | None = Query(None, gt=0),
    max_units_sold: float = Query(
        SLOW_MOVING_MAX_UNITS, ge=0,
        description="Flag pairs selling at most this many units in the window",
    ),
    min_stock: float = Query(
        SLOW_MOVING_MIN_STOCK, ge=0,
        description="Flag pairs holding at least this much stock",
    ),
    limit: int = Query(200, ge=1, le=1000),
) -> list[SlowMovingProduct]:
    """
    Find stock that is not moving while capital sits in it.

    The window ends at the most recent day that has sales, not today - see
    `_data_anchor_date`. Anchoring on CURRENT_DATE would find zero sales
    everywhere and flag the entire catalogue.

    Pairs with no sales in the window are included with `units_sold_30d = 0`
    and `days_of_cover = None`, because "sold nothing at all" is exactly the
    case worth surfacing and `None` says "no rate exists" rather than
    implying an infinite one.
    """
    anchor = _data_anchor_date(db)
    window_start = anchor - timedelta(days=days)

    # Sales per store+product inside the window.
    sold_rows = db.execute(
        select(
            Order.store_id,
            OrderItem.product_id,
            func.coalesce(func.sum(OrderItem.quantity), 0),
        )
        .select_from(OrderItem)
        .join(Order, Order.order_id == OrderItem.order_id)
        .where(
            Order.status == "completed",
            Order.order_type == "sale",
            Order.order_date >= _start_of_day(window_start),
            Order.order_date < _start_of_day(anchor + timedelta(days=1)),
        )
        .group_by(Order.store_id, OrderItem.product_id)
    ).all()
    sold = {(s, p): _f(q) for s, p, q in sold_rows}

    # Current stock per store+product.
    stock_rows = db.execute(
        select(
            Inventory.store_id,
            Inventory.product_id,
            func.coalesce(func.sum(Inventory.quantity), 0),
        )
        .where(Inventory.quantity > 0)
        .group_by(Inventory.store_id, Inventory.product_id)
    ).all()
    stock = {(s, p): _f(q) for s, p, q in stock_rows}

    if not stock:
        return []

    pairs = sorted(stock.keys())
    product_ids = {p for _, p in pairs}
    store_ids = {s for s, _ in pairs}

    products = {
        p.product_id: p
        for p in db.execute(
            select(Product).where(Product.product_id.in_(product_ids))
        ).scalars().all()
    }
    categories = {
        c.category_id: c
        for c in db.execute(
            select(Category).where(
                Category.category_id.in_([p.category_id for p in products.values()])
            )
        ).scalars().all()
    }
    stores = {
        s.store_id: s
        for s in db.execute(
            select(Store).where(Store.store_id.in_(store_ids))
        ).scalars().all()
    }

    results = []
    for s_id, p_id in pairs:
        current = stock[(s_id, p_id)]
        if current < min_stock:
            continue
        units = sold.get((s_id, p_id), 0.0)
        if units > max_units_sold:
            continue

        product = products.get(p_id)
        store = stores.get(s_id)
        if product is None or store is None:
            continue

        avg_daily = units / days
        # None rather than a huge number: with zero sales there is no rate
        # to compute cover from, and an invented figure would mislead.
        days_of_cover = round(current / avg_daily, 1) if avg_daily > 0 else None

        stock_value = current * _f(product.unit_cost)

        if units == 0:
            action = "stop_ordering"
            reason = (
                f"KHONG ban duoc 1 san pham trong {days} ngay, van ton "
                f"{current:,.0f} - ngung nhap va xu ly ton kho"
            )
            priority = "high"
        elif current > avg_daily * days * 2:
            action = "reduce_order"
            reason = (
                f"Chi ban {units:,.0f} san pham trong {days} ngay nhung van "
                f"ton {current:,.0f} - giam don nhap va chay khuyen mai"
            )
            priority = "high" if stock_value > 5_000_000 else "medium"
        else:
            action = "promotion"
            reason = (
                f"Chi ban {units:,.0f} san pham trong {days} ngay, ton "
                f"{current:,.0f} - chay khuyen mai de giai phong ton kho"
            )
            priority = "low"

        results.append(
            SlowMovingProduct(
                product_id=p_id,
                product_code=product.product_code,
                product_name=product.product_name,
                category_name=(
                    categories[product.category_id].category_name
                    if product.category_id in categories
                    else None
                ),
                store_id=s_id,
                store_code=store.store_code,
                store_name=store.store_name,
                current_stock=current,
                stock_value=round(stock_value, 2),
                units_sold_30d=units,
                avg_daily_sales_30d=round(avg_daily, 4),
                days_of_cover=days_of_cover,
                priority=priority,
                action=action,
                reason=reason,
            )
        )

    results.sort(key=lambda r: r.stock_value, reverse=True)
    return results[:limit]

