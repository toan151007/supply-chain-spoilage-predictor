"""
Test suite for B10 (recommendations), B11 (reports) and B12 (auth).

Run with the server listening on 127.0.0.1:8000:

    cd backend
    python -m uvicorn app.main:app --port 8000
    python test_b10_b11_b12.py

Expected values are cross-checked against SQL, so the suite fails if the API
and the database disagree rather than confirming the API agrees with itself.

Nothing here writes to the database: recommendations and reports are GETs,
and the auth tests only issue and revoke tokens. The write-permission
checks use a product that is created and then removed by primary key.
"""

import os
import sys
import uuid

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_support import (  # noqa: E402
    FAILURES,
    MANAGER,
    OWNER,
    STAFF,
    check,
    delete,
    get,
    login,
    ok,
    post,
    put,
    report,
    request,
    section,
)

TAG = uuid.uuid4().hex[:8].upper()

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="spoilage_predictor",
    user="postgres", password=os.environ["DB_PASSWORD"],
)
cur = conn.cursor()


def sql(query, params=None):
    cur.execute(query, params)
    return cur.fetchall()


# =========================================================================
section("B12 - AUTH: login")
# =========================================================================
r = request("POST", "/auth/login", {"username": "owner", "password": "sai-mat-khau"})
check("sai mat khau -> 401", r.status_code, 401)
ok("thong bao khong lo username ton tai",
   "Incorrect username or password" in r.json()["detail"], r.json()["detail"])

r = request("POST", "/auth/login", {"username": "khong-ton-tai", "password": "x"})
check("username khong ton tai -> 401", r.status_code, 401)
ok("cung thong bao voi sai mat khau (khong lo username)",
   r.json()["detail"] == "Incorrect username or password")

check("thieu username -> 422",
      request("POST", "/auth/login", {"password": "x"}).status_code, 422)
check("thieu password -> 422",
      request("POST", "/auth/login", {"username": "owner"}).status_code, 422)

owner_token, owner_refresh = login(OWNER)
r = request("POST", "/auth/login", {"username": "owner", "password": "Owner@2026"})
body = r.json()
check("login dung -> 200", r.status_code, 200)
ok("co access_token", len(body["access_token"]) > 50, f"len={len(body['access_token'])}")
ok("co refresh_token", len(body["refresh_token"]) > 50)
check("token_type", body["token_type"], "bearer")
check("expires_in = 60 phut", body["expires_in"], 3600)
check("user.username", body["user"]["username"], "owner")
check("user.role", body["user"]["role"], "owner")
ok("KHONG lo password_hash", "password_hash" not in body["user"],
   str(list(body["user"].keys())))

manager_token, _ = login(MANAGER)
staff_token, _ = login(STAFF)
ok("lay duoc token cho ca 3 vai tro",
   all([owner_token, manager_token, staff_token]))

section("B12 - AUTH: /me")
r = get("/auth/me", owner_token)
check("co token -> 200", r.status_code, 200)
check("dung user", r.json()["username"], "owner")
check("dung role", r.json()["role"], "owner")
check("khong token -> 401", get("/auth/me").status_code, 401)
check("token rac -> 401", get("/auth/me", "abc.def.ghi").status_code, 401)
check("token khong phai chuoi -> 401", get("/auth/me", "khong-hop-le").status_code, 401)

section("B12 - AUTH: bao ve endpoint ghi")
check("GET khong token -> van mo (chi bao ve POST/PUT/DELETE)",
      get("/products?page_size=1").status_code, 200)

product_body = {
    "product_code": f"B12-{TAG}", "product_name": "SP test B12",
    "category_id": 1, "unit": "hop", "unit_cost": 1000,
    "selling_price": 1500, "shelf_life_days": 180,
}
check("POST khong token -> 401",
      post("/products", product_body).status_code, 401)
check("PUT khong token -> 401",
      put("/products/1", {"product_name": "x"}).status_code, 401)
check("DELETE khong token -> 401", delete("/products/99999").status_code, 401)
check("POST don hang khong token -> 401",
      post("/orders", {"order_code": "X", "store_id": 1,
                       "items": [{"product_id": 1, "quantity": 1,
                                  "unit_price": 1}]}).status_code, 401)
check("POST import khong token -> 401",
      post("/import/products", {}).status_code, 401)

r = post("/products", product_body, owner_token)
check("owner tao duoc san pham", r.status_code, 201)
new_pid = r.json()["product_id"] if r.status_code == 201 else None

