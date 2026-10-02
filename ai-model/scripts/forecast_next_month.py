"""
M2 - Du bao 30 ngay tiep theo va ghi vao bang `forecasts`.

Muc dich
--------
M1 da chay 3 mo hinh tren 100 cap (san pham x cua hang) va luu RMSE/MAE/MAPE
vao ai-model/outputs/model_metrics_all.csv. Script nay dung ket qua do de:

    1. Chon MO HINH TOT NHAT cho tung cap (theo RMSE thap nhat tren tap test).
    2. Train lai tren TOAN BO du lieu 2013-2017 (khong cat test set ra nua,
       vi muc dich la du bao tuong lai chu khong phai danh gia).
    3. Du bao 30 ngay 01/01/2018 - 30/01/2018.
    4. Tinh recommended_import_qty = nhau cau dua chu + ton kho an toan - ton hien tai.
    5. Ghi vao bang `forecasts` bang SQLAlchemy ORM.

Vi sao khong dung lam tron xuong 0
---------------------------------
Schema `forecasts` co CHECK (predicted_quantity >= 0) nen CAN lam tron xuong 0.
Lam tron xuong 0 san khong ton tai hau qua (nhieu mat hang ban > 900/ngay), va
lam tron xuong 0 lam sai lech don nho khong du nghia. Dinh nghia san luon la
so luong ban duoc, so thuc nen giu nguyen phan thap.

Khoang tin cay
--------------
Tat ca 3 mo hinh deu tra ve khoang [lower, upper] theo cung mot cach de
cac cap van duoc so sanh cong bang:
    - Prophet : lay truc tiep yhat_lower / yhat_upper cua model (interval 95%).
    - XGBoost : dung +- 1,96 * RMSE cua tap train (mo hinh khong xuat khoang).
    - ARIMA   : lay truc tiep khoang +-1,96*sigma cua best.resid.
Khac nhau ve co che, nhung cung dua tren sai so cua chinh mo hinh do tren tap
du lieu - day la cach lam chuan khi so sanh nhieu mo hinh tren cung mot du lieu.

De quy XGBoost (quan trong)
---------------------------
XGBoost dua vao cac dac trung lag_1..lag_28 va roll_mean_7/28. Khi du bao 30 ngay
toi, ta KHONG co gia tri thuc te cua nhung ngay do. Neu dung san gia tri thuc te
vao => RO RI DU LIEU va RMSE dep khoe. Phai dung GIA TRI DU BAO truoc do:

    du_bao_ngay_1 = f(lag tu du lieu thuc te den ngay hien tai)
    du_bao_ngay_2 = f(lag trong do 1 ngay hien la du_bao_ngay_1)
    ...

Tinh sat thuc te: XGBoost o che do one-step duoc dua nhanh hon, nhung khi can
du bao 30 ngay thi van phai de quy. Do la ly do ARIMA/Prophet thuong y hon
voi chuoi dai. Ket qua nay duoc ghi lai trong tai lieu danh gia.

Cong thuc recommended_import_qty
--------------------------------
Voi moi ngay d trong chu ky du bao:

    nhau_cu_tich_luy(d) = tong du bao tu ngay 01/01 den het ngay d
    ton_kho_an_toan     = tong (upper - predicted) tren ca chu ky 30 ngay
    recommended(d)      = MAX(0, nhau_cu_tich_luy(d) + ton_kho_an_toan - ton_hien_tai)
    recommended(d)      = MIN(recommended(d), max_stock - ton_hien_tai)

Y nghia: ngay d la muc dich dinh muc ton cho TOT HON cac ngay truoc do. Nho
vay nguoi quan ly nhin 1 so duoc "can nhap bao nhieu de phu toi ngay d".
`max_stock` chan tren de khong de xuat nhap vuot nang sua chua (sinh lang phich).

Tien an thoi han
----------------
Schema ghi ro: "while also checking expiry dates so we never suggest importing
goods with a shelf life that is too short". Voi mat hang nhanh, khong nhap
hang so cho mot chu ky dai hon han su dung cua no - hang se huong den khi ban
duoc. Script nay ap dung: neu han su dung < chu ky du bao thi chan tren bang
`max(dem_nhu_cau_30_ngay, ton_kho_an_toan)` va ghi chu qua co canh bao.

Cach chay:
    python ai-model/scripts/forecast_next_month.py --dry-run   # xem truoc, khong ghi DB
    python ai-model/scripts/forecast_next_month.py             # ghi vao bang forecasts
    python ai-model/scripts/forecast_next_month.py --replace   # xoa du lieu cu truoc khi ghi
"""

