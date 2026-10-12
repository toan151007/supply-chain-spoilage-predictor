"""
Router kiem tra trang thai he thong (health check).

Tach rieng router na de cac endpoint khac khong bi lan vao file main.py.
Tien khi phat trien (B2 tro len), cac router nghiep vu se nam o day.
"""

from fastapi import APIRouter

from app.config import settings
from app.database import check_database

router = APIRouter(tags=["health"])


@router.get("/health", summary="Kiem tra trang thai API")
def health() -> dict:
    """
    Endpoint kiem tra backend con song khong.

    KHONG truy van du lieu nghiep vu - dung de smoke test sau khi deploy
    va de frontend biet co nen goi API khong.
    """
    return {
        "status": "ok",
        "service": "supply-chain-spoilage-predictor",
    }


@router.get("/health/database", summary="Kiem tra ket noi database")
def health_database() -> dict:
    """
    Kiem tra ket noi PostgreSQL.

    `connected` la False thi frontend nen hien thi canh bao thay vi goi
    cac API khac. `error` chi la TEN LOI (vd OperationalError) de giup
    chan doan - KHONG tra ve message cua psycopg2 vi co the chua thong
    tin ket noi nho cam.
    """
    connected, error = check_database()

    db_info = {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "database": settings.DB_NAME,
        "connected": connected,
    }
    if error:
        db_info["error"] = error

    return {
        "status": "ok" if connected else "degraded",
        "database": db_info,
    }