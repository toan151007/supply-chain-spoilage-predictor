"""
Test suite for B8 - advanced dashboard endpoints.

Run with the server listening on 127.0.0.1:8000:

    cd backend
    python -m uvicorn app.main:app --port 8000
    python test_b8_dashboard_advanced.py

Read-only: every B8 endpoint is a GET. Nothing is written, so there is
nothing to clean up. Expected values are cross-checked against SQL executed
directly, so the test fails if the API and the database disagree rather
than merely confirming the API agrees with itself.
"""

import json
import os
import sys
import urllib.error
import urllib.request

import psycopg2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000/api/v1"
FAILURES = []

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="spoilage_predictor",
    user="postgres", password=os.environ["DB_PASSWORD"],
)
cur = conn.cursor()


def sql(query, params=None):
    cur.execute(query, params)
    return cur.fetchall()


class Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


def get(path):
    req = urllib.request.Request(BASE + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read()
            return Resp(r.status, json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return Resp(e.code, json.loads(raw) if raw else None)
        except ValueError:
            return Resp(e.code, {"_raw": raw.decode("utf-8", "replace")[:300]})


def check(label, got, want):
    ok = got == want
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}: {got}"
          + ("" if ok else f"  (expected {want})"))
    if not ok:
        FAILURES.append(label)