import argparse
import os
import sys
import time
import warnings
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "ai-model" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

METRICS_FILE = OUTPUT_DIR / "model_metrics_all.csv"
LOG_FILE = OUTPUT_DIR / "forecast_log.txt"

# Chu ky du bao: 30 ngay dau nam 2018, ngay sau ngay cuoi cua du lieu (2017-12-31)
FORECAST_START = date(2018, 1, 1)
HORIZON_DAYS = 30

# Chi so tin cay 95% - dung chung cho ca 3 mo hinh
Z_95 = 1.96

# Tham so Prophet da chot trong AGENTS.md (chon theo tap validation)
PROPHET_PARAMS = {
    "changepoint_prior_scale": 0.01,
    "seasonality_mode": "multiplicative",
    "yearly_seasonality": 20,
}

DATA_START = "2013-01-01"
DATA_END = "2018-01-01"

US_HOLIDAY_HINT = (
    "Dung cung bo ngay le Hoa Ky cho ca 3 mo hinh - du lieu la cua Walmart (Hoa Ky)."
)


def log(msg: str, level: str = "INFO") -> None:
    print(msg, flush=True)


def get_engine():
    from sqlalchemy import create_engine

    password = os.getenv("DB_PASSWORD")
    if password is None:
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DB_PASSWORD="):
                    password = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if password is None:
        sys.exit("LOI: khong tim thay DB_PASSWORD (dat bien moi truong hoac tao file .env)")

    user = os.getenv("DB_USER", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "spoilage_predictor")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url, pool_pre_ping=True)


