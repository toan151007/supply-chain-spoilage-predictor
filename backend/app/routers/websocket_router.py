"""
WebSocket endpoint for realtime alerts.
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket_manager import manager

router = APIRouter()


@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await manager.send_personal(
            {"type": "connected", "message": "Ket noi realtime thanh cong"},
            websocket,
        )
        while True:
            await asyncio.sleep(30)
            await manager.send_personal({"type": "ping"}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
