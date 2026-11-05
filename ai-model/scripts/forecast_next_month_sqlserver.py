"""
M2 (SQL Server) - du bao 30 ngay 01/01/2018 - 30/01/2018 va ghi bang forecasts.

Vi sao co script nay
--------------------
`forecast_next_month.py` duoc viet cho PostgreSQL (psycopg2 + pg_insert +
FILTER (WHERE ...)) nen khong chay duoc tren SQL Server. Khi chuyen sang SQL
Server, buoc nap du lieu `scripts/load_sqlserver_data.py` da thay the no bang
mot phep tinh gian luoc:

    daily = total_predicted / 30      # lap lai cho ca 30 ngay
    lower = daily * 0.9               # khong phai khoang tin cay that
    upper = daily * 1.1
    rmse  = 9.97, mae = 7.94, mape = 10.43   # so trung binh toan he thong

Hau qua: bang `forecasts` khong con la du bao tung ngay. Moi ngay trong 30
ngay co cung mot gia tri, nen bang nay khong the dung de doi chieu voi doanh
so thuc te theo ngay, va chi so sai so tren tung dong khong phai sai so cua
cap san pham x cua hang do.

Script nay lam lai dung viec do:
    1. Doc lich su 2013-2017 tu `v_daily_sales` (pyodbc).
    2. Chon mo hinh thang cuoc cua tung cap theo `model_metrics_all.csv`.
    3. Train lai tren TOAN BO du lieu, du bao 30 ngay (khong cat test set).
    4. Ghi `predicted_quantity` / `lower_bound` / `upper_bound` THAT cua tung
       ngay, `horizon_days = 1..30`, `model_name` dung ten mo hinh da thang.
    5. Ghi `rmse` / `mae` / `mape` cua CHINH cap do (khong phai so toan he thong).
    6. Xuat `forecasts_30d.csv` de `load_sqlserver_data.py` nap lai duoc.

Cot `recommended_import_qty` giu nguyen gia tri snapshot cua lan chay M2
(`forecast_summary_30d.csv`). Ly do: API `/recommendations/import` KHONG doc
cot nay - `sp_Recommendations_Import` tu tinh lai tu `SUM(predicted_quantity)`
va ton kho hien tai. Neu tinh lai o day theo ton kho SQL Server hien tai thi
moi cap deu ra 0 (ton kho seed 393 > max_stock 48), lam sai lech tai lieu ma
khong cai thien duoc gi.

Cac ham mo hinh duoc import lai tu `forecast_next_month.py` - chung khong phu
thuoc vao he quan tri CSDL, chi phan doc/ghi du lieu la phai viet lai.

Cach chay:
    python ai-model/scripts/forecast_next_month_sqlserver.py --dry-run
    python ai-model/scripts/forecast_next_month_sqlserver.py
    python ai-model/scripts/forecast_next_month_sqlserver.py --limit 3
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyodbc

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "ai-model" / "outputs"

FORECAST_START = date(2018, 1, 1)
HORIZON_DAYS = 30
DATA_START = "2013-01-01"
DATA_END = "2018-01-01"

DAILY_CSV = OUTPUT_DIR / "forecasts_30d.csv"
SUMMARY_CSV = OUTPUT_DIR / "forecast_summary_30d.csv"

# =============================================================================
#  NAP MODULE MO HINH (dung chung voi ban PostgreSQL)
# =============================================================================

def load_model_module():
    path = Path(__file__).with_name("forecast_next_month.py")
    spec = importlib.util.spec_from_file_location("forecast_next_month", path)
    if spec is None or spec.loader is None:
        sys.exit(f"LOI: khong nap duoc {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =============================================================================
#  KET NOI SQL SERVER
# =============================================================================

def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    for key in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        if os.getenv(key):
            values[key] = os.environ[key]
    missing = [k for k in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME")
               if not values.get(k)]
    if missing:
        sys.exit(f"LOI: thieu cau hinh {', '.join(missing)} trong .env")
    return values


def connect() -> pyodbc.Connection:
    env = read_env()
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={env['DB_HOST']};"
        f"DATABASE={env['DB_NAME']};"
        f"UID={env['DB_USER']};"
        f"PWD={env['DB_PASSWORD']};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, timeout=60)


# =============================================================================
#  DOC DU LIEU
# =============================================================================

def load_history(conn: pyodbc.Connection, product_id: int, store_id: int) -> pd.DataFrame:
    """
    Doc chuoi doanh so 1 cap tu v_daily_sales va reindex ve du 1826 ngay.

    Reindex la BAT BUOC: view chi co dong cho ngay co phat sinh giao dich.
    Thieu buoc nay thi cac dac trung lag/rolling lech ngay va mo hinh hoc sai.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT sale_date, quantity_sold FROM dbo.v_daily_sales "
        "WHERE product_id = ? AND store_id = ? "
        "AND sale_date >= ? AND sale_date < ? "
        "ORDER BY sale_date",
        product_id, store_id, DATA_START, DATA_END,
    )
    rows = cur.fetchall()

    frame = pd.DataFrame(
        [(r[0], float(r[1])) for r in rows],
        columns=["sale_date", "y"],
    )
    frame["sale_date"] = pd.to_datetime(frame["sale_date"])

    full_dates = pd.date_range(
        start=DATA_START,
        end=pd.Timestamp(DATA_END) - pd.Timedelta(days=1),
        freq="D",
    )
    frame = frame.set_index("sale_date").reindex(full_dates)
    frame.index.name = "sale_date"
    frame["y"] = frame["y"].fillna(0.0)

    return frame.reset_index()[["sale_date", "y"]]


