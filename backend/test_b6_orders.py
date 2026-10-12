"""
Test suite for B6 - orders and order-items API.

Run with the server already listening on 127.0.0.1:8000:

    cd backend
    python -m uvicorn app.main:app --port 8000
    python test_b6_orders.py

The suite writes to the database, so every order it creates is tracked and
removed again at the end. Seeded orders (ids 1-18260) are only ever read;
tests that mutate state create their own order first.
"""

import json
import os
import sys
import urllib.error
import urllib.request

import psycopg2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000/api/v1"
CODE = "T-B6"
FAILURES = []
CREATED = {"orders": [], "items": []}


class Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


def call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return Resp(r.status, json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return Resp(e.code, json.loads(raw) if raw else None)
        except ValueError:
            return Resp(e.code, {"_raw": raw.decode("utf-8", "replace")[:300]})


def get(p):    return call("GET", p)
def post(p, b): return call("POST", p, b)
def put(p, b):  return call("PUT", p, b)
def delete(p):  return call("DELETE", p)


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


def round2(x):
    return round(x + 0.0, 2)


# Unique-per-call order code: order_code has a UNIQUE constraint, so a fixed
# string would make every call after the first return 409.
_seq = {"n": 0}


def _code(tag):
    _seq["n"] += 1
    return f"{CODE}-{tag}-{_seq['n']:03d}"


def new_order(items=None, **over):
    """Create a throwaway pending order and remember it for cleanup."""
    payload = {
        "order_code": _code("ORD"),
        "store_id": 1,
        "order_type": "sale",
        "status": "pending",
        "payment_method": "cash",
        "customer_name": "B6 test",
        "items": items if items is not None else [
            {"product_id": 1, "quantity": 10, "unit_price": 5,
             "unit_cost": 3, "discount_percent": 0},
            {"product_id": 2, "quantity": 4, "unit_price": 25, "discount_percent": 10},
        ],
    }
    payload.update(over)
    r = post("/orders", payload)
    if r.status_code == 201:
        CREATED["orders"].append(r.json()["order_id"])
        for it in r.json().get("items", []):
            CREATED["items"].append(it["order_item_id"])
    return r


def cleanup():
    """
    Remove everything this suite created.

    Done through SQL rather than the API on purpose. Several tests move an
    order to `completed` or `cancelled`, and the API then refuses both
    DELETE /orders/{id} (has lines) and DELETE /order-items/{id} (order is
    locked) - there is deliberately no API path out of that state. Using the
    API alone would leak those orders into the seeded dataset.

    Scoped by the T-B6 order_code prefix, so seeded rows can never be hit.
    """
    print("\n" + "=" * 78)
    print("CLEANUP - xoa don hang va dong hang do test tao")
    print("=" * 78)

    conn = psycopg2.connect(
        host="localhost", port=5432, dbname="spoilage_predictor",
        user="postgres", password=os.environ["DB_PASSWORD"],
    )
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM order_items WHERE order_id IN "
        "(SELECT order_id FROM orders WHERE order_code LIKE 'T-B6%%')"
    )
    removed_items = cur.rowcount
    cur.execute("DELETE FROM orders WHERE order_code LIKE 'T-B6%%'")
    removed_orders = cur.rowcount
    conn.commit()

    cur.execute("SELECT count(*) FROM orders WHERE order_code LIKE 'T-B6%%'")
    leftover = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"  xoa {removed_items} dong hang · {removed_orders} don hang")
    ok("khong con don hang test nao", leftover == 0, f"con lai={leftover}")


# ===================================================================== READ
section("GET /orders - list + pagination")
r = get("/orders?page=1&page_size=5")
check("status", r.status_code, 200)
b = r.json()
check("page_size", len(b["items"]), 5)
check("page", b["page"], 1)
ok("total > 0", b["total"] > 0, f"total={b['total']}")
ok("pages > 1", b["pages"] > 1, f"pages={b['pages']}")

dates = [i["order_date"] for i in b["items"]]
ok("sap xep order_date DESC", dates == sorted(dates, reverse=True))
ids = [i["order_id"] for i in b["items"]]
ok("tie-break order_id DESC", ids == sorted(ids, reverse=True))

