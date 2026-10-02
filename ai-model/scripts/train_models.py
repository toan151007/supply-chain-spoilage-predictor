"""
Huyen luyen va danh gia 3 mo hinh du bao nhu cau cho chuoi luong hang ngan.

Mo hinh so sanh (dung 3 mo hinh da chot o Chuong 2):
    - Prophet     : mo hinh co so, tu dong phat hien changepoint
    - XGBoost     : mo hinh chinh, su dung dac trung ngoai + feature importance
    - ARIMA       : mo hinh doi chung thong ke

Cau hinh da chot (03/10/2026):
    - Dung TOAN BO 5 nam du lieu (2013-2017) de Prophet uoc luong duoc mua
      vu nam. Can it nhat 730 ngay, neu chi 1 nam Prophet bao loi va RMSE
      tu 9,98 tang len 23,20.
    - Chia theo moc NGAY 2017-10-01: train 1.734 ngay, test 92 ngay.
      KHONG chia 80/20 va KHONG chia ngau nhien: tach ngay giu cac mua,
      va ngau nhien se lam roi du lieu tuong lai vao tap train.
    - Reindex chuoi ve dung 1.826 ngay lien tuc, ngay thieu duoc dien 0.
      View v_daily_sales chi co dong cho ngay co phat sinh giao dich, nen
      khong reindex thi cac ham lag/rolling se lech ngay va hoc sai.
    - Dung bo ngay le MY cho ca Prophet va XGBoost de so sanh cong bang.
      Luu y: day la du lieu Hoa Ky, khong phai Viet Nam.
    - 15 dac trung cho XGBoost: lag_1..7, lag_14, lag_28, roll_mean_7,
      roll_mean_28, dow, month, is_weekend, trend, is_holiday.

Cach chay:
    # test 1 cap truoc
    python ai-model/scripts/train_models.py --product 15 --store 1

    # chay toan bo 100 cap
    python ai-model/scripts/train_models.py --all

Ket qua duoc luu vao ai-model/outputs/
"""

import argparse
import json
import logging
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "ai-model" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 10 san pham da chot - xem AGENTS.md
PRODUCT_IDS = [45, 8, 15, 13, 25, 11, 28, 48, 38, 18]

FORECAST_HORIZON = 30

# Moc chia tap: dung 5 nam du lieu (2013-2017) de Prophet uoc luong duoc
# mua vu nam (can it nhat 2 nam theo canh bao cua Prophet).
# Test = quy cuoi nam 2017, dung ngay 01/10/2017 lam moc.
TEST_START_DATE = "2017-10-01"
DATA_START = "2013-01-01"
DATA_END = "2018-01-01"

# Tham so Prophet da duyet qua grid search 18 bo tren du lieu 5 NAM
# (2013-2017) va CHON THEO TAP VALIDATION - xem tune_prophet.py
# va ai-model/outputs/prophet_tuning_5y_p15_s1.csv.
#
#   cps 0,01 + additive           -> RMSE_val 10,60 | RMSE_test  9,92
#   cps 0,5  + additive           -> RMSE_val 11,47 | RMSE_test  9,76  <- bien theo test = ro ri du lieu
#   cps 0,01 + multiplicative + 20-> RMSE_val 10,49 | RMSE_test 10,23  <- CHON
#
# Khong chon bo co RMSE_test thap hon, vi chon tham so tren tap test la
# ro ri du lieu: con so bao cao se khong con trung thuc.
PROPHET_PARAMS = {
    "changepoint_prior_scale": 0.01,
    "seasonality_mode": "multiplicative",
    "yearly_seasonality": 20,
}

# Cung ngay le Hoa Ky dung chung cho ca Prophet va XGBoost.
# Du lieu la cua Walmart (Hoa Ky) nen KHONG dung ngay le Viet Nam.
US_HOLIDAY_NAMES = [
    "New Year's Day", "Martin Luther King Jr. Day", "Presidents Day",
    "Memorial Day", "Independence Day", "Labor Day", "Columbus Day",
    "Veterans Day", "Thanksgiving", "Christmas",
]