r = post("/products", {**product_body, "product_code": f"B12-{TAG}-2"}, staff_token)
check("staff tao san pham -> 403", r.status_code, 403)
ok("thong bao 403 nen ro vai tro",
   "staff" in r.json()["detail"] and "owner" in r.json()["detail"],
   r.json()["detail"][:80])

r = post("/products", {**product_body, "product_code": f"B12-{TAG}-3"}, manager_token)
check("manager tao duoc san pham", r.status_code, 201)
if r.status_code == 201:
    manager_pid = r.json()["product_id"]
    delete(f"/products/{manager_pid}", manager_token)

check("staff duoc tao don hang (vai tro thap van lam viec hang ngay)",
      post("/orders", {"order_code": f"B12-ORD-{TAG}", "store_id": 1,
                       "items": [{"product_id": 1, "quantity": 1,
                                  "unit_price": 100}]},
           staff_token).status_code, 201)

section("B12 - AUTH: refresh")
r = request("POST", "/auth/refresh", None, token=owner_refresh)
check("refresh bang header -> 200", r.status_code, 200)
new_access = r.json()["access_token"]
new_refresh = r.json()["refresh_token"]
ok("token moi khac token cu", new_access != owner_token)
ok("co the dung access token moi",
   get("/auth/me", new_access).status_code == 200)

r = request("POST", "/auth/refresh", {"refresh_token": owner_refresh})
check("refresh token cu da xoay -> 401", r.status_code, 401)
ok("thong bao da bi thu hoi", "revoked" in r.json()["detail"].lower(),
   r.json()["detail"])

check("access token khong duoc dung de refresh -> 401",
      request("POST", "/auth/refresh", None, token=owner_token).status_code, 401)

section("B12 - AUTH: logout")
tok, _ = login(OWNER)
check("token moi hoat dong", get("/auth/me", tok).status_code == 200, True)
r = request("POST", "/auth/logout", None, token=tok)
check("logout -> 200", r.status_code, 200)
check("token bi thu hoi -> 401", get("/auth/me", tok).status_code, 401)
check("logout khong token -> 401", request("POST", "/auth/logout").status_code, 401)

# =========================================================================
section("B10 - RECOMMENDATIONS /import")
# =========================================================================
r = get("/recommendations/import")
check("status", r.status_code, 200)
rows = r.json()
ok("co du lieu", len(rows) > 0, f"{len(rows)} dong")

first = rows[0]
for field in ("product_id", "product_name", "store_id", "store_name",
              "current_stock", "predicted_demand", "recommended_import_qty",
              "priority", "reason"):
    ok(f"co truong '{field}'", field in first)
ok("priority hop le", first["priority"] in ("high", "medium", "low"),
   first["priority"])
ok("co ' | ' trong reason de giai thich", " | " in first["reason"])

db_fc = sql("SELECT store_id, product_id, sum(predicted_quantity) "
            "FROM forecasts WHERE model_name='prophet' "
            "GROUP BY store_id, product_id ORDER BY sum(predicted_quantity) DESC "
            "LIMIT 1")[0]
mine = next(x for x in rows if x["store_id"] == db_fc[0]
            and x["product_id"] == db_fc[1])
ok("du bao khop DB", abs(mine["predicted_demand"] - float(db_fc[2])) < 0.01,
   f"api={mine['predicted_demand']} db={db_fc[2]}")
print(f"     lon nhat: {mine['store_code']} {mine['product_code']} "
      f"du_bao={mine['predicted_demand']:,.0f} "
      f"ton={mine['current_stock']:,.0f} "
      f"de_xuat={mine['recommended_import_qty']:,.0f}")

# The formula must hold exactly.
calc = max(0.0, mine["predicted_demand"] - (mine["current_stock"] - mine["expiring_stock"])
           + mine["safety_stock"])
ok("cong thuc khop: max(0, du_bao - ton_dung + an_toan)",
   abs(mine["recommended_import_qty"] - round(calc, 3)) < 0.01,
   f"api={mine['recommended_import_qty']} calc={round(calc, 3)}")

ok("tat ca de_xuat >= 0", all(x["recommended_import_qty"] >= 0 for x in rows))
ok("sap xep giam dan",
   [x["recommended_import_qty"] for x in rows]
   == sorted([x["recommended_import_qty"] for x in rows], reverse=True))
ok("chi co cap SP/CH co du bao",
   len(rows) <= 100, f"{len(rows)}/100 cap")