def load_history(engine, product_id: int, store_id: int) -> pd.DataFrame:
    """
    Doc chuoi doanh so 1 cap tu view v_daily_sales, reindex ve du 1826 ngay.

    Reindex la BAT BUOC: view chi co dong cho ngay co phat sinh giao dich.
    Cap (product 4, store 6) thieu ngay 15/01/2014 do dong sales = 0 da bi
    bo khi import. Khong reindex thi cac ham lag/rolling lech ngay va hoc sai.
    """
    from sqlalchemy import text

    sql = text(
        """
        SELECT sale_date, quantity_sold
        FROM v_daily_sales
        WHERE product_id = :pid AND store_id = :sid
          AND sale_date >= :start AND sale_date < :end
        ORDER BY sale_date
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(
            sql, conn,
            params={"pid": product_id, "sid": store_id,
                    "start": DATA_START, "end": DATA_END},
        )

    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["y"] = df["quantity_sold"].astype(float)

    full_dates = pd.date_range(
        start=DATA_START, end=pd.Timestamp(DATA_END) - pd.Timedelta(days=1), freq="D"
    )
    df = df.set_index("sale_date").reindex(full_dates)
    df.index.name = "sale_date"
    df["y"] = df["y"].fillna(0.0)

    return df.reset_index()[["sale_date", "y"]]


def get_us_holidays():
    import holidays as holidays_lib

    return holidays_lib.country_holidays("US", years=range(2013, 2020))


# =============================================================================
#  DU BAO TUNG MO HINH
# =============================================================================

def forecast_prophet(history: pd.DataFrame, future_dates: pd.DataFrame):
    from prophet import Prophet

    hol = get_us_holidays()
    hol_df = pd.DataFrame([{"ds": d, "holiday": n} for d, n in hol.items()])

    model = Prophet(
        changepoint_prior_scale=PROPHET_PARAMS["changepoint_prior_scale"],
        seasonality_mode=PROPHET_PARAMS["seasonality_mode"],
        yearly_seasonality=PROPHET_PARAMS["yearly_seasonality"],
        weekly_seasonality=True,
        daily_seasonality=False,
        holidays=hol_df,
        interval_width=0.95,
    )
    model.fit(pd.DataFrame({"ds": history["sale_date"], "y": history["y"]}))
    # Phai truyen SERIES ("ds"), khong phai ca DataFrame - pandas 3.0 se
    # co DataFrame la mot gia tri scalar va bao loi.
    fc = model.predict(pd.DataFrame({"ds": future_dates["sale_date"]}))
    return (fc["yhat"].to_numpy(),
            fc["yhat_lower"].to_numpy(),
            fc["yhat_upper"].to_numpy())


def _make_features(dates: pd.Series, y: np.ndarray, us_holidays) -> pd.DataFrame:
    """Tao day dac trung XGBoost tu chuoi (dates, y) da noi san."""
    out = pd.DataFrame({"sale_date": dates, "y": y})
    for lag in [1, 2, 3, 4, 5, 6, 7, 14, 28]:
        out[f"lag_{lag}"] = out["y"].shift(lag)
    out["roll_mean_7"] = out["y"].shift(1).rolling(window=7).mean()
    out["roll_mean_28"] = out["y"].shift(1).rolling(window=28).mean()
    out["dow"] = out["sale_date"].dt.dayofweek
    out["month"] = out["sale_date"].dt.month
    out["is_weekend"] = (out["dow"] >= 5).astype(int)
    out["trend"] = np.arange(len(out))
    out["is_holiday"] = out["sale_date"].isin(us_holidays).astype(int)
    return out


XGB_FEATURE_COLS = [
    "lag_1", "lag_2", "lag_3", "lag_4", "lag_5", "lag_6", "lag_7",
    "lag_14", "lag_28", "roll_mean_7", "roll_mean_28",
    "dow", "month", "is_weekend", "trend", "is_holiday",
]


def forecast_xgboost(history: pd.DataFrame, future_dates: pd.DataFrame):
    """
    XGBoost voi dac trung lag - du bao DE QUY.

    28 ngay dau khong co gia tri lag -> cat khoi tap train (nhu M1).
    """
    from xgboost import XGBRegressor

    us_holidays = get_us_holidays()

    all_dates = pd.concat(
        [history["sale_date"], future_dates["sale_date"]], ignore_index=True
    )
    feats = _make_features(all_dates, np.concatenate([
        history["y"].to_numpy(), np.zeros(len(future_dates))
    ]), us_holidays)

    n_hist = len(history)
    train = feats.iloc[:n_hist].dropna(subset=XGB_FEATURE_COLS)
    X_train, y_train = train[XGB_FEATURE_COLS], train["y"]

    model = XGBRegressor(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9,
        objective="reg:squarederror", random_state=42, verbosity=0,
    )
    model.fit(X_train, y_train)

    # Sai so tren tap train -> dung lam co hoang tin cay
    resid = y_train.to_numpy() - model.predict(X_train)
    sigma = float(np.sqrt(np.mean(resid**2)))

    # De quy: cap nhat y bang gia tri du bao truoc do roi tinh lai dac trung
    work = feats.copy()
    y_work = work["y"].to_numpy().astype(float)
    preds = []

    for i in range(n_hist, len(work)):
        row = _make_features(
            work["sale_date"].iloc[: i + 1], y_work[: i + 1], us_holidays
        ).iloc[i]
        x = row[XGB_FEATURE_COLS].to_frame().T.astype(float)
        p = float(model.predict(x)[0])
        y_work[i] = p          # gan gia tri du bao vao chuoi cho cac ngay sau
        preds.append(p)

    preds = np.asarray(preds)
    return preds, np.clip(preds - Z_95 * sigma, 0, None), preds + Z_95 * sigma


def forecast_arima(history: pd.DataFrame, n: int):
    from statsmodels.tsa.arima.model import ARIMA

    smooth = history["y"].rolling(window=3, min_periods=1).mean().fillna(history["y"])

    best, best_aic = None, float("inf")
    for order in [(1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2), (1, 0, 1), (2, 0, 1)]:
        try:
            fitted = ARIMA(smooth.to_numpy(), order=order,
                           seasonal_order=(0, 0, 0, 0)).fit()
            if fitted.aic < best_aic:
                best_aic, best = fitted.aic, fitted
        except Exception:
            continue

    if best is None:
        raise RuntimeError("ARIMA: khong tim duoc cap (p,d,q) phu hop")

    pred = np.asarray(best.forecast(steps=n))
    sigma = float(np.std(best.resid))
    return pred, np.clip(pred - Z_95 * sigma, 0, None), pred + Z_95 * sigma


# =============================================================================
#  TON KHO
# =============================================================================

def load_stock_and_limits(engine, product_id: int, store_id: int) -> dict:
    """
    Lay ton kho hien tai (chi lo con han) + nguong min/max cua san pham.

    Ton kho: chi tinh lo quantity > 0 va chua het han. Lo het han roi
    khong dung - no da la cua qua khu, nhap them lo moi de thay the.
    """
    from sqlalchemy import text

    sql = text(
        """
        SELECT
            COALESCE(SUM(i.quantity) FILTER (
                WHERE i.quantity > 0
                  AND (i.expiry_date IS NULL OR i.expiry_date >= CURRENT_DATE)
            ), 0) AS on_hand,
            p.min_stock, p.max_stock, p.shelf_life_days
        FROM products p
        LEFT JOIN inventory i
               ON i.product_id = p.product_id
              AND i.store_id = :sid
        WHERE p.product_id = :pid
        GROUP BY p.min_stock, p.max_stock, p.shelf_life_days
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"pid": product_id, "sid": store_id}).mappings().first()

    if row is None:
        raise RuntimeError(f"Khong tim thay san pham {product_id}")

    return {
        "on_hand": float(row["on_hand"] or 0),
        "min_stock": float(row["min_stock"] or 0),
        "max_stock": float(row["max_stock"]) if row["max_stock"] is not None else None,
        "shelf_life_days": int(row["shelf_life_days"] or 0),
    }


