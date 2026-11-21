"""Move the demo dataset into the present day and rebuild the current year.

Why this exists
---------------
The Kaggle history ends on 31/12/2017 while the application is presented in
2026, so every screen that filters "the last 30 days" found nothing: the
dashboard looked empty, the forecasts were for 2018 and the alerts were
unrelated to any sale. This one-off maintenance script fixes the calendar.

What it does
------------
1. SHIFT  +9 years on every row that still belongs to the Kaggle window
   (before 2019-01-01):
       orders.order_date / created_at / updated_at (+ rebuilt order_code)
       order_items.created_at
       inventory.* and inventory_transactions.* (no rows currently match)
   The shift is a fixed 3287-day offset rather than DATEADD(YEAR, 9, ...):
   the latter maps 29/02/2016 and 28/02/2016 onto the same 2025 date and
   breaks the unique order_code. A constant offset is injective, so no two
   days can collapse into one.
   Running it twice is harmless: shifted rows no longer fall before 2019.

2. REGENERATE sales for 01/01/<current year> .. today:
   the shifted history already contains a copy of 2017 in the current year,
   so that block is deleted and rebuilt from the remaining history with
       - the average quantity of the same (store, product, month, weekday),
       - a holiday lift around the US retail calendar,
       - a small random noise so the days are not clones.
   The result is a clean series ending *today*, which is what every
   "last 30 days" widget expects.

3. RE-ANCHOR the stored forecasts to the next 30 days (tomorrow .. +29).
   The original block was 2018-01-01..30; a flat +9 shift would land in 2027,
   a year with no sales at all, so the horizon is moved to the day after the
   last observed sale instead. Quantities, model names and error metrics are
   kept as the model produced them.

4. REBUILD the alerts through the migration-012 procedures so expiry dates
   and created_at are relative to today.

All DML is direct, like `load_sqlserver_data.py` and unlike the API: wrapping
162k rows in stored-procedure calls would take hours. Every *runtime* write in
the application still goes through a procedure.

Usage (from the repository root):
    python scripts/shift_and_generate_2026.py
"""

import sys
from datetime import date, datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path  # noqa: E402

import pyodbc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402

SHIFT_DAYS = 3287  # nine calendar years (2013-01-01 -> 2022-01-01)
SHIFT_CUTOFF = "2019-01-01"
FORECAST_DAYS = 30
WARNING_DAYS = 7
LOW_STOCK_PAIRS = 8

# US retail holidays that the Walmart series reacts to. Only the ones that
# fall between January and November matter for the regenerated window, but
# the full set keeps the function reusable.
HOLIDAY_RULES = [
    (1, "day", 1),      # New Year
    (1, "nth", 3, 0),   # Martin Luther King (3rd Monday)
    (2, "nth", 3, 0),   # Presidents' Day
    (5, "last", 0),     # Memorial Day (last Monday)
    (7, "day", 4),      # Independence Day
    (9, "nth", 1, 0),   # Labor Day
    (10, "nth", 2, 0),  # Columbus Day
    (11, "day", 11),    # Veterans Day
    (11, "nth", 4, 3),  # Thanksgiving (4th Thursday)
]


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
    return pyodbc.connect(conn_str, autocommit=False)


def query(cur: pyodbc.Cursor, sql: str, params: tuple = ()) -> list[tuple]:
    cur.execute(sql, params) if params else cur.execute(sql)
    return cur.fetchall()


def print_ranges(cur: pyodbc.Cursor, title: str) -> None:
    rows = query(
        cur,
        """
        SELECT 'orders' AS t,
               CONVERT(VARCHAR(10), MIN(order_date), 23) + ' -> '
               + CONVERT(VARCHAR(10), MAX(order_date), 23),
               COUNT(*)
        FROM dbo.orders
        UNION ALL
        SELECT 'forecasts',
               CONVERT(VARCHAR(10), MIN(forecast_date), 23) + ' -> '
               + CONVERT(VARCHAR(10), MAX(forecast_date), 23),
               COUNT(*)
        FROM dbo.forecasts
        UNION ALL
        SELECT 'alerts',
               CONVERT(VARCHAR(10), MIN(created_at), 23) + ' -> '
               + CONVERT(VARCHAR(10), MAX(created_at), 23),
               COUNT(*)
        FROM dbo.alerts
        UNION ALL
        SELECT 'inventory.expiry',
               CONVERT(VARCHAR(10), MIN(expiry_date), 23) + ' -> '
               + CONVERT(VARCHAR(10), MAX(expiry_date), 23),
               COUNT(*)
        FROM dbo.inventory
        """,
    )
    print(f"  {title}")
    for name, span, count in rows:
        print(f"    {name:<18} {span}   rows={count:,}")


