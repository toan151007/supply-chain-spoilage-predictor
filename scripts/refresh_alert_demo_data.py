"""
Refresh the demo data used by the Alerts page so every date is relative to
today.

Why this exists
---------------
The SQL Server seed was generated on 24/10/2026 and never moved. By November
every alert still carried created_at = 24/10/2026 while the matching batch
expiry date kept drifting into the past. The UI therefore showed lines such
as "expired 33 days ago" next to a creation date from October.

What it does
------------
The script only calls stored procedures (no raw DML, per AGENTS.md):

    1. EXEC dbo.sp_Maintenance_RefreshInventoryDates
           rewrite inventory expiry dates relative to today, push a few
           (store, product) pairs below min_stock, wipe the alerts table
    2. EXEC dbo.sp_Alerts_Generate @WarningDays = 7
           rebuild expired / expiring_soon / low_stock alerts
    3. EXEC dbo.sp_Maintenance_FinalizeAlerts
           drop the meaningless over_stock alerts and spread created_at
           over the last three days

Both procedures live in database/03-migrations/012-refresh-alert-demo-data.sql.

Usage (from the repository root):
    python scripts/refresh_alert_demo_data.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pyodbc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402

WARNING_DAYS = 7
LOW_STOCK_PAIRS = 8


def connect() -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{{settings.DB_DRIVER}}};"
        f"SERVER={settings.DB_HOST};"
        f"DATABASE={settings.DB_NAME};"
        f"UID={settings.DB_USER};"
        f"PWD={settings.DB_PASSWORD};"
        "TrustServerCertificate=yes;"
        "Encrypt=yes;"
    )
    return pyodbc.connect(conn_str, autocommit=True)


def call(cur: pyodbc.Cursor, sql: str, params: tuple = ()) -> list[list[dict]]:
    """Run one statement and collect every result set as a list of dicts."""
    cur.execute(sql, params) if params else cur.execute(sql)

    sets: list[list[dict]] = []
    while True:
        if cur.description is not None:
            columns = [column[0] for column in cur.description]
            sets.append(
                [
                    {columns[index]: value for index, value in enumerate(row)}
                    for row in cur.fetchall()
                ]
            )
        if not cur.nextset():
            break
    return sets


def print_set(title: str, rows: list[dict]) -> None:
    print(f"  {title}")
    if not rows:
        print("    (khong co dong nao)")
        return
    for row in rows:
        print("    " + ", ".join(f"{key}={value}" for key, value in row.items()))


def main() -> int:
    conn = connect()
    cur = conn.cursor()

    try:
        print("1/3 - Lam moi han su dung ton kho ...")
        sets = call(
            cur,
            "EXEC dbo.sp_Maintenance_RefreshInventoryDates @WarningDays = ?, @LowStockPairs = ?",
            (WARNING_DAYS, LOW_STOCK_PAIRS),
        )
        if sets:
            print_set("ket qua", sets[0])

        print(f"2/3 - Tao lai canh bao ( WarningDays={WARNING_DAYS} ) ...")
        sets = call(
            cur,
            "EXEC dbo.sp_Alerts_Generate @WarningDays = ?",
            (WARNING_DAYS,),
        )
        if sets:
            print_set("ket qua", sets[0])

        print("3/3 - Don dep canh bao va gian created_at ...")
        sets = call(cur, "EXEC dbo.sp_Maintenance_FinalizeAlerts")
        if sets:
            print_set("ket qua", sets[0])

        print()
        print("=== KIEM TRA SAU KHI LAM MOI ===")
        sets = call(
            cur,
            """
            SELECT CONVERT(VARCHAR(10), CAST(SYSDATETIME() AS DATE), 23) AS today,
                   (SELECT COUNT(*) FROM dbo.alerts) AS alerts_total,
                   (SELECT COUNT(*) FROM dbo.alerts WHERE alert_type = 'expired') AS expired,
                   (SELECT COUNT(*) FROM dbo.alerts WHERE alert_type = 'expiring_soon') AS expiring_soon,
                   (SELECT COUNT(*) FROM dbo.alerts WHERE alert_type = 'low_stock') AS low_stock,
                   (SELECT COUNT(*) FROM dbo.alerts WHERE alert_type = 'over_stock') AS over_stock
            """,
        )
        print_set("tong hop", sets[0])

        sets = call(
            cur,
            """
            SELECT alert_type,
                   severity,
                   COUNT(*) AS total,
                   MIN(expiry_date) AS min_expiry,
                   MAX(expiry_date) AS max_expiry
            FROM dbo.alerts
            GROUP BY alert_type, severity
            ORDER BY alert_type, severity
            """,
        )
        print_set("theo loai va muc do", sets[0])

        sets = call(
            cur,
            """
            SELECT MIN(created_at) AS oldest_created,
                   MAX(created_at) AS newest_created
            FROM dbo.alerts
            """,
        )
        print_set("khoang created_at", sets[0])

        sets = call(
            cur,
            """
            SELECT TOP 8
                   a.alert_id,
                   a.alert_type,
                   a.severity,
                   p.product_name,
                   s.store_name,
                   a.expiry_date,
                   DATEDIFF(DAY, CAST(SYSDATETIME() AS DATE), a.expiry_date) AS days_to_expiry,
                   a.current_stock,
                   a.created_at
            FROM dbo.alerts a
            LEFT JOIN dbo.products p ON p.product_id = a.product_id
            LEFT JOIN dbo.stores s ON s.store_id = a.store_id
            ORDER BY a.created_at DESC, a.alert_id
            """,
        )
        print_set("8 canh bao moi nhat", sets[0])

        # Guard: the timeline must make sense (created after expiry for
        # expired rows, created before expiry for expiring-soon rows).
        sets = call(
            cur,
            """
            SELECT SUM(CASE WHEN alert_type = 'expired'
                             AND CAST(created_at AS DATE) < expiry_date THEN 1 ELSE 0 END) AS expired_created_too_early,
                   SUM(CASE WHEN alert_type = 'expiring_soon'
                             AND CAST(created_at AS DATE) > expiry_date THEN 1 ELSE 0 END) AS expiring_created_too_late
            FROM dbo.alerts
            WHERE expiry_date IS NOT NULL
            """,
        )
        print_set("kiem tra logic thoi gian", sets[0])

        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
