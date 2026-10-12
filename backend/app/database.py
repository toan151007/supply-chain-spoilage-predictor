"""
Ket noi database qua SQLAlchemy ORM.

QUY TAC DU AN: moi truy van DB phai qua ORM.
`create_engine` + `SessionLocal` + `declarative_base` la 3 thanh phan
chuan cua SQLAlchemy 2.x. Raw SQL chi duoc phep trong file SQL
(database/) va trong services khi that su can cau lenh dac thu
(vi du goi ham trigger trong DB) - KHONG viet raw SQL trong routers.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# pool_pre_ping=True: kiem tra ket noi truoc moi lay connection tu pool.
# Can thiet vi PostgreSQL hay dong connection khi khong dung lau, neu
# khong co thi request dau tien sau thoi gian cho se bao loi "server
# closed the connection unexpectedly".
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,          # Bat SQL log khi len production
)

# SessionLocal la factory, moi lan goi tao mot Session moi.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """
    Base class cho tat ca ORM model.

    SQLAlchemy 2.x dung DeclarativeBase thay cho declarative_base() cu.
    Cac model trong backend/app/models/ se ke thua tu day.
    """


def get_db():
    """
    Dependency FastAPI cung cap mot session DB cho moi request.

    Dung `yield` de dam bao session LUON duoc dong - ke ca khi handler
    nem exception. Neu thieu `finally`, mot request loi se giu connection
    mo lai va dan den can bang het connection pool.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> tuple[bool, str | None]:
    """
    Kiem tra ket noi database. Dung cho endpoint /health.

    Tra ve (True, None) neu ket noi duoc, (False, "<ten_loi>") neu khong.

    KHONG nem exception ra ngoai, vi muc tieu cua endpoint la bao cao
    trang thai chu khong phai lam server crash.

    CHI tra ve TEN LOI (OperationalError, InterfaceError...), KHONG tra ve
    `str(exc)`: message cua psycopg2 co the chua thong tin nho cam, khong
    nen gui thang ra HTTP response.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, type(exc).__name__