LOG_FILE = OUTPUT_DIR / "train_log.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)


def log(msg: str, level: str = "INFO") -> None:
    getattr(logging, level.lower())(msg)
    print(msg)


# =============================================================================
#  DATABASE
# =============================================================================

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
        sys.exit("LOI: khong tim thay DB_PASSWORD")

    user = os.getenv("DB_USER", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "spoilage_predictor")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url, pool_pre_ping=True)


def load_series(engine, product_id: int, store_id: int) -> pd.DataFrame:
    """
    Doc chuoi doanh so 1 cap (san pham x cua hang) tu view v_daily_sales.

    Lay TOAN BO 2013-2017 roi reindex ve dung 1826 ngay lien tuc.
    Cac ngay khong co du lieu duoc dien 0 - day co the la ngay khong ban
    duoc mat hang, va la truong hop censored demand duoc mo ta trong
    Chuong 2. So ngay bi dien 0 duoc ghi lai de bao cao trung thuc.
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
            params={
                "pid": product_id, "sid": store_id,
                "start": DATA_START, "end": DATA_END,
            },
        )

    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["y"] = df["quantity_sold"].astype(float)

    # Reindex ve chuoi ngay lien tuc
    full_dates = pd.date_range(start=DATA_START, end=pd.Timestamp(DATA_END) - pd.Timedelta(days=1),
                               freq="D")
    df = df.set_index("sale_date").reindex(full_dates)
    df.index.name = "sale_date"

    missing_days = int(df["y"].isna().sum())
    df["y"] = df["y"].fillna(0.0)

    out = df.reset_index()
    out.attrs["missing_days"] = missing_days
    out.attrs["zero_days"] = int((out["y"] == 0).sum())
    return out[["sale_date", "y"]]


# =============================================================================
#  CHI TIE DANH GIA
# =============================================================================

def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Tinh RMSE, MAE, MAPE.

    Luu y MAPE: bo qua cac diem co y_true = 0. Neu giu lai, do le toi vo cuc
    o nhung ngay khong ban duoc gi. Du lieu hien khong co ngay bang 0,
    nhung van giu ma de an toan khi dua sang du lieu khac.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_true - y_pred

    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(np.abs(err)))

    mask = y_true != 0
    if mask.sum() > 0:
        mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
    else:
        mape = float("nan")

    return {"rmse": rmse, "mae": mae, "mape": mape}


# =============================================================================
#  MO HINH 1: PROPHET
# =============================================================================

def run_prophet(train: pd.DataFrame, test: pd.DataFrame, future: pd.DataFrame):
    """
    Prophet tu tach trend + seasonality + holiday.
    Dung chung bo ngay le Hoa Ky voi XGBoost de so sanh cong bang.
    """
    from prophet import Prophet
    import holidays as holidays_lib

    us_holidays = holidays_lib.country_holidays("US", years=range(2013, 2019))

    # Prophet yeu cau holidays la DataFrame co 2 cot "ds" va "holiday",
    # khong chap nhan dict truc tiep.
    hol_df = pd.DataFrame(
        [{"ds": d, "holiday": n} for d, n in us_holidays.items()]
    )

    df_train = pd.DataFrame({"ds": train["sale_date"], "y": train["y"]})
    df_future = pd.DataFrame({"ds": future["sale_date"]})

    model = Prophet(
        changepoint_prior_scale=PROPHET_PARAMS["changepoint_prior_scale"],
        seasonality_mode=PROPHET_PARAMS["seasonality_mode"],
        yearly_seasonality=PROPHET_PARAMS["yearly_seasonality"],
        weekly_seasonality=True,
        daily_seasonality=False,
        holidays=hol_df,
        interval_width=0.95,
    )
    model.fit(df_train)

    forecast = model.predict(df_future)
    return forecast["yhat"].to_numpy(), forecast["yhat_lower"].to_numpy(), forecast["yhat_upper"].to_numpy()


# =============================================================================
#  MO HINH 2: XGBOOST
# =============================================================================

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tao dac trung cho XGBoost.

    KHONG dung future value trong bat ky dac trung nao - chi dung gia tri
    trong qua. Neu dung y.shift(-1) se bi ro ri du lieu va RMSE se dep
    gia ma khong co y nghia.
    """
    out = df.copy()
    for lag in [1, 2, 3, 4, 5, 6, 7, 14, 28]:
        out[f"lag_{lag}"] = out["y"].shift(lag)
    out["roll_mean_7"] = out["y"].shift(1).rolling(window=7).mean()
    out["roll_mean_28"] = out["y"].shift(1).rolling(window=28).mean()

    out["dow"] = out["sale_date"].dt.dayofweek
    out["month"] = out["sale_date"].dt.month
    out["is_weekend"] = (out["dow"] >= 5).astype(int)
    out["trend"] = np.arange(len(out))

    return out