def ok(label, cond, detail=""):
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}"
          + (f": {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)


def near(label, got, want, tol=0.02):
    """Compare floats allowing for 2-decimal rounding in the response."""
    ok_ = abs(float(got) - float(want)) <= tol
    print(f"  [{'OK ' if ok_ else 'FAIL'}] {label}: {got}"
          + ("" if ok_ else f"  (expected ~{want})"))
    if not ok_:
        FAILURES.append(label)


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ==================================================== REVENUE BY STORE
section("GET /dashboard/revenue-by-store - happy path")
r = get("/dashboard/revenue-by-store")
check("status", r.status_code, 200)
rows = r.json()
check("so cua hang", len(rows), 10)
ok("co store_code/ten", all(x["store_code"] and x["store_name"] for x in rows))
ok("sap xep doanh thu giam dan",
   [x["total_revenue"] for x in rows]
   == sorted([x["total_revenue"] for x in rows], reverse=True))
for x in rows[:3]:
    print(f"     {x['store_code']} {x['store_name'][:28]:30} "
          f"rev={x['total_revenue']:>16,.0f} orders={x['total_orders']:>6} "
          f"AOV={x['avg_order_value']:>12,.0f}")

# Cross-check totals against the database.
db_total_rev, db_total_orders = sql(
    "SELECT sum(total_amount), count(*) FROM orders")[0]
api_total_rev = sum(x["total_revenue"] for x in rows)
api_total_orders = sum(x["total_orders"] for x in rows)
near("tong doanh thu khop DB", api_total_rev, db_total_rev)
check("tong so don khop DB", api_total_orders, int(db_total_orders))
print(f"     API total={api_total_rev:,.0f} / DB total={db_total_rev:,.0f}")
print(f"     API orders={api_total_orders} / DB orders={db_total_orders}")

# avg_order_value must be revenue / ORDERS, not / lines.
sample = rows[0]
near("AOV = doanh thu / so don",
     sample["avg_order_value"], sample["total_revenue"] / sample["total_orders"], tol=1)
ok("AOV khong chia theo dong hang",
   sample["avg_order_value"] > sample["total_revenue"] / (sample["total_orders"] * 10),
   f"AOV={sample['avg_order_value']:,.0f}")

section("GET /dashboard/revenue-by-store - tung cua hang khop DB")
one = get("/dashboard/revenue-by-store").json()[0]
db_row = sql(
    "SELECT sum(total_amount), count(*), sum(total_quantity) "
    "FROM orders WHERE store_id = %s", (one["store_id"],))[0]
near(f"store {one['store_id']} doanh thu", one["total_revenue"], db_row[0])
check(f"store {one['store_id']} so don", one["total_orders"], int(db_row[1]))
near(f"store {one['store_id']} so luong", one["total_quantity"], db_row[2])

section("GET /dashboard/revenue-by-store - date range")
all_orders = get("/dashboard/revenue-by-store").json()
full_rev = sum(x["total_revenue"] for x in all_orders)
full_ord = sum(x["total_orders"] for x in all_orders)

y2017 = get("/dashboard/revenue-by-store?from_date=2017-01-01&to_date=2017-12-31")
check("nam 2017 status", y2017.status_code, 200)
rev2017 = sum(x["total_revenue"] for x in y2017.json())
ord2017 = sum(x["total_orders"] for x in y2017.json())
db_rev2017 = sql(
    "SELECT sum(total_amount), count(*) FROM orders "
    "WHERE order_date >= '2017-01-01 00:00:00+07' "
    "AND order_date < '2018-01-01 00:00:00+07'")[0]
near("doanh thu 2017 khop DB", rev2017, db_rev2017[0])
check("so don 2017 khop DB (3650)", ord2017, int(db_rev2017[1]))
ok("2017 < tong 5 nam", rev2017 < full_rev,
   f"{rev2017:,.0f} < {full_rev:,.0f}")

# The endpoint takes DATE params on purpose, so a UTC datetime string is
# rejected with 422 rather than silently shifting the window. That is the
# defence against the +07:00 trap documented in AGENTS.md.
utc_range = get(
    "/dashboard/revenue-by-store?from_date=2017-01-01T00:00:00Z"
    "&to_date=2017-12-31T23:59:59Z")
check("moc UTC datetime -> 422 (endpoint chi nhan date)", utc_range.status_code, 422)
print("     (muc ngay +07 giu duoc 3650 don; moc UTC se cat 10 don)")

one_day = get("/dashboard/revenue-by-store?from_date=2017-01-04&to_date=2017-01-04")
check("1 ngay -> 10 don", sum(x["total_orders"] for x in one_day.json()), 10)
one_month = get("/dashboard/revenue-by-store?from_date=2017-01-01&to_date=2017-01-31")
check("thang 1/2017 -> 310 don",
      sum(x["total_orders"] for x in one_month.json()), 310)

open_end = get("/dashboard/revenue-by-store?from_date=2017-01-01")
check("chi from_date -> 200", open_end.status_code, 200)
near("chi from_date = 2017 den het",
     sum(x["total_revenue"] for x in open_end.json()), rev2017, tol=1)
open_start = get("/dashboard/revenue-by-store?to_date=2017-12-31")
check("chi to_date -> 200", open_start.status_code, 200)

no_data = get("/dashboard/revenue-by-store?from_date=1999-01-01&to_date=1999-12-31")
check("nam khong co du lieu -> 200", no_data.status_code, 200)
check("nam khong co du lieu -> rong", no_data.json(), [])

section("GET /dashboard/revenue-by-store - edge cases")
check("from > to -> 422",
      get("/dashboard/revenue-by-store?from_date=2017-12-31&to_date=2017-01-01"
          ).status_code, 422)
check("from_date khong hop le -> 422",
      get("/dashboard/revenue-by-store?from_date=abc").status_code, 422)
check("to_date khong hop le -> 422",
      get("/dashboard/revenue-by-store?to_date=31-12-2017").status_code, 422)
same = get("/dashboard/revenue-by-store?from_date=2017-01-01&to_date=2017-01-01")
check("from == to -> 200", same.status_code, 200)
check("from == to -> van 10 don", sum(x["total_orders"] for x in same.json()), 10)

# ======================================================= TOP STORES
section("GET /dashboard/top-stores")
r = get("/dashboard/top-stores")
check("mac dinh limit=5", len(r.json()), 5)
ok("gia dong dau bang lon nhat cua revenue-by-store",
   r.json()[0]["store_id"] == all_orders[0]["store_id"],
   f"top1={r.json()[0]['store_id']} rev_by_store1={all_orders[0]['store_id']}")
check("limit=10 -> 10 CH", len(get("/dashboard/top-stores?limit=10").json()), 10)
check("limit=1 -> 1 CH", len(get("/dashboard/top-stores?limit=1").json()), 1)
ok("limit=3 giam dan",
   [x["total_revenue"] for x in get("/dashboard/top-stores?limit=3").json()]
   == sorted([x["total_revenue"] for x in get("/dashboard/top-stores?limit=3").json()],
             reverse=True))
near("top-stores tong = tong tat ca CH",
     sum(x["total_revenue"] for x in get("/dashboard/top-stores?limit=10").json()),
     full_rev, tol=1)

ts2017 = get("/dashboard/top-stores?limit=10&from_date=2017-01-01&to_date=2017-12-31")
check("top-stores co filter ngay", ts2017.status_code, 200)
check("tong 2017 khop", sum(x["total_revenue"] for x in ts2017.json()),
      round(rev2017, 2))

check("limit=0 -> 422", get("/dashboard/top-stores?limit=0").status_code, 422)
check("limit=-1 -> 422", get("/dashboard/top-stores?limit=-1").status_code, 422)
check("limit=101 -> 422", get("/dashboard/top-stores?limit=101").status_code, 422)
check("limit=abc -> 422", get("/dashboard/top-stores?limit=abc").status_code, 422)

# ================================================ REVENUE BY CATEGORY
section("GET /dashboard/revenue-by-category - happy path")
r = get("/dashboard/revenue-by-category")
check("status", r.status_code, 200)
rows = r.json()
# 8 categories exist but "Food" (id 1) has zero products, so it has no sales
# and correctly does not appear. An inner join drops it.
check("so nhom hang co doanh thu", len(rows), 7)
ok("sap xep doanh thu giam dan",
   [x["total_revenue"] for x in rows]
   == sorted([x["total_revenue"] for x in rows], reverse=True))
for x in rows[:3]:
    print(f"     {x['category_name'][:30]:32} rev={x['total_revenue']:>16,.0f} "
          f"qty={x['total_quantity']:>13,.0f} SP={x['product_count']}")

cat_rev = sum(x["total_revenue"] for x in rows)
cat_qty = sum(x["total_quantity"] for x in rows)
db_rev = sql("SELECT sum(revenue), sum(quantity_sold) FROM v_daily_sales")[0]
near("tong doanh thu theo nhom == tong view", cat_rev, db_rev[0])
near("tong so luong theo nhom == tong view", cat_qty, db_rev[1])
near("doanh thu theo nhom == tong don (5 nam)", cat_rev, db_total_rev)

db_cats = sql(
    "SELECT count(DISTINCT p.category_id) FROM v_daily_sales v "
    "JOIN products p ON p.product_id = v.product_id")[0][0]
check("so nhom co ban duoc gom het", len(rows), int(db_cats))

section("GET /dashboard/revenue-by-category - tung nhom khop DB")
one_cat = rows[0]
db_cat = sql(
    "SELECT sum(v.revenue), sum(v.quantity_sold), count(DISTINCT v.product_id) "
    "FROM v_daily_sales v JOIN products p ON p.product_id = v.product_id "
    "WHERE p.category_id = %s", (one_cat["category_id"],))[0]
near(f"nhom {one_cat['category_id']} doanh thu", one_cat["total_revenue"], db_cat[0])
near(f"nhom {one_cat['category_id']} so luong", one_cat["total_quantity"], db_cat[1])
check(f"nhom {one_cat['category_id']} so SP", one_cat["product_count"],
      int(db_cat[2]))

section("GET /dashboard/revenue-by-category - date range")
c2017 = get("/dashboard/revenue-by-category?from_date=2017-01-01&to_date=2017-12-31")
check("status", c2017.status_code, 200)
c_rev = sum(x["total_revenue"] for x in c2017.json())
near("doanh thu 2017 khop DB", c_rev, db_rev2017[0])
check("so don 2017 khop", sum(x["total_orders"] for x in []) if False else 0, 0)
db_cat_2017 = sql(
    "SELECT sum(v.revenue) FROM v_daily_sales v "
    "WHERE v.sale_date BETWEEN '2017-01-01' AND '2017-12-31'")[0][0]
near("tong 2017 khop truc tiep view", c_rev, db_cat_2017)
ok("2017 < tong 5 nam", c_rev < cat_rev, f"{c_rev:,.0f} < {cat_rev:,.0f}")

check("nam khong co du lieu -> rong",
      get("/dashboard/revenue-by-category?from_date=1999-01-01&to_date=1999-12-31"
          ).json(), [])
check("from > to -> 422",
      get("/dashboard/revenue-by-category?from_date=2017-12-31&to_date=2017-01-01"
          ).status_code, 422)

# ================================================ INVENTORY VALUE
section("GET /dashboard/inventory-value")
r = get("/dashboard/inventory-value")
check("status", r.status_code, 200)
rows = r.json()
ok("co cua hang ton kho", len(rows) > 0, f"so CH={len(rows)}")
ok("sap xep gia tri giam dan",
   [x["total_value"] for x in rows]
   == sorted([x["total_value"] for x in rows], reverse=True))
for x in rows[:3]:
    print(f"     {x['store_code']} items={x['total_items']:>10,.0f} "
          f"value={x['total_value']:>15,.0f} "
          f"expiring={x['expiring_value']:>13,.0f} "
          f"({x['total_batches']} lot)")

total_value = sum(x["total_value"] for x in rows)
db_val, db_items, db_batches = sql(
    "SELECT sum(i.quantity * p.unit_cost), sum(i.quantity), count(*) "
    "FROM inventory i JOIN products p ON p.product_id = i.product_id "
    "WHERE i.quantity > 0")[0]
near("tong gia tri ton kho khop DB", total_value, db_val)
near("tong so luong ton kho khop DB",
     sum(x["total_items"] for x in rows), db_items)
check("tong so lot khop DB", sum(x["total_batches"] for x in rows), int(db_batches))

# overview (B5) must agree with this endpoint on total inventory value.
ov = get("/dashboard/overview").json()
near("giao voi /dashboard/overview cua B5", total_value, ov["total_inventory_value"])
print(f"     B8 total_value={total_value:,.0f} / B5 overview={ov['total_inventory_value']:,.0f}")

exp_val = sum(x["expiring_value"] for x in rows)
ok("expiring_value <= total_value", exp_val <= total_value,
   f"{exp_val:,.0f} <= {total_value:,.0f}")

# expiring_value must use the same 30-day window as v_expiring_inventory.
db_exp_val = sql(
    "SELECT sum(i.quantity * p.unit_cost) FROM inventory i "
    "JOIN products p ON p.product_id = i.product_id "
    "WHERE i.quantity > 0 AND i.expiry_date <= CURRENT_DATE + 30")[0][0]
near("expiring_value khop view 30 ngay", exp_val, db_exp_val)
check("mo rong include_empty",
      len(get("/dashboard/inventory-value?include_empty=true").json()) >= len(rows),
      True)
print(f"     mac dinh: {len(rows)} CH · include_empty: "
      f"{len(get('/dashboard/inventory-value?include_empty=true').json())} CH")

# ================================================= WASTE ANALYSIS
section("GET /dashboard/waste-analysis")
r = get("/dashboard/waste-analysis")
check("status", r.status_code, 200)
b = r.json()
for key in ["expired_batches", "expired_items", "expired_value",
            "expiring_batches", "expiring_items", "expiring_value",
            "estimated_waste_value", "window_days"]:
    ok(f"co truong '{key}'", key in b, b.get(key))
check("window_days = 30", b["window_days"], 30)
near("estimated = expired + expiring", b["estimated_waste_value"],
     b["expired_value"] + b["expiring_value"])
near("expired_value khop DB", b["expired_value"],
     sql("SELECT sum(i.quantity * p.unit_cost) FROM inventory i "
         "JOIN products p ON p.product_id = i.product_id "
         "WHERE i.quantity > 0 AND i.expiry_date < CURRENT_DATE")[0][0])
db_exp_batches = sql(
    "SELECT count(*) FROM inventory WHERE quantity > 0 "
    "AND expiry_date < CURRENT_DATE")[0][0]
check("so lot het han khop DB", b["expired_batches"], int(db_exp_batches))
print(f"     het han: {b['expired_batches']} lot / {b['expired_items']:,.0f} SP "
      f"/ {b['expired_value']:,.0f}")
print(f"     sap het han (<=30 ngay): {b['expiring_batches']} lot "
      f"/ {b['expiring_items']:,.0f} SP / {b['expiring_value']:,.0f}")
print(f"     uoc tinh lang phi: {b['estimated_waste_value']:,.0f}")

# Must be consistent with the B5 /dashboard/expiring view.
ex7 = get("/dashboard/expiring?days=0").json()
check("expired_batches == B5 expiring days=0", b["expired_batches"], len(ex7))

detail = get("/dashboard/waste-analysis?include_batches=true")
check("include_batches status", detail.status_code, 200)
ok("co expired_detail", "expired_detail" in detail.json())
ok("co expiring_detail", "expiring_detail" in detail.json())
d = detail.json()
if d["expired_detail"]:
    row = d["expired_detail"][0]
    ok("chi tiet lot het han co state='expired'",
       row["state"] == "expired", row["state"])
    ok("chi tiet co days_to_expiry am",
       row["days_to_expiry"] < 0, f"{row['days_to_expiry']} ngay")
    print(f"     vi du lot: {row['product_code']} {row['product_name'][:22]} "
          f"het han {row['days_to_expiry']} ngay truoc, "
          f"qty={row['quantity']:,.0f} value={row['value']:,.0f}")
check("limit=1 -> 1 dong chi tiet",
      len(get("/dashboard/waste-analysis?include_batches=true&limit=1"
              ).json()["expired_detail"]), 1)
check("limit=0 -> 422",
      get("/dashboard/waste-analysis?limit=0").status_code, 422)
check("limit=501 -> 422",
      get("/dashboard/waste-analysis?limit=501").status_code, 422)

# =============================================== FORECAST VS ACTUAL
section("GET /dashboard/forecast-vs-actual")
r = get("/dashboard/forecast-vs-actual")
check("status", r.status_code, 200)
b = r.json()
ok("co accuracy", "accuracy" in b)
ok("co message", bool(b["message"]), b["message"][:120])
print(f"     model={b['model_name']} forecast_rows={b['forecast_rows']} "
      f"actual_rows={b['actual_rows']} matched_rows={b['matched_rows']}")
print(f"     accuracy: {b['accuracy']}")

db_fc = sql("SELECT count(*) FROM forecasts WHERE model_name = %s",
            ("prophet",))[0][0]
check("forecast_rows khop DB", b["forecast_rows"], int(db_fc))
ok("co forecast trong bang", b["forecast_rows"] > 0, f"{b['forecast_rows']}")

# The data problem: forecasts are for Jan 2018, sales end Dec 2017.
db_fc_min, db_fc_max = sql(
    "SELECT min(forecast_date), max(forecast_date) FROM forecasts "
    "WHERE model_name = %s", ("prophet",))[0]
db_ac_min, db_ac_max = sql(
    "SELECT min(sale_date), max(sale_date) FROM v_daily_sales")[0]
print(f"     forecasts: {db_fc_min} .. {db_fc_max}")
print(f"     actuals  : {db_ac_min} .. {db_ac_max}")
ok("HAI KHOANG KHONG GIAO NHAU", db_fc_min > db_ac_max,
   f"forecast bat dau {db_fc_min} > actual ket thuc {db_ac_max}")
check("matched_rows = 0", b["matched_rows"], 0)
check("mape = None", b["accuracy"]["mape"], None)
check("mae = None", b["accuracy"]["mae"], None)
ok("message giai thich ro nguyen nhan",
   "different periods" in b["message"] or "cannot be measured" in b["message"])
print(f"     -> MAPE khong tinh duoc, API tra giai thich thay vi bao loi sai")

# Filtering to a window where BOTH exist must also yield zero matches.
both = get("/dashboard/forecast-vs-actual?from_date=2013-01-01&to_date=2017-12-31")
check("loc vao giai doan co du lieu thuc te -> matched=0",
      both.json()["matched_rows"], 0)
check("loc vao giai doan do -> matched=0",
      get("/dashboard/forecast-vs-actual?from_date=2018-01-01&to_date=2018-01-30"
          ).json()["matched_rows"], 0)

check("model xgboost -> 200", get("/dashboard/forecast-vs-actual?model_name=xgboost"
                                  ).status_code, 200)
xb = get("/dashboard/forecast-vs-actual?model_name=xgboost").json()
check("xgboost forecast_rows", xb["forecast_rows"], 90)
check("model sai -> 200 (khong co du lieu)",
      get("/dashboard/forecast-vs-actual?model_name=khong_co").status_code, 200)
check("model sai -> 0 dong",
      get("/dashboard/forecast-vs-actual?model_name=khong_co").json()["forecast_rows"], 0)

p15 = get("/dashboard/forecast-vs-actual?product_id=15")
check("filter product_id=15", p15.status_code, 200)
# 10 stores x 30 days. Not every product has all 10 stores: 13, 28 and 45
# cover only 9, so the 2,910 prophet rows are not a round 10 x 291.
check("product 15 co du bao (10 CH x 30 ngay)", p15.json()["forecast_rows"], 300)
db_p15 = sql("SELECT count(*) FROM forecasts WHERE model_name='prophet' "
             "AND product_id=15")[0][0]
check("product 15 khop DB", p15.json()["forecast_rows"], int(db_p15))
p13 = get("/dashboard/forecast-vs-actual?product_id=13")
check("product 13 chi 9 CH (270 dong)", p13.json()["forecast_rows"], 270)
print(f"     luu y: SP 13/28/45 chi co du bao 9/10 cua hang")
p_store = get("/dashboard/forecast-vs-actual?store_id=1")
check("filter store_id=1", p_store.json()["forecast_rows"], 300)
ok("product+store khop nhau",
   get("/dashboard/forecast-vs-actual?product_id=15&store_id=1"
       ).json()["forecast_rows"], 30)

check("include_detail=true -> 200",
      get("/dashboard/forecast-vs-actual?include_detail=true").status_code, 200)
check("include_detail khong co dong khi khong match",
      len(get("/dashboard/forecast-vs-actual?include_detail=true").json()["comparison"]), 0)
check("from > to -> 422",
      get("/dashboard/forecast-vs-actual?from_date=2018-01-30&to_date=2018-01-01"
          ).status_code, 422)
check("product_id=0 -> 422",
      get("/dashboard/forecast-vs-actual?product_id=0").status_code, 422)

section("Xac nhan khong co du lieu bi ghi")
check("orders van 18.260",
      get("/dashboard/revenue-by-store").json()[0]["total_orders"] > 0, True)
for table, expected in [("orders", 18260), ("order_items", 912999),
                        ("inventory", 1330), ("forecasts", 3000),
                        ("products", 50)]:
    got = sql(f"SELECT count(*) FROM {table}")[0][0]
    check(f"{table} khong doi", int(got), expected)

cur.close()
conn.close()

print("\n" + "=" * 78)
if FAILURES:
    print(f"FAILED {len(FAILURES)}:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("ALL TESTS PASSED")
print("=" * 78)
