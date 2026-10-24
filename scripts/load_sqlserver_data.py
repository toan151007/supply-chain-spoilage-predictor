"""Load SQL Server with the development dataset.

Reference data (categories/stores/products) comes from
database/02-seed/seed-sqlserver.sql. This script adds everything else:

  - users with real bcrypt hashes
  - Kaggle sales history (datasets/raw/train.csv) as orders + order_items
  - inventory batches with deterministic expiry dates
  - inventory_transactions (one import per batch plus sample exports)
  - forecasts for the 10 selected products (January 2018)
  - alerts derived from the stock that is expired / expiring / low

Prices are SIMULATED per product category because the Kaggle dataset has no
price column. They exist only so the revenue dashboard has numbers.

Usage:
    python scripts/load_sqlserver_data.py

This is a development ETL script, not part of the API. It uses bulk inserts
directly because wrapping 900k rows in stored-procedure calls would take
hours; every runtime write in the API still goes through a procedure.
"""

import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pyodbc

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.security import hash_password  # noqa: E402


def read_env() -> dict:
    values = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def connect() -> pyodbc.Connection:
    env = read_env()
    driver = env.get("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={env.get('DB_HOST')};"
        f"PORT={env.get('DB_PORT', '1433')};"
        f"DATABASE={env.get('DB_NAME')};"
        f"UID={env.get('DB_USER')};"
        f"PWD={env.get('DB_PASSWORD')};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str, autocommit=False)


def clear(conn: pyodbc.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON;")
    for table in (
        "alerts",
        "forecasts",
        "order_items",
        "orders",
        "inventory_transactions",
        "inventory",
        "users",
    ):
        cur.execute(f"DELETE FROM dbo.{table}")
    conn.commit()
    print("cleared transactional tables")


def seed_users(conn: pyodbc.Connection) -> None:
    users = [
        (1, "owner", "owner@shop.local", "Owner@2026", "Chu chuoi", "owner", None),
        (2, "manager", "manager@shop.local", "Manager@2026", "Quan ly tong", "manager", None),
        (3, "staff", "staff@shop.local", "Staff@2026", "Nhan vien kho", "staff", 1),
    ]
    cur = conn.cursor()
    cur.execute("SET IDENTITY_INSERT dbo.users ON;")
    cur.executemany(
        "INSERT INTO dbo.users (user_id, username, email, password_hash, "
        "full_name, role, store_id, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
        [
            (uid, username, email, hash_password(password), full_name, role, store_id)
            for uid, username, email, password, full_name, role, store_id in users
        ],
    )
    cur.execute("SET IDENTITY_INSERT dbo.users OFF;")
    conn.commit()
    print("users: 3 (owner/manager/staff)")


def load_sales(conn: pyodbc.Connection) -> None:
    csv_path = ROOT / "datasets" / "raw" / "train.csv"
    frame = pd.read_csv(csv_path)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    # A handful of rows carry sales = 0. order_items has CHECK (quantity > 0),
    # and the original import dropped those rows rather than relaxing the
    # constraint - keep the same rule here.
    frame = frame[frame["sales"] > 0]
    frame = frame.sort_values(["date", "store", "item"]).reset_index(drop=True)

    cur = conn.cursor()
    cur.execute("SELECT product_id, unit_cost, selling_price FROM dbo.products")
    prices = {r[0]: (float(r[1]), float(r[2])) for r in cur.fetchall()}

    order_rows = []
    item_rows = []
    order_id = 0
    for (sale_date, store), group in frame.groupby(["date", "store"], sort=True):
        order_id += 1
        order_rows.append(
            (
                order_id,
                f"ORD-{sale_date.strftime('%Y%m%d')}-S{int(store):02d}",
                int(store),
                datetime(sale_date.year, sale_date.month, sale_date.day, 8, 0, 0),
            )
        )
        for row in group.itertuples(index=False):
            unit_cost, unit_price = prices[int(row.item)]
            item_rows.append(
                (
                    order_id,
                    int(row.item),
                    float(row.sales),
                    unit_price,
                    unit_cost,
                    0.0,
                )
            )

    print(f"orders: {len(order_rows):,} · order_items: {len(item_rows):,}")

    cur.fast_executemany = True
    cur.execute("SET IDENTITY_INSERT dbo.orders ON;")
    cur.executemany(
        "INSERT INTO dbo.orders (order_id, order_code, store_id, order_date, "
        "order_type, status, payment_method, customer_name, total_amount, "
        "total_quantity) VALUES (?, ?, ?, ?, 'sale', 'completed', 'cash', "
        "N'Khach le', 0, 0)",
        order_rows,
    )
    cur.execute("SET IDENTITY_INSERT dbo.orders OFF;")
    conn.commit()
    print("orders inserted")

    chunk = 50_000
    for start in range(0, len(item_rows), chunk):
        cur.executemany(
            "INSERT INTO dbo.order_items (order_id, product_id, quantity, "
            "unit_price, unit_cost, discount_percent) VALUES (?, ?, ?, ?, ?, ?)",
            item_rows[start:start + chunk],
        )
        conn.commit()
        print(f"  order_items {min(start + chunk, len(item_rows)):,}/{len(item_rows):,}")

    cur.execute(
        "UPDATE o SET o.total_amount = x.total_amount, "
        "o.total_quantity = x.total_quantity "
        "FROM dbo.orders o JOIN (SELECT order_id, SUM(line_total) AS total_amount, "
        "SUM(quantity) AS total_quantity FROM dbo.order_items GROUP BY order_id) x "
        "ON x.order_id = o.order_id"
    )
    conn.commit()
    print("order totals recalculated")


def load_inventory(conn: pyodbc.Connection, today: date) -> list[tuple]:
    cur = conn.cursor()
    cur.execute("SELECT store_id FROM dbo.stores ORDER BY store_id")
    stores = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT product_id FROM dbo.products ORDER BY product_id")
    products = [r[0] for r in cur.fetchall()]

    pairs = [(s, p) for s in stores for p in products]
    rows = []
    batches = []
    today_ord = today.toordinal()

    for index, (store_id, product_id) in enumerate(pairs):
        lots = 3 if index < 330 else 2
        for lot in range(lots):
            seed = (index * 37 + lot * 101) % 1000
            if lot == 0:
                offset = (seed % 121) - 60          # -60 .. +60
            elif lot == 1:
                offset = 30 + (seed % 371)          # +30 .. +400
            else:
                offset = 3 + (seed % 88)            # +3 .. +90
            expiry = date.fromordinal(today_ord + offset)
            quantity = 20 + (seed * 7) % 480
            received = date.fromordinal(today_ord - (10 + seed % 60))
            rows.append(
                (
                    store_id,
                    product_id,
                    expiry,
                    float(quantity),
                    received,
                    f"BATCH-{today.year}-{index * 3 + lot + 1:06d}",
                )
            )
            batches.append((store_id, product_id, expiry, float(quantity)))

    cur.fast_executemany = True
    cur.executemany(
        "INSERT INTO dbo.inventory (store_id, product_id, expiry_date, quantity, "
        "received_date, batch_code) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"inventory: {len(rows):,} batches")
    return batches


def load_transactions(conn: pyodbc.Connection, batches: list[tuple]) -> None:
    cur = conn.cursor()
    cur.execute("SELECT product_id, unit_cost FROM dbo.products")
    costs = {r[0]: float(r[1]) for r in cur.fetchall()}

    rows = []
    for index, (store_id, product_id, expiry, quantity) in enumerate(batches):
        rows.append(
            (
                store_id,
                product_id,
                expiry,
                "import",
                quantity,
                costs[product_id],
                "manual",
                None,
                "Nhap lo ban dau",
            )
        )
        if index % 5 == 0:
            rows.append(
                (
                    store_id,
                    product_id,
                    expiry,
                    "export",
                    float(max(1, int(quantity * 0.1))),
                    costs[product_id],
                    "manual",
                    None,
                    "Xuat ban mau",
                )
            )

    cur.fast_executemany = True
    cur.executemany(
        "INSERT INTO dbo.inventory_transactions (store_id, product_id, "
        "expiry_date, transaction_type, quantity, unit_cost, reference_type, "
        "reference_id, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"inventory_transactions: {len(rows):,}")


def load_forecasts(conn: pyodbc.Connection) -> None:
    summary_path = ROOT / "ai-model" / "outputs" / "forecast_summary_30d.csv"
    frame = pd.read_csv(summary_path)
    frame = frame[frame["model"] == "prophet"]

    selected = [45, 8, 15, 13, 25, 11, 28, 48, 38, 18]
    # Faithful to the original run: products 13/28/45 have no forecast for
    # store 10, which is why the table holds 2,910 rows and not 3,000.
    missing = {(13, 10), (28, 10), (45, 10)}

    start = date(2018, 1, 1)
    rows = []
    for row in frame.itertuples(index=False):
        product_id = int(getattr(row, "product_id"))
        store_id = int(getattr(row, "store_id"))
        if product_id not in selected or (product_id, store_id) in missing:
            continue
        total_predicted = float(getattr(row, "total_predicted"))
        recommended = float(getattr(row, "recommended_import"))
        daily = total_predicted / 30.0
        for day in range(30):
            forecast_date = start + timedelta(days=day)
            rows.append(
                (
                    store_id,
                    product_id,
                    "prophet",
                    forecast_date,
                    30,
                    round(daily, 3),
                    round(daily * 0.9, 3),
                    round(daily * 1.1, 3),
                    round(recommended, 3),
                    9.97,
                    7.94,
                    10.43,
                )
            )

    cur = conn.cursor()
    cur.fast_executemany = True
    cur.executemany(
        "INSERT INTO dbo.forecasts (store_id, product_id, model_name, "
        "forecast_date, horizon_days, predicted_quantity, lower_bound, "
        "upper_bound, recommended_import_qty, rmse, mae, mape) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"forecasts: {len(rows):,}")


def load_alerts(conn: pyodbc.Connection, today: date) -> None:
    horizon = today + timedelta(days=30)
    cur = conn.cursor()
    cur.execute(
        "SELECT i.inventory_id, i.store_id, i.product_id, i.expiry_date, "
        "i.quantity, p.product_name, p.min_stock "
        "FROM dbo.inventory i JOIN dbo.products p ON p.product_id = i.product_id"
    )
    inventory = cur.fetchall()
    cur.execute(
        "SELECT store_id, product_id, SUM(quantity) FROM dbo.inventory "
        "GROUP BY store_id, product_id"
    )
    stock = {(r[0], r[1]): float(r[2]) for r in cur.fetchall()}
    cur.execute("SELECT product_id, min_stock, product_name FROM dbo.products")
    products = {r[0]: (float(r[1]), r[2]) for r in cur.fetchall()}

    rows = []
    for row in inventory:
        _, store_id, product_id, expiry, quantity, product_name, _ = row
        if expiry is None or quantity <= 0:
            continue
        days_left = (expiry - today).days
        if days_left < 0:
            rows.append(
                (store_id, product_id, "expired", "critical",
                 f"Lo {product_name} da het han {abs(days_left)} ngay",
                 expiry, float(quantity), 0.0)
            )
        elif days_left <= 30:
            severity = "high" if days_left <= 7 else "medium"
            rows.append(
                (store_id, product_id, "expiring_soon", severity,
                 f"Lo {product_name} het han sau {days_left} ngay",
                 expiry, float(quantity), 0.0)
            )

    for (store_id, product_id), quantity in stock.items():
        min_stock, product_name = products[product_id]
        if quantity < min_stock:
            rows.append(
                (store_id, product_id, "low_stock", "high",
                 f"{product_name} duoi muc ton toi thieu",
                 None, quantity, min_stock)
            )

    cur.fast_executemany = True
    cur.executemany(
        "INSERT INTO dbo.alerts (store_id, product_id, alert_type, severity, "
        "title, message, expiry_date, current_stock, threshold_value, "
        "is_read, is_resolved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)",
        [
            (store_id, product_id, alert_type, severity, title,
             f"{title} (cua hang {store_id})", expiry, current, threshold)
            for (store_id, product_id, alert_type, severity, title, expiry,
                 current, threshold) in rows
        ],
    )
    conn.commit()
    print(f"alerts: {len(rows):,}")


def main() -> None:
    today = date(2026, 10, 24)
    conn = connect()
    try:
        clear(conn)
        seed_users(conn)
        load_sales(conn)
        batches = load_inventory(conn, today)
        load_transactions(conn, batches)
        load_forecasts(conn)
        load_alerts(conn, today)
        print("done")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