def load_stock(conn: pyodbc.Connection, product_id: int, store_id: int) -> dict:
    """Ton kho con han + nguong min/max + han su dung cua san pham."""
    cur = conn.cursor()
    cur.execute(
        "SELECT "
        "  COALESCE(SUM(CASE WHEN i.quantity > 0 "
        "        AND (i.expiry_date IS NULL OR i.expiry_date >= CAST(GETDATE() AS DATE)) "
        "        THEN i.quantity ELSE 0 END), 0) AS on_hand, "
        "  p.min_stock, p.max_stock, p.shelf_life_days "
        "FROM dbo.products p "
        "LEFT JOIN dbo.inventory i "
        "       ON i.product_id = p.product_id AND i.store_id = ? "
        "WHERE p.product_id = ? "
        "GROUP BY p.min_stock, p.max_stock, p.shelf_life_days",
        store_id, product_id,
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"khong tim thay san pham {product_id}")

    return {
        "on_hand": float(row[0] or 0),
        "min_stock": float(row[1] or 0),
        "max_stock": float(row[2]) if row[2] is not None else None,
        "shelf_life_days": int(row[3] or 0),
    }


# =============================================================================
#  GHI DU LIEU
# =============================================================================

INSERT_SQL = (
    "INSERT INTO dbo.forecasts ("
    "store_id, product_id, model_name, forecast_date, horizon_days, "
    "predicted_quantity, lower_bound, upper_bound, recommended_import_qty, "
    "rmse, mae, mape, trained_at"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def replace_forecasts(conn: pyodbc.Connection, rows: list[tuple]) -> None:
    """
    Xoa toan bo roi ghi lai trong MOT transaction.

    Bang forecasts khong co du lieu lich su can giu: no la ket qua tinh toan,
    sinh lai duoc tu model + CSV. Xoa truoc de khong con dong cu mang gia tri
    trung binh thang.
    """
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM dbo.forecasts")
        cur.fast_executemany = True
        cur.executemany(INSERT_SQL, rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# =============================================================================
#  MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Du bao 30 ngay (SQL Server) va ghi bang forecasts"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Tinh va xuat CSV, KHONG ghi vao database")
    parser.add_argument("--limit", type=int, default=0,
                        help="Chi chay N cap dau (de test nhanh)")
    args = parser.parse_args()

    model = load_model_module()

    metrics_path = OUTPUT_DIR / "model_metrics_all.csv"
    if not metrics_path.exists():
        sys.exit(f"LOI: khong tim thay {metrics_path}. Chay M1 truoc.")

    metrics = pd.read_csv(metrics_path)
    metrics = metrics[metrics["best_model"].notna()].reset_index(drop=True)
    if args.limit:
        metrics = metrics.head(args.limit)

    # Snapshot cua lan chay M2 goc - dung cho cot recommended_import_qty.
    snapshot: dict[tuple[int, int], float] = {}
    if SUMMARY_CSV.exists():
        previous = pd.read_csv(SUMMARY_CSV)
        for row in previous.itertuples(index=False):
            snapshot[(int(row.product_id), int(row.store_id))] = float(
                row.recommended_import
            )

    print("=" * 78)
    print("M2 (SQL Server) - DU BAO 30 NGAY "
          f"{FORECAST_START:%d/%m/%Y} - "
          f"{(FORECAST_START + timedelta(days=HORIZON_DAYS - 1)):%d/%m/%Y}")
    print("=" * 78)
    print(f"So cap se chay: {len(metrics)}")
    print(f"Model: {metrics['best_model'].value_counts().to_dict()}")
    print()

    conn = connect()

    future_dates = pd.DataFrame({
        "sale_date": pd.date_range(
            start=FORECAST_START, periods=HORIZON_DAYS, freq="D"
        )
    })

    trained_at = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

    all_rows: list[tuple] = []
    csv_rows: list[dict] = []
    summary: list[dict] = []
    failures: list[str] = []

    t_start = time.time()

    for index, metric in enumerate(metrics.itertuples(index=False), 1):
        product_id = int(metric.product_id)
        store_id = int(metric.store_id)
        model_name = str(metric.best_model)
        t_pair = time.time()

        try:
            history = load_history(conn, product_id, store_id)
            if len(history) < 100:
                raise RuntimeError(f"chi co {len(history)} ngay du lieu")

            if model_name == "prophet":
                pred, low, high = model.forecast_prophet(history, future_dates)
            elif model_name == "xgboost":
                pred, low, high = model.forecast_xgboost(history, future_dates)
            else:
                pred, low, high = model.forecast_arima(history, HORIZON_DAYS)

            stock = load_stock(conn, product_id, store_id)

            computed, raw_need = model.compute_recommended(
                pred, high, stock["on_hand"],
                stock["max_stock"], stock["shelf_life_days"],
            )

            # Uu tien snapshot M2; chi tinh lai khi cap chua co trong file.
            snapshot_value = snapshot.get((product_id, store_id))
            if snapshot_value is not None:
                recommended = np.full(HORIZON_DAYS, snapshot_value, dtype=float)
            else:
                recommended = computed

            pred = np.clip(pred, 0, None)
            low = np.clip(low, 0, None)
            high = np.clip(high, 0, None)
            recommended = np.clip(recommended, 0, None)

            rmse = float(metric.best_rmse) if pd.notna(metric.best_rmse) else None
            mae = float(getattr(metric, f"{model_name}_mae"))
            mape = float(getattr(metric, f"{model_name}_mape"))

            for day in range(HORIZON_DAYS):
                forecast_date = FORECAST_START + timedelta(days=day)
                predicted = round(float(pred[day]), 3)
                lower = round(float(low[day]), 3)
                upper = round(float(high[day]), 3)
                rec = round(float(recommended[day]), 3)

                all_rows.append((
                    store_id, product_id, model_name, forecast_date, day + 1,
                    predicted, lower, upper, rec,
                    round(rmse, 4) if rmse is not None else None,
                    round(mae, 4), round(mape, 4), trained_at,
                ))
                csv_rows.append({
                    "store_id": store_id,
                    "product_id": product_id,
                    "model_name": model_name,
                    "forecast_date": forecast_date.isoformat(),
                    "horizon_days": day + 1,
                    "predicted_quantity": predicted,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "recommended_import_qty": rec,
                    "rmse": round(rmse, 4) if rmse is not None else None,
                    "mae": round(mae, 4),
                    "mape": round(mape, 4),
                })

            summary.append({
                "product_id": product_id,
                "store_id": store_id,
                "model": model_name,
                "on_hand": stock["on_hand"],
                "total_predicted": round(float(pred.sum()), 1),
                "safety_stock": round(float((high - pred).sum()), 1),
                "recommended_import": round(float(recommended[-1]), 1),
                "raw_need": round(float(raw_need[-1]), 1),
                "headroom": (
                    round(float(max(stock["max_stock"] - stock["on_hand"], 0.0)), 1)
                    if stock["max_stock"] is not None else None
                ),
                "shelf_life_days": stock["shelf_life_days"],
                "max_stock": stock["max_stock"],
            })

            print(f"[{index:>3}/{len(metrics)}] p{product_id:<3} s{store_id:<3} "
                  f"{model_name:<8} 30 ngay={pred.sum():>9.0f} "
                  f"ton={stock['on_hand']:>7.0f} "
                  f"de xuat={recommended[-1]:>8.0f} "
                  f"({time.time() - t_pair:.1f}s)", flush=True)

        except Exception as exc:
            failures.append(f"p{product_id} s{store_id}: {type(exc).__name__}: {exc}")
            print(f"[{index:>3}/{len(metrics)}] p{product_id:<3} s{store_id:<3} "
                  f"LOI -> {type(exc).__name__}: {exc}", flush=True)

    elapsed = time.time() - t_start

    print()
    print("=" * 78)
    print(f"HOAN THANH {len(summary)}/{len(metrics)} cap trong {elapsed / 60:.1f} phut")
    print("=" * 78)
    if failures:
        print(f"LOI ({len(failures)}):")
        for item in failures:
            print(f"  - {item}")

    if not all_rows:
        sys.exit("KHONG co cap nao du bao duoc")

    daily = pd.DataFrame(csv_rows)
    daily.to_csv(DAILY_CSV, index=False, encoding="utf-8")
    print(f"Chi tiet tung ngay: {DAILY_CSV} ({len(daily):,} dong)")

    summary_frame = pd.DataFrame(summary)
    print(f"Tong hop 30 ngay   : {len(summary_frame)} cap (khong ghi de {SUMMARY_CSV.name})")

    print()
    print("Tong hop:")
    print(f"  Tong luong du bao 30 ngay  : {summary_frame['total_predicted'].sum():>12,.0f}")
    print(f"  Tong ton kho hien tai      : {summary_frame['on_hand'].sum():>12,.0f}")
    print(f"  Tong nhu cau thuan         : {summary_frame['raw_need'].sum():>12,.0f}")
    print(f"  Tong de xuat nhap (sau cap): {summary_frame['recommended_import'].sum():>12,.0f}")

    n_cap = int((summary_frame["recommended_import"]
                 >= summary_frame["headroom"] - 0.5).sum())
    print(f"  So cap bi max_stock chan    : {n_cap}/{len(summary_frame)}")

    if args.dry_run:
        print("\n[DRY-RUN] KHONG ghi vao database.")
        conn.close()
        return

    replace_forecasts(conn, all_rows)
    print(f"\nDa ghi {len(all_rows):,} dong vao bang forecasts.")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dbo.forecasts")
    print(f"Tong so dong trong bang forecasts: {cur.fetchone()[0]:,}")
    cur.execute(
        "SELECT model_name, COUNT(*) AS rows_, "
        "COUNT(DISTINCT CONCAT(product_id, '-', store_id)) AS pairs_ "
        "FROM dbo.forecasts GROUP BY model_name ORDER BY rows_ DESC"
    )
    for name, rows_, pairs in cur.fetchall():
        print(f"  {name:<10} {rows_:>5} dong / {pairs} cap")

    conn.close()


if __name__ == "__main__":
    main()
