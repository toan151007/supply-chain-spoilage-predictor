"""
Diem khoi dong FastAPI.

Chay:
    cd backend
    uvicorn app.main:app --reload --port 8000

Mo trang tai: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    alert_router,
    category_router,
    dashboard_router,
    forecast_router,
    health,
    inventory_router,
    order_item_router,
    order_router,
    product_router,
    store_router,
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend cho he thong quan tri chuoi cung ung chong lang phich.\n\n"
        "Phien ban nay (B1) moi khoi dong server va endpoint kiem tra "
        "trang thai. Cac API nghiep vu (san pham, ton kho, du bao, canh bao) "
        "se duoc them o cac task sau."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---- CORS ----
# BAT BUOC: frontend chay o cong 3000 se goi API tren cong 8000 - khac
# origin nen trinh duyet se chan bang CORS neu khong bat middleware nay.
# WebSocket cung can CORS cho frontend localhost:3000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Health check ----
# KHONG co tien to /api/v1: endpoint nay phuc vu HA TANG, dung cho uptime
# check va smoke test. Frontend van co the goi binh thuong.
app.include_router(health.router)

# ---- API nghiep vu ----
# QUY TAC: moi API nghiep vu phai nam sau tien to /api/v1/
# Vi du: app.include_router(order_router.router, prefix=settings.API_V1_PREFIX)
# -> endpoint: /api/v1/orders
#
# Thu tu khai bao khong quan trong giua cac router khac nhau, nhung THU TU
# TRONG MOT ROUTER co quan trong: `/alerts/unread` phai khai bao truoc
# `/alerts/{alert_id}` de FastAPI khop dung path.
app.include_router(health.api_router, prefix=settings.API_V1_PREFIX)
app.include_router(product_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(store_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(category_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(inventory_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(forecast_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(alert_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(order_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(order_item_router.router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict:
    """Huong dan nhanh khi mo dau tien, khong hien thi trong /docs."""
    return {
        "message": "API dang chay",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_v1": settings.API_V1_PREFIX,
    }