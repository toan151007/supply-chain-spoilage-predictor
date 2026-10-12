"""
Read-only router for forecasts.

Rows here are produced by `ai-model/scripts/forecast_next_month.py`, which
picks the best model per product-store pair and writes 30 days per pair.
The API deliberately offers no POST or PUT: hand-written rows would mix
with evaluated model output and make the 3000-row dataset unreliable for
the Chapter 4 write-up.

DELETE is available because nothing references the forecasts table, and a
stale horizon needs to be cleared before the next model run.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Forecast
from app.schemas.common import Page
from app.schemas.forecast_schema import ForecastRead, LatestForecast, LatestForecastList

router = APIRouter(prefix="/forecasts", tags=["forecasts"])

MODEL_NAME_PATTERN = "^(prophet|xgboost|arima|moving_average|naive)$"

# Starlette renamed 422 to HTTP_422_UNPROCESSABLE_CONTENT; using the new
# name keeps the deprecation warning out of the logs.
HTTP_422_UNPROCESSABLE_CONTENT = 422


@router.get(
    "/latest", response_model=LatestForecastList,
    summary="Latest forecast per product-store pair",
)
def latest_forecasts(
    db: Session = Depends(get_db),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> LatestForecastList:
    """
    Return the most recent forecast row for each product-store pair.

    The table holds 30 rows per pair (one per horizon day). This endpoint
    keeps only the newest date so the frontend gets one clean row per pair
    instead of grouping 3000 rows itself.

    These are single-day figures, NOT horizon totals. For demand across the
    whole 30 days, use `GET /api/v1/forecasts` and aggregate client side.

    If several models share the newest date for one pair, the row with the
    best RMSE wins - that is the model M1 selected, so it is the one a
    planner should see. A row with no recorded RMSE never beats one that
    has the metric.
    """
    filters = []
    if store_id is not None:
        filters.append(Forecast.store_id == store_id)
    if product_id is not None:
        filters.append(Forecast.product_id == product_id)

    newest_date = db.execute(
        select(func.max(Forecast.forecast_date)).where(*filters)
    ).scalar_one()

    if newest_date is None:
        return LatestForecastList(
            total=0, page=page, page_size=page_size, pages=0, items=[]
        )

    rows = db.execute(
        select(Forecast)
        .options(joinedload(Forecast.store), joinedload(Forecast.product))
        .where(Forecast.forecast_date == newest_date, *filters)
        .order_by(Forecast.store_id, Forecast.product_id, Forecast.forecast_id)
    ).scalars().all()

    best: dict[tuple[int, int], Forecast] = {}
    for f in rows:
        key = (f.store_id, f.product_id)
        current = best.get(key)
        if current is None:
            best[key] = f
        elif current.rmse is None or (
            f.rmse is not None and float(f.rmse) < float(current.rmse)
        ):
            best[key] = f

    items = [
        LatestForecast(
            store_id=f.store_id,
            product_id=f.product_id,
            model_name=f.model_name,
            forecast_date=f.forecast_date,
            predicted_quantity=float(f.predicted_quantity),
            lower_bound=float(f.lower_bound) if f.lower_bound is not None else None,
            upper_bound=float(f.upper_bound) if f.upper_bound is not None else None,
            recommended_import_qty=(
                float(f.recommended_import_qty)
                if f.recommended_import_qty is not None
                else None
            ),
            store=f.store,
            product=f.product,
        )
        for f in best.values()
    ]

    total = len(items)
    start = (page - 1) * page_size
    window = items[start:start + page_size]
    pages = (total + page_size - 1) // page_size

    return LatestForecastList(
        total=total, page=page, page_size=page_size, pages=pages, items=window
    )


@router.get("", response_model=Page[ForecastRead], summary="List forecasts")
def list_forecasts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    forecast_date: date | None = Query(None),
    forecast_from: date | None = Query(None),
    forecast_to: date | None = Query(None),
    model_name: str | None = Query(None, pattern=MODEL_NAME_PATTERN),
) -> Page[ForecastRead]:
    """Paginated forecast rows with store, product, date and model filters."""
    filters = []
    if store_id is not None:
        filters.append(Forecast.store_id == store_id)
    if product_id is not None:
        filters.append(Forecast.product_id == product_id)
    if forecast_date is not None:
        filters.append(Forecast.forecast_date == forecast_date)
    if forecast_from is not None:
        filters.append(Forecast.forecast_date >= forecast_from)
    if forecast_to is not None:
        filters.append(Forecast.forecast_date <= forecast_to)
    if model_name is not None:
        filters.append(Forecast.model_name == model_name)

    total = db.execute(
        select(func.count()).select_from(Forecast).where(*filters)
    ).scalar_one()

    items = db.execute(
        select(Forecast)
        .options(joinedload(Forecast.store), joinedload(Forecast.product))
        .where(*filters)
        .order_by(
            Forecast.store_id, Forecast.product_id, Forecast.horizon_days
        )
        .offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    pages = (total + page_size - 1) // page_size
    return Page[ForecastRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{forecast_id}", response_model=ForecastRead, summary="Get one forecast")
def get_forecast(forecast_id: int, db: Session = Depends(get_db)) -> Forecast:
    forecast = db.get(Forecast, forecast_id)
    if forecast is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast {forecast_id} not found",
        )
    return forecast


@router.delete(
    "/{forecast_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one forecast row",
)
def delete_forecast(forecast_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a single forecast row. Nothing references forecasts, so this succeeds."""
    forecast = db.get(Forecast, forecast_id)
    if forecast is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast {forecast_id} not found",
        )
    db.delete(forecast)
    db.commit()


@router.delete(
    "", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete forecasts by filter",
)
def delete_forecasts(
    db: Session = Depends(get_db),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    model_name: str | None = Query(None, pattern=MODEL_NAME_PATTERN),
    forecast_to: date | None = Query(None),
) -> None:
    """
    Delete forecast rows matching the given filters.

    At least one filter is required. Without any, one stray request would
    wipe all 3000 rows.
    """
    filters = []
    if store_id is not None:
        filters.append(Forecast.store_id == store_id)
    if product_id is not None:
        filters.append(Forecast.product_id == product_id)
    if model_name is not None:
        filters.append(Forecast.model_name == model_name)
    if forecast_to is not None:
        filters.append(Forecast.forecast_date <= forecast_to)

    if not filters:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Refusing to delete all forecasts. Pass at least one of "
                "store_id, product_id, model_name or forecast_to."
            ),
        )

    db.execute(delete(Forecast).where(*filters))
    db.commit()