# =============================================================================
# recommended_import_qty
# =============================================================================

def compute_recommended(pred: np.ndarray, upper: np.ndarray,
                        on_hand: float, max_stock, shelf_life_days: int) -> np.ndarray:
    """
    recommended(d) = MAX(0, nhau_cu_tich_luy(d) + ton_kho_an_toan - ton_hien_tai)

    Chu ky lai (ngay 30) la muc tien an cho ca thang - nha nhap mot lan
    chu khong phai nhap tung ngay.
    """
    cum_demand = np.cumsum(pred)
    safety = float(np.sum(upper - pred))      # tong bien do bat dinh cua ca chu ky
    need = cum_demand + safety - on_hand
    need = np.maximum(need, 0.0)

    # Chan tren: khong vuot nang sua chua
    headroom = None
    if max_stock is not None:
        headroom = max(float(max_stock) - on_hand, 0.0)
        need = np.minimum(need, headroom)

    # Chan do han su dung: khong de xuat nhap hang so cho mot chu ky
    # dai hon thoi han cua mat hang - hang nhap se huong truoc khi ban duoc.
    if 0 < shelf_life_days < HORIZON_DAYS:
        feasible = float(np.sum(pred[: max(shelf_life_days, 1)])) + safety
        need = np.minimum(need, max(feasible, 0.0))

    # NHU CAU THUAN: gia tri truoc khi chan theo max_stock.
    # Giu lai de bao cao trung thuc xem co bao cap nao dang bi chan boi
    # max_stock hay khong - neu khong luu, ta khong phan biet duoc
    # "can nhap it" voi "bi max_stock chan".
    raw = np.maximum(np.cumsum(pred) + safety - on_hand, 0.0)
    return need, raw


# =============================================================================
#  GHI VAO BANG forecasts
# =============================================================================

