"""
Cau hinh backend - doc tu bien moi truong va file .env.

QUY TAC: KHONG hardcode mat khau trong file nay.
Mat khau chi nam trong file `.env` cuc bo, file nay da co trong .gitignore.
Neu khong tim thay bien moi truong, dung gia tri mac dinh cho phat trien
(localhost) - KHONG dat mat khau mac dinh o day.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Thu muc goc cua du an (cha cua backend/)
# backend/app/config.py -> backend/app -> backend -> <root>
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

# Danh sach mac dinh khi khong cau hinh duoc tu .env.
# Frontend Vite mac dinh chay o cong 3000; 5173 la port fallback.
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",   # Vite co the random port
    "http://127.0.0.1:5173",
]


class Settings(BaseSettings):
    """
    Cau hinh chung cho toan bo backend.

    pydantic-settings tu doc bien moi truong theo ten truong, va doc file
    .env o thu muc goc du an. Uu tien: bien moi truong > .env > mac dinh.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Database ----
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "spoilage_predictor"

    # ---- Application ----
    APP_NAME: str = "Supply Chain Spoilage Predictor API"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Cho phep tat kiem tra mat khau khi chay may khong co bien moi truong.
    # Chi nen BAT khi develop, khong bat khi len production.
    DEBUG: bool = True

    # ---- CORS ----
    # Frontend Vite mac dinh chay o cong 3000.
    # WebSocket yeu cau CORS cho frontend localhost:3000 (xem AGENTS.md).
    #
    # KHONG khai bao kieu `list[str]`. Bien moi truong luon la CHUOI, va
    # pydantic-settings chi doc chuoi do theo dang JSON:
    #     CORS_ORIGINS=["http://localhost:3000"]
    # Nguoi doc duong dan lai se viet "a,b" va gap ValidationError.
    # Vi vay khai bao str roi tach thu cong trong property ben duoi.
    CORS_ORIGINS: str = ",".join(DEFAULT_CORS_ORIGINS)

    # ---- JWT / xac thuc (B12) ----
    # SECRET_KEY chi dung cho KY TOKEN, KHONG lien quan mat khau database.
    # Mac dinh duoi day LA GIA TRI PHAT TRIEN - bat buoc dat trong `.env`
    # that truoc khi len production. Xem `.env.example`.
    SECRET_KEY: str = "dev-only-insecure-key-DOI-TRUOC-KHI-LEN-PRODUCTION"
    ALGORITHM: str = "HS256"

    # Access token song ngan (phut) - dung cho moi request.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Refresh token song dai (ngay) - chi dung de lay access token moi.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def cors_origins_list(self) -> list[str]:
        """
        Danh sach origin cho middleware CORS.

        KHONG khai bao `CORS_ORIGINS: list[str]`. Bien moi truong luon la
        CHUOI, va pydantic-settings chi doc chuoi do theo dang JSON:
            CORS_ORIGINS=["http://localhost:3000"]
        Do do file `backend/.env.example` viet dang danh sach ("a,b") se
        bao loi `ValidationError: Input should be a valid list` cho nguoi
        clone repo. Xem GHI-CHU-TIEN-DO.md muc 8k.

        Property nay chap nhan ca hai dang:
            CORS_ORIGINS=["http://localhost:3000"]        (JSON)
            CORS_ORIGINS=http://localhost:3000,http://x   (danh sach)
        """
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("["):
            try:
                import json

                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except (ValueError, TypeError):
                # JSON hong -> thu tach bang dau phay ben duoi
                pass
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def database_url(self) -> str:
        """Chuoi ket noi SQLAlchemy (chuan PostgreSQL + psycopg2)."""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    """
    Cache instance de khong doc lai .env moi request.

    @lru_cache bat buoc: settings duoc dung o module import, doc file moi
    lan se lam backend cham dong thoi khong can thiet.
    """
    return Settings()


settings = get_settings()