def run_xgboost(train_feat: pd.DataFrame, target_rows: pd.DataFrame):
    """
    Huyen luyen XGBoost tren tap train, du bao cho cac dong trong target_rows.

    Dac trung lag duoc tinh tren TOAN BO chuoi truoc, roi cat theo vi tri.
    Nho vay dac trung cua ngay can du bao van dung gia tri quan sat duoc
    (khong phai NaN) ma khong dung du lieu tuong lai.
    """
    import holidays as holidays_lib
    from xgboost import XGBRegressor

    us_holidays = holidays_lib.country_holidays("US", years=range(2013, 2019))

    feature_cols = [
        "lag_1", "lag_2", "lag_3", "lag_4", "lag_5", "lag_6", "lag_7",
        "lag_14", "lag_28", "roll_mean_7", "roll_mean_28",
        "dow", "month", "is_weekend", "trend",
    ]

    # Cot is_holiday phai duoc them TRUOC khi chon dac trung,
    # neu khong se bao loi KeyError.
    base_train = train_feat.copy()
    base_train["is_holiday"] = base_train["sale_date"].isin(us_holidays).astype(int)

    all_cols = feature_cols + ["is_holiday"]

    X_train = base_train[all_cols]

    # 28 ngay lag dau tien khong co duoc gia tri -> bo cac dong day
    X_train = X_train.dropna()
    y_train = base_train.loc[X_train.index, "y"]

    model = XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    # Phai them is_holiday VAO target_rows TRUOC khi chon cot,
    # neu khong KeyError khi truy cap cot chua ton tai.
    target_rows = target_rows.copy()
    target_rows["is_holiday"] = target_rows["sale_date"].isin(us_holidays).astype(int)
    X_pred = target_rows[all_cols]

    pred = model.predict(X_pred)

    return pred, model, all_cols


# =============================================================================
#  MO HINH 3: ARIMA
# =============================================================================

def run_arima(train: pd.DataFrame, n_periods: int):
    """ARIMA tu chon bang AIC, co phan mua vu theo tuan (m=7)."""
    from statsmodels.tsa.arima.model import ARIMA

    # Thu nho don vi chuoi de ARIMA chay nhanh tren 100 cap
    train_smooth = train["y"].rolling(window=3, min_periods=1).mean().fillna(train["y"])

    best = None
    best_aic = float("inf")
    for order in [(1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2), (1, 0, 1), (2, 0, 1)]:
        try:
            fitted = ARIMA(train_smooth.to_numpy(), order=order,
                           seasonal_order=(0, 0, 0, 0)).fit()
            if fitted.aic < best_aic:
                best_aic = fitted.aic
                best = fitted
        except Exception:
            continue

    if best is None:
        raise RuntimeError("ARIMA: khong tim duoc cap (p,d,q) phu hop")

    pred = best.forecast(steps=n_periods)
    # Khoang tin cay: dua tren sai so cua phan du train
    resid = best.resid
    sigma = float(np.std(resid))
    lower = pred - 1.96 * sigma
    upper = pred + 1.96 * sigma
    return np.asarray(pred), np.clip(lower, 0, None), np.clip(upper, None, None)