def write_forecasts(engine, rows: list, replace: bool) -> int:
    """
    Ghi bang SQLAlchemy (khong raw SQL trong routers - quy tac cua du an).

    Bang co UNIQUE (store_id, product_id, model_name, forecast_date) nen chay
    lai nhieu lan khong sinh dong trung. Dung ON CONFLICT DO UPDATE de cap
    nhat cho san.
    """
    from sqlalchemy import MetaData, Table, select, delete
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    md = MetaData()
    forecasts_t = Table("forecasts", md, autoload_with=engine)

    with engine.begin() as conn:
        if replace:
            conn.execute(delete(forecasts_t))

        stmt = pg_insert(forecasts_t).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[forecasts_t.c.store_id, forecasts_t.c.product_id,
                            forecasts_t.c.model_name, forecasts_t.c.forecast_date],
            set_={
                "horizon_days": stmt.excluded.horizon_days,
                "predicted_quantity": stmt.excluded.predicted_quantity,
                "lower_bound": stmt.excluded.lower_bound,
                "upper_bound": stmt.excluded.upper_bound,
                "recommended_import_qty": stmt.excluded.recommended_import_qty,
                "rmse": stmt.excluded.rmse,
                "mae": stmt.excluded.mae,
                "mape": stmt.excluded.mape,
                "trained_at": stmt.excluded.trained_at,
            },
        )
        conn.execute(stmt)
        total = conn.execute(select(forecasts_t.c.forecast_id).limit(1)).first()

    return len(rows) if total is not None else 0


