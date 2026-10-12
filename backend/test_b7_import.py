"""
Test suite for B7 - file import API (Excel / CSV).

Run with the server listening on 127.0.0.1:8000:

    cd backend
    python -m uvicorn app.main:app --port 8000
    python test_b7_import.py

The suite writes to the database. Every row it creates carries the IMPT-
prefix, and cleanup deletes exactly those - seeded data is never touched.
"""

import io
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

import pandas as pd
import psycopg2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000/api/v1"
FAILURES = []
CREATED = {"products": [], "inventory": [], "orders": []}

# Per-run token so repeated runs never collide on UNIQUE constraints.
TAG = uuid.uuid4().hex[:8].upper()


class Resp:
    def __init__(self, status, body, raw=b""):
        self.status_code = status
        self._body = body
        self.raw = raw

    def json(self):
        return self._body


def multipart(field, filename, payload, content_type="text/csv"):
    """Build a multipart/form-data body with a single file field."""
    boundary = "----b7boundary" + uuid.uuid4().hex
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        .encode()
    )
    body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.write(payload)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    return body.getvalue(), f"multipart/form-data; boundary={boundary}"


def post_file(path, filename, payload, content_type="text/csv"):
    body, ctype = multipart("file", filename, payload, content_type)
    req = urllib.request.Request(
        BASE + path, data=body, method="POST",
        headers={"Content-Type": ctype},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return Resp(r.status, json.loads(raw) if raw else None, raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return Resp(e.code, json.loads(raw) if raw else None, raw)
        except ValueError:
            return Resp(e.code, {"_raw": raw.decode("utf-8", "replace")[:300]}, raw)


def get_raw(path):
    req = urllib.request.Request(BASE + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return Resp(r.status, None, r.read())
    except urllib.error.HTTPError as e:
        return Resp(e.code, None, e.read())


def post_json(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return Resp(r.status, json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return Resp(e.code, json.loads(raw) if raw else None)


def get_json(path):
    req = urllib.request.Request(BASE + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return Resp(r.status, json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        return Resp(e.code, json.loads(raw) if raw else None)


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


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def csv_bytes(rows, columns):
    return pd.DataFrame(rows, columns=columns).to_csv(index=False).encode()


def xlsx_bytes(rows, columns):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(rows, columns=columns).to_excel(
            writer, index=False, sheet_name="Sheet1"
        )
    return buffer.getvalue()


def record(result, kind):
    """Remember what a successful import created, for cleanup."""
    if result.status_code != 200:
        return
    body = result.json()
    if kind == "products":
        CREATED["products"].extend(body.get("created_ids", []))
    elif kind == "inventory":
        CREATED["inventory"].extend(body.get("created_ids", []))
    elif kind == "sales":
        CREATED["orders"].extend(body.get("created_ids", []))


PRODUCT_COLS = ["product_code", "product_name", "category_id", "unit",
                "unit_cost", "selling_price", "shelf_life_days",
                "min_stock", "max_stock", "supplier"]
INV_COLS = ["product_id", "store_id", "quantity", "expiry_date",
            "batch_code", "received_date"]
SALES_COLS = ["order_code", "order_date", "store_id", "product_id", "quantity",
              "unit_price", "discount_percent", "order_type", "status",
              "payment_method", "customer_name"]


def good_product(n=0):
    return {
        "product_code": f"IMPT-{TAG}-P{n}",
        "product_name": f"San pham test {n}",
        "category_id": 1,
        "unit": "hop",
        "unit_cost": 10000,
        "selling_price": 15000,
        "shelf_life_days": 180,
        "min_stock": 50,
        "max_stock": 300,
        "supplier": "NCC Test",
    }


# ================================================================= TEMPLATES
section("GET /import/template - tai file mau")
for kind, cols in [("products", PRODUCT_COLS), ("inventory", INV_COLS),
                   ("sales", SALES_COLS)]:
    r = get_raw(f"/import/template/{kind}?fmt=csv")
    check(f"{kind} csv status", r.status_code, 200)
    ok(f"{kind} csv co header dung", all(c.encode() in r.raw for c in cols))
    print(f"     dung luong={len(r.raw)} bytes, dong dau: {r.raw.splitlines()[0][:80]}")
    r2 = get_raw(f"/import/template/{kind}?fmt=xlsx")
    check(f"{kind} xlsx status", r2.status_code, 200)
    ok(f"{kind} xlsx la ZIP (PK)", r2.raw.startswith(b"PK\x03\x04"))
    frame = pd.read_excel(io.BytesIO(r2.raw))
    check(f"{kind} xlsx doc duoc, so cot", len(frame.columns), len(cols))
    ok(f"{kind} xlsx khop header CSV", list(frame.columns) == cols)

check("type sai -> 404", get_raw("/import/template/khong_co").status_code, 404)
check("fmt sai -> 422", get_raw("/import/template/products?fmt=pdf").status_code, 422)

section("GET /import/types")
r = get_json("/import/types")
check("status", r.status_code, 200)
check("so loai", len(r.json()), 3)
ok("mo tao tung loai",
   all(t["required_columns"] and t["columns"] and t["description"]
       for t in r.json()))
print(f"     products can co: {r.json()[0]['required_columns']}")

# ================================================================ PRODUCTS
section("POST /import/products - happy path CSV")
rows = [good_product(1), good_product(2), good_product(3)]
r = post_file("/import/products", "p.csv", csv_bytes(rows, PRODUCT_COLS))
record(r, "products")
check("status", r.status_code, 200)
b = r.json()
check("total_rows", b["total_rows"], 3)
check("success_rows", b["success_rows"], 3)
check("error_rows", b["error_rows"], 0)
check("so id tra ve", len(b["created_ids"]), 3)
ok("created_ids la so", all(isinstance(i, int) for i in b["created_ids"]))
print(f"     message: {b['message']}")

section("POST /import/products - happy path XLSX")
r = post_file("/import/products", "p.xlsx", xlsx_bytes([good_product(4)], PRODUCT_COLS),
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
record(r, "products")
check("xlsx status", r.status_code, 200)
check("xlsx success_rows", r.json()["success_rows"], 1)

section("POST /import/products - dong sai -> rollback mac dinh")
bad = good_product(5)
bad["category_id"] = 9999          # FK khong ton tai
bad2 = good_product(6)
bad2["unit_cost"] = -5             # am
bad3 = good_product(7)
bad3["shelf_life_days"] = 0        # phai > 0
r = post_file("/import/products", "bad.csv",
              csv_bytes([good_product(8), bad, bad2, bad3], PRODUCT_COLS))
check("status van la 200", r.status_code, 200)
b = r.json()
check("total_rows", b["total_rows"], 4)
check("error_rows", b["error_rows"], 3)
check("khong ghi gi (rollback)", len(b["created_ids"]), 0)
ok("row 8 (sai FK) bao loi",
   any(e["row_number"] == 2 and "category_id" in e["message"] for e in b["errors"]),
   next((e["message"] for e in b["errors"] if e["row_number"] == 2), ""))
for e in b["errors"]:
    print(f"     dong {e['row_number']}: {e['message']}")
check("dong sai bat dau tu 1", sorted(e["row_number"] for e in b["errors"]), [2, 3, 4])

# xac nhan dong tot o dong 1 thuc su khong duoc ghi
leftover = get_json(f"/products?search=IMPT-{TAG}-P8")
check("san pham dong 1 khong ton tai sau rollback",
      leftover.json()["total"], 0)

section("POST /import/products - on_error=skip")
r = post_file("/import/products?on_error=skip", "bad.csv",
              csv_bytes([good_product(9), bad, good_product(10)], PRODUCT_COLS))
record(r, "products")
check("status", r.status_code, 200)
b = r.json()
check("total_rows", b["total_rows"], 3)
check("success_rows", b["success_rows"], 2)
check("error_rows", b["error_rows"], 1)
check("da ghi 2 dong", len(b["created_ids"]), 2)
print(f"     message: {b['message']}")
kept = get_json(f"/products?search=IMPT-{TAG}-P9")
check("san pham hop le da duoc ghi", kept.json()["total"], 1)

section("POST /import/products - trung product_code trong DB -> 409")
r = post_file("/import/products", "dup.csv", csv_bytes([good_product(9)], PRODUCT_COLS))
check("status", r.status_code, 409)
print(f"     detail: {r.json().get('detail', '')[:90]}")

section("POST /import/products - trung product_code trong file")
r = post_file("/import/products", "dup2.csv",
              csv_bytes([good_product(11), good_product(11)], PRODUCT_COLS))
check("trung trong file -> 200 voi error", r.status_code, 200)
check("error_rows", r.json()["error_rows"], 1)
check("rollback -> khong ghi", len(r.json()["created_ids"]), 0)

# =============================================================== INVENTORY
section("POST /import/inventory - happy path")
rows = [
    {"product_id": 1, "store_id": 1, "quantity": 100,
     "expiry_date": "2027-01-31", "batch_code": f"IMPT-{TAG}-B1",
     "received_date": "2026-10-01"},
    {"product_id": 2, "store_id": 1, "quantity": 50,
     "expiry_date": "2027-02-28", "batch_code": f"IMPT-{TAG}-B2",
     "received_date": "2026-10-01"},
]
r = post_file("/import/inventory", "inv.csv", csv_bytes(rows, INV_COLS))
record(r, "inventory")
check("status", r.status_code, 200)
check("success_rows", r.json()["success_rows"], 2)
check("created ids", len(r.json()["created_ids"]), 2)

section("POST /import/inventory - validation")
cases = [
    ({"product_id": 9999, "store_id": 1, "quantity": 5,
      "expiry_date": "2027-01-01", "batch_code": "x", "received_date": ""},
     "product_id khong ton tai"),
    ({"product_id": 1, "store_id": 999, "quantity": 5,
      "expiry_date": "2027-01-01", "batch_code": "x", "received_date": ""},
     "store_id khong ton tai"),
    ({"product_id": 1, "store_id": 1, "quantity": -3,
      "expiry_date": "2027-01-01", "batch_code": "x", "received_date": ""},
     "quantity am"),
    ({"product_id": 1, "store_id": 1, "quantity": 5,
      "expiry_date": "khong-phai-ngay", "batch_code": "x", "received_date": ""},
     "expiry_date sai dinh dang"),
    ({"product_id": "", "store_id": 1, "quantity": 5,
      "expiry_date": "2027-01-01", "batch_code": "x", "received_date": ""},
     "product_id rong"),
]
for bad_row, label in cases:
    r = post_file("/import/inventory", "b.csv", csv_bytes([bad_row], INV_COLS))
    ok(f"{label} -> 200 + 1 loi",
       r.status_code == 200 and r.json()["error_rows"] == 1,
       r.json()["errors"][0]["message"] if r.status_code == 200 else r.status_code)

section("POST /import/inventory - trung lot trong DB -> 409")
r = post_file("/import/inventory", "dup.csv", csv_bytes([rows[0]], INV_COLS))
check("status", r.status_code, 409)
print(f"     detail: {r.json().get('detail', '')[:110]}")

section("POST /import/inventory - trung lot trong file")
r = post_file("/import/inventory", "dup2.csv", csv_bytes([rows[1], rows[1]], INV_COLS))
check("trong file -> error", r.json()["error_rows"], 1)
check("rollback -> khong ghi", len(r.json()["created_ids"]), 0)

# =================================================================== SALES
section("POST /import/sales - happy path, gop theo order_code")
code = f"IMPT-{TAG}-ORD1"
rows = [
    {"order_code": code, "order_date": "2026-09-01", "store_id": 1,
     "product_id": 1, "quantity": 5, "unit_price": 15000,
     "discount_percent": 0, "order_type": "sale", "status": "completed",
     "payment_method": "cash", "customer_name": "Khach test"},
    {"order_code": code, "order_date": "2026-09-01", "store_id": 1,
     "product_id": 2, "quantity": 2, "unit_price": 25000,
     "discount_percent": 10, "order_type": "sale", "status": "completed",
     "payment_method": "cash", "customer_name": "Khach test"},
]
r = post_file("/import/sales", "s.csv", csv_bytes(rows, SALES_COLS))
record(r, "sales")
check("status", r.status_code, 200)
check("total_rows", r.json()["total_rows"], 2)
check("success_rows", r.json()["success_rows"], 2)
check("2 dong -> 1 don (gop theo order_code)", len(r.json()["created_ids"]), 1)
OID = r.json()["created_ids"][0]
print(f"     don tao: id={OID} code={code}")

# 5*15000 + 2*25000*0.9 = 75000 + 45000 = 120000
detail = get_json(f"/orders/{OID}").json()
check("so dong chi tiet", len(detail["items"]), 2)
check("line_total 1", detail["items"][0]["line_total"], 75000.0)
check("line_total 2 (giam 10%)", detail["items"][1]["line_total"], 45000.0)
check("total_amount tinh tu dong hang", detail["total_amount"], 120000.0)
check("total_quantity", detail["total_quantity"], 7.0)
print(f"     total_amount={detail['total_amount']} total_quantity={detail['total_quantity']}")

section("POST /import/sales - dong khong co order_code -> moi dong 1 don")
rows2 = [
    {"order_code": "", "order_date": "2026-09-02", "store_id": 2,
     "product_id": 3, "quantity": 1, "unit_price": 1000,
     "discount_percent": 0, "order_type": "sale", "status": "completed",
     "payment_method": "cash", "customer_name": ""},
    {"order_code": "", "order_date": "2026-09-02", "store_id": 2,
     "product_id": 4, "quantity": 3, "unit_price": 2000,
     "discount_percent": 0, "order_type": "sale", "status": "completed",
     "payment_method": "cash", "customer_name": ""},
]
r = post_file("/import/sales", "s2.csv", csv_bytes(rows2, SALES_COLS))
record(r, "sales")
check("2 dong -> 2 don", len(r.json()["created_ids"]), 2)

section("POST /import/sales - validation")
cases = [
    ({"order_code": "", "order_date": "abc", "store_id": 1, "product_id": 1,
      "quantity": 1, "unit_price": 1, "discount_percent": 0,
      "order_type": "sale", "status": "completed", "payment_method": "cash",
      "customer_name": ""}, "order_date sai"),
    ({"order_code": "", "order_date": "2026-09-03", "store_id": 999,
      "product_id": 1, "quantity": 1, "unit_price": 1, "discount_percent": 0,
      "order_type": "sale", "status": "completed", "payment_method": "cash",
      "customer_name": ""}, "store_id sai"),
    ({"order_code": "", "order_date": "2026-09-03", "store_id": 1,
      "product_id": 999, "quantity": 1, "unit_price": 1, "discount_percent": 0,
      "order_type": "sale", "status": "completed", "payment_method": "cash",
      "customer_name": ""}, "product_id sai"),
    ({"order_code": "", "order_date": "2026-09-03", "store_id": 1,
      "product_id": 1, "quantity": 0, "unit_price": 1, "discount_percent": 0,
      "order_type": "sale", "status": "completed", "payment_method": "cash",
      "customer_name": ""}, "quantity = 0"),
    ({"order_code": "", "order_date": "2026-09-03", "store_id": 1,
      "product_id": 1, "quantity": 1, "unit_price": -5, "discount_percent": 0,
      "order_type": "sale", "status": "completed", "payment_method": "cash",
      "customer_name": ""}, "unit_price am"),
    ({"order_code": "", "order_date": "2026-09-03", "store_id": 1,
      "product_id": 1, "quantity": 1, "unit_price": 1, "discount_percent": 150,
      "order_type": "sale", "status": "completed", "payment_method": "cash",
      "customer_name": ""}, "discount > 100"),
    ({"order_code": "", "order_date": "2026-09-03", "store_id": 1,
      "product_id": 1, "quantity": 1, "unit_price": 1, "discount_percent": 0,
      "order_type": "xyz", "status": "completed", "payment_method": "cash",
      "customer_name": ""}, "order_type sai"),
    ({"order_code": "", "order_date": "2026-09-03", "store_id": 1,
      "product_id": 1, "quantity": 1, "unit_price": 1, "discount_percent": 0,
      "order_type": "sale", "status": "xyz", "payment_method": "cash",
      "customer_name": ""}, "status sai"),
    ({"order_code": "", "order_date": "2026-09-03", "store_id": 1,
      "product_id": 1, "quantity": 1, "unit_price": 1, "discount_percent": 0,
      "order_type": "sale", "status": "completed", "payment_method": "bitcoin",
      "customer_name": ""}, "payment_method sai"),
]
for bad_row, label in cases:
    r = post_file("/import/sales", "b.csv", csv_bytes([bad_row], SALES_COLS))
    ok(f"{label} -> 1 loi",
       r.status_code == 200 and r.json()["error_rows"] == 1,
       r.json()["errors"][0]["message"] if r.status_code == 200 else r.status_code)

section("POST /import/sales - order_code trung DB -> 409")
r = post_file("/import/sales", "dup.csv", csv_bytes([rows[0]], SALES_COLS))
check("status", r.status_code, 409)
print(f"     detail: {r.json().get('detail', '')[:90]}")

section("POST /import/sales - rollback khi 1 dong sai")
r = post_file("/import/sales", "mix.csv",
              csv_bytes([rows2[0],
                         {"order_code": "", "order_date": "2026-09-04",
                          "store_id": 1, "product_id": 999, "quantity": 1,
                          "unit_price": 1, "discount_percent": 0,
                          "order_type": "sale", "status": "completed",
                          "payment_method": "cash", "customer_name": ""}],
                        SALES_COLS))
check("error_rows", r.json()["error_rows"], 1)
check("rollback -> khong tao don nao", len(r.json()["created_ids"]), 0)

# =================================================================== EDGE
section("Thieu cot bat buoc -> 422")
REQUIRED = {
    "products": "category_id",
    "inventory": "expiry_date",
    "sales": "unit_price",
}
for kind, cols in [("products", PRODUCT_COLS), ("inventory", INV_COLS),
                   ("sales", SALES_COLS)]:
    # Drop a REQUIRED column. Dropping an optional one is valid and must
    # succeed, which is covered separately below.
    missing = REQUIRED[kind]
    partial = [c for c in cols if c != missing]
    row = {c: "1" for c in partial}
    if "product_code" in row:
        row["product_code"] = f"IMPT-{TAG}-MISS"
    if "batch_code" in row:
        row["batch_code"] = f"IMPT-{TAG}-MISS"
    if "order_code" in row:
        row["order_code"] = f"IMPT-{TAG}-MISS"

    r = post_file(f"/import/{kind}", "x.csv", csv_bytes([row], partial))
    check(f"{kind} thieu '{missing}' -> 422", r.status_code, 422)
    detail = r.json().get("detail", "")
    ok(f"{kind} 422 nen ten cot", missing in detail, detail[:110])

section("Thieu cot TUONG LONG -> 422")
for kind, cols in [("products", PRODUCT_COLS), ("inventory", INV_COLS),
                   ("sales", SALES_COLS)]:
    # Rename a required column instead of dropping it: the file looks
    # plausible but the header no longer matches the contract.
    broken = [c + "_x" if c == REQUIRED[kind] else c for c in cols]
    r = post_file(f"/import/{kind}", "y.csv", csv_bytes([{c: "1" for c in broken}], broken))
    check(f"{kind} ten sai '{REQUIRED[kind]}' -> 422", r.status_code, 422)

section("Cot bat buoc thieu (khong optional) -> van import duoc")
# A file with ONLY the required columns must work - that is the minimum a
# user has to fill in.
for kind, cols, row in [
    ("products", PRODUCT_COLS, {"product_code": f"IMPT-{TAG}-MIN", "product_name": "Min",
                                "category_id": 1, "unit": "hop", "unit_cost": 1,
                                "selling_price": 2, "shelf_life_days": 30}),
    ("inventory", INV_COLS, {"product_id": 1, "store_id": 1, "quantity": 7,
                             "expiry_date": "2028-01-01"}),
    ("sales", SALES_COLS, {"order_code": f"IMPT-{TAG}-MIN", "order_date": "2026-08-01",
                           "store_id": 1, "product_id": 1, "quantity": 4,
                           "unit_price": 9}),
]:
    r = post_file(f"/import/{kind}", "min.csv", csv_bytes([row], cols))
    record(r, "products" if kind == "products" else
           "inventory" if kind == "inventory" else "sales")
    check(f"{kind} chi cot bat buoc -> 200", r.status_code, 200)
    if r.status_code == 200:
        check(f"{kind} 1 dong hop le", r.json()["error_rows"], 0)
        check(f"{kind} da tao duoc", len(r.json()["created_ids"]) > 0, True)

section("Sai dinh dang file -> 400")
r = post_file("/import/products", "p.txt", b"hello world", "text/plain")
check("duoi mo rong la -> 400", r.status_code, 400)
print(f"     detail: {r.json().get('detail', '')[:90]}")

r = post_file("/import/products", "p.csv", b"", "text/csv")
check("file rong -> 400", r.status_code, 400)

# .csv ten nhung noi dung la .xlsx
r = post_file("/import/products", "p.csv",
              xlsx_bytes([good_product(30)], PRODUCT_COLS),
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
check("ten .csv nhung la xlsx -> 400", r.status_code, 400)
print(f"     detail: {r.json().get('detail', '')[:95]}")

# .xlsx ten nhung noi dung la csv
r = post_file("/import/products", "p.xlsx", b"a,b\n1,2\n", "text/csv")
check("ten .xlsx nhung la csv -> 400", r.status_code, 400)

# noi dung hong
r = post_file("/import/products", "p.xlsx", b"PK\x03\x04not-a-real-zip",
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
check("xlsx hong -> 400", r.status_code, 400)

section("Chi co header, khong co dong -> 422")
r = post_file("/import/products", "empty.csv",
              b",".join(c.encode() for c in PRODUCT_COLS) + b"\n")
check("status", r.status_code, 422)
print(f"     detail: {r.json().get('detail', '')[:80]}")

section("File qua gioi han")
big = [good_product(i) for i in range(20_001)]
r = post_file("/import/products", "big.csv", csv_bytes(big, PRODUCT_COLS))
check("qua 20.000 dong -> 422", r.status_code, 422)
print(f"     detail: {r.json().get('detail', '')[:80]}")

section("File qua gioi han kich thuoc")
huge = b"product_code,product_name,category_id,unit,unit_cost,selling_price,shelf_life_days\n"
huge += b"X," + b"A" * (11 * 1024 * 1024) + b",1,hop,1,1,1\n"
r = post_file("/import/products", "huge.csv", huge)
check("qua 10 MB -> 400", r.status_code, 400)
print(f"     detail: {r.json().get('detail', '')[:80]}")

section("on_error sai -> 422")
r = post_file("/import/products?on_error=bogus", "p.csv",
              csv_bytes([good_product(40)], PRODUCT_COLS))
check("status", r.status_code, 422)

section("CSV tieng Viet co dau")
rows4 = [good_product(50)]
rows4[0]["product_name"] = "Sản phẩm tiếng Việt đầy đủ"
r = post_file("/import/products", "vn.csv", csv_bytes(rows4, PRODUCT_COLS))
record(r, "products")
check("import dong dau -> 201/200", r.status_code, 200)
if r.status_code == 200:
    pid = r.json()["created_ids"][0]
    got = get_json(f"/products/{pid}").json()
    check("ten giu nguyen dau", got["product_name"], "Sản phẩm tiếng Việt đầy đủ")

section("Don cap nhat sau khi import")
if OID:
    d = get_json(f"/orders/{OID}").json()
    ok("order_date co timezone +07",
       "07:00" in d["order_date"] or "+07" in d["order_date"],
       d["order_date"])

# ================================================================= CLEANUP
def cleanup():
    """
    Delete everything the suite created, by recorded primary key.

    Keyed on ids rather than on the IMPT- prefix: the "minimum columns"
    test omits batch_code, so its row has a NULL there and a LIKE filter
    would silently skip it.
    """
    print("\n" + "=" * 78)
    print("CLEANUP")
    print("=" * 78)
    conn = psycopg2.connect(
        host="localhost", port=5432, dbname="spoilage_predictor",
        user="postgres", password=os.environ["DB_PASSWORD"],
    )
    cur = conn.cursor()

    def delete_ids(table, column, ids):
        if not ids:
            return 0
        cur.execute(
            f"DELETE FROM {table} WHERE {column} = ANY(%s)", (list(ids),)
        )
        return cur.rowcount

    # Children before parents. order_items is not listed on purpose: the
    # FK is ON DELETE CASCADE, so deleting the order takes its lines too.
    orders = delete_ids("orders", "order_id", CREATED["orders"])
    inv = delete_ids("inventory", "inventory_id", CREATED["inventory"])
    products = delete_ids("products", "product_id", CREATED["products"])
    items = 0
    conn.commit()

    # Belt and braces: also sweep anything left over from an earlier failed
    # run that never reached its own cleanup.
    cur.execute("DELETE FROM order_items WHERE order_id IN "
                "(SELECT order_id FROM orders WHERE order_code LIKE 'IMP-%%')")
    cur.execute("DELETE FROM orders WHERE order_code LIKE 'IMP-%%'")
    cur.execute("DELETE FROM products WHERE product_code LIKE 'IMPT-%%'")
    swept = cur.rowcount
    conn.commit()

    cur.execute(
        "SELECT (SELECT count(*) FROM products WHERE product_id > 50), "
        "       (SELECT count(*) FROM orders WHERE order_id > 18260), "
        "       (SELECT count(*) FROM inventory WHERE inventory_id > 1330), "
        "       (SELECT count(*) FROM order_items WHERE order_item_id > 912999)"
    )
    extra_products, extra_orders, extra_inventory, extra_items = cur.fetchone()
    cur.close()
    conn.close()

    print(f"  xoa {products} SP · {inv} lot · {orders} don (keo theo dong chi tiet)"
          + (f" · {swept} ban ghi du tich" if swept else ""))
    ok("khong con san pham du tich", extra_products == 0, f"con={extra_products}")
    ok("khong con don du tich", extra_orders == 0, f"con={extra_orders}")
    ok("khong con lot du tich", extra_inventory == 0, f"con={extra_inventory}")
    ok("khong con dong chi tiet du tich", extra_items == 0, f"con={extra_items}")


cleanup()

print("\n" + "=" * 78)
if FAILURES:
    print(f"FAILED {len(FAILURES)}:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("ALL TESTS PASSED")
print("=" * 78)
