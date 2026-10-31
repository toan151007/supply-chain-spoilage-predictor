"""
AI Agent Chatbot endpoint using Google Gemini API (google-genai).

Ba toi uu toc do:
1. CAU HOI KHONG LIEN QUAN NGHIEP VU -> tra loi ngay, khong cham database va
   khong goi Gemini. Truoc day moi cau "xin chao" cung phai chay 5 Stored
   Procedure roi moi goi API.
2. Chi nap nhung khoi du lieu lien quan den cau hoi (ton kho, canh bao, don
   hang, du bao, dieu chuyen, mua vu) thay vi nap tat ca.
3. Phan du bao mua vu duoc cache 5 phut trong `app.services.seasonal`, vi
   Stored Procedure cua no phai quet toan bo 912.999 dong order_items.

Ngoai ra module sua loi chinh ta tieng Viet (ca kieu go sai dau lan kieu go
khong dau) TRUOC khi nhan dien tu khoa va truoc khi gui Gemini.

The context builder turns Stored Procedure output into human readable
sentences (product names, store names, relative expiry days) so the model
never has to echo raw rows or abbreviations such as SP# / CH# / SL / HH.
"""

import os
import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from pyodbc import Error as PyodbcError

from app.config import settings
from app.database import DbSession, get_db, map_sqlserver_error
from app.services import seasonal

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]] = []
    model: str | None = None


SYSTEM_PROMPT = (
    "Bạn là trợ lý AI của FreshChain — nền tảng quản trị chuỗi cung ứng chống "
    "lãng phí thực phẩm.\n"
    "\n"
    "QUY TẮC BẮT BUỘC KHI TRẢ LỜI:\n"
    "1. Chỉ sử dụng DỮ LIỆU HỆ THỐNG được cung cấp bên dưới. Không bịa số liệu. "
    "Nếu thiếu dữ liệu, nói rõ là chưa có thông tin đó.\n"
    "2. TUYỆT ĐỐI KHÔNG in ra danh sách thô. Không dùng các ký hiệu viết tắt như "
    "SP#, CH#, SL, HH, CB#, DH. Không liệt kê hàng loạt dòng bắt đầu bằng dấu "
    "gạch đầu dòng.\n"
    "3. Trả lời bằng MỘT đoạn văn ngắn gọn 3-5 câu. Tóm tắt ý chính và con số "
    "quan trọng nhất. Chỉ nêu tối đa 3 mục khi thật sự cần thiết.\n"
    "4. Luôn gọi tên sản phẩm và tên cửa hàng bằng tên thật trong dữ liệu "
    "(ví dụ: “Rau muống” tại “Cửa hàng tiện lợi Q.3”), không gọi bằng mã số.\n"
    "5. Xưng hô “Tôi” với chính mình và “Bạn” với người dùng. Giọng điệu lịch sự, "
    "chuyên nghiệp, thân thiện như một quản lý cửa hàng.\n"
    "6. Khi phù hợp, kết thúc bằng một câu hỏi mời người dùng xem chi tiết, ví dụ: "
    "“Bạn có muốn xem chi tiết không?”.\n"
    "7. Trả lời bằng tiếng Việt có đầy đủ dấu, số liệu định dạng dễ đọc.\n"
    "8. Khi người dùng hỏi nên nhập gì, hỏi theo mùa hoặc hỏi về thời điểm nhập "
    "hàng, hãy dùng mục DỰ BÁO THEO MÙA VỤ: nêu tên sản phẩm nên nhập nhiều hơn "
    "và sản phẩm nên hạn chế, giải thích ngắn rằng chỉ số mùa vụ của chúng cao "
    "hơn hoặc thấp hơn mức chung. Không đọc nguyên bảng số.\n"
    "9. Khi người dùng hỏi về điều chuyển hàng, hãy nhắc quy trình gồm đề xuất, "
    "chờ duyệt, đã duyệt, đang chuyển và đã nhận, kèm số yêu cầu đang ở mỗi bước.\n"
    "10. Nếu dữ liệu cho thấy một sản phẩm vừa sắp hết hạn vừa dư so với nhu cầu, "
    "hãy chủ động gợi ý chuyển bớt sang cửa hàng khác thay vì nhập thêm.\n"
    "\n"
    "VÍ DỤ TRẢ LỜI ĐÚNG:\n"
    "Hỏi: “Tồn kho hiện tại thế nào?”\n"
    "Đáp: “Hiện tại hệ thống đang có 30 lô hàng trong kho. Đáng chú ý, có 2 lô sắp "
    "hết hạn trong tháng này là Rau muống tại Cửa hàng tiện lợi Q.1 và Sữa chua "
    "500g tại Cửa hàng tiện lợi Q.3. Nhìn chung lượng tồn kho vẫn đủ để đáp ứng "
    "nhu cầu bán ra. Bạn có muốn xem chi tiết từng lô không?”\n"
    "\n"
    "VÍ DỤ TRẢ LỜI SAI (không được làm):\n"
    "“- Kho #16 SP#6 CH#1 SL=355000 HH=2026-10-28”\n"
)