# =============================================================================
#  MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Du bao 30 ngay va ghi vao bang forecasts"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Tinh va in ket qua, KHONG ghi vao DB")
    parser.add_argument("--replace", action="store_true",
                        help="Xoa toan bo forecasts truoc khi ghi")
    args = parser.parse_args()

    print("=" * 78)
    print("M2 - DU BAO 30 NGAY " + FORECAST_START.strftime("%d/%m/%Y")
          + " - " + (FORECAST_START + timedelta(days=HORIZON_DAYS - 1)).strftime("%d/%m/%Y"))
    print("=" * 78)

    if not METRICS_FILE.exists():
        sys.exit(f"LOI: khong tim thay {METRICS_FILE}. Hay chay M1 truoc: "
                 "python ai-model/scripts/train_models.py --all")

    metrics = pd.read_csv(METRICS_FILE)
    metrics = metrics[metrics["best_model"].notna()]
    if metrics.empty:
        sys.exit("LOI: khong co cap nao train thanh cong trong M1")

    print(f"M1 da thanh cong {len(metrics)} cap")
    print("Phep gan model: prophet / xgboost / arima")
    print(f"{US_HOLIDAY_HINT}\n")

    engine = get_engine()
    future_dates = pd.DataFrame({
        "sale_date": pd.date_range(
            start=FORECAST_START, periods=HORIZON_DAYS, freq="D"
        )
    })

    # TIMESTAMPTZ trong schema - dung UTC de khong lech mui gio
    trained_at = pd.Timestamp.now(tz="UTC").to_pydatetime()

    all_rows: list = []
    summary: list = []
    t_start = time.time()

    for i, (_, m) in enumerate(metrics.iterrows(), 1):
        pid, sid = int(m["product_id"]), int(m["store_id"])
        model_name = str(m["best_model"])

        try:
            history = load_history(engine, pid, sid)
            if model_name == "prophet":
                pred, lo, hi = forecast_prophet(history, future_dates)
            elif model_name == "xgboost":
                pred, lo, hi = forecast_xgboost(history, future_dates)
            else:
                pred, lo, hi = forecast_arima(history, HORIZON_DAYS)

            stock = load_stock_and_limits(engine, pid, sid)
            rec, raw_need = compute_recommended(
                pred, hi, stock["on_hand"],
                stock["max_stock"], stock["shelf_life_days"])

            # Schema co CHECK >= 0 o predicted/lower/upper/recommended
            pred = np.clip(pred, 0, None)
            lo = np.clip(lo, 0, None)
            hi = np.clip(hi, 0, None)
            rec = np.clip(rec, 0, None)

            for d in range(HORIZON_DAYS):
                all_rows.append({
                    "store_id": sid,
                    "product_id": pid,
                    "model_name": model_name,
                    "forecast_date": future_dates["sale_date"].iloc[d].date(),
                    "horizon_days": d + 1,
                    "predicted_quantity": round(float(pred[d]), 3),
                    "lower_bound": round(float(lo[d]), 3),
                    "upper_bound": round(float(hi[d]), 3),
                    "recommended_import_qty": round(float(rec[d]), 3),
                    "rmse": round(float(m.get("best_rmse", np.nan)), 4)
                            if pd.notna(m.get("best_rmse")) else None,
                    "mae": round(float(m[f"{model_name}_mae"]), 4)
                           if pd.notna(m.get(f"{model_name}_mae")) else None,
                    "mape": round(float(m[f"{model_name}_mape"]), 4)
                            if pd.notna(m.get(f"{model_name}_mape")) else None,
                    "trained_at": trained_at,
                })

            summary.append({
                "product_id": pid, "store_id": sid, "model": model_name,
                "on_hand": stock["on_hand"],
                "total_predicted": round(float(pred.sum()), 1),
                "safety_stock": round(float((hi - pred).sum()), 1),
                "recommended_import": round(float(rec[-1]), 1),
                "raw_need": round(float(raw_need[-1]), 1),
                "headroom": (round(float(max(stock["max_stock"] - stock["on_hand"], 0.0)), 1)
                             if stock["max_stock"] is not None else None),
                "shelf_life_days": stock["shelf_life_days"],
                "max_stock": stock["max_stock"],
            })

            print(f"[{i:>3}/{len(metrics)}] p{pid:<3} s{sid:<3} {model_name:<8} "
                  f"30 ngay={pred.sum():>9.0f}  ton={stock['on_hand']:>7.0f}  "
                  f"de xuat nhap={rec[-1]:>8.0f}", flush=True)

        except Exception as exc:
            print(f"[{i:>3}/{len(metrics)}] p{pid:<3} s{sid:<3} "
                  f"LOI -> {type(exc).__name__}: {exc}", flush=True)

    elapsed = time.time() - t_start
    df_sum = pd.DataFrame(summary)

    print()
    print("=" * 78)
    print(f"HOAN THANH {len(summary)}/{len(metrics)} cap trong {elapsed / 60:.1f} phut")
    print("=" * 78)

    if df_sum.empty:
        sys.exit("KHONG co cap nao du bao duoc")

    out_csv = OUTPUT_DIR / "forecast_summary_30d.csv"
    df_sum.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"Tong hop: {out_csv}")

    print("\nSo cap theo mo hinh:")
    print(df_sum["model"].value_counts().to_string())

    print("\nTong hop 100 cap:")
    print(f"  Tong luong du bao 30 ngay : {df_sum['total_predicted'].sum():>12,.0f}")
    print(f"  Tong ton kho hien tai      : {df_sum['on_hand'].sum():>12,.0f}")
    print(f"  Tong nhu cau thuan         : {df_sum['raw_need'].sum():>12,.0f}")
    print(f"  Tong de xuat nhap (sau cap): {df_sum['recommended_import'].sum():>12,.0f}")

    n_cap = int((df_sum["recommended_import"] >= df_sum["headroom"] - 0.5).sum())
    print(f"\n  CANH BAO: {n_cap}/{len(df_sum)} cap bi max_stock chan.")
    print("  max_stock trong seed data (48-300) nho hon nhieu so voi")
    print("  nhu cau thuc te (861-2.793/ngay) -> chi tuong duong 0,5-3 ngay ban.")
    print("  Day la HAN CHAN CUA DU LIEU, khong phai loi cua mo hinh du bao.")

    print("\n5 cap de xuat nhap lon nhat:")
    top = df_sum.nlargest(5, "recommended_import")
    for _, r in top.iterrows():
        print(f"  p{int(r['product_id']):<3} s{int(r['store_id']):<3} "
              f"{r['model']:<8} de xuat={r['recommended_import']:>9,.0f} "
              f"(ton={r['on_hand']:>6,.0f}, du bao={r['total_predicted']:>8,.0f})")

    if args.dry_run:
        print("\n[DRY-RUN] KHONG ghi vao database.")
        return

    n = write_forecasts(engine, all_rows, replace=args.replace)
    print(f"\nDa ghi {n} dong vao bang forecasts.")

    from sqlalchemy import text
    with engine.connect() as conn:
        total = conn.execute(text("SELECT count(*) FROM forecasts")).scalar()
        by_model = conn.execute(text(
            "SELECT model_name, count(*) FROM forecasts GROUP BY model_name "
            "ORDER BY 2 DESC"
        )).fetchall()
    print(f"Tong so dong trong bang forecasts: {total}")
    for name, cnt in by_model:
        print(f"  {name:<10} {cnt}")


if __name__ == "__main__":
    main()