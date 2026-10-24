"""Smoke-test every API group against the running server."""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000/api/v1"
results = []


def call(method, path, token=None, body=None, form=None):
    url = BASE + path
    data = None
    headers = {}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = resp.read()
            try:
                parsed = json.loads(payload)
            except Exception:
                parsed = payload[:80]
            return resp.status, parsed
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            parsed = json.loads(payload)
        except Exception:
            parsed = payload[:200]
        return exc.code, parsed
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc)


def check(label, method, path, expected=200, token=None, body=None, form=None):
    status, payload = call(method, path, token=token, body=body, form=form)
    ok = status == expected
    results.append((ok, label, status, payload))
    mark = "PASS" if ok else "FAIL"
    extra = ""
    if isinstance(payload, list):
        extra = f" ({len(payload)} rows)"
    elif isinstance(payload, dict):
        keys = list(payload)[:4]
        extra = f" keys={keys}"
    print(f"{mark} {label}: {status}{extra}")
    if not ok:
        print(f"     {payload}")
    return payload


def main() -> None:
    check("health", "GET", "/health")
    check("health/db", "GET", "/health/database")

    login = check(
        "auth/login", "POST", "/auth/login", body={"username": "owner", "password": "Owner@2026"},
    )
    token = login.get("access_token") if isinstance(login, dict) else None
    if not token:
        print("no token, stopping")
        sys.exit(1)

    check("auth/me", "GET", "/auth/me", token=token)

    check("products list", "GET", "/products?page=1&page_size=5")
    check("products get", "GET", "/products/8")
    check("stores list", "GET", "/stores")
    check("categories list", "GET", "/categories")
    check("inventory list", "GET", "/inventory?page=1&page_size=5")
    check("inventory expiring", "GET", "/inventory/expiring?days=7")
    check("forecasts list", "GET", "/forecasts?page=1&page_size=5")
    check("forecasts latest", "GET", "/forecasts/latest")
    check("alerts list", "GET", "/alerts?page=1&page_size=5")
    check("alerts unread", "GET", "/alerts/unread")
    check("alerts unread-count", "GET", "/alerts/unread-count")
    check("orders list", "GET", "/orders?page=1&page_size=5")
    check("orders get", "GET", "/orders/1")
    check("order-items list", "GET", "/order-items?page=1&page_size=5")

    check("dashboard overview", "GET", "/dashboard/overview")
    check("dashboard revenue", "GET", "/dashboard/revenue?period=month")
    check("dashboard revenue year", "GET", "/dashboard/revenue?period=month&year=2017")
    check("dashboard top", "GET", "/dashboard/top-products?limit=5")
    check("dashboard low", "GET", "/dashboard/low-stock")
    check("dashboard expiring", "GET", "/dashboard/expiring?days=7")
    check("dashboard alerts", "GET", "/dashboard/alerts-summary")

    check("adv revenue by store", "GET", "/dashboard/revenue-by-store")
    check("adv top stores", "GET", "/dashboard/top-stores?limit=5")
    check("adv revenue by category", "GET", "/dashboard/revenue-by-category")
    check("adv inventory value", "GET", "/dashboard/inventory-value")
    check("adv waste", "GET", "/dashboard/waste-analysis?include_batches=true&limit=5")
    check("adv forecast", "GET", "/dashboard/forecast-vs-actual?model_name=prophet")

    check("reco import", "GET", "/recommendations/import?limit=5")
    check("reco expiring", "GET", "/recommendations/expiring?limit=5")
    check("reco slow", "GET", "/recommendations/slow-moving?limit=5")

    for fmt in ("csv", "xlsx", "pdf"):
        check(f"report inventory {fmt}", "GET", f"/reports/inventory/export?format={fmt}&limit=50")
    check("report sales csv", "GET", "/reports/sales/export?format=csv&group_by=day&limit=100")
    check("report waste csv", "GET", "/reports/waste/export?format=csv&limit=100")
    check("report expiring csv", "GET", "/reports/expiring/export?format=csv&limit=100")

    check("import types", "GET", "/import/types")
    check("import template", "GET", "/import/template/products?fmt=csv")

    # Validation / error mapping
    check("products 404", "GET", "/products/99999", expected=404)
    check("bad period", "GET", "/dashboard/revenue?period=fortnight", expected=422)
    check("bad format", "GET", "/reports/sales/export?format=bogus", expected=422)
    check("bad group_by", "GET", "/reports/sales/export?group_by=bogus", expected=422)
    check("bad days", "GET", "/dashboard/expiring?days=99", expected=422)
    check(
        "login bad password", "POST", "/auth/login", expected=401,
        body={"username": "owner", "password": "wrong"},
    )

    passed = sum(1 for ok, *_ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    failures = [(label, status, payload) for ok, label, status, payload in results if not ok]
    if failures:
        print("FAILURES:")
        for label, status, payload in failures:
            print(f" - {label}: {status} {str(payload)[:300]}")


if __name__ == "__main__":
    import urllib.parse  # noqa: F401
    main()

