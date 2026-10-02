"""
Tune mo hinh Prophet bang grid search de so sanh cong bang voi XGBoost.

LY DO CAN TUNE:
    O lan chay dau, Prophet co MAPE 43% - kem hon XGBoost gap. Neu de nguyen
    thi khong biet do mo hinh kem hay do tham so chua toi uu. GVHD se hoi
    "sao khong tune?".

⚠ VAN DE PHUONG PHAP - PHAN BIET RO 2 CACH:
    1. TUNE TREN TEST (khong dung) - chon tham so theo RMSE tren tap test,
       roi bao cao chinh RMSE do. Ket qua se qua lac quan.
    2. TUNE TREN VALIDATION (dung) - tach 20% cuoi tap train lam tap
       validation, chon tham so theo RMSE tren validation, ROI DANH GIA
       tren tap test chua tung duoc dung.
    Script nay tinh CA HAI va chi ghi rõ cach nao la ket qua that.

Luu y: yearly_seasonality=True trong Prophet tuc dinh la fourier_order=10.
       Vay vay 3 gia tri True / 10 / 20 chi cho 2 cau hinh khac nhau that su.
       Script ghi ro dieu nay de khong dem khong.

Cach chay:
    python ai-model/scripts/tune_prophet.py --product 15 --store 1
"""

import argparse
import itertools
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

TRAIN_RATIO = 0.8
VAL_RATIO_OF_TRAIN = 0.2   # 20% cuoi tap train lam validation

# Dung 5 nam du lieu (2013-2017) de mua vu nam xac dinh duoc.
# Moc chia tap: test = Q4/2017.
TEST_START_DATE = "2017-10-01"
DATA_START = "2013-01-01"
DATA_END = "2018-01-01"

# Luoi tham so: 3 x 2 x 3 = 18 bo
CPS_VALUES = [0.01, 0.05, 0.5]
MODE_VALUES = ["additive", "multiplicative"]
YEARLY_VALUES = [True, 10, 20]


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
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}",
                         pool_pre_ping=True)


