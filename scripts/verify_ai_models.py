"""
Kiem thu AI cho GVHD - script tong hop, chay lai duoc nhieu lan.

Script nay tra loi 3 cau hoi cua giang vien huong dan:

    1. So lieu du bao cua AI co dung khong?
       -> Huan luyen lai mo hinh tren du lieu QUA KHU va do sai so that
          (MAE / RMSE / MAPE) tren 92 ngay cuoi nam 2017, roi doi chieu voi
          `ai-model/outputs/model_metrics_all.csv`.

    2. AI dieu phoi / mua vu co bi loi logic khong?
       -> Goi API `/api/v1/forecasts/seasonal`, in ra 5 san pham nen nhap va
          5 san pham nen hanh che moi mua, roi TINH DOC LAP lai tu SQL Server
          de so sanh tung con so (chi so mua vu, xep hang, khuyen nghi).

    3. Chatbot co nhanh va tra loi dung khong?
       -> Gui 3 cau hoi (chao hoi / ton kho / mua vu) va do thoi gian phan hoi.

Ngoai ra con kiem tra tinh toan ven cua bang `forecasts`: moi cap phai du 30
ngay, gia tri tung ngay phai bien thien (khong duoc la mot so lap lai), va
khoang tin cay phai bao quanh gia tri du bao.

Vi sao phan mua vu doc SQL truc tiep:
    Day la phep DOI CHIEU DOC LAP. Neu lay lai chinh ket qua API roi so voi
    API thi khong chung minh duoc gi. Script chi SELECT (khong ghi), va nam
    ngoai backend nen khong vi pham quy tac "moi thao tac du lieu qua Stored
    Procedure" cua API.

Cach chay (backend phai dang chay o cong 8000):
    cd backend; python -m uvicorn app.main:app --port 8000
    python scripts/verify_ai_models.py
    python scripts/verify_ai_models.py --skip-models    # bo qua phan train lai
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import platform
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyodbc

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "ai-model" / "outputs"
REPORT_DIR = PROJECT_ROOT / "docs" / "02-bao-cao"
LOG_PATH = REPORT_DIR / "kiem-thu-ai-log.txt"
BACKTEST_CSV = REPORT_DIR / "kiem-thu-ai-backtest.csv"

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API = BASE_URL + "/api/v1"

# Cac cap (san pham, cua hang) se train lai. Chon cap dai dien:
#   (45,1) Prophet thang | (45,2) XGBoost thang | (8,1) san pham lon thu 2
BACKTEST_PAIRS = [(45, 1), (45, 2), (8, 1)]

# 3 cau hoi chatbot bat buoc + 1 cau kiem tra kha nang hieu cau khong dau.
# expected: mot trong cac chuoi nay phai xuat hien trong cau tra loi.
CHAT_QUESTIONS = [
    ("Chao hoi", "Xin chào, bạn là ai và bạn giúp được gì cho tôi?", None),
    ("Ton kho", "Tồn kho của cửa hàng Q.3 hiện tại thế nào?", ["150"]),
    ("Mua vu", "Mùa này nên nhập nhiều mặt hàng nào?",
     ["Kem chống nắng", "Bông biển sáng", "Khoai lang", "Phô mai vi t", "Bưởi Long An"]),
    ("Khong dau", "mua nay nen nhap nhieu mat hang nao",
     ["Kem chống nắng", "Bông biển sáng", "Khoai lang", "Phô mai vi t", "Bưởi Long An"]),
]

FORBIDDEN = [
    (r"\bSP#\d+", "SP#<so>"),
    (r"\bCH#\d+", "CH#<so>"),
    (r"\bCB#\d+", "CB#<so>"),
    (r"\bDH#\d+", "DH#<so>"),
    (r"\bSL\b", "SL (so luong)"),
    (r"\bHH\b", "HH (nhom hang)"),
]

SEASON_MONTHS = {
    "spring": [2, 3, 4],
    "summer": [5, 6, 7],
    "autumn": [8, 9, 10],
    "winter": [11, 12, 1],
}
SEASON_LABELS = {"spring": "Xuan", "summer": "Ha", "autumn": "Thu", "winter": "Dong"}


# =============================================================================
#  GHI LOG (vua in ra man hinh vua luu file UTF-8)
# =============================================================================

class Tee:
    """Chuyen huong stdout sang ca console va buffer de ghi file."""

    def __init__(self, stream, buffer: io.StringIO):
        self._stream = stream
        self._buffer = buffer

    def write(self, text):
        self._stream.write(text)
        self._buffer.write(text)
        return len(text)

    def flush(self):
        self._stream.flush()

    def isatty(self):
        return False

    def reconfigure(self, **kwargs):
        return None

    @property
    def encoding(self):
        return "utf-8"


def say(text: str = "") -> None:
    print(text, flush=True)


def rule(char: str = "=", width: int = 78) -> None:
    say(char * width)


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


def query(conn: pyodbc.Connection, sql: str, params: tuple = ()) -> list[dict]:
    cur = conn.cursor()
    cur.execute(sql, *params) if params else cur.execute(sql)
    columns = [c[0] for c in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


# =============================================================================
#  HTTP
# =============================================================================

def http_json(method: str, path: str, payload: dict | None = None,
              timeout: int = 180) -> tuple[dict, float]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(API + path, data=data,
                                     headers=headers, method=method)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"LOI: khong goi duoc {API + path}\n"
            f"     {exc}\n"
            "     Hay chay backend truoc: cd backend; "
            "python -m uvicorn app.main:app --port 8000"
        ) from exc
    elapsed_ms = (time.perf_counter() - start) * 1000
    return json.loads(body), elapsed_ms


# =============================================================================
#  NAP MODULE HUAN LUYEN (dung chinh code da dung khi lam do an)
# =============================================================================

def load_train_module():
    path = PROJECT_ROOT / "ai-model" / "scripts" / "train_models.py"
    spec = importlib.util.spec_from_file_location("train_models", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"LOI: khong nap duoc {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_series(conn: pyodbc.Connection, product_id: int, store_id: int) -> pd.DataFrame:
    """Chuoi doanh so 1 cap, reindex ve du 1826 ngay (giong train_models)."""
    rows = query(
        conn,
        "SELECT sale_date, quantity_sold FROM dbo.v_daily_sales "
        "WHERE product_id = ? AND store_id = ? "
        "AND sale_date >= '2013-01-01' AND sale_date < '2018-01-01' "
        "ORDER BY sale_date",
        (product_id, store_id),
    )
    frame = pd.DataFrame(
        [(r["sale_date"], float(r["quantity_sold"])) for r in rows],
        columns=["sale_date", "y"],
    )
    frame["sale_date"] = pd.to_datetime(frame["sale_date"])

    full_dates = pd.date_range("2013-01-01", "2017-12-31", freq="D")
    frame = frame.set_index("sale_date").reindex(full_dates)
    frame.index.name = "sale_date"

    missing_days = int(frame["y"].isna().sum())
    frame["y"] = frame["y"].fillna(0.0)

    out = frame.reset_index()[["sale_date", "y"]]
    out.attrs["missing_days"] = missing_days
    out.attrs["zero_days"] = int((out["y"] == 0).sum())
    return out


# =============================================================================
#  PHAN 0 - MOI TRUONG VA DU LIEU
# =============================================================================

def part_environment(conn: pyodbc.Connection) -> dict:
    rule()
    say("PHAN 0 - MOI TRUONG VA DU LIEU DANG CO")
    rule()

    import prophet
    import xgboost

    say(f"Python          : {platform.python_version()} ({platform.system()})")
    say(f"pandas          : {pd.__version__}")
    say(f"numpy           : {np.__version__}")
    say(f"prophet         : {prophet.__version__}")
    say(f"xgboost         : {xgboost.__version__}")
    try:
        import statsmodels
        say(f"statsmodels     : {statsmodels.__version__}")
    except Exception:
        say("statsmodels     : (khong co)")

    env = read_env()
    say(f"SQL Server      : {env.get('DB_HOST')} / {env.get('DB_NAME')}")

    sales = query(
        conn,
        "SELECT COUNT(*) AS rows_, MIN(sale_date) AS dmin, MAX(sale_date) AS dmax, "
        "COUNT(DISTINCT store_id) AS stores_, COUNT(DISTINCT product_id) AS products_ "
        "FROM dbo.v_daily_sales",
    )[0]
    say(f"v_daily_sales   : {sales['rows_']:,} dong | {sales['dmin']} -> {sales['dmax']} "
        f"| {sales['stores_']} cua hang x {sales['products_']} san pham")

    forecasts = query(
        conn,
        "SELECT COUNT(*) AS rows_, COUNT(DISTINCT CONCAT(product_id,'-',store_id)) AS pairs_, "
        "MIN(forecast_date) AS dmin, MAX(forecast_date) AS dmax "
        "FROM dbo.forecasts",
    )[0]
    say(f"forecasts       : {forecasts['rows_']:,} dong | {forecasts['pairs_']} cap "
        f"| {forecasts['dmin']} -> {forecasts['dmax']}")

    metrics_path = OUTPUT_DIR / "model_metrics_all.csv"
    metrics = pd.read_csv(metrics_path)
    say(f"model_metrics   : {len(metrics)} cap (train/test 2017-10-01)")

    say("")
    say(f"Ket luan: doanh so thuc te ket thuc {sales['dmax']}, "
        f"du bao bat dau {forecasts['dmin']}.")
    if forecasts["dmin"] > sales["dmax"]:
        say("          -> HAI KHOANG KHONG GIAO NHAU. Khong the do sai so cua bang")
        say("             forecasts bang cach so voi doanh so that (xem PHAN 2).")
    say("")

    return {"sales": sales, "forecasts": forecasts, "metrics": metrics}


# =============================================================================
#  PHAN 1 - DO CHINH XAC THAT (BACKTEST)
# =============================================================================

def part_accuracy(conn: pyodbc.Connection, metrics: pd.DataFrame) -> pd.DataFrame:
    rule()
    say("PHAN 1 - DO CHINH XAC THAT CUA MO HINH (BACKTEST TREN DU LIEU QUA KHU)")
    rule()
    say("Phuong phap (dung chinh code cua do an, khong viet lai):")
    say("  - Du lieu   : 2013-01-01 -> 2017-12-31, reindex du 1.826 ngay, ngay thieu = 0")
    say("  - Tap train : 2013-01-01 -> 2017-09-30 (1.734 ngay)")
    say("  - Tap test  : 2017-10-01 -> 2017-12-31 (92 ngay, quy 4 - mua cao diem)")
    say("  - Moc chia theo NGAY, khong dung 80/20 (xem AGENTS.md)")
    say("  - Sai so    : MAE / RMSE / MAPE tinh tren 92 ngay test")
    say("")

    trainer = load_train_module()
    results: list[dict] = []

    for index, (product_id, store_id) in enumerate(BACKTEST_PAIRS, 1):
        say(f"[{index}/{len(BACKTEST_PAIRS)}] Cap san pham {product_id} - cua hang {store_id}")
        started = time.time()
        series = load_series(conn, product_id, store_id)

        say(f"    chuoi  : {len(series)} ngay | thieu {series.attrs['missing_days']} ngay "
            f"| ban = 0 o {series.attrs['zero_days']} ngay")

        outcome = trainer.evaluate_pair(series, product_id, store_id)
        elapsed = time.time() - started

        row = {
            "product_id": product_id,
            "store_id": store_id,
            "train_days": outcome.get("train_days"),
            "test_days": outcome.get("test_days"),
        }
        for name in ("prophet", "xgboost", "arima"):
            row[f"{name}_rmse"] = outcome.get(f"{name}_rmse")
            row[f"{name}_mae"] = outcome.get(f"{name}_mae")
            row[f"{name}_mape"] = outcome.get(f"{name}_mape")
        row["best_model"] = outcome.get("best_model")
        row["best_rmse"] = outcome.get("best_rmse")
        row["seconds"] = round(elapsed, 1)
        results.append(row)

        say(f"    ket qua: Prophet RMSE {row['prophet_rmse']:.2f} | "
            f"MAE {row['prophet_mae']:.2f} | MAPE {row['prophet_mape']:.2f}%")
        say(f"             XGBoost RMSE {row['xgboost_rmse']:.2f} | "
            f"MAE {row['xgboost_mae']:.2f} | MAPE {row['xgboost_mape']:.2f}%")
        say(f"             ARIMA   RMSE {row['arima_rmse']:.2f} | "
            f"MAE {row['arima_mae']:.2f} | MAPE {row['arima_mape']:.2f}%")
        say(f"             -> tot nhat: {str(row['best_model']).upper()} "
            f"(RMSE {row['best_rmse']:.2f}) | {elapsed:.1f} giay")
        say("")

    fresh = pd.DataFrame(results)

    # Doi chieu voi ket qua da luu trong model_metrics_all.csv
    say("Doi chieu voi ai-model/outputs/model_metrics_all.csv:")
    say(f"  {'cap':>8} | {'RMSE moi':>9} {'RMSE cu':>9} {'lech':>9} | "
        f"{'MAPE moi':>9} {'MAPE cu':>9} {'lech':>9}")
    say("  " + "-" * 70)
    max_delta = 0.0
    for row in fresh.itertuples(index=False):
        stored = metrics[(metrics["product_id"] == row.product_id)
                         & (metrics["store_id"] == row.store_id)]
        if stored.empty:
            say(f"  {row.product_id:>3}/{row.store_id:<4} | khong co trong CSV")
            continue
        stored = stored.iloc[0]
        delta_rmse = abs(row.prophet_rmse - float(stored["prophet_rmse"]))
        delta_mape = abs(row.prophet_mape - float(stored["prophet_mape"]))
        max_delta = max(max_delta, delta_rmse)
        say(f"  {row.product_id:>3}/{row.store_id:<4} | "
            f"{row.prophet_rmse:>9.4f} {float(stored['prophet_rmse']):>9.4f} "
            f"{delta_rmse:>9.6f} | "
            f"{row.prophet_mape:>9.4f} {float(stored['prophet_mape']):>9.4f} "
            f"{delta_mape:>9.6f}")
    say("")
    say(f"  Lech RMSE lon nhat: {max_delta:.6f} -> "
        + ("KHOP (mo hinh tai lap duoc)" if max_delta < 0.01 else "KHONG KHOP"))

    # Tong hop 100 cap tu file goc
    say("")
    say("Tong hop 100 cap (doc tu model_metrics_all.csv, do la ket qua M1 da chay):")
    for name in ("prophet", "xgboost", "arima"):
        column = f"{name}_rmse"
        if column not in metrics.columns:
            continue
        valid = metrics[metrics[column].notna()]
        wins = int((metrics["best_model"] == name).sum())
        say(f"  {name.upper():<8}: RMSE TB {valid[column].mean():>7.2f} | "
            f"MAE TB {valid[f'{name}_mae'].mean():>7.2f} | "
            f"MAPE TB {valid[f'{name}_mape'].mean():>6.2f}% | "
            f"thang {wins:>3}/{len(metrics)} cap")
    say("")
    return fresh


# =============================================================================
#  PHAN 2 - BANG forecasts CO DOI CHIEU DUOC VOI THUC TE KHONG?
# =============================================================================

def part_forecast_vs_actual(conn: pyodbc.Connection, sales: dict) -> None:
    rule()
    say("PHAN 2 - SO SANH BANG forecasts VOI DOANH SO THUC TE")
    rule()

    window = query(
        conn,
        "SELECT MIN(forecast_date) AS dmin, MAX(forecast_date) AS dmax "
        "FROM dbo.forecasts",
    )[0]
    say(f"Khoang du bao   : {window['dmin']} -> {window['dmax']}")
    say(f"Khoang ban that : {sales['dmin']} -> {sales['dmax']}")

    payload, elapsed = http_json(
        "GET", "/dashboard/forecast-vs-actual?product_id=45&store_id=1&model_name=prophet"
    )
    say(f"Goi API GET /api/v1/dashboard/forecast-vs-actual "
        f"(san pham 45, cua hang 1) trong {elapsed:.0f} ms")
    say(f"  matched_rows = {payload.get('matched_rows')}")
    say(f"  mape         = {payload.get('mape')}")
    say(f"  rmse         = {payload.get('rmse')}")
    say(f"  mae          = {payload.get('mae')}")
    message = payload.get("message")
    if message:
        say(f"  message      = {message}")
    say("")
    say("Ket luan: hai khoang khong giao nhau nen KHONG the do MAPE cua bang")
    say("          forecasts bang doanh so that. API tra mape = null kem giai")
    say("          thich, khong bia ra mot con so. Sai so that duoc do bang")
    say("          backtest o PHAN 1 (92 ngay quy 4/2017).")
    say("")


# =============================================================================
#  PHAN 3 - TINH TOAN VEN CUA BANG forecasts
# =============================================================================

def part_forecast_integrity(conn: pyodbc.Connection, metrics: pd.DataFrame) -> None:
    rule()
    say("PHAN 3 - KIEM TRA TINH TOAN VEN CUA BANG forecasts")
    rule()

    per_pair = query(
        conn,
        "SELECT store_id, product_id, model_name, COUNT(*) AS days, "
        "       COUNT(DISTINCT predicted_quantity) AS distinct_pred, "
        "       MIN(horizon_days) AS h_min, MAX(horizon_days) AS h_max, "
        "       SUM(predicted_quantity) AS total_predicted, "
        "       MIN(lower_bound) AS lo_min, MAX(upper_bound) AS hi_max, "
        "       MIN(rmse) AS rmse, MIN(mae) AS mae, MIN(mape) AS mape "
        "FROM dbo.forecasts "
        "GROUP BY store_id, product_id, model_name "
        "ORDER BY product_id, store_id",
    )
    say(f"So cap co du bao: {len(per_pair)}")

    flat = [r for r in per_pair if r["distinct_pred"] == 1]
    say(f"  - Cap co dung 30 ngay      : "
        f"{sum(1 for r in per_pair if r['days'] == 30)}/{len(per_pair)}")
    say(f"  - Cap co gia tri LAP LAI   : {len(flat)}/{len(per_pair)} "
        f"(0 la tot - moi ngay phai khac nhau)")

    horizon_ok = all(r["h_min"] == 1 and r["h_max"] == 30 for r in per_pair)
    say(f"  - horizon_days = 1..30     : {'DUNG' if horizon_ok else 'SAI'}")

    bounds_bad = query(
        conn,
        "SELECT COUNT(*) AS n FROM dbo.forecasts "
        "WHERE lower_bound > predicted_quantity OR upper_bound < predicted_quantity",
    )[0]["n"]
    say(f"  - lower <= predicted <= upper: "
        f"{'DUNG' if bounds_bad == 0 else f'SAI o {bounds_bad} dong'}")

    models = query(
        conn,
        "SELECT model_name, COUNT(*) AS rows_, "
        "COUNT(DISTINCT CONCAT(product_id,'-',store_id)) AS pairs_ "
        "FROM dbo.forecasts GROUP BY model_name ORDER BY rows_ DESC",
    )
    say("  - Mo hinh theo cap:")
    for row in models:
        say(f"      {row['model_name']:<8} {row['rows_']:>5} dong / {row['pairs_']} cap")

    # Tong 30 ngay phai khop total_predicted cua lan chay M2
    summary_path = OUTPUT_DIR / "forecast_summary_30d.csv"
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        expected = {(int(r.product_id), int(r.store_id)): float(r.total_predicted)
                    for r in summary.itertuples(index=False)}
        worst = 0.0
        missing = 0
        for row in per_pair:
            key = (int(row["product_id"]), int(row["store_id"]))
            if key not in expected:
                missing += 1
                continue
            worst = max(worst, abs(float(row["total_predicted"]) - expected[key]))
        say(f"  - Tong 30 ngay khop forecast_summary_30d.csv: "
            f"lech lon nhat {worst:.3f} (thieu {missing} cap)")

    # rmse/mae/mape phai la cua tung cap, khong phai mot so dung chung
    mismatched = 0
    for row in per_pair:
        stored = metrics[(metrics["product_id"] == row["product_id"])
                         & (metrics["store_id"] == row["store_id"])]
        if stored.empty:
            continue
        stored = stored.iloc[0]
        name = row["model_name"]
        if abs(float(row["mae"]) - float(stored[f"{name}_mae"])) > 0.001:
            mismatched += 1
    say(f"  - rmse/mae/mape dung cua tung cap (khop model_metrics_all.csv): "
        f"{len(per_pair) - mismatched}/{len(per_pair)}")

    sample = query(
        conn,
        "SELECT forecast_date, horizon_days, predicted_quantity, lower_bound, "
        "upper_bound, rmse, mae, mape FROM dbo.forecasts "
        "WHERE product_id = 45 AND store_id = 1 ORDER BY forecast_date",
    )
    say("")
    say("Vi du 7 ngay dau cua cap san pham 45 - cua hang 1:")
    say(f"  {'ngay':<12} {'h':>3} {'du bao':>10} {'duoi':>10} {'tren':>10}")
    for row in sample[:7]:
        say(f"  {str(row['forecast_date']):<12} {row['horizon_days']:>3} "
            f"{float(row['predicted_quantity']):>10.3f} "
            f"{float(row['lower_bound']):>10.3f} "
            f"{float(row['upper_bound']):>10.3f}")
    values = [float(r["predicted_quantity"]) for r in sample]
    say(f"  -> {len(set(values))}/30 gia tri khac nhau, "
        f"min {min(values):.1f} / max {max(values):.1f} "
        f"(co mua vu tuan, khong con la mot so lap lai)")
    say("")


# =============================================================================
#  PHAN 4 - AI DIEU PHOI / MUA VU
# =============================================================================

def recompute_seasonal(conn: pyodbc.Connection) -> dict[tuple[str, int], dict]:
    """Tinh lai chi so mua vu tu SQL, doc lap voi API."""
    season_case = (
        "CASE WHEN MONTH(o.order_date) IN (2,3,4) THEN 'spring' "
        "WHEN MONTH(o.order_date) IN (5,6,7) THEN 'summer' "
        "WHEN MONTH(o.order_date) IN (8,9,10) THEN 'autumn' "
        "ELSE 'winter' END"
    )

    product_season = query(
        conn,
        f"SELECT oi.product_id, {season_case} AS season_code, "
        f"SUM(oi.quantity) AS qty "
        f"FROM dbo.order_items oi "
        f"JOIN dbo.orders o ON o.order_id = oi.order_id "
        f"WHERE o.status = 'completed' AND o.order_type = 'sale' "
        f"GROUP BY oi.product_id, {season_case}",
    )
    season_total = query(
        conn,
        f"SELECT {season_case} AS season_code, SUM(oi.quantity) AS qty, "
        f"COUNT(DISTINCT CAST(o.order_date AS DATE)) AS days "
        f"FROM dbo.order_items oi "
        f"JOIN dbo.orders o ON o.order_id = oi.order_id "
        f"WHERE o.status = 'completed' AND o.order_type = 'sale' "
        f"GROUP BY {season_case}",
    )
    names = {
        int(r["product_id"]): r["product_name"]
        for r in query(conn, "SELECT product_id, product_name FROM dbo.products")
    }

    product_total: dict[int, float] = {}
    for row in product_season:
        product_total[int(row["product_id"])] = (
            product_total.get(int(row["product_id"]), 0.0) + float(row["qty"])
        )

    season_qty = {r["season_code"]: float(r["qty"]) for r in season_total}
    grand_total = sum(season_qty.values())

    computed: dict[tuple[str, int], dict] = {}
    for row in product_season:
        product_id = int(row["product_id"])
        code = row["season_code"]
        share = float(row["qty"]) / product_total[product_id]
        overall = season_qty[code] / grand_total
        computed[(code, product_id)] = {
            "product_id": product_id,
            "product_name": names.get(product_id, ""),
            "season_code": code,
            "index": share / overall,
            "sample_days": int(
                next(r["days"] for r in season_total if r["season_code"] == code)
            ),
        }

    # Xep hang trong tung mua: chi so giam dan, cung chi so thi theo ten
    for code in SEASON_MONTHS:
        items = sorted(
            (v for (c, _), v in computed.items() if c == code),
            key=lambda item: (-item["index"], item["product_name"]),
        )
        total = len(items)
        cut = int(np.ceil(total * 0.2))
        for position, item in enumerate(items, 1):
            item["rank"] = position
            item["season_products"] = total
            if position <= cut:
                item["recommendation"] = "import"
            elif position > total - cut:
                item["recommendation"] = "avoid"
            else:
                item["recommendation"] = "neutral"

    return computed


def part_seasonal(conn: pyodbc.Connection) -> None:
    rule()
    say("PHAN 4 - AI DIEU PHOI / DU BAO THEO MUA VU")
    rule()

    payload, elapsed = http_json("GET", "/forecasts/seasonal")
    say(f"Goi API GET /api/v1/forecasts/seasonal trong {elapsed:.0f} ms")
    say(f"  du lieu   : {payload.get('data_from')} -> {payload.get('data_to')}")
    say(f"  mua hien tai: {payload.get('current_season')}")
    say(f"  so mua    : {len(payload.get('seasons') or [])}")
    say("")

    for season in payload.get("seasons") or []:
        label = SEASON_LABELS.get(season["season_code"], season["season_code"])
        say(f"--- {label.upper()} (thang {', '.join(map(str, season['months']))})"
            f"{'  <== mua hien tai' if season.get('is_current') else ''}")
        say(f"    {season['total_products']} san pham | nen nhap "
            f"{season['import_count']} | trung tinh {season['neutral_count']} "
            f"| nen hanh che {season['avoid_count']}")
        say("    5 san pham NEN NHAP nhieu nhat:")
        for item in season["import_items"][:5]:
            say(f"      {item['rank_in_season']:>2}. {item['product_name']:<28} "
                f"chi so {item['seasonal_index']:.4f}  ({item['category_name']})")
        say("    5 san pham NEN HANH CHE nhat:")
        for item in season["avoid_items"][:5]:
            say(f"      {item['rank_in_season']:>2}. {item['product_name']:<28} "
                f"chi so {item['seasonal_index']:.4f}  ({item['category_name']})")
        say("")

    # ---- Kiem tra doc lap ----
    say("Kiem tra doc lap (tinh lai tu SQL Server, khong dung API):")
    computed = recompute_seasonal(conn)

    failures: list[str] = []
    checked = 0
    worst_index = 0.0
    ties = 0

    for season in payload.get("seasons") or []:
        code = season["season_code"]
        if season["months"] != SEASON_MONTHS[code]:
            failures.append(f"{code}: danh sach thang sai {season['months']}")
        if season["total_products"] != 50:
            failures.append(f"{code}: tong san pham {season['total_products']} != 50")
        if season["import_count"] != 10 or season["avoid_count"] != 10:
            failures.append(
                f"{code}: so luong nen nhap/hanh che "
                f"{season['import_count']}/{season['avoid_count']} != 10/10"
            )

        all_items = (season["import_items"] + season["neutral_items"]
                     + season["avoid_items"])
        if len(all_items) != season["total_products"]:
            failures.append(
                f"{code}: tong so dong {len(all_items)} != total_products"
            )

        # (a) Chi so mua vu phai khop phep tinh doc lap
        for item in all_items:
            reference = computed.get((code, int(item["product_id"])))
            if reference is None:
                failures.append(f"{code}/{item['product_id']}: khong tinh lai duoc")
                continue
            checked += 1
            diff = abs(float(item["seasonal_index"]) - reference["index"])
            worst_index = max(worst_index, diff)
            if diff > 1e-3:
                failures.append(
                    f"{code}/{item['product_id']}: chi so lech {diff:.6f}"
                )

        # (b) Quy tac khuyen nghi phai dung: 20% dau = import, 20% cuoi = avoid
        cut = int(np.ceil(len(all_items) * 0.2))
        for item in all_items:
            rank = int(item["rank_in_season"])
            expected = (
                "import" if rank <= cut
                else "avoid" if rank > len(all_items) - cut
                else "neutral"
            )
            if item["recommendation"] != expected:
                failures.append(
                    f"{code}/{item['product_id']}: hang {rank} phai la "
                    f"{expected}, API tra {item['recommendation']}"
                )

        ranks = sorted(int(item["rank_in_season"]) for item in all_items)
        if ranks != list(range(1, len(all_items) + 1)):
            failures.append(f"{code}: hang khong phai hoan vi 1..{len(all_items)}")

        # (c) Thu tu phai nhat quan voi chi so (cho phep trung so)
        triples = [
            (float(item["seasonal_index"]), int(item["rank_in_season"]),
             int(item["product_id"]))
            for item in all_items
        ]
        inverted = 0
        for a in triples:
            for b in triples:
                if a[0] > b[0] + 1e-4 and a[1] >= b[1]:
                    inverted += 1
        if inverted:
            failures.append(f"{code}: {inverted} cap xep hang nguoc voi chi so")

        ordered = sorted(triples, key=lambda item: item[1])
        for previous, current in zip(ordered, ordered[1:]):
            if abs(previous[0] - current[0]) <= 1e-4:
                ties += 1

        values = [item[0] for item in ordered]
        gap = abs(values[cut - 1] - values[cut]) if len(values) > cut else 0.0
        say(f"  {code:<7}: chi so {values[0]:.4f} -> {values[-1]:.4f} "
            f"(bien do {values[0] - values[-1]:.4f}) | "
            f"ranh gioi hang {cut}/{cut + 1} chenh {gap:.5f}")

        imports = [float(i["seasonal_index"]) for i in season["import_items"]]
        avoids = [float(i["seasonal_index"]) for i in season["avoid_items"]]
        if imports != sorted(imports, reverse=True):
            failures.append(f"{code}: danh sach nen nhap khong giam dan")
        if avoids != sorted(avoids):
            failures.append(f"{code}: danh sach nen hanh che khong tang dan")

    # Phan vung: cho phep trung chi so dung o ranh gioi 20%
    for season in payload.get("seasons") or []:
        code = season["season_code"]
        imp = [float(i["seasonal_index"]) for i in season["import_items"]]
        neu = [float(i["seasonal_index"]) for i in season["neutral_items"]]
        avo = [float(i["seasonal_index"]) for i in season["avoid_items"]]
        if imp and neu and min(imp) < max(neu) - 1e-4:
            failures.append(f"{code}: co san pham neutral lon hon san pham import")
        if neu and avo and min(neu) < max(avo) - 1e-4:
            failures.append(f"{code}: co san pham avoid lon hon san pham neutral")

    if payload.get("data_from") != "2013-01-01" or payload.get("data_to") != "2017-12-31":
        failures.append(
            f"khoang du lieu {payload.get('data_from')} -> {payload.get('data_to')} "
            "khong dung 2013-01-01 -> 2017-12-31"
        )

    say(f"  - So dong doi chieu        : {checked} (200 dong = 50 san pham x 4 mua)")
    say(f"  - Lech chi so mua vu lon nhat: {worst_index:.6f} "
        f"(API lam tron 4 chu so thap phan)")
    say(f"  - Cap hang ke nhau trung chi so: {ties} (tie-break theo ten san pham)")
    say(f"  - So loi logic             : {len(failures)}")
    for item in failures[:10]:
        say(f"      ! {item}")
    say("")
    say("Ket luan: " + (
        "chi so, xep hang va khuyen nghi khop hoan toan voi phep tinh doc lap."
        if not failures else "CO LOI - xem danh sach tren."
    ))
    say("")


# =============================================================================
#  PHAN 5 - CHATBOT
# =============================================================================

def part_chatbot() -> None:
    rule()
    say("PHAN 5 - CHATBOT AI (Gemini)")
    rule()

    for label, question, expected in CHAT_QUESTIONS:
        payload, elapsed = http_json("POST", "/chat", {"message": question},
                                     timeout=180)
        answer = str(payload.get("answer") or "").strip()
        model_name = payload.get("model") or "(duong nhanh, khong goi Gemini)"

        say(f"[{label}] Hoi: {question}")
        say(f"   Tra loi ({elapsed:.0f} ms, model: {model_name}):")
        for line in answer.splitlines():
            say(f"     {line}")
        say("   Kiem tra chat luong cau tra loi:")
        say(f"     - do dai            : {len(answer)} ky tu")
        say(f"     - so cau           : {len([s for s in re.split(r'[.!?]', answer) if s.strip()])}")

        found = [name for pattern, name in FORBIDDEN if re.search(pattern, answer)]
        say(f"     - ky hieu viet tat  : {'KHONG co (dat)' if not found else ', '.join(found)}")

        if expected:
            hit = [item for item in expected if item.lower() in answer.lower()]
            say(f"     - so lieu dung      : "
                f"{'KHOP (' + hit[0] + ')' if hit else 'KHONG THAY so lieu ky vong'}")
        say("")


# =============================================================================
#  MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Kiem thu AI cho GVHD")
    parser.add_argument("--skip-models", action="store_true",
                        help="Bo qua phan train lai (chi kiem tra API va du lieu)")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    original = sys.stdout
    sys.stdout = Tee(original, buffer)

    started = time.time()
    status = 0

    try:
        rule()
        say("KIEM THU AI - SUPPLY CHAIN SPOILAGE PREDICTOR")
        say(f"Thoi diem chay: {date.today():%d/%m/%Y}")
        rule()
        say("")

        conn = connect()
        try:
            environment = part_environment(conn)
            if not args.skip_models:
                backtest = part_accuracy(conn, environment["metrics"])
                backtest.to_csv(BACKTEST_CSV, index=False, encoding="utf-8")
                say(f"Da luu bang sai so: {BACKTEST_CSV.name}")
                say("")
            part_forecast_vs_actual(conn, environment["sales"])
            part_forecast_integrity(conn, environment["metrics"])
            part_seasonal(conn)
        finally:
            conn.close()

        part_chatbot()

        rule()
        say(f"HOAN THANH trong {time.time() - started:.1f} giay")
        rule()

    except SystemExit as exc:
        status = 1
        say(f"\n{exc}")
    except Exception as exc:  # noqa: BLE001 - bao loi ro rang cho nguoi cham
        status = 1
        say(f"\nLOI KHONG MONG DOI: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout = original
        LOG_PATH.write_text(buffer.getvalue(), encoding="utf-8")
        print(f"\nLog day du: {LOG_PATH}")

    raise SystemExit(status)


if __name__ == "__main__":
    main()