# --------------------------------------------------------------------------
# 1. shift
# --------------------------------------------------------------------------
def shift_history(cur: pyodbc.Cursor) -> None:
    cur.execute(
        f"""
        UPDATE dbo.orders
        SET order_date = DATEADD(DAY, {SHIFT_DAYS}, order_date),
            order_code = 'ORD-'
                         + CONVERT(VARCHAR(8), DATEADD(DAY, {SHIFT_DAYS}, order_date), 112)
                         + '-S' + RIGHT('0' + CONVERT(VARCHAR(2), store_id), 2),
            created_at = CASE WHEN created_at < '{SHIFT_CUTOFF}'
                              THEN DATEADD(DAY, {SHIFT_DAYS}, created_at)
                              ELSE created_at END,
            updated_at = CASE WHEN updated_at < '{SHIFT_CUTOFF}'
                              THEN DATEADD(DAY, {SHIFT_DAYS}, updated_at)
                              ELSE updated_at END
        WHERE order_date < '{SHIFT_CUTOFF}'
        """
    )
    shifted_orders = cur.rowcount

    cur.execute(
        f"""
        UPDATE dbo.order_items
        SET created_at = DATEADD(DAY, {SHIFT_DAYS}, created_at)
        WHERE created_at < '{SHIFT_CUTOFF}'
        """
    )
    shifted_items = cur.rowcount

    # Inventory and its transaction log were already seeded relative to 2024,
    # so this normally matches nothing. It stays for a database restored from
    # an older backup where the batches still carry 2017 dates.
    cur.execute(
        f"""
        UPDATE dbo.inventory
        SET received_date = DATEADD(DAY, {SHIFT_DAYS}, received_date)
        WHERE received_date < '{SHIFT_CUTOFF}'
        """
    )
    shifted_inventory = cur.rowcount

    cur.execute(
        f"""
        UPDATE dbo.inventory_transactions
        SET transaction_date = DATEADD(DAY, {SHIFT_DAYS}, transaction_date)
        WHERE transaction_date < '{SHIFT_CUTOFF}'
        """
    )
    shifted_tx = cur.rowcount

    print(
        f"  orders={shifted_orders:,}  order_items={shifted_items:,}  "
        f"inventory={shifted_inventory:,}  inventory_transactions={shifted_tx:,}"
    )


