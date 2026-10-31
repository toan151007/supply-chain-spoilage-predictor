"""
Du bao theo mua vu (seasonal forecast).

Module nay goi `EXEC dbo.sp_Forecasts_Seasonal` va gom 200 dong
(50 san pham x 4 mua) thanh cau truc theo mua de frontend ve 4 tab.

Vi sao phai cache:
- Stored Procedure quet toan bo `order_items` (912.999 dong) moi lan chay.
- Frontend tu dong goi lai moi 5 phut (yeu cau auto-refresh), nen khong cache
  thi moi 5 phut lai co mot phep gom nang.
- Chatbot cung doc phan tom tat mua vu nay de tra loi, ma chatbot phai nhanh.

TTL mac dinh 300 giay (dung bang chu ky auto-refresh cua frontend). Goi
`force=True` de bo qua cache (nut "Lam moi" tren giao dien).
"""

import time
from datetime import datetime, timezone
from typing import Any

from app.database import DbSession

SEASON_ORDER = ["spring", "summer", "autumn", "winter"]

SEASON_LABELS = {
    "spring": "Xuân",
    "summer": "Hạ",
    "autumn": "Thu",
    "winter": "Đông",
}

SEASON_MONTHS = {
    "spring": [2, 3, 4],
    "summer": [5, 6, 7],
    "autumn": [8, 9, 10],
    "winter": [11, 12, 1],
}

METHOD_NOTE = (
    "Chỉ số mùa vụ là chỉ số TƯƠNG ĐỐI: tỷ trọng doanh số của sản phẩm trong "
    "mùa chia cho tỷ trọng doanh số của toàn hệ thống trong mùa đó. Cách tính "
    "này loại bỏ phần mùa vụ chung (mọi sản phẩm cùng tăng vào tháng 7, cùng "
    "giảm vào tháng 1) để thấy sản phẩm nào thực sự nổi bật trong từng mùa. "
    "Xếp hạng lấy 20% cao nhất là nên nhập, 20% thấp nhất là nên hạn chế."
)

CACHE_TTL_SECONDS = 300

_CACHE: dict[str, Any] = {"expires_at": 0.0, "payload": None}


def current_season(moment: datetime | None = None) -> str:
    """Mua hien tai theo lich Viet Nam (spring = thang 2-4)."""
    month = (moment or datetime.now()).month
    if month in (2, 3, 4):
        return "spring"
    if month in (5, 6, 7):
        return "summer"
    if month in (8, 9, 10):
        return "autumn"
    return "winter"


def _number(value: Any, default: float = 0.0) -> float:
    """SQL Server tra DECIMAL thanh `decimal.Decimal`; Pydantic can float."""
    if value is None:
        return default
    return float(value)


def _to_item(row: dict) -> dict:
    return {
        "product_id": row["product_id"],
        "product_code": row.get("product_code") or "",
        "product_name": row.get("product_name") or "",
        "unit": row.get("unit"),
        "category_name": row.get("category_name"),
        "avg_daily_qty": _number(row.get("avg_daily_qty")),
        "overall_daily_qty": _number(row.get("overall_daily_qty")),
        "sample_days": int(row.get("sample_days") or 0),
        "season_share": _number(row.get("season_share")),
        "seasonal_index": _number(row.get("seasonal_index")),
        "rank_in_season": int(row.get("rank_in_season") or 0),
        "season_products": int(row.get("season_products") or 0),
        "recommendation": row.get("recommendation") or "neutral",
    }


def get_seasonal(
    db: DbSession,
    ttl_seconds: int = CACHE_TTL_SECONDS,
    force: bool = False,
) -> dict:
    """
    Tra ve dict da gom theo mua, dung lam response cua API va context chatbot.

    Ket qua rong (chua co du lieu ban hang) van tra ve du 4 mua voi danh sach
    trong, de frontend khong phai xu ly truong hop thieu key.
    """
    now = time.monotonic()
    if not force and _CACHE["payload"] is not None and now < _CACHE["expires_at"]:
        return _CACHE["payload"]

    rows = db.rows("sp_Forecasts_Seasonal", {"Season": None})

    grouped: dict[str, list[dict]] = {code: [] for code in SEASON_ORDER}
    data_from: str | None = None
    data_to: str | None = None

    for raw in rows:
        row = dict(raw)
        code = row.get("season_code")
        if code not in grouped:
            continue
        if data_from is None:
            data_from = row.get("data_from")
        if data_to is None:
            data_to = row.get("data_to")
        grouped[code].append(_to_item(row))

    today_season = current_season()
    seasons = []

    for code in SEASON_ORDER:
        items = grouped[code]
        # Danh sach "nen nhap" xep giam dan (manh nhat truoc), danh sach "nen
        # han che" xep tang dan (yeu nhat truoc) de nguoi doc thay ngay muc
        # canh bao nghiem trong nhat, khong phai dao nguoc trong dau.
        import_items = sorted(
            (i for i in items if i["recommendation"] == "import"),
            key=lambda i: (-i["seasonal_index"], i["product_name"]),
        )
        avoid_items = sorted(
            (i for i in items if i["recommendation"] == "avoid"),
            key=lambda i: (i["seasonal_index"], i["product_name"]),
        )
        neutral_items = [i for i in items if i["recommendation"] == "neutral"]
        indexes = [i["seasonal_index"] for i in items]

        seasons.append(
            {
                "season_code": code,
                "season_name": SEASON_LABELS[code],
                "months": SEASON_MONTHS[code],
                "is_current": code == today_season,
                "total_products": len(items),
                "import_count": len(import_items),
                "avoid_count": len(avoid_items),
                "neutral_count": len(neutral_items),
                "avg_index": round(sum(indexes) / len(indexes), 4) if indexes else None,
                "import_items": import_items,
                "avoid_items": avoid_items,
                "neutral_items": neutral_items,
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc),
        "data_from": data_from,
        "data_to": data_to,
        "current_season": today_season,
        "method": METHOD_NOTE,
        "seasons": seasons,
    }

    _CACHE["payload"] = payload
    _CACHE["expires_at"] = now + max(0, ttl_seconds)
    return payload


def briefing_text(payload: dict, limit: int = 3) -> str:
    """
    Tom tat ngan gon de nhet vao context cua chatbot.

    Chi lay mua hien tai va 2 mua ke tiep, moi mua vai san pham dau, du de
    model tra loi duoc cau hoi "mua nay nen nhap gi" ma khong lam prompt dai.
    """
    seasons = payload.get("seasons") or []
    if not seasons:
        return ""

    order = [s["season_code"] for s in seasons]
    current = payload.get("current_season")
    start = order.index(current) if current in order else 0
    picked = [seasons[(start + i) % len(seasons)] for i in range(min(3, len(seasons)))]

    lines = []
    for season in picked:
        imports = season["import_items"][:limit]
        avoids = season["avoid_items"][:limit]
        if not imports and not avoids:
            continue
        label = season["season_name"]
        months = ", ".join(f"tháng {m}" for m in season["months"])
        mark = " (mùa hiện tại)" if season.get("is_current") else ""
        line = f"- {label}{mark} ({months}):"
        if imports:
            names = ", ".join(
                f"{i['product_name']} ({i['seasonal_index']:.3f})" for i in imports
            )
            line += f" nên nhập nhiều hơn: {names}."
        if avoids:
            names = ", ".join(
                f"{i['product_name']} ({i['seasonal_index']:.3f})" for i in avoids
            )
            line += f" nên hạn chế nhập: {names}."
        lines.append(line)

    return "\n".join(lines)