# ---------------------------------------------------------------------------
# Sua loi chinh ta
# ---------------------------------------------------------------------------
# Khoa la chuoi go sai (co dau hoac khong dau), gia tri la chuoi dung.
# Chi sua cac cum tu nghiep vu de tranh doi nghia cau.
TYPO_MAP: dict[str, str] = {
    # --- go sai dau ---
    "tồn khô": "tồn kho",
    "tồn khỏ": "tồn kho",
    "sản phảm": "sản phẩm",
    "sản phâm": "sản phẩm",
    "sản phẩn": "sản phẩm",
    "cảnh bào": "cảnh báo",
    "cảnh páo": "cảnh báo",
    "đơn hàn": "đơn hàng",
    "đơn hành": "đơn hàng",
    "cửa hàn": "cửa hàng",
    "cửa hành": "cửa hàng",
    "kho hành": "kho hàng",
    "hết hàn": "hết hạn",
    "hết hạng": "hết hạn",
    "dự páo": "dự báo",
    "dự bào": "dự báo",
    "nhập hàn": "nhập hàng",
    "điều chuyển": "điều chuyển",
    "điều chuyện": "điều chuyển",
    "số lương": "số lượng",
    "doanh thụ": "doanh thu",
    "mùa vụ": "mùa vụ",
    "mùa vu": "mùa vụ",
    # --- go khong dau (rat pho bien tren dien thoai) ---
    "ton kho": "tồn kho",
    "ton khô": "tồn kho",
    "san pham": "sản phẩm",
    "san phẩm": "sản phẩm",
    "canh bao": "cảnh báo",
    "don hang": "đơn hàng",
    "du bao": "dự báo",
    "het han": "hết hạn",
    "dieu chuyen": "điều chuyển",
    "cua hang": "cửa hàng",
    "nhap hang": "nhập hàng",
    "mua vu": "mùa vụ",
    "so luong": "số lượng",
    "doanh thu": "doanh thu",
    "ton that": "tổn thất",
    "xuat kho": "xuất kho",
    "kiem ke": "kiểm kê",
    "bao cao": "báo cáo",
    "thong ke": "thống kê",
    "nhan vien": "nhân viên",
}

# Sap xep theo do dai giam dan de cum dai duoc khop truoc cum ngan
# ("ton kho" phai khop truoc "kho").
_TYPO_PATTERN = re.compile(
    "|".join(
        rf"(?<!\w){re.escape(key)}(?!\w)"
        for key in sorted(TYPO_MAP, key=len, reverse=True)
    ),
    re.IGNORECASE | re.UNICODE,
)


