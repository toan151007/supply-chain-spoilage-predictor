"""Write-path smoke test: exercises the stored-procedure mutations."""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api/v1"
results = []


def call(method, path, token=None, body=None, raw=None, content_type=None):
    url = BASE + path
    headers = {}
    data = None
    if raw is not None:
        data = raw
        headers["Content-Type"] = content_type or "application/octet-stream"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = resp.read()
            try:
                return resp.status, json.loads(payload)
            except Exception:
                return resp.status, payload[:80]
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            return exc.code, json.loads(payload)
        except Exception:
            return exc.code, payload[:200]
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc)


def check(label, method, path, expected=200, token=None, body=None, raw=None,
          content_type=None):
    status, payload = call(method, path, token=token, body=body, raw=raw,
                           content_type=content_type)
    ok = status == expected
    results.append((ok, label, status, payload))
    print(f"{'PASS' if ok else 'FAIL'} {label}: {status}")
    if not ok:
        print(f"     {payload}")
    return payload


def login(username, password):
    return check(
        f"login {username}", "POST", "/auth/login", expected=200,
        body={"username": username, "password": password},
    )


def multipart(field, filename, content: bytes):
    boundary = "----smoke-boundary-42"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        "Content-Type: text/csv\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def main() -> None:
    global results
    check("health/db", "GET", "/health/database")

    owner = login("owner", "Owner@2026")["access_token"]
    staff = login("staff", "Staff@2026")["access_token"]

    # ---- products ----
    product = check(
        "create product", "POST", "/products", expected=201, token=owner,
        body={
            "product_code": "SMOKE-001",
            "product_name": "San pham kiem thu",
            "category_id": 3,
            "unit": "chai",
            "unit_cost": 5000,
            "selling_price": 9000,
            "shelf_life_days": 60,
            "min_stock": 5,
            "max_stock": 100,
            "is_perishable": True,
            "reorder_point": 10,
            "supplier": "Smoke Test",
        },
    )
    product_id = product.get("product_id")

    check(
        "duplicate product code", "POST", "/products", expected=409, token=owner,
        body={
            "product_code": "SMOKE-001",
            "product_name": "Trung ma",
            "category_id": 3,
            "unit": "chai",
            "unit_cost": 5000,
            "selling_price": 9000,
            "shelf_life_days": 60,
        },
    )
    check(
        "staff cannot create product", "POST", "/products", expected=403,
        token=staff,
        body={
            "product_code": "SMOKE-002",
            "product_name": "Khong duoc phep",
            "category_id": 3,
            "unit": "chai",
            "unit_cost": 1,
            "selling_price": 2,
            "shelf_life_days": 1,
        },
    )
    check(
        "update product", "PUT", f"/products/{product_id}", token=owner,
        body={"selling_price": 9500},
    )

    # ---- inventory ----
    batch = check(
        "create inventory", "POST", "/inventory", expected=201, token=staff,
        body={
            "store_id": 1,
            "product_id": product_id,
            "expiry_date": "2027-06-30",
            "quantity": 25,
            "received_date": "2026-10-20",
            "batch_code": "SMOKE-BATCH-1",
        },
    )
    inventory_id = batch.get("inventory_id")
    check(
        "duplicate inventory lot", "POST", "/inventory", expected=409, token=staff,
        body={
            "store_id": 1,
            "product_id": product_id,
            "expiry_date": "2027-06-30",
            "quantity": 10,
        },
    )
    check(
        "update inventory", "PUT", f"/inventory/{inventory_id}", token=staff,
        body={"quantity": 30},
    )

    # ---- orders ----
    order = check(
        "create order", "POST", "/orders", expected=201, token=staff,
        body={
            "order_code": "SMOKE-ORDER-1",
            "store_id": 1,
            "order_type": "sale",
            "order_date": "2026-10-24T08:00:00",
            "status": "pending",
            "payment_method": "cash",
            "customer_name": "Khach test",
            "items": [
                {"product_id": 8, "quantity": 2, "unit_price": 145000,
                 "discount_percent": 0},
                {"product_id": 45, "quantity": 3, "unit_price": 55000,
                 "discount_percent": 10},
            ],
        },
    )
    order_id = order.get("order_id")
    expected_total = 2 * 145000 + 3 * 55000 * 0.9
    if abs(float(order.get("total_amount", 0)) - expected_total) > 0.01:
        results.append((False, "order totals", order.get("total_amount"),
                        expected_total))
        print(f"FAIL order totals: {order.get('total_amount')} != {expected_total}")
    else:
        results.append((True, "order totals", 200, None))
        print("PASS order totals")

    check(
        "duplicate order code", "POST", "/orders", expected=409, token=staff,
        body={
            "order_code": "SMOKE-ORDER-1",
            "store_id": 1,
            "order_date": "2026-10-24T09:00:00",
            "items": [{"product_id": 8, "quantity": 1, "unit_price": 1000}],
        },
    )
    check(
        "update order status", "PUT", f"/orders/{order_id}/status",
        token=staff, body={"status": "completed"},
    )
    check(
        "completed order is locked", "PUT", f"/orders/{order_id}", expected=409,
        token=staff, body={"note": "khong duoc sua"},
    )
    check(
        "completed cannot revert", "PUT", f"/orders/{order_id}/status",
        expected=409, token=staff, body={"status": "pending"},
    )
    check(
        "order detail", "GET", f"/orders/{order_id}", token=staff,
    )

    # ---- alerts ----
    alert = check("first alert", "GET", "/alerts?page=1&page_size=1")
    alert_id = alert["items"][0]["alert_id"]
    check(
        "alert read", "PUT", f"/alerts/{alert_id}/read", token=staff,
        body={"is_read": True},
    )
    check(
        "alert resolve", "PUT", f"/alerts/{alert_id}/resolve", token=staff,
        body={"is_resolved": True},
    )
    check(
        "alert reopen", "PUT", f"/alerts/{alert_id}/resolve", token=staff,
        body={"is_resolved": False},
    )

    # ---- pending order lifecycle (delete path) ----
    pending = check(
        "create pending order", "POST", "/orders", expected=201, token=staff,
        body={
            "order_code": "SMOKE-ORDER-2",
            "store_id": 2,
            "order_date": "2026-10-24T10:00:00",
            "items": [{"product_id": 8, "quantity": 1, "unit_price": 1000}],
        },
    )
    check(
        "delete pending order", "DELETE", f"/orders/{pending['order_id']}",
        expected=204, token=staff,
    )

    # ---- import ----
    csv = (
        "product_code,product_name,category_id,unit,unit_cost,selling_price,"
        "shelf_life_days,min_stock,max_stock,supplier\n"
        "SMOKE-IMP-01,San pham import 1,3,chai,1000,2000,30,1,10,Import Test\n"
        "SMOKE-IMP-02,San pham import 2,3,chai,1000,2000,30,1,10,Import Test\n"
    ).encode("utf-8")
    raw, ctype = multipart("file", "products.csv", csv)
    imported = check(
        "import products", "POST", "/import/products", token=owner,
        raw=raw, content_type=ctype,
    )
    if isinstance(imported, dict) and imported.get("success_rows") == 2:
        results.append((True, "import count", 200, None))
        print("PASS import count")
    else:
        results.append((False, "import count", imported, 2))
        print("FAIL import count")

    # cleanup: delete imports, created product/batch
    for created in imported.get("created_ids", []):
        check(f"delete imported product {created}", "DELETE",
              f"/products/{created}", expected=204, token=owner)
    check("delete inventory", "DELETE", f"/inventory/{inventory_id}",
          expected=204, token=staff)
    check("delete product", "DELETE", f"/products/{product_id}",
          expected=204, token=owner)

    passed = sum(1 for ok, *_ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    failures = [r for r in results if not r[0]]
    for ok, label, status, payload in failures:
        print(f" - {label}: {status} {str(payload)[:300]}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
