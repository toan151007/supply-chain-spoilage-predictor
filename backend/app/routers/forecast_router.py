"""
Read-only router for forecasts (B3 - SQL Server Stored Procedure).

Rows here are produced by `ai-model/scripts/forecast_next_month.py`, which
picks the best model per product-store pair and writes 30 days per pair. The
API deliberately offers no POST or PUT: hand-written rows would mix with
evaluated model output and make the 3000-row dataset unreliable for the
Chapter 4 write-up.

DELETE is available because nothing references the forecasts table, and a
stale horizon needs to be cleared before the next model run.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pyodbc import Error as PyodbcError

from app.database import DbSession, get_db, map_sqlserver_error
from app.dependencies import require_role
from app.schemas.common import Page
from app.schemas.forecast_schema import ForecastRead, LatestForecastList
from app.sp_helpers import attach_product, attach_store

router = APIRouter(prefix="/forecasts", tags=["forecasts"])

MODEL_NAME_PATTERN = "^(prophet|xgboost|arima|moving_average|naive)$"


def _to_read(row: dict) -> dict:
    row = dict(row)
    attach_store(row)
    attach_product(row)
    return row


# NOTE: `/latest` must be declared BEFORE `/{forecast_id}`.
@router.get(
    "/latest", response_model=LatestForecastList,
    summary="Latest forecast per product-store pair",
)
def latest_forecasts(
    db: DbSession = Depends(get_db),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> LatestForecastList:
    """
    One row per product-store pair: the newest forecast date, and among
    several models on that date the one with the best RMSE. These are
    single-day figures, NOT horizon totals.
    """
    try:
        sets = db.call(
            "sp_Forecasts_Latest",
            {
                "StoreId": store_id,
                "ProductId": product_id,
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = [_to_read(row) for row in (sets[1] if len(sets) > 1 else [])]
    pages = (total + page_size - 1) // page_size
    return LatestForecastList(
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("", response_model=Page[ForecastRead], summary="List forecasts")
def list_forecasts(
    db: DbSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    forecast_date: date | None = Query(None),
    forecast_from: date | None = Query(None),
    forecast_to: date | None = Query(None),
    model_name: str | None = Query(None, pattern=MODEL_NAME_PATTERN),
) -> Page[ForecastRead]:
    try:
        sets = db.call(
            "sp_Forecasts_List",
            {
                "StoreId": store_id,
                "ProductId": product_id,
                "ForecastDate": forecast_date,
                "ForecastFrom": forecast_from,
                "ForecastTo": forecast_to,
                "ModelName": model_name,
                "Page": page,
                "PageSize": page_size,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    total = int(sets[0][0]["total"]) if sets and sets[0] else 0
    items = [_to_read(row) for row in (sets[1] if len(sets) > 1 else [])]
    pages = (total + page_size - 1) // page_size
    return Page[ForecastRead](
        total=total, page=page, page_size=page_size, pages=pages, items=items
    )


@router.get("/{forecast_id}", response_model=ForecastRead, summary="Get one forecast")
def get_forecast(forecast_id: int, db: DbSession = Depends(get_db)) -> dict:
    try:
        row = db.one("sp_Forecasts_Get", {"ForecastId": forecast_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast {forecast_id} not found",
        )
    return _to_read(row)


@router.delete(
    "/{forecast_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one forecast row",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def delete_forecast(forecast_id: int, db: DbSession = Depends(get_db)) -> None:
    try:
        db.call("sp_Forecasts_Delete", {"ForecastId": forecast_id})
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None


@router.delete(
    "", status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete forecasts by filter",
    dependencies=[Depends(require_role("owner", "manager"))],
)
def delete_forecasts(
    db: DbSession = Depends(get_db),
    store_id: int | None = Query(None, gt=0),
    product_id: int | None = Query(None, gt=0),
    model_name: str | None = Query(None, pattern=MODEL_NAME_PATTERN),
    forecast_to: date | None = Query(None),
) -> None:
    """
    Delete forecast rows matching the given filters.

    At least one filter is required. Without any, one stray request would
    wipe all 3000 rows. The guard lives in the router because the procedure
    cannot tell "no filter" from "delete everything".
    """
    if all(v is None for v in (store_id, product_id, model_name, forecast_to)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Refusing to delete all forecasts. Pass at least one of "
                "store_id, product_id, model_name or forecast_to."
            ),
        )

    try:
        db.call(
            "sp_Forecasts_DeleteByFilter",
            {
                "StoreId": store_id,
                "ProductId": product_id,
                "ModelName": model_name,
                "FromDate": None,
                "ToDate": forecast_to,
            },
        )
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc
    return None