def _fix_typos(text: str) -> str:
    """Thay cac cum tu go sai bang cum tu dung, giu nguyen phan con lai."""

    def replace(match: re.Match[str]) -> str:
        return TYPO_MAP.get(match.group(0).lower(), match.group(0))

    return _TYPO_PATTERN.sub(replace, text)


# ---------------------------------------------------------------------------
# Nhan dien cau hoi nghiep vu
# ---------------------------------------------------------------------------
SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "inventory": (
        "tồn kho",
        "tồn",
        "kho",
        "lô",
        "hết hạn",
        "hạn sử dụng",
        "hàng hóa",
        "lưu kho",
        "kiểm kê",
        "tổn thất",
    ),
    "alerts": ("cảnh báo", "xử lý", "nguy cơ", "rủi ro", "cần chú ý"),
    "orders": ("đơn hàng", "đơn", "bán hàng", "doanh thu", "doanh số", "khách hàng"),
    "forecasts": ("dự báo", "nhu cầu", "đề xuất nhập", "nhập hàng", "nhập thêm"),
    "transfers": ("điều chuyển", "chuyển hàng", "luân chuyển", "chuyển kho"),
    "seasonal": ("mùa", "mùa vụ", "xuân", "hạ", "thu", "đông", "thời vụ"),
}

# Tu khoa nghiep vu chung: khong tro dung mot khoi nao nhung van can du lieu.
GENERAL_KEYWORDS: tuple[str, ...] = (
    "sản phẩm",
    "cửa hàng",
    "nhân viên",
    "giá",
    "số lượng",
    "báo cáo",
    "thống kê",
    "hệ thống",
    "freshchain",
    "quản lý",
    "chi nhánh",
    "tổng quan",
    "tình hình",
    "hoạt động",
)

GREETING_PATTERN = re.compile(
    r"(?<!\w)(xin chào|chào bạn|chào|hello|hi|hey|alo)(?!\w)", re.IGNORECASE | re.UNICODE
)
THANKS_PATTERN = re.compile(
    r"(?<!\w)(cảm ơn|cam on|thank|thanks|cám ơn)(?!\w)", re.IGNORECASE | re.UNICODE
)

CAPABILITY_ANSWER = (
    "Tôi là trợ lý của FreshChain, có thể cho bạn biết tình hình tồn kho, danh "
    "sách hàng sắp hết hạn, các cảnh báo cần xử lý, đơn hàng gần đây, dự báo nhu "
    "cầu và gợi ý nên nhập hay hạn chế nhập mặt hàng nào theo từng mùa. Bạn muốn "
    "xem phần nào trước?"
)

GREETING_ANSWER = (
    "Chào bạn, tôi là trợ lý của FreshChain. Tôi có thể giúp bạn kiểm tra tồn "
    "kho, hàng sắp hết hạn, cảnh báo cần xử lý, đơn hàng gần đây và gợi ý nhập "
    "hàng theo mùa. Bạn cần xem thông tin gì trước?"
)

THANKS_ANSWER = (
    "Rất vui được hỗ trợ bạn. Nếu cần kiểm tra thêm tồn kho, hàng sắp hết hạn "
    "hay gợi ý nhập hàng theo mùa, bạn cứ hỏi tôi nhé."
)


def _match(text: str, keywords: tuple[str, ...]) -> bool:
    """Khop theo ranh gioi tu de 'hạ' khong khop vao giua 'hạch toán'."""
    return any(
        re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text, re.IGNORECASE | re.UNICODE)
        for word in keywords
    )


def _pick_sections(text: str) -> set[str]:
    """Chon khoi du lieu can nap dua tren tu khoa cua cau hoi."""
    picked = {
        name for name, keywords in SECTION_KEYWORDS.items() if _match(text, keywords)
    }
    if "seasonal" in picked:
        # Hoi ve mua thi gan nhu luon kem cau hoi nhap hang.
        picked.add("forecasts")
    return picked