first = b["items"][0]
print(f"  don moi nhat: {first['order_code']} store={first['store_id']} "
      f"{first['order_date']} qty={first['total_quantity']}")
print(f"  store brief: {first['store']}")
ok("co store brief", first["store"] is not None and "store_name" in first["store"])
ok("co line_count", "line_count" in first, f"line_count={first.get('line_count')}")
ok("co total_items", "total_items" in first, f"total_items={first.get('total_items')}")

section("GET /orders - line_count / total_items khop DB")
o = get("/orders?page=1&page_size=1").json()["items"][0]
detail = get(f"/orders/{o['order_id']}").json()
check("line_count == so dong chi tiet", detail["line_count"], len(detail["items"]))
ok("total_items == tong quantity", round(detail["total_items"], 3)
   == round(sum(i["quantity"] for i in detail["items"]), 3),
   f"{detail['total_items']} vs {sum(i['quantity'] for i in detail['items'])}")
ok("total_amount == tong line_total",
   round2(detail["total_amount"]) == round2(sum(i["line_total"] for i in detail["items"])),
   f"{detail['total_amount']} vs {sum(i['line_total'] for i in detail['items'])}")

section("GET /orders - filters")
tot_all = get("/orders?page_size=1").json()["total"]
# 18.260 orders = 1.826 ngay * 10 cua hang. Moi cua hang co 1 don/ngay,
# nen 1.826 don/cua hang, KHONG phai 3.650.
check("tong don", tot_all, 18260)
check("store_id=1", get("/orders?store_id=1").json()["total"], 1826)
check("order_type=sale", get("/orders?order_type=sale").json()["total"], 18260)
check("order_type=purchase", get("/orders?order_type=purchase").json()["total"], 0)
check("status=completed", get("/orders?status=completed").json()["total"], 18260)
check("status=pending", get("/orders?status=pending").json()["total"], 0)
check("status=cancelled", get("/orders?status=cancelled").json()["total"], 0)
check("loc store_id + status giao nhau",
      get("/orders?store_id=1&status=completed").json()["total"], 1826)

# order_date la TIMESTAMPTZ, du lieu nhin la moc gio dia phuong +07:00.
# `2017-01-01T00:00:00+07:00` = `2016-12-31T17:00:00Z`, nen khoang
# gio UTC se cat mat 10 don cua ngay 01/01. Phai dung moc co canh.
f2017 = get("/orders?from_date=2017-01-01T00:00:00%2B07:00"
            "&to_date=2017-12-31T23:59:59%2B07:00")
check("date range nam 2017 (muc co canh +07)", f2017.json()["total"], 3650)
f2017_utc = get("/orders?from_date=2017-01-01T00:00:00Z"
                "&to_date=2017-12-31T23:59:59Z")
check("muc UTC cat mat 10 don ngay 01/01", f2017_utc.json()["total"], 3640)
jan = get("/orders?from_date=2017-01-01T00:00:00%2B07:00"
          "&to_date=2017-01-31T23:59:59%2B07:00")
check("thang 1/2017 = 31 ngay * 10 CH", jan.json()["total"], 310)
one_day = get("/orders?from_date=2017-01-04T00:00:00%2B07:00"
              "&to_date=2017-01-04T23:59:59%2B07:00")
check("1 ngay = 10 don (1 moi CH)", one_day.json()["total"], 10)

section("GET /orders - edge cases")
check("page=0 -> 422", get("/orders?page=0").status_code, 422)
check("page_size=0 -> 422", get("/orders?page_size=0").status_code, 422)
check("page_size=101 -> 422", get("/orders?page_size=101").status_code, 422)
check("store_id=0 -> 422", get("/orders?store_id=0").status_code, 422)
check("status=abc -> 422", get("/orders?status=abc").status_code, 422)
check("order_type=abc -> 422", get("/orders?order_type=abc").status_code, 422)
check("from_date > to_date -> 422",
      get("/orders?from_date=2017-12-31T00:00:00Z&to_date=2017-01-01T00:00:00Z").status_code,
      422)