check("filter store_id", len(get("/recommendations/import?store_id=1").json()) <= 10, True)
check("limit=5", len(get("/recommendations/import?limit=5").json()), 5)
check("limit=0 -> 422", get("/recommendations/import?limit=0").status_code, 422)
check("store_id=0 -> 422",
      get("/recommendations/import?store_id=0").status_code, 422)

section("B10 - RECOMMENDATIONS /expiring")
# limit=1000 so the count can be compared with the database: the default of
# 200 silently truncates, which would make the row-count check meaningless.
r = get("/recommendations/expiring?days=7&limit=1000")
check("status", r.status_code, 200)
rows = r.json()
ok("co du lieu", len(rows) > 0, f"{len(rows)} lot")
for field in ("inventory_id", "store_name", "product_name", "days_to_expiry",
              "quantity", "total_value", "priority", "action", "reason"):
    ok(f"co truong '{field}'", field in rows[0])
ok("action hop le",
   all(x["action"] in ("discount", "transfer", "destroy") for x in rows))
ok("san pham het han phai destroy",
   all(x["action"] == "destroy" for x in rows if x["days_to_expiry"] < 0))
# Compare unrounded so two batches with the same stored value but different
# 2-decimal rounding cannot trip this.
ok("sap xep theo gia tri giam dan",
   all(rows[i]["total_value"] >= rows[i + 1]["total_value"] - 0.01
       for i in range(len(rows) - 1)))

db_exp = sql("SELECT count(*) FROM inventory WHERE quantity > 0 "
             "AND expiry_date <= CURRENT_DATE + 7")[0][0]
check("so lot khop DB (limit=1000 khong cat)", len(rows), int(db_exp))
print(f"     7 ngay: {len(rows)} lot · mau: {rows[0]['product_code']} "
      f"con {rows[0]['days_to_expiry']} ngay · {rows[0]['action']}")
check("limit mac dinh 200 co cat",
      len(get("/recommendations/expiring?days=7").json()) <= 200, True)

check("days=30 (gioi han) -> 200",
      get("/recommendations/expiring?days=30").status_code, 200)
check("days=31 -> 422",
      get("/recommendations/expiring?days=31").status_code, 422)
check("days=0 -> 422", get("/recommendations/expiring?days=0").status_code, 422)
check("filter store_id",
      len(get("/recommendations/expiring?days=7&store_id=1").json())
      <= len(rows), True)

section("B10 - RECOMMENDATIONS /slow-moving")
r = get("/recommendations/slow-moving")
check("status", r.status_code, 200)
ok("danh sach (co the rong tren du lieu nay)", isinstance(r.json(), list),
   f"{len(r.json())} dong")
print(f"     mac dinh (ban <=5, ton >=50): {len(r.json())} dong")
print("     -> dataset nay moi san pham ban 300-1500/30 ngay nen KHONG co "
      "hang ban cham; dung nguong linh hoat de kiem chung:")

r = get("/recommendations/slow-moving?min_stock=1&max_units_sold=100000&limit=1000")
rows = r.json()
check("nguong linh hoat -> co du lieu", len(rows) > 0, True)
ok("co truong day du",
   all(k in rows[0] for k in
       ("current_stock", "units_sold_30d", "days_of_cover", "action", "reason")))
ok("days_of_cover khong am",
   all((x["days_of_cover"] is None) or x["days_of_cover"] >= 0 for x in rows))
if rows[0]["units_sold_30d"] == 0:
    ok("ban 0 -> days_of_cover = None",
       rows[0]["days_of_cover"] is None)
print(f"     mau: {rows[0]['store_code']} {rows[0]['product_code']} "
      f"ban_30d={rows[0]['units_sold_30d']} ton={rows[0]['current_stock']} "
      f"cover={rows[0]['days_of_cover']} -> {rows[0]['action']}")

# The 30-day window must end at the last day WITH DATA, not today.
# Anchoring on today would find zero sales everywhere and flag the whole
# catalogue as dead stock.
db_last = sql("SELECT max(order_date)::date FROM orders "
              "WHERE status='completed' AND order_type='sale'")[0][0]
db_window_start = str(db_last - __import__("datetime").timedelta(days=30))
# Upper bound is exclusive and must cover db_last itself, matching the
# endpoint's `anchor + 1 day`.
db_window_end = str(db_last + __import__("datetime").timedelta(days=1))
db_sold = sql(
    "SELECT o.store_id, oi.product_id, sum(oi.quantity) FROM order_items oi "
    "JOIN orders o ON o.order_id = oi.order_id "
    "WHERE o.status='completed' AND o.order_type='sale' "
    "  AND o.order_date >= %s AND o.order_date < %s "
    "GROUP BY o.store_id, oi.product_id ORDER BY 3 DESC LIMIT 1",
    (db_window_start, db_window_end))[0]