def _is_business_question(text: str, sections: set[str]) -> bool:
    if sections:
        return True
    return _match(text, GENERAL_KEYWORDS)


# ---------------------------------------------------------------------------
# Dinh dang so / ngay
# ---------------------------------------------------------------------------
def _num(value: Any) -> str:
    """Format a number the Vietnamese way (dot as thousands separator)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    if number == int(number):
        return f"{int(number):,}".replace(",", ".")
    return f"{number:,.2f}".replace(",", ".")


def _money(value: Any) -> str:
    return f"{_num(value)} đ"


def _text(value: Any, fallback: str = "không rõ") -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _expiry_phrase(days_left: Any, expiry_date: Any) -> str:
    """Turn a raw date plus day delta into a sentence a human would say."""
    date_text = _text(expiry_date)
    try:
        days = int(days_left)
    except (TypeError, ValueError):
        return f"hết hạn ngày {date_text}"
    if days < 0:
        return f"đã hết hạn {-days} ngày (từ ngày {date_text})"
    if days == 0:
        return f"hết hạn ngay hôm nay ({date_text})"
    if days == 1:
        return f"hết hạn vào ngày mai ({date_text})"
    if days <= 31:
        return f"hết hạn sau {days} ngày (ngày {date_text})"
    return f"hết hạn ngày {date_text}"


TRANSFER_STATUS_LABELS = {
    "proposed": "đề xuất",
    "pending": "chờ duyệt",
    "approved": "đã duyệt",
    "in_transit": "đang chuyển",
    "received": "đã nhận",
    "rejected": "bị từ chối",
    "cancelled": "đã huỷ",
}


def _build_context(
    db: DbSession, sections: set[str]
) -> tuple[str, dict[str, Any]]:
    """Build a readable briefing plus the headline facts used as fallback."""
    blocks: list[str] = []
    facts: dict[str, Any] = {}

    # --- Inventory -----------------------------------------------------
    if "inventory" in sections:
        try:
            sets = db.call(
                "sp_Inventory_List", {"InStockOnly": 1, "Page": 1, "PageSize": 15}
            )
            total_lots = int(sets[0][0]["total"]) if sets and sets[0] else 0
            rows = sets[1] if len(sets) > 1 else []
            facts["total_lots"] = total_lots
            lines = [f"Tổng số lô hàng còn tồn trong kho: {_num(total_lots)} lô."]
            for row in rows[:10]:
                lines.append(
                    f"- Sản phẩm {_text(row.get('product_name'))} tại "
                    f"{_text(row.get('store_name'))}: còn {_num(row.get('quantity'))} sản phẩm, "
                    f"{_expiry_phrase(row.get('days_to_expiry'), row.get('expiry_date'))}."
                )
            blocks.append("TỒN KHO:\n" + "\n".join(lines))
        except Exception:
            pass

    # --- Expiring batches ----------------------------------------------
    if "inventory" in sections or "alerts" in sections:
        try:
            rows = db.call(
                "sp_Inventory_ListExpiring", {"Days": 30, "IncludeExpired": 0}
            ) or []
            facts["expiring_lots"] = len(rows)
            lines = [f"Số lô hàng sắp hết hạn trong 30 ngày tới: {_num(len(rows))} lô."]
            for row in rows[:8]:
                lines.append(
                    f"- {_text(row.get('product_name'))} tại {_text(row.get('store_name'))}: "
                    f"còn {_num(row.get('quantity'))} sản phẩm, "
                    f"{_expiry_phrase(row.get('days_left'), row.get('expiry_date'))}."
                )
            blocks.append("HÀNG SẮP HẾT HẠN:\n" + "\n".join(lines))
        except Exception:
            pass

    # --- Unresolved alerts ---------------------------------------------
    if "alerts" in sections:
        try:
            sets = db.call("sp_Alerts_List", {"IsResolved": 0, "Page": 1, "PageSize": 20})
            total_alerts = int(sets[0][0]["total"]) if sets and sets[0] else 0
            rows = sets[1] if len(sets) > 1 else []
            facts["open_alerts"] = total_alerts
            lines = [f"Số cảnh báo chưa xử lý: {_num(total_alerts)}."]
            for row in rows[:6]:
                product = _text(row.get("product_name"))
                store = _text(row.get("store_name"))
                title = _text(row.get("title"))
                message = _text(row.get("message"), fallback="")
                lines.append(
                    f"- Cảnh báo mức độ {_text(row.get('severity'))}: {title} "
                    f"({product} tại {store}). {message}".strip()
                )
            blocks.append("CẢNH BÁO CHƯA XỬ LÝ:\n" + "\n".join(lines))
        except Exception:
            pass

    # --- Recent orders ---------------------------------------------------
    if "orders" in sections:
        try:
            sets = db.call("sp_Orders_List", {"Page": 1, "PageSize": 6})
            total_orders = int(sets[0][0]["total"]) if sets and sets[0] else 0
            rows = sets[1] if len(sets) > 1 else []
            facts["total_orders"] = total_orders
            lines = [f"Tổng số đơn hàng trong hệ thống: {_num(total_orders)} đơn."]
            for row in rows[:5]:
                lines.append(
                    f"- Đơn {_text(row.get('order_code'))} tại {_text(row.get('store_name'))}: "
                    f"loại {_text(row.get('order_type'))}, trạng thái {_text(row.get('status'))}, "
                    f"tổng tiền {_money(row.get('total_amount'))}, ngày {_text(row.get('order_date'))}."
                )
            blocks.append("ĐƠN HÀNG GẦN NHẤT:\n" + "\n".join(lines))
        except Exception:
            pass

    # --- Latest forecasts ------------------------------------------------
    if "forecasts" in sections:
        try:
            sets = db.call("sp_Forecasts_Latest", {"Page": 1, "PageSize": 8})
            rows = sets[1] if len(sets) > 1 else []
            if rows:
                facts["forecast_date"] = rows[0].get("forecast_date")
                lines = [
                    "Dự báo nhu cầu mới nhất (mô hình "
                    f"{_text(rows[0].get('model_name'))}):"
                ]
                for row in rows[:5]:
                    lines.append(
                        f"- {_text(row.get('product_name'))} tại {_text(row.get('store_name'))}: "
                        f"dự báo {_num(row.get('predicted_quantity'))} sản phẩm, "
                        f"đề xuất nhập {_num(row.get('recommended_import_qty'))} sản phẩm."
                    )
                blocks.append("DỰ BÁO NHU CẦU:\n" + "\n".join(lines))
        except Exception:
            pass

    # --- Seasonal briefing (cached, see app.services.seasonal) -----------
    if "seasonal" in sections:
        try:
            payload = seasonal.get_seasonal(db)
            brief = seasonal.briefing_text(payload)
            if brief:
                facts["seasonal_brief"] = brief
                blocks.append(
                    "DỰ BÁO THEO MÙA VỤ (tính từ dữ liệu bán hàng lịch sử, chỉ số "
                    "1.000 là đúng mức chung):\n" + brief
                )
        except Exception:
            pass

    # --- Transfers --------------------------------------------------------
    if "transfers" in sections:
        try:
            sets = db.call("sp_Transfer_Summary")
            counts = {
                row.get("status"): int(row.get("total") or 0)
                for row in (sets[0] if sets else [])
            }
            totals = (sets[1][0] if len(sets) > 1 and sets[1] else {}) or {}
            facts["transfers_total"] = int(totals.get("total") or 0)
            lines = [
                f"Tổng số yêu cầu điều chuyển hàng: {_num(totals.get('total'))}.",
                "Số lượng hàng đang trên đường: "
                f"{_num(totals.get('in_transit_quantity'))} sản phẩm.",
            ]
            detail = ", ".join(
                f"{label}: {counts.get(code, 0)}"
                for code, label in TRANSFER_STATUS_LABELS.items()
                if counts.get(code)
            )
            if detail:
                lines.append("Chi tiết theo trạng thái: " + detail + ".")
            blocks.append("ĐIỀU CHUYỂN HÀNG:\n" + "\n".join(lines))
        except Exception:
            pass

    blocks.append(f"Thời gian hệ thống: {datetime.now().strftime('%d/%m/%Y %H:%M')}.")
    return "\n\n".join(blocks), facts


def _fallback_answer(facts: dict[str, Any]) -> str:
    """Short natural summary used when no Gemini API key is configured."""
    parts = [
        "Hệ thống chưa được cấu hình khóa API cho trợ lý AI, nên tôi chỉ tóm tắt "
        "được số liệu có sẵn."
    ]
    if "total_lots" in facts:
        parts.append(f"Hiện tại kho còn {_num(facts['total_lots'])} lô hàng.")
    if facts.get("expiring_lots"):
        parts.append(
            f"Có {_num(facts['expiring_lots'])} lô sắp hết hạn trong 30 ngày tới cần ưu tiên xử lý."
        )
    if facts.get("open_alerts"):
        parts.append(f"Đang có {_num(facts['open_alerts'])} cảnh báo chưa xử lý.")
    if facts.get("transfers_total"):
        parts.append(
            f"Có {_num(facts['transfers_total'])} yêu cầu điều chuyển hàng đang được theo dõi."
        )
    if facts.get("seasonal_brief"):
        parts.append("Về mùa vụ, tôi đã tổng hợp được danh sách mặt hàng nên nhập và nên hạn chế.")
    parts.append("Bạn có thể hỏi tôi về tồn kho, đơn hàng, cảnh báo hoặc dự báo nhu cầu.")
    return " ".join(parts)


def _fast_answer(message: str) -> str | None:
    """
    Tra loi ngay nhung cau khong can du lieu.

    Tra ve None khi cau hoi co lien quan nghiep vu (de di tiep xuong phan
    truy van database).
    """
    if THANKS_PATTERN.search(message):
        return THANKS_ANSWER
    if GREETING_PATTERN.search(message):
        return GREETING_ANSWER
    return None


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession = Depends(get_db)) -> ChatResponse:
    message = _fix_typos(payload.message).strip()
    sections = _pick_sections(message)

    # --- Duong nhanh: khong cham database, khong goi Gemini --------------
    if not _is_business_question(message, sections):
        quick = _fast_answer(message)
        return ChatResponse(
            answer=quick or CAPABILITY_ANSWER,
            sources=[{"type": "instant"}],
            model=None,
        )

    try:
        context, facts = _build_context(db, sections)
    except PyodbcError as exc:
        raise map_sqlserver_error(exc) from exc

    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        return ChatResponse(
            answer=_fallback_answer(facts),
            sources=[{"type": "context", "count": len(context.splitlines())}],
            model=None,
        )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = (
            SYSTEM_PROMPT
            + "\nDỮ LIỆU HỆ THỐNG (số liệu thật lấy từ cơ sở dữ liệu):\n"
            + context
            + f"\n\nCÂU HỎI CỦA NGƯỜI DÙNG: {message}"
            + "\n\nCÂU TRẢ LỜI (3-5 câu, văn nói, không danh sách thô):"
        )
        model_name = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        response = client.models.generate_content(model=model_name, contents=prompt)
        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates") and response.candidates:
            try:
                text = response.candidates[0].content.parts[0].text
            except Exception:
                text = None
        if not text:
            text = str(response)
        return ChatResponse(
            answer=text.strip(),
            sources=[
                {
                    "type": "context",
                    "sections": sorted(sections),
                    "count": len(context.splitlines()),
                }
            ],
            model=model_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loi goi Gemini API: {exc}",
        )