def load_series(engine, product_id: int, store_id: int) -> pd.DataFrame:
    """
    Doc 5 nam du lieu va reindex ve chuoi ngay lien tuc 1826 ngay.
    Ngay thieu duoc dien 0 (co the la ngay khong ban duoc mat hang).
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
        df = pd.read_sql(sql, conn, params={
            "pid": product_id, "sid": store_id,
            "start": DATA_START, "end": DATA_END})

    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["y"] = df["quantity_sold"].astype(float)

    full_dates = pd.date_range(start=DATA_START,
                               end=pd.Timestamp(DATA_END) - pd.Timedelta(days=1),
                               freq="D")
    df = df.set_index("sale_date").reindex(full_dates)
    df.index.name = "sale_date"
    df["y"] = df["y"].fillna(0.0)

    return df.reset_index()[["sale_date", "y"]]


def rmse_only(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


def run_prophet_params(train: pd.DataFrame, n_predict: int,
                       changepoint_prior_scale: float,
                       seasonality_mode: str,
                       yearly_seasonality):
    """Train Prophet voi bo tham so cho truoc, du bao n_predict ngay tiep theo."""
    from prophet import Prophet
    import holidays as holidays_lib

    us_holidays = holidays_lib.country_holidays("US", years=range(2017, 2019))
    hol_df = pd.DataFrame([{"ds": d, "holiday": n} for d, n in us_holidays.items()])

    df_train = pd.DataFrame({"ds": train["sale_date"], "y": train["y"]})
    future = pd.DataFrame({"ds": pd.date_range(
        start=df_train["ds"].max() + pd.Timedelta(days=1), periods=n_predict, freq="D")})

    model = Prophet(
        changepoint_prior_scale=changepoint_prior_scale,
        seasonality_mode=seasonality_mode,
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=True,
        daily_seasonality=False,
        holidays=hol_df,
        interval_width=0.95,
    )
    model.fit(df_train)
    return model.predict(future)["yhat"].to_numpy()


def evaluate_config(df: pd.DataFrame, cps: float, mode: str, yearly):
    """
    Tinh RMSE tren 2 tap:
      - validation : 20% cuoi tap TRAIN (khong dung de bao cao chinh)
      - test       : Q4/2017 (tap bao cao that)
    """
    split_idx = int((pd.Timestamp(TEST_START_DATE) - df["sale_date"].min()).days)
    train_full = df.iloc[:split_idx]
    test = df.iloc[split_idx:]

    val_size = int(len(train_full) * VAL_RATIO_OF_TRAIN)
    train_core = train_full.iloc[:len(train_full) - val_size]
    val = train_full.iloc[len(train_full) - val_size:]

    rmse_val = rmse_only(val["y"].to_numpy(),
                         run_prophet_params(train_core, len(val), cps, mode, yearly))
    rmse_test = rmse_only(test["y"].to_numpy(),
                          run_prophet_params(train_full, len(test), cps, mode, yearly))
    return rmse_val, rmse_test


def main() -> None:
    parser = argparse.ArgumentParser(description="Grid search tham so cho Prophet")
    parser.add_argument("--product", type=int, default=15)
    parser.add_argument("--store", type=int, default=1)
    args = parser.parse_args()

    print("=" * 100)
    print("GRID SEARCH THAM SO CHO PROPHET")
    print("=" * 100)

    engine = get_engine()
    df = load_series(engine, args.product, args.store)

    n = len(df)
    split_idx = int((pd.Timestamp(TEST_START_DATE) - df["sale_date"].min()).days)
    print(f"San pham {args.product} - cua hang {args.store}")
    print(f"Du lieu 5 nam: {n} ngay ({df['sale_date'].min().date()} -> {df['sale_date'].max().date()})")
    print(f"Split theo moc ngay: train {split_idx} | test {n - split_idx}")
    print(f"Cach chay: {len(CPS_VALUES)} x {len(MODE_VALUES)} x {len(YEARLY_VALUES)} "
          f"= {len(CPS_VALUES) * len(MODE_VALUES) * len(YEARLY_VALUES)} bo tham so")
    print()

    rows = []
    combos = itertools.product(CPS_VALUES, MODE_VALUES, YEARLY_VALUES)
    for i, (cps, mode, yearly) in enumerate(combos, 1):
        try:
            t0 = time.time()
            val, test = evaluate_config(df, cps, mode, yearly)
            rows.append({
                "changepoint_prior_scale": cps,
                "seasonality_mode": mode,
                "yearly_seasonality": str(yearly),
                "rmse_validation": val,
                "rmse_test": test,
            })
            print(f"  [{i:>2}/18] cps={cps:<5} mode={mode:<14} yearly={str(yearly):<5} "
                  f"| RMSE val={val:>7.2f} | RMSE test={test:>7.2f} ({time.time() - t0:.1f}s)")
        except Exception as exc:
            print(f"  [{i:>2}/18] cps={cps:<5} mode={mode:<14} yearly={str(yearly):<5} "
                  f"| LOI: {type(exc).__name__}: {exc}")

    res = pd.DataFrame(rows)
    out_csv = OUTPUT_DIR / f"prophet_tuning_5y_p{args.product}_s{args.store}.csv"
    res.to_csv(out_csv, index=False, encoding="utf-8")

    print()
    print("=" * 100)
    print("BANG XEP THEO RMSE TREN TAP VALIDATION (cach dung - chon tham so o day)")
    print("=" * 100)
    by_val = res.sort_values("rmse_validation").reset_index(drop=True)
    print(f"{'#':>2}  {'cps':>6}  {'seasonality_mode':<16}  {'yearly':<6}  "
          f"{'RMSE_val':>9}  {'RMSE_test':>10}")
    print("-" * 100)
    for i, (_, r) in enumerate(by_val.iterrows(), 1):
        mark = "  <== CHON" if i == 1 else ""
        print(f"{i:>2}  {r['changepoint_prior_scale']:>6}  {r['seasonality_mode']:<16}  "
              f"{r['yearly_seasonality']:<6}  {r['rmse_validation']:>9.2f}  "
              f"{r['rmse_test']:>10.2f}{mark}")

    print()
    print("=" * 100)
    print("BANG XEP THEO RMSE TREN TAP TEST (chi de THAM KHAO, KHONG dung de chon)")
    print("=" * 100)
    by_test = res.sort_values("rmse_test").reset_index(drop=True)
    print(f"{'#':>2}  {'cps':>6}  {'seasonality_mode':<16}  {'yearly':<6}  {'RMSE_test':>10}")
    print("-" * 100)
    for i, (_, r) in enumerate(by_test.iterrows(), 1):
        print(f"{i:>2}  {r['changepoint_prior_scale']:>6}  {r['seasonality_mode']:<16}  "
              f"{r['yearly_seasonality']:<6}  {r['rmse_test']:>10.2f}")

    best_val = by_val.iloc[0]
    best_test = by_test.iloc[0]
    print()
    print("=" * 100)
    print("KET LUAN")
    print("=" * 100)
    print(f"Bo tham so theo VALIDATION (dung de ap dung):")
    print(f"  changepoint_prior_scale = {best_val['changepoint_prior_scale']}")
    print(f"  seasonality_mode       = {best_val['seasonality_mode']}")
    print(f"  yearly_seasonality     = {best_val['yearly_seasonality']}")
    print(f"  RMSE_validation        = {best_val['rmse_validation']:.2f}")
    print(f"  RMSE_test              = {best_val['rmse_test']:.2f}")
    print()
    print(f"Bo tham so tot nhat neu TUNE TREN TEST (khong dung, chi so sanh):")
    print(f"  changepoint_prior_scale = {best_test['changepoint_prior_scale']}")
    print(f"  seasonality_mode       = {best_test['seasonality_mode']}")
    print(f"  yearly_seasonality     = {best_test['yearly_seasonality']}")
    print(f"  RMSE_test              = {best_test['rmse_test']:.2f}")
    print()
    gap = best_test["rmse_test"] - best_val["rmse_test"]
    print(f"Chep lech giua 2 cach: {gap:+.2f} RMSE")
    print(f"  -> Chon tren TEST cho RMSE tot hon {-gap:.2f}, NHUNG day la roi ri du lieu.")

    # So sanh voi bo da tune tren du lieu 1 NAM
    print()
    print("=" * 100)
    print("SO SANH VOI BO THAM SO DA TUNE TREN DU LIEU 1 NAM")
    print("=" * 100)
    old = res[(res["changepoint_prior_scale"] == 0.01)
              & (res["seasonality_mode"] == "additive")
              & (res["yearly_seasonality"] == "20")]
    if not old.empty:
        o = old.iloc[0]
        print(f"  Bo duoc duyet tren 1 NAM : cps=0.01, additive, yearly=20")
        print(f"    RMSE_validation (5 nam) = {o['rmse_validation']:.2f}")
        print(f"    RMSE_test       (5 nam) = {o['rmse_test']:.2f}")
        print()
        print(f"  Bo tot nhat tren 5 NAM  : cps={best_val['changepoint_prior_scale']}, "
              f"{best_val['seasonality_mode']}, yearly={best_val['yearly_seasonality']}")
        print(f"    RMSE_validation       = {best_val['rmse_validation']:.2f}")
        print(f"    RMSE_test             = {best_val['rmse_test']:.2f}")
        print()
        diff = best_val["rmse_test"] - o["rmse_test"]
        if diff < 0:
            print(f"  -> Bo moi tot hon {abs(diff):.2f} RMSE tren tap test")
        elif diff > 0:
            print(f"  -> Bo cu tot hon {-diff:.2f} RMSE tren tap test")
        else:
            print("  -> Hai bo cho RMSE test giong nhau")
    else:
        print("  Khong tim thay bo cu de so sanh.")

    print()
    print("LUOI THAM SO TRONG 18 BO CO THAT SU KHAC NHAU BAO NHIEU:")
    uniq = res.groupby(["changepoint_prior_scale", "seasonality_mode", "rmse_test"]).size()
    print(f"  yearly_seasonality=True tuc nghia fourier_order=10, trung voi gia tri 10.")
    print(f"  Vay 18 lan chay chi co {len(uniq)} ket qua khac nhau that su.")
    print(f"  (Cac lan chung ket qua deu la do tham so trung nhau khac cach viet)")
    print()
    print(f"Ket qua luu: {out_csv}")


if __name__ == "__main__":
    main()