mine = next((x for x in rows if x["store_id"] == db_sold[0]
             and x["product_id"] == db_sold[1]), None)
ok("cap ban nhieu nhat co trong danh sach",
   mine is not None, f"store={db_sold[0]} product={db_sold[1]}")
if mine:
    ok("so luong ban 30 ngay khop DB (dung ngay du lieu, khong dung hom nay)",
       abs(mine["units_sold_30d"] - float(db_sold[2])) < 0.01,
       f"api={mine['units_sold_30d']} db={db_sold[2]}")
    print(f"     cua so ban thuc te: store={db_sold[0]} product={db_sold[1]} "
          f"-> {db_sold[2]} (API: {mine['units_sold_30d']})")
print(f"     cua so ban nhieu nhat trong 30 ngay: {db_sold[2]} san pham")

check("days=0 -> 422", get("/recommendations/slow-moving?days=0").status_code, 422)
check("min_stock=-1 -> 422",
      get("/recommendations/slow-moving?min_stock=-1").status_code, 422)

# =========================================================================
section("B11 - REPORTS: 4 endpoint x 3 dinh dang")
# =========================================================================
EXPECTED_MAGIC = {"csv": b"\xef\xbb\xbf", "xlsx": b"PK\x03\x04", "pdf": b"%PDF"}
EXPECTED_CTYPE = {
    "csv": "text/csv",
    "xlsx": "spreadsheetml",
    "pdf": "application/pdf",
}

for endpoint in ("inventory", "expiring", "sales", "waste"):
    for fmt, magic in EXPECTED_MAGIC.items():
        r = get(f"/reports/{endpoint}/export?format={fmt}")
        if not ok(f"{endpoint}/{fmt} -> 200", r.status_code == 200,
                  str(r.status_code), FAILURES):
            continue
        ok(f"{endpoint}/{fmt} co dung magic bytes",
           r.raw.startswith(magic), r.raw[:8].hex())
        ok(f"{endpoint}/{fmt} dung Content-Type",
           EXPECTED_CTYPE[fmt] in r.headers.get("content-type", ""),
           r.headers.get("content-type", "")[:50])
        ok(f"{endpoint}/{fmt} la file download",
           "attachment" in r.headers.get("content-disposition", ""),
           r.headers.get("content-disposition", "")[:60])
        ok(f"{endpoint}/{fmt} co noi dung", len(r.raw) > 100, f"{len(r.raw):,} bytes")
        print(f"       {len(r.raw):>10,} bytes  {r.headers.get('Content-Type','')[:38]}")

section("B11 - REPORTS: noi dung dung dac")
r = get("/reports/inventory/export?format=csv")
text = r.raw.decode("utf-8-sig")
ok("CSV co BOM (Excel Windows doc dung tieng Viet)", r.raw.startswith(b"\xef\xbb\xbf"))
header = text.splitlines()[0]
for col in ("Ma lot", "Ma CH", "Ten SP", "Han su dung", "So luong"):
    ok(f"CSV co cot '{col}'", col in header)
csv_rows = text.strip().splitlines()[1:]
db_inv = sql("SELECT count(*) FROM inventory WHERE quantity > 0")[0][0]
check("so dong CSV khop DB", len(csv_rows), int(db_inv))
print(f"     {len(csv_rows)} dong, dau: {csv_rows[0][:80]}")

r = get("/reports/sales/export?format=csv&group_by=day")
text = r.raw.decode("utf-8-sig")
day_rows = len(text.strip().splitlines()) - 1
db_days = sql("SELECT count(DISTINCT order_date::date) FROM orders "
              "WHERE status='completed' AND order_type='sale'")[0][0]
check("sales theo ngay -> 1 dong/ngay", day_rows, int(db_days))
print(f"     group_by=day: {day_rows} dong (DB co {db_days} ngay ban)")

for gb, expected in [("store", 10), ("category", 7), ("product", 50)]:
    n = len(get(f"/reports/sales/export?format=csv&group_by={gb}").raw
            .decode("utf-8-sig").strip().splitlines()) - 1
    check(f"group_by={gb} -> {expected} dong", n, expected)