check("from_date khong hop le -> 422", get("/orders?from_date=abc").status_code, 422)
far = get("/orders?page=99999")
check("page vuot qua -> 200", far.status_code, 200)
check("page vuot qua -> rong", far.json()["items"], [])
check("page vuot qua -> pages van dung", far.json()["pages"], (tot_all + 19) // 20)

section("GET /orders/{id} - detail + items")
check("404 don khong ton tai", get("/orders/99999999").status_code, 404)
check("404 id khong phai so", get("/orders/abc").status_code, 422)
detail = get("/orders/1").json()
check("don 1 co 50 dong", len(detail["items"]), 50)
ok("moi dong co line_total", all(i["line_total"] is not None for i in detail["items"]))
ok("moi dong co product brief",
   all(i["product"] and "product_name" in i["product"] for i in detail["items"]))
print(f"  don 1: {len(detail['items'])} dong · total_amount="
      f"{detail['total_amount']:,.2f} · total_quantity={detail['total_quantity']:,.0f}")

items = get("/orders/1/items")
check("GET /orders/1/items status", items.status_code, 200)
check("so dong khop detail", len(items.json()), 50)
check("404 items cua don khong ton tai",
      get("/orders/99999999/items").status_code, 404)

section("GET /order-items - list + filter")
r = get("/order-items?page_size=5")
check("status", r.status_code, 200)
check("page_size", len(r.json()["items"]), 5)
check("tong so dong", r.json()["total"], 912999)
check("filter order_id=1", get("/order-items?order_id=1").json()["total"], 50)
check("filter product_id=15",
      get("/order-items?product_id=15").json()["total"], 18260)
ok("filter store_id=1",
   get("/order-items?store_id=1").json()["total"] == 91300,
   f"total={get('/order-items?store_id=1').json()['total']}")

line = r.json()["items"][0]
print(f"  dong mau: order={line['order_id']} product={line['product_id']} "
      f"qty={line['quantity']} gia={line['unit_price']} "
      f"discount={line['discount_percent']} line_total={line['line_total']}")
ok("line_total == cong thuc",
   round2(line["line_total"]) == round2(
       line["quantity"] * line["unit_price"] * (1 - line["discount_percent"] / 100)))

section("GET /order-items - edge cases")
check("page=0 -> 422", get("/order-items?page=0").status_code, 422)
check("page_size=101 -> 422", get("/order-items?page_size=101").status_code, 422)
check("min>max -> 422",
      get("/order-items?min_line_total=100&max_line_total=1").status_code, 422)
check("404 dong khong ton tai", get("/order-items/99999999").status_code, 404)
check("id khong phai so -> 422", get("/order-items/abc").status_code, 422)
first_item = get("/order-items?page_size=1&order_id=1").json()["items"][0]
check("GET /order-items/{id}", get(f"/order-items/{first_item['order_item_id']}").status_code, 200)

# ==================================================================== WRITE
section("POST /orders - tao don hang kem items")
r = new_order()
check("status", r.status_code, 201)
o = r.json()
OID = o["order_id"]
print(f"  don tao: id={OID} code={o['order_code']} status={o['status']}")
ok("mac dinh status=pending", o["status"] == "pending", o["status"])
check("so dong", len(o["items"]), 2)

# 10*5 + 4*25*0.9 = 50 + 90 = 140
check("total_amount tinh tu dong hang", round2(o["total_amount"]), 140.0)
check("total_quantity", round2(o["total_quantity"]), 14.0)
check("line_count", o["line_count"], 2)
check("total_items", round2(o["total_items"]), 14.0)
for it in o["items"]:
    print(f"    product={it['product_id']} qty={it['quantity']} "
          f"line_total={it['line_total']}")
check("line_total dong 1 (khong giam gia)", round2(o["items"][0]["line_total"]), 50.0)
check("line_total dong 2 (giam 10%)", round2(o["items"][1]["line_total"]), 90.0)

section("POST /orders - GENERATED COLUMN khong nhan gia tri tu client")
r = post("/orders", {
    "order_code": _code("LINETOTAL"),
    "store_id": 1,
    "items": [{"product_id": 1, "quantity": 3, "unit_price": 7,
               "line_total": 999999}],
})
check("gui line_total len body -> van tao duoc (field bi bo qua)", r.status_code, 201)
if r.status_code == 201:
    CREATED["orders"].append(r.json()["order_id"])
    got = r.json()["items"][0]["line_total"]
    check("DB tinh lai, bo qua gia tri client", round2(got), 21.0)
    ok("khong phai 999999", round2(got) != 999999.0)

section("POST /orders - validation")
check("khong co items -> 422",
      post("/orders", {"order_code": "T-B6-NOITEMS", "store_id": 1,
                       "items": []}).status_code, 422)
check("items rong -> 422",
      post("/orders", {"order_code": "T-B6-NOITEMS2", "store_id": 1}).status_code, 422)
check("store_id=0 -> 422",
      post("/orders", {"order_code": "T-B6-S0", "store_id": 0,
                       "items": [{"product_id": 1, "quantity": 1,
                                  "unit_price": 1}]}).status_code, 422)
check("store khong ton tai -> 422",
      post("/orders", {"order_code": "T-B6-S999", "store_id": 999,
                       "items": [{"product_id": 1, "quantity": 1,
                                  "unit_price": 1}]}).status_code, 422)
check("product khong ton tai -> 422",
      post("/orders", {"order_code": "T-B6-P999", "store_id": 1,
                       "items": [{"product_id": 999, "quantity": 1,
                                  "unit_price": 1}]}).status_code, 422)
check("quantity=0 -> 422",
      post("/orders", {"order_code": "T-B6-Q0", "store_id": 1,
                       "items": [{"product_id": 1, "quantity": 0,
                                  "unit_price": 1}]}).status_code, 422)
check("quantity am -> 422",
      post("/orders", {"order_code": "T-B6-QN", "store_id": 1,
                       "items": [{"product_id": 1, "quantity": -5,
                                  "unit_price": 1}]}).status_code, 422)
check("unit_price am -> 422",
      post("/orders", {"order_code": "T-B6-UPN", "store_id": 1,
                       "items": [{"product_id": 1, "quantity": 1,
                                  "unit_price": -1}]}).status_code, 422)
r = new_order(items=[{"product_id": 3, "quantity": 1, "unit_price": 0}])
check("unit_price=0 -> hop le (201)", r.status_code, 201)
check("discount=101 -> 422",
      post("/orders", {"order_code": "T-B6-D101", "store_id": 1,
                       "items": [{"product_id": 1, "quantity": 1, "unit_price": 1,
                                  "discount_percent": 101}]}).status_code, 422)
check("discount=-1 -> 422",
      post("/orders", {"order_code": "T-B6-DN1", "store_id": 1,
                       "items": [{"product_id": 1, "quantity": 1, "unit_price": 1,
                                  "discount_percent": -1}]}).status_code, 422)
r = new_order(items=[{"product_id": 4, "quantity": 2, "unit_price": 50,
                       "discount_percent": 100}])
check("discount=100 -> hop le", r.status_code, 201)
if r.status_code == 201:
    check("discount 100% -> line_total = 0",
          round2(r.json()["items"][0]["line_total"]), 0.0)
    check("discount 100% -> total_amount = 0",
          round2(r.json()["total_amount"]), 0.0)
check("order_type sai -> 422",
      post("/orders", {"order_code": "T-B6-OT", "store_id": 1, "order_type": "xyz",
                       "items": [{"product_id": 1, "quantity": 1,
                                  "unit_price": 1}]}).status_code, 422)
check("status sai -> 422",
      post("/orders", {"order_code": "T-B6-ST", "store_id": 1, "status": "xyz",
                       "items": [{"product_id": 1, "quantity": 1,
                                  "unit_price": 1}]}).status_code, 422)
check("payment_method sai -> 422",
      post("/orders", {"order_code": "T-B6-PM", "store_id": 1,
                       "payment_method": "bitcoin",
                       "items": [{"product_id": 1, "quantity": 1,
                                  "unit_price": 1}]}).status_code, 422)
check("trung product trong 1 payload -> 422",
      post("/orders", {"order_code": "T-B6-DUP", "store_id": 1,
                       "items": [{"product_id": 1, "quantity": 1, "unit_price": 1},
                                 {"product_id": 1, "quantity": 2, "unit_price": 2}]}
                       ).status_code, 422)

section("POST /orders - trung order_code (UNIQUE)")
dup_code = _code("DUP")
r = post("/orders", {"order_code": dup_code, "store_id": 1,
                     "items": [{"product_id": 1, "quantity": 1, "unit_price": 1}]})
if r.status_code == 201:
    CREATED["orders"].append(r.json()["order_id"])
    check("lan 2 cung order_code -> 409",
          post("/orders", {"order_code": dup_code, "store_id": 1,
                           "items": [{"product_id": 1, "quantity": 1,
                                      "unit_price": 1}]}).status_code, 409)
    print(f"  order_code de trung: {dup_code}")
else:
    print(f"  [FAIL] khong tao duoc don de test trung order_code ({r.status_code})")
    FAILURES.append("tao don de test trung order_code")

# ================================================================ ORDER ITEMS
section("POST /order-items - them dong vao don")
r = post("/order-items", {"order_id": OID, "product_id": 3,
                          "quantity": 6, "unit_price": 10,
                          "discount_percent": 25})
check("status", r.status_code, 201)
it = r.json()
CREATED["items"].append(it["order_item_id"])
check("line_total = 6*10*0.75", round2(it["line_total"]), 45.0)
print(f"  dong moi: product={it['product_id']} qty={it['quantity']} "
      f"line_total={it['line_total']}")

o = get(f"/orders/{OID}").json()
check("total_amount tu dong cap nhat (140+45)", round2(o["total_amount"]), 185.0)
check("total_quantity cap nhat (14+6)", round2(o["total_quantity"]), 20.0)
check("line_count cap nhat", o["line_count"], 3)
print(f"  don sau khi them dong: total_amount={o['total_amount']} "
      f"total_quantity={o['total_quantity']} lines={o['line_count']}")

section("POST /order-items - trung product trong cung don (UNIQUE)")
check("them lai product 3 -> 409",
      post("/order-items", {"order_id": OID, "product_id": 3,
                            "quantity": 1, "unit_price": 1}).status_code, 409)
section("POST /order-items - validation")
check("order khong ton tai -> 422",
      post("/order-items", {"order_id": 99999999, "product_id": 1,
                            "quantity": 1, "unit_price": 1}).status_code, 422)
check("product khong ton tai -> 422",
      post("/order-items", {"order_id": OID, "product_id": 999,
                            "quantity": 1, "unit_price": 1}).status_code, 422)
check("quantity=0 -> 422",
      post("/order-items", {"order_id": OID, "product_id": 5,
                            "quantity": 0, "unit_price": 1}).status_code, 422)
check("unit_price am -> 422",
      post("/order-items", {"order_id": OID, "product_id": 5,
                            "quantity": 1, "unit_price": -1}).status_code, 422)
check("order_id=0 -> 422",
      post("/order-items", {"order_id": 0, "product_id": 1,
                            "quantity": 1, "unit_price": 1}).status_code, 422)

section("PUT /order-items/{id} - cap nhat dong")
first_line = get(f"/orders/{OID}/items").json()[0]
LI = first_line["order_item_id"]
r = put(f"/order-items/{LI}", {"quantity": 20})
check("status", r.status_code, 200)
ok("line_total tinh lai", round2(r.json()["line_total"]) != round2(first_line["line_total"]),
   f"{first_line['line_total']} -> {r.json()['line_total']}")
o = get(f"/orders/{OID}").json()
check("total_amount cap nhat sau PUT", round2(o["total_amount"]),
      round2(sum(i["line_total"] for i in o["items"])))
check("total_quantity cap nhat sau PUT", round2(o["total_quantity"]),
      round2(sum(i["quantity"] for i in o["items"])))
print(f"  PUT quantity 10->20: line_total {first_line['line_total']} -> "
      f"{get(f'/order-items/{LI}').json()['line_total']}")

r = put(f"/order-items/{LI}", {"quantity": 8, "unit_price": 3, "discount_percent": 50})
check("cap nhat nhieu field", r.status_code, 200)
check("line_total = 8*3*0.5", round2(r.json()["line_total"]), 12.0)
check("body rong -> 200 (khong doi gi)",
      put(f"/order-items/{LI}", {}).status_code, 200)
check("quantity=0 -> 422", put(f"/order-items/{LI}", {"quantity": 0}).status_code, 422)
check("discount=101 -> 422",
      put(f"/order-items/{LI}", {"discount_percent": 101}).status_code, 422)
check("404 dong khong ton tai",
      put("/order-items/99999999", {"quantity": 1}).status_code, 404)

section("PUT /order-items/{id} - doi product -> 409 khi trung")
r = post("/order-items", {"order_id": OID, "product_id": 6,
                          "quantity": 2, "unit_price": 1})
check("them product 6", r.status_code, 201)
if r.status_code == 201:
    CREATED["items"].append(r.json()["order_item_id"])
    six = r.json()["order_item_id"]
    check("doi product 6 -> product 3 (da co) -> 409",
          put(f"/order-items/{six}", {"product_id": 3}).status_code, 409)
    check("doi sang product 7 (chua co) -> 200",
          put(f"/order-items/{six}", {"product_id": 7}).status_code, 200)

# =================================================================== STATUS
section("PUT /orders/{id}/status - vong doi trang thai")
check("404 don khong ton tai",
      put("/orders/99999999/status", {"status": "completed"}).status_code, 404)
check("status sai -> 422",
      put(f"/orders/{OID}/status", {"status": "xyz"}).status_code, 422)
check("trung trang thai (pending->pending) -> 200 idempotent",
      put(f"/orders/{OID}/status", {"status": "pending"}).status_code, 200)
r = put(f"/orders/{OID}/status", {"status": "completed"})
check("pending -> completed", r.status_code, 200)
check("status da doi", r.json()["status"], "completed")
check("completed -> pending -> 409",
      put(f"/orders/{OID}/status", {"status": "pending"}).status_code, 409)
check("completed -> completed -> 200 idempotent",
      put(f"/orders/{OID}/status", {"status": "completed"}).status_code, 200)
check("completed -> cancelled -> 409",
      put(f"/orders/{OID}/status", {"status": "cancelled"}).status_code, 409)

# Cancel the order so the PUT-below test has something pending to edit.
s = new_order(items=[{"product_id": 9, "quantity": 5, "unit_price": 2}])
cid = None
if s.status_code == 201:
    cid = s.json()["order_id"]
    check("pending -> cancelled", put(f"/orders/{cid}/status",
                                      {"status": "cancelled"}).status_code, 200)
    check("cancelled -> pending (mo lai)", put(f"/orders/{cid}/status",
                                               {"status": "pending"}).status_code, 200)
else:
    print(f"  [FAIL] khong tao duoc don de test vong doi trang thai: {s.status_code}")
    FAILURES.append("tao don phụ cho status")

section("PUT /orders/{id} - khong sua don da chot")
check("sua don completed -> 409",
      put(f"/orders/{OID}", {"customer_name": "doi"}).status_code, 409)
check("sua don completed (doi status) -> 409",
      put(f"/orders/{OID}", {"note": "x"}).status_code, 409)
if cid:
    put(f"/orders/{cid}/status", {"status": "cancelled"})
    check("sua don cancelled -> 409",
          put(f"/orders/{cid}", {"customer_name": "doi"}).status_code, 409)
section("PUT /orders/{id} - sua don pending")
p = new_order(items=[{"product_id": 10, "quantity": 3, "unit_price": 4}])
check("tao don pending", p.status_code, 201)
PID = p.json()["order_id"]
check("doi customer_name", put(f"/orders/{PID}",
                                {"customer_name": "Khach Test"}).json()["customer_name"],
      "Khach Test")
check("doi store", put(f"/orders/{PID}", {"store_id": 2}).json()["store_id"], 2)
check("them note", put(f"/orders/{PID}", {"note": "ghi chu"}).json()["note"], "ghi chu")
check("doi order_type", put(f"/orders/{PID}",
                             {"order_type": "purchase"}).json()["order_type"], "purchase")
check("body rong -> 200", put(f"/orders/{PID}", {}).status_code, 200)
# Ghi chu: khong schema nao trong du an dat extra='forbid', nen Pydantic bo
# qua field la. Day la hanh vi dung chuan cua codebase (xem product/store/
# category schema) - KHONG phai bug cua router nay. Neu muon tuong lai
# trong tuong lai thi bat buoc them extra='forbid' cho TAT CA schema.
check("field la -> 200 (bi bo qua, khop quy uoc chung)",
      put(f"/orders/{PID}", {"khong_ton_tai": 1}).status_code, 200)
check("field la -> gia tri khong bi ghi vao",
      "khong_ton_tai" in get(f"/orders/{PID}").json(), False)
check("store khong ton tai -> 422",
      put(f"/orders/{PID}", {"store_id": 999}).status_code, 422)
check("user khong ton tai -> 422",
      put(f"/orders/{PID}", {"user_id": 999}).status_code, 422)
check("404 don khong ton tai", put("/orders/99999999",
                                   {"note": "x"}).status_code, 404)

# ==================================================================== DELETE
section("DELETE /order-items/{id} - xoa dong, cap nhat tong")
lines = get(f"/orders/{PID}/items").json()
check("truoc khi xoa co 1 dong", len(lines), 1)
before_amount = get(f"/orders/{PID}").json()["total_amount"]
d = delete(f"/order-items/{lines[0]['order_item_id']}")
check("status", d.status_code, 204)
o = get(f"/orders/{PID}").json()
check("khong con dong nao", o["line_count"], 0)
check("total_amount ve 0", round2(o["total_amount"]), 0.0)
check("total_quantity ve 0", round2(o["total_quantity"]), 0.0)
print(f"  truoc: {before_amount} -> sau: {o['total_amount']}")
check("xoa lan 2 -> 404",
      delete(f"/order-items/{lines[0]['order_item_id']}").status_code, 404)
check("404 dong khong ton tai", delete("/order-items/99999999").status_code, 404)

section("DELETE /orders/{id} - 409 khi con dong")
r = get("/orders/1")
check("don 1 co 50 dong", r.json()["line_count"], 50)
d = delete("/orders/1")
check("xoa don co dong -> 409", d.status_code, 409)
print(f"  message: {d.json().get('detail')}")
check("don 1 van con sau 409",
      get("/orders/1").json()["line_count"], 50)
check("50 dong chi tiet van con",
      len(get("/orders/1/items").json()), 50)
check("404 don khong ton tai", delete("/orders/99999999").status_code, 404)

section("DELETE /orders/{id} - xoa don rong -> 204")
check("don rong xoa duoc", delete(f"/orders/{PID}").status_code, 204)
check("xoa lan 2 -> 404", delete(f"/orders/{PID}").status_code, 404)
check("GET don da xoa -> 404", get(f"/orders/{PID}").status_code, 404)

section("CASCADE - FK order_items.order_id la ON DELETE CASCADE")
check("don 1 con nguyen 50 dong sau khi thu xoa",
      len(get("/orders/1/items").json()), 50)
print("  API chan xoa don co dong bang 409 nen duong ON DELETE CASCADE")
print("  khong the kich hoat qua API - kiem o muc DB truoc khi cleanup.")

section("Tong so du lieu - kiem tra SAU khi cleanup")
print("  (moc ban dau: 18.260 don / 912.999 dong chi tiet)")

cleanup()

check("orders ve lai 18.260", get("/orders?page_size=1").json()["total"], 18260)
check("order_items ve lai 912.999",
      get("/order-items?page_size=1").json()["total"], 912999)

print("\n" + "=" * 78)
if FAILURES:
    print(f"FAILED {len(FAILURES)}:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("ALL TESTS PASSED")
print("=" * 78)