# --------------------------------------------------------------------------
# 2. regenerate the current year
# --------------------------------------------------------------------------
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """weekday: 0 = Monday. n: 1-based occurrence in the month."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def holidays(year: int) -> set[date]:
    days = set()
    for rule in HOLIDAY_RULES:
        month = rule[0]
        kind = rule[1]
        if kind == "day":
            days.add(date(year, month, rule[2]))
        elif kind == "nth":
            days.add(_nth_weekday(year, month, rule[3], rule[2]))
        elif kind == "last":
            days.add(_last_weekday(year, month, rule[2]))
    return days


def holiday_factor(day: date, holiday_cache: dict[int, set[date]]) -> float:
    """Retail lift: strong on the holiday, softer in the run-up."""
    year_days = holiday_cache.setdefault(day.year, holidays(day.year))
    if day in year_days:
        return 1.25
    for delta in (1, 2, 3):
        if day + timedelta(days=delta) in year_days:
            return 1.12
    for delta in (1, 2, 3):
        if day - timedelta(days=delta) in year_days:
            return 1.06
    return 1.0


def load_demand_pattern(cur: pyodbc.Cursor, before: date) -> tuple[dict, dict, dict]:
    """Average quantity per (store, product) keyed three ways."""
    rows = query(
        cur,
        """
        SELECT o.store_id,
               oi.product_id,
               MONTH(o.order_date) AS month_no,
               (DATEDIFF(DAY, '1900-01-01', o.order_date) % 7) + 1 AS dow,
               AVG(CAST(oi.quantity AS FLOAT)) AS avg_qty
        FROM dbo.orders o
        JOIN dbo.order_items oi ON oi.order_id = o.order_id
        WHERE o.order_type = 'sale' AND o.order_date < ?
        GROUP BY o.store_id, oi.product_id, MONTH(o.order_date),
                 (DATEDIFF(DAY, '1900-01-01', o.order_date) % 7) + 1
        """,
        (before,),
    )

    by_month_dow: dict[tuple, float] = {}
    by_month_sum: dict[tuple, list] = {}
    by_pair_sum: dict[tuple, list] = {}
    for store_id, product_id, month_no, dow, avg_qty in rows:
        value = float(avg_qty)
        by_month_dow[(store_id, product_id, month_no, dow)] = value
        bucket = by_month_sum.setdefault((store_id, product_id, month_no), [0.0, 0])
        bucket[0] += value
        bucket[1] += 1
        pair = by_pair_sum.setdefault((store_id, product_id), [0.0, 0])
        pair[0] += value
        pair[1] += 1

    by_month = {key: total / count for key, (total, count) in by_month_sum.items()}
    by_pair = {key: total / count for key, (total, count) in by_pair_sum.items()}
    return by_month_dow, by_month, by_pair


def regenerate_current_year(cur: pyodbc.Cursor, today: date) -> None:
    year = today.year
    start = date(year, 1, 1)
    end = today

    # Drop the shifted copy of last year's tail so the series stops today.
    cur.execute(
        "SELECT order_id FROM dbo.orders WHERE order_date >= ?", (start,)
    )
    stale_ids = [row[0] for row in cur.fetchall()]
    for offset in range(0, len(stale_ids), 2000):
        chunk = stale_ids[offset:offset + 2000]
        marks = ",".join("?" * len(chunk))
        cur.execute(
            f"DELETE FROM dbo.order_items WHERE order_id IN ({marks})", chunk
        )
    cur.execute("DELETE FROM dbo.orders WHERE order_date >= ?", (start,))
    print(f"  removed {len(stale_ids):,} shifted orders dated {year}")

    by_month_dow, by_month, by_pair = load_demand_pattern(cur, start)
    if not by_pair:
        raise RuntimeError(
            "No history found before "
            f"{start} - run the shift step on a loaded database first."
        )

    cur.execute(
        "SELECT product_id, unit_cost, selling_price FROM dbo.products ORDER BY product_id"
    )
    prices = {row[0]: (float(row[1]), float(row[2])) for row in cur.fetchall()}
    cur.execute("SELECT store_id FROM dbo.stores ORDER BY store_id")
    stores = [row[0] for row in cur.fetchall()]
    products = list(prices)

    cur.execute("SELECT ISNULL(MAX(order_id), 0) FROM dbo.orders")
    next_order_id = int(cur.fetchone()[0]) + 1
    first_order_id = next_order_id

    # Deterministic noise: same input, same output, so a re-run is repeatable.
    state = 20260101
    holiday_cache: dict[int, set[date]] = {}
    day = start
    order_total = 0

    # Insert one day at a time. Building all 162k item tuples first is what
    # made an earlier version fail with MemoryError while the Vite build was
    # running beside it; a single day is 500 rows and cannot spike.
    cur.fast_executemany = True
    cur.execute("SET IDENTITY_INSERT dbo.orders ON;")
    while day <= end:
        factor = holiday_factor(day, holiday_cache)
        dow = day.weekday() + 1  # 1 = Monday, matching the SQL expression
        day_orders = []
        day_items = []
        for store_id in stores:
            order_id = next_order_id
            next_order_id += 1
            day_orders.append(
                (
                    order_id,
                    f"ORD-{day.strftime('%Y%m%d')}-S{store_id:02d}",
                    store_id,
                    datetime(day.year, day.month, day.day, 8, 0, 0),
                )
            )
            for product_id in products:
                state = (1103515245 * state + 12345) % (2 ** 31)
                jitter = 1.0 + ((state % 2001) - 1000) / 10000.0  # +/-10%
                base = by_month_dow.get((store_id, product_id, day.month, dow))
                if base is None:
                    base = by_month.get((store_id, product_id, day.month))
                if base is None:
                    base = by_pair[(store_id, product_id)]
                quantity = int(round(base * factor * jitter))
                if quantity < 1:
                    quantity = 1
                unit_cost, unit_price = prices[product_id]
                day_items.append(
                    (order_id, product_id, float(quantity), unit_price, unit_cost)
                )

        cur.executemany(
            "INSERT INTO dbo.orders (order_id, order_code, store_id, order_date, "
            "order_type, status, payment_method, customer_name, total_amount, "
            "total_quantity) VALUES (?, ?, ?, ?, 'sale', 'completed', 'cash', "
            "N'Khach le', 0, 0)",
            day_orders,
        )
        cur.executemany(
            "INSERT INTO dbo.order_items (order_id, product_id, quantity, "
            "unit_price, unit_cost, discount_percent) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            day_items,
        )
        order_total += len(day_orders)
        day += timedelta(days=1)
    cur.execute("SET IDENTITY_INSERT dbo.orders OFF;")

    cur.execute(
        """
        UPDATE o
        SET o.total_amount = x.total_amount,
            o.total_quantity = x.total_quantity
        FROM dbo.orders o
        JOIN (
            SELECT order_id,
                   SUM(line_total) AS total_amount,
                   SUM(quantity) AS total_quantity
            FROM dbo.order_items
            WHERE order_id >= ?
            GROUP BY order_id
        ) x ON x.order_id = o.order_id
        """,
        (first_order_id,),
    )
    print(
        f"  generated {order_total:,} orders and "
        f"{order_total * len(products):,} order_items for {start} .. {end}"
    )


# --------------------------------------------------------------------------
# 3. re-anchor forecasts
# --------------------------------------------------------------------------
def reanchor_forecasts(cur: pyodbc.Cursor, today: date) -> None:
    rows = query(
        cur,
        "SELECT MIN(forecast_date), MAX(forecast_date), COUNT(*) FROM dbo.forecasts",
    )
    if not rows or rows[0][0] is None:
        print("  no forecasts to re-anchor")
        return

    current_min, current_max, count = rows[0]
    target = today + timedelta(days=1)
    offset = (target - current_min).days
    if offset == 0:
        print(f"  already anchored at {current_min} .. {current_max}")
        return

    cur.execute(
        """
        UPDATE dbo.forecasts
        SET forecast_date = DATEADD(DAY, ?, forecast_date),
            trained_at = SYSDATETIME(),
            created_at = SYSDATETIME()
        """,
        (offset,),
    )
    new_min = query(cur, "SELECT MIN(forecast_date), MAX(forecast_date) FROM dbo.forecasts")[0]
    print(
        f"  {count:,} rows moved {offset:+d} days: "
        f"{current_min} .. {current_max} -> {new_min[0]} .. {new_min[1]}"
    )


# --------------------------------------------------------------------------
# 4. rebuild alerts
# --------------------------------------------------------------------------
def rebuild_alerts(cur: pyodbc.Cursor) -> None:
    for sql, params in (
        (
            "EXEC dbo.sp_Maintenance_RefreshInventoryDates "
            "@WarningDays = ?, @LowStockPairs = ?",
            (WARNING_DAYS, LOW_STOCK_PAIRS),
        ),
        ("EXEC dbo.sp_Alerts_Generate @WarningDays = ?", (WARNING_DAYS,)),
        ("EXEC dbo.sp_Maintenance_FinalizeAlerts", ()),
    ):
        cur.execute(sql, params) if params else cur.execute(sql)
        while cur.nextset():
            pass

def main() -> int:
    today = date.today()
    print(f"=== SHIFT + REGENERATE 2026 (today = {today}) ===")

    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON;")
        print_ranges(cur, "before")

        print("1/4 - shift Kaggle history by +9 years ...")
        shift_history(cur)

        # The shift and the regeneration are committed together: a failure in
        # the second step must not leave the table shifted but still holding
        # the old current-year block.
        print("2/4 - regenerate sales for the current year ...")
        regenerate_current_year(cur, today)
        conn.commit()

        print("3/4 - re-anchor the forecast horizon ...")
        reanchor_forecasts(cur, today)
        conn.commit()

        print("4/4 - rebuild alerts ...")
        # The migration-012 procedures manage their own transaction and end
        # with COMMIT. Running them inside the connection's implicit
        # transaction raises 266 ("transaction count after EXECUTE ..."), so
        # the last step is the one place that must run in autocommit mode.
        conn.autocommit = True
        try:
            rebuild_alerts(cur)
        finally:
            conn.autocommit = False

        print_ranges(cur, "after")

        checks = query(
            cur,
            """
            SELECT (SELECT COUNT(*) FROM dbo.orders WHERE order_date >= ?),
                   (SELECT COUNT(*) FROM dbo.orders o
                    WHERE NOT EXISTS (SELECT 1 FROM dbo.order_items oi
                                      WHERE oi.order_id = o.order_id)),
                   (SELECT COUNT(*) FROM dbo.order_items oi
                    WHERE NOT EXISTS (SELECT 1 FROM dbo.orders o
                                      WHERE o.order_id = oi.order_id)),
                   (SELECT COUNT(*) FROM dbo.orders
                    WHERE total_amount = 0 OR total_quantity = 0),
                   (SELECT COUNT(*) FROM dbo.alerts
                    WHERE alert_type = 'expired'
                      AND CAST(created_at AS DATE) < expiry_date)
            """,
            (date(today.year, 1, 1),),
        )[0]
        names = (
            "orders in the current year",
            "orders without items",
            "orphan order_items",
            "orders with zero totals",
            "expired alerts created before expiry",
        )
        print("  integrity checks:")
        for name, value in zip(names, checks):
            print(f"    {name:<38} {value}")

        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
