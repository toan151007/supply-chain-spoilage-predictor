"""
AI Agent Chatbot endpoint using Google Gemini API (google-genai).
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


def _build_context(db: DbSession) -> str:
    context_lines: list[str] = []
    try:
        inv_sets = db.call("sp_Inventory_List", {"Page": 1, "PageSize": 50})
        items = inv_sets[1] if len(inv_sets) > 1 else []
        context_lines.append("TON KHO (50 ban ghi gan nhat):")
        for row in items[:30]:
            context_lines.append(
                f"- Kho #{row.get('inventory_id')} SP#{row.get('product_id')} CH#{row.get('store_id')} SL={row.get('quantity')} HH={row.get('expiry_date')}"
            )
    except Exception:
        pass

    try:
        ord_sets = db.call("sp_Orders_List", {"Page": 1, "PageSize": 20})
        items = ord_sets[1] if len(ord_sets) > 1 else []
        context_lines.append("DON HANG (20 don gan nhat):")
        for row in items[:15]:
            context_lines.append(
                f"- DH {row.get('order_code')} loai={row.get('order_type')} trangthai={row.get('status')} tong={row.get('total_amount')} ngay={row.get('order_date')}"
            )
    except Exception:
        pass

    try:
        al_sets = db.call("sp_Alerts_List", {"Page": 1, "PageSize": 20, "IsResolved": 0})
        items = al_sets[1] if len(al_sets) > 1 else []
        context_lines.append("CANH BAO CHUA XU LY (20):")
        for row in items[:15]:
            context_lines.append(
                f"- CB#{row.get('alert_id')} loai={row.get('alert_type')} mucdo={row.get('severity')} SP#{row.get('product_id')} CH#{row.get('store_id')}"
            )
    except Exception:
        pass

    try:
        fc_sets = db.call("sp_Forecasts_Latest", {"Page": 1, "PageSize": 20})
        items = fc_sets[1] if len(fc_sets) > 1 else []
        context_lines.append("DU BAO MOI NHAT (20 cap SPxCH):")
        for row in items[:15]:
            context_lines.append(
                f"- SP#{row.get('product_id')} CH#{row.get('store_id')} model={row.get('model_name')} du_bao={row.get('predicted_quantity')} ngay={row.get('forecast_date')}"
            )
    except Exception:
        pass

    context_lines.append(f"Thoi gian he thong: {datetime.now().isoformat()}")
    return "\n".join(context_lines)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession = Depends(get_db)) -> ChatResponse:
    context = _build_context(db)
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        answer = (
            "Chua cau hinh GEMINI_API_KEY. Hien tai toi tra loi dua tren du lieu he thong:\n\n"
            f"{context}\n\n"
            "Ban co the hoi: 'Hang nao sap het han?', 'Don hang hom nay?', 'Co canh bao nao chua xu ly?'"
        )
        return ChatResponse(answer=answer, sources=[{"type": "context", "count": len(context.splitlines())}], model=None)

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = (
            "Ban la tro ly AI cho he thong quan tri chuoi cung ung chong lang phi thuc pham (FreshChain).\n"
            "Chi tra loi dua tren DU LIEU THAT duoc cung cap ben duoi. Neu khong du du lieu de tra loi chinh xac, hay noi ro dieu do.\n"
            "Tra loi bang tieng Viet, ngan gon, ro rang, co so lieu neu co.\n\n"
            "DU LIEU HE THONG:\n"
            f"{context}\n\n"
            f"CAU HOI CUA NGUOI DUNG: {payload.message}\n\n"
            "TRA LOI:"
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
        return ChatResponse(answer=text, sources=[{"type": "context", "count": len(context.splitlines())}], model=model_name)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loi goi Gemini API: {exc}",
        )