r = get("/reports/sales/export?format=csv&from_date=2017-01-01&to_date=2017-12-31")
ok("loc nam 2017 -> nho hon toan bo",
   len(r.raw) < len(get("/reports/sales/export?format=csv").raw),
   f"{len(r.raw):,} bytes")
ok("co header X-Total-Rows", "x-total-rows" in r.headers,
   r.headers.get("x-total-rows", ""))
ok("X-Truncated=false khi khong cat", r.headers.get("x-truncated") == "false",
   r.headers.get("x-truncated", ""))

r = get("/reports/waste/export?format=csv")
waste_rows = len(r.raw.decode("utf-8-sig").strip().splitlines()) - 1
db_waste = sql("SELECT count(*) FROM inventory WHERE quantity > 0 "
               "AND expiry_date IS NOT NULL "
               "AND expiry_date <= CURRENT_DATE + 30")[0][0]
check("waste khop DB", waste_rows, int(db_waste))

r = get("/reports/inventory/export?format=xlsx")
ok("XLSX doc duoc bang pandas/openpyxl", r.raw.startswith(b"PK\x03\x04"))
try:
    import io

    import pandas as pd
    frame = pd.read_excel(io.BytesIO(r.raw))
    check("XLSX so dong khop CSV", len(frame), int(db_inv))
    ok("XLSX co cung cot", "Han su dung" in frame.columns, str(list(frame.columns)[:4]))
except ImportError:
    ok("co openpyxl de doc lai", False, "thieu openpyxl")

r = get("/reports/waste/export?format=pdf")
ok("PDF bat dau bang %PDF", r.raw.startswith(b"%PDF"))
ok("PDF co EOF", b"%%EOF" in r.raw[-1024:])

section("B11 - REPORTS: edge cases")
check("format=pdf -> 200", get("/reports/inventory/export?format=pdf").status_code, 200)
check("format=doc -> 422", get("/reports/inventory/export?format=doc").status_code, 422)
check("khong format -> mac dinh csv", "text/csv" in get(
    "/reports/inventory/export").headers.get("content-type", ""), True)
check("from > to -> 422",
      get("/reports/sales/export?from_date=2017-12-31&to_date=2017-01-01"
          ).status_code, 422)
check("expiring days=31 -> 422",
      get("/reports/expiring/export?days=31").status_code, 422)
check("waste days=31 -> 422",
      get("/reports/waste/export?days=31").status_code, 422)
check("group_by sai -> 422",
      get("/reports/sales/export?group_by=quy").status_code, 422)
check("store_id=0 -> 422",
      get("/reports/inventory/export?store_id=0").status_code, 422)
check("loc store khong co du lieu -> 200",
      get("/reports/inventory/export?store_id=999").status_code, 200)

# =========================================================================
section("Cleanup - xoa theo KHOA CHINH")


def cleanup():
    # Orders: the FK is ON DELETE CASCADE so deleting the order takes the
    # lines with it.
    ids = [row[0] for row in sql(
        "SELECT order_id FROM orders WHERE order_code LIKE %s", (f"B12-ORD-{TAG}%",))]
    if ids:
        cur.execute("DELETE FROM orders WHERE order_id = ANY(%s)", (ids,))
        print(f"  xoa {cur.rowcount} don (cascade dong chi tiet)")
    # Products by primary key, never by a LIKE on the code.
    ids = [row[0] for row in sql(
        "SELECT product_id FROM products WHERE product_code LIKE %s",
        (f"B12-{TAG}%",))]
    if ids:
        cur.execute("DELETE FROM products WHERE product_id = ANY(%s)", (ids,))
        print(f"  xoa {cur.rowcount} san pham")
    conn.commit()

    leftover = sql("SELECT count(*) FROM products WHERE product_id > 50")[0][0]
    leftover_ord = sql("SELECT count(*) FROM orders WHERE order_id > 18260")[0][0]
    ok("khong con san pham du tich", leftover == 0, f"con={leftover}")
    ok("khong con don du tich", leftover_ord == 0, f"con={leftover_ord}")


cleanup()

for table, expected in [("orders", 18260), ("order_items", 912999),
                        ("products", 50), ("inventory", 1330),
                        ("forecasts", 3000), ("users", 3)]:
    check(f"{table} khong doi", int(sql(f"SELECT count(*) FROM {table}")[0][0]),
          expected)

cur.close()
conn.close()

print("\n" + "=" * 78)
sys.exit(report())