# =============================================================================
#  CHU TRINH 1 CAP
# =============================================================================

def evaluate_pair(df: pd.DataFrame, product_id: int, store_id: int) -> dict:
    """Train + danh gia 3 mo hinh tren 1 cap. Tra ve dict ket qua."""
    # Moc chia: test bat dau tu 2017-10-01 (khong dung 80/20)
    split_idx = int((pd.Timestamp(TEST_START_DATE) - df["sale_date"].min()).days)
    train = df.iloc[:split_idx].copy()
    test = df.iloc[split_idx:].copy().reset_index(drop=True)

    last_train_date = train["sale_date"].max()
    future_dates = pd.date_range(start=last_train_date + pd.Timedelta(days=1),
                                 periods=len(test), freq="D")
    future = pd.DataFrame({"sale_date": future_dates})

    log(f"  chuoi   : {len(df)} ngay ({df['sale_date'].min().date()} -> "
        f"{df['sale_date'].max().date()})")
    log(f"  split   : train {len(train)} ngay (-> {last_train_date.date()}), "
        f"test {len(test)} ngay ({test['sale_date'].min().date()} -> {test['sale_date'].max().date()})")
    missing = df.attrs.get("missing_days", 0)
    zeros = df.attrs.get("zero_days", 0)
    log(f"  ngay 0  : {zeros} ngay (trong do {missing} ngay thieu du lieu, duoc dien 0)")

    results = {"product_id": product_id, "store_id": store_id,
               "train_days": len(train), "test_days": len(test)}

    y_test = test["y"].to_numpy()

    # --- Prophet ---
    try:
        t0 = time.time()
        pred, lo, hi = run_prophet(train, test, future)
        m = metrics(y_test, pred)
        results.update({"prophet_rmse": m["rmse"],
                        "prophet_mae": m["mae"],
                        "prophet_mape": m["mape"]})
        log(f"  prophet : RMSE={m['rmse']:8.2f}  MAE={m['mae']:8.2f}  "
            f"MAPE={m['mape']:6.2f}%  ({time.time() - t0:.1f}s)")
    except Exception as exc:
        log(f"  prophet : LOI -> {type(exc).__name__}: {exc}", "ERROR")
        logging.exception("prophet failed")

    # --- XGBoost ---
    try:
        t0 = time.time()
        full = build_features(df)
        train_feat = full.iloc[:split_idx]
        target_rows = full.iloc[split_idx:]
        pred, _, feat_cols = run_xgboost(train_feat, target_rows)
        m = metrics(y_test, pred)
        results.update({"xgboost_rmse": m["rmse"],
                        "xgboost_mae": m["mae"],
                        "xgboost_mape": m["mape"]})
        log(f"  xgboost : RMSE={m['rmse']:8.2f}  MAE={m['mae']:8.2f}  "
            f"MAPE={m['mape']:6.2f}%  ({time.time() - t0:.1f}s)")
    except Exception as exc:
        log(f"  xgboost : LOI -> {type(exc).__name__}: {exc}", "ERROR")
        logging.exception("xgboost failed")

    # --- ARIMA ---
    try:
        t0 = time.time()
        pred, lo, hi = run_arima(train, len(test))
        m = metrics(y_test, pred)
        results.update({"arima_rmse": m["rmse"],
                        "arima_mae": m["mae"],
                        "arima_mape": m["mape"]})
        log(f"  arima   : RMSE={m['rmse']:8.2f}  MAE={m['mae']:8.2f}  "
            f"MAPE={m['mape']:6.2f}%  ({time.time() - t0:.1f}s)")
    except Exception as exc:
        log(f"  arima   : LOI -> {type(exc).__name__}: {exc}", "ERROR")
        logging.exception("arima failed")

    # Chon mo hinh tot nhat theo RMSE
    candidates = {
        name: results[f"{name}_rmse"]
        for name in ("prophet", "xgboost", "arima")
        if results.get(f"{name}_rmse") is not None
        and not pd.isna(results.get(f"{name}_rmse"))
    }
    if candidates:
        best_model = min(candidates, key=candidates.get)
        results["best_model"] = best_model
        results["best_rmse"] = candidates[best_model]
        log(f"  -> MO HINH TOT NHAT: {best_model.upper()} (RMSE={candidates[best_model]:.2f})")
    else:
        results["best_model"] = None
        log("  -> KHONG co mo hinh nao train thanh cong", "ERROR")

    return results


