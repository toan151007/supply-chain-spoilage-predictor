"""
AI Agent Chatbot endpoint using Google Gemini API (google-genai).

The context builder turns Stored Procedure output into human readable
sentences (product names, store names, relative expiry days) so the model
never has to echo raw rows or abbreviations such as SP# / CH# / SL / HH.
"""

import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from pyodbc import Error as PyodbcError

from app.config import settings
from app.database import DbSession, get_db, map_sqlserver_error

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


def _build_context(db: DbSession) -> tuple[str, dict[str, Any]]:
    """Build a readable briefing plus the headline facts used as fallback."""
    blocks: list[str] = []
    facts: dict[str, Any] = {}

    # --- Inventory -----------------------------------------------------
    try:
        sets = db.call("sp_Inventory_List", {"InStockOnly": 1, "Page": 1, "PageSize": 15})
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
    try:
        rows = db.call("sp_Inventory_ListExpiring", {"Days": 30, "IncludeExpired": 0}) or []
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
    parts.append("Bạn có thể hỏi tôi về tồn kho, đơn hàng, cảnh báo hoặc dự báo nhu cầu.")
    return " ".join(parts)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession = Depends(get_db)) -> ChatResponse:
    try:
        context, facts = _build_context(db)
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
            + f"\n\nCÂU HỎI CỦA NGƯỜI DÙNG: {payload.message}"
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
            sources=[{"type": "context", "count": len(context.splitlines())}],
            model=model_name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loi goi Gemini API: {exc}",
        )
