"""
Recommendation endpoints (B10 / SQL Server Stored Procedure).

All database access goes through `EXEC dbo.sp_Recommendations_*`; there is
no ORM query in this file. The procedures return the numbers, this module
turns them into the human-readable `reason`, `priority` and `action` fields.

The anchor date is the most important decision in this module. Sales data
ends 2017-12-31 and the forecast horizon is January 2018, so "the last 30
days" has to mean the last 30 days *of available data*, not the last 30 days
before today. Anchoring on `CURRENT_DATE` would put the window in 2026,
find zero sales for every product, and report the entire catalogue as
dead stock. `sp_Recommendations_SlowMoving` finds the real maximum sale date.

A second consequence of that gap: the recommended quantities are not
actionable in a real sense. The forecast covers a period for which no actual
demand will ever be observed from this dataset, and current stock is seeded
against `max_stock` values that are 0.5-3 days of sales (see AGENTS.md). The
maths below is correct; the inputs make the output hypothetical. That is
stated in each `reason` string so the number never travels without its
caveat.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.schemas.recommendation_schema import (
    ExpiringRecommendation,
    ImportRecommendation,
    SlowMovingProduct,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

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


def _priority_for(value: float, high: float, medium: float) -> str:
    """Map a magnitude onto high / medium / low."""
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return "low"


@router.get(
    "/import",
    response_model=list[ImportRecommendation],
    summary="Recommended reorder quantity per store and product",
)
def recommend_import(
    db: DbSession = Depends(get_db),
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
    try:
        rows = db.rows(
            "sp_Recommendations_Import",
            {
                "StoreId": store_id,
                "ProductId": product_id,
                "MinQty": min_qty,
                "Limit": limit,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    results = []
    for r in rows:
        predicted = _f(r["predicted_demand"])
        current_stock = _f(r["current_stock"])
        at_risk = _f(r["expiring_stock"])
        safety = _f(r["safety_stock"])
        recommended = _f(r["recommended_import_qty"])
        horizon_days = int(r["horizon_days"] or 0)
        lower = r["lower_sum"]
        upper = r["upper_sum"]

        usable_stock = max(0.0, current_stock - at_risk)

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
                product_id=r["product_id"],
                product_code=r["product_code"],
                product_name=r["product_name"],
                category_name=r["category_name"],
                store_id=r["store_id"],
                store_code=r["store_code"],
                store_name=r["store_name"],
                current_stock=current_stock,
                expiring_stock=at_risk,
                predicted_demand=round(predicted, 3),
                safety_stock=safety,
                recommended_import_qty=round(recommended, 3),
                priority=priority,
                reason=" | ".join(reasons),
            )
        )

    return results


@router.get(
    "/expiring",
    response_model=list[ExpiringRecommendation],
    summary="Recommended actions for batches about to expire",
)
def recommend_expiring(
    db: DbSession = Depends(get_db),
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
    try:
        rows = db.rows(
            "sp_Recommendations_Expiring",
            {
                "Days": days,
                "StoreId": store_id,
                "ProductId": product_id,
                "MinValue": min_value,
                "Limit": limit,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    today = date.today()
    halfway = today + timedelta(days=days // 2)

    results = []
    for r in rows:
        expiry_date = r["expiry_date"]
        d_left = int(r["days_to_expiry"] or 0)
        total_value = _f(r["total_value"])

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
                inventory_id=r["inventory_id"],
                store_id=r["store_id"],
                store_code=r["store_code"],
                store_name=r["store_name"],
                product_id=r["product_id"],
                product_code=r["product_code"],
                product_name=r["product_name"],
                expiry_date=expiry_date.isoformat(),
                days_to_expiry=d_left,
                quantity=_f(r["quantity"]),
                unit_value=_f(r["unit_value"]),
                total_value=round(total_value, 2),
                priority=priority,
                action=action,
                reason=reason,
            )
        )

    return results


@router.get(
    "/slow-moving",
    response_model=list[SlowMovingProduct],
    summary="Products holding stock that is not selling",
)
def recommend_slow_moving(
    db: DbSession = Depends(get_db),
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

    The window ends at the most recent day that has sales, not today - the
    procedure computes that anchor. Anchoring on CURRENT_DATE would find
    zero sales everywhere and flag the entire catalogue.

    Pairs with no sales in the window are included with `units_sold_30d = 0`
    and `days_of_cover = None`, because "sold nothing at all" is exactly the
    case worth surfacing and `None` says "no rate exists" rather than
    implying an infinite one.
    """
    try:
        rows = db.rows(
            "sp_Recommendations_SlowMoving",
            {
                "Days": days,
                "StoreId": store_id,
                "MaxUnitsSold": max_units_sold,
                "MinStock": min_stock,
                "Limit": limit,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    results = []
    for r in rows:
        current = _f(r["current_stock"])
        units = _f(r["units_sold"])
        stock_value = _f(r["stock_value"])

        avg_daily = units / days
        # None rather than a huge number: with zero sales there is no rate
        # to compute cover from, and an invented figure would mislead.
        days_of_cover = round(current / avg_daily, 1) if avg_daily > 0 else None

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
                product_id=r["product_id"],
                product_code=r["product_code"],
                product_name=r["product_name"],
                category_name=r["category_name"],
                store_id=r["store_id"],
                store_code=r["store_code"],
                store_name=r["store_name"],
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

    return results