# =============================================================================
#  MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Train va danh gia 3 mo hinh du bao")
    parser.add_argument("--product", type=int, help="product_id can test")
    parser.add_argument("--store", type=int, help="store_id can test")
    parser.add_argument("--all", action="store_true", help="Chay ca 100 cap")
    args = parser.parse_args()

    print("=" * 78)
    print("HUYEN LUYEN VA DANH GIA 3 MO HINH DU BAO")
    print("=" * 78)
    log("=" * 60)
    log("Bat dau chay")

    engine = get_engine()

    if args.all:
        pairs = [(p, s) for p in PRODUCT_IDS for s in range(1, 11)]
        out_name = "model_metrics_all.csv"
    elif args.product and args.store:
        pairs = [(args.product, args.store)]
        out_name = f"model_metrics_p{args.product}_s{args.store}.csv"
    else:
        sys.exit("Can chi dinh --product VA --store, hoac dung --all")

    print(f"Tong so cap se chay: {len(pairs)}")
    print(f"Log: {LOG_FILE}")
    print()

    all_results = []
    t_start = time.time()

    for i, (pid, sid) in enumerate(pairs, 1):
        print(f"[{i}/{len(pairs)}] product_id={pid}  store_id={sid}")
        try:
            df = load_series(engine, pid, sid)
            if len(df) < 100:
                log(f"  BO QUA: chi co {len(df)} ngay du lieu", "WARNING")
                continue
            if df.attrs.get("zero_days", 0) > len(df) * 0.5:
                log("  BO QUA: qua nhieu ngay ban = 0, du lieu khong dung duoc", "WARNING")
                continue
            res = evaluate_pair(df, pid, sid)
            all_results.append(res)
        except Exception as exc:
            log(f"  LOI CAP: {type(exc).__name__}: {exc}", "ERROR")
            logging.exception("pair failed")
            continue

        # Luu ket qua tam thoi sau moi cap de khong mat cong neu crash
        pd.DataFrame(all_results).to_csv(
            OUTPUT_DIR / out_name, index=False, encoding="utf-8"
        )

    elapsed = time.time() - t_start

    print()
    print("=" * 78)
    print(f"HOAN THANH trong {elapsed / 60:.1f} phut")
    print("=" * 78)

    df_res = pd.DataFrame(all_results)
    if df_res.empty:
        print("KHONG co ket qua")
        sys.exit(1)

    print(f"Ket qua da luu: {OUTPUT_DIR / out_name}")
    print()

    for model in ["prophet", "xgboost", "arima"]:
        if model not in df_res.columns:
            continue
        col_rmse = f"{model}_rmse"
        if col_rmse not in df_res.columns:
            continue
        ok = df_res[df_res[col_rmse].notna()]
        if ok.empty:
            print(f"{model.upper():9} : KHONG co cap nao thanh cong")
            continue
        print(f"{model.upper():9} : thanh cong {len(ok):>3}/{len(df_res)} cap | "
              f"RMSE trung binh {ok[col_rmse].mean():>8.2f} | "
              f"tot nhat {ok[col_rmse].min():>8.2f} | "
              f"xau nhat {ok[col_rmse].max():>8.2f}")

    if "best_model" in df_res.columns:
        print()
        print("So cap chien thang theo mo hinh:")
        print(df_res["best_model"].value_counts().to_string())


if __name__ == "__main__":
    main()
