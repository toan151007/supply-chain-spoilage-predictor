"""
Ket noi database SQL Server qua pyodbc (B3).

Quy tac du an: 100% thao tac du lieu phai goi Stored Procedure.
Module nay cung cap mot lop mong `DbSession` boc pyodbc de router goi
`db.call("sp_Ten", {...})` va nhan ve danh sach cac result set.

Vi sao khong dung SQLAlchemy Session cho Stored Procedure:
- Cac SP tu mo transaction (`BEGIN TRANSACTION ... COMMIT`). Voi
  `autocommit=False`, pyodbc da mo mot transaction ngam, nen `COMMIT`
  trong SP dong luon transaction ngoai -> loi 266
  "Transaction count after EXECUTE indicates a mismatching number".
- Mot SP tra ve NHIEU result set (total + rows). SQLAlchemy `CursorResult`
  khong co `nextset()`, va neu khong doc het result set se bao
  "Connection is busy with results for another command".

Vi vay lop nay dung truc tiep pyodbc cursor, luon doc het result set va
dong cursor trong `finally`.
"""

import re
from typing import Any

import pyodbc
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# Engine chi con dung de giu Base/legacy va lay raw connection tu pool.
# Cac router KHONG dung SQLAlchemy ORM de doc/ghi nghiep vu nua.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
    # SP tu quan ly transaction; xem docstring dau file.
    connect_args={"autocommit": True},
)

# Giu lai cho tuong thich voi cac model/script cu chua chuyen.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class cho cac ORM model cu (chi con de import, khong dung ghi)."""


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------

# SQL Server business error codes raised by THROW in stored procedures.
BUSINESS_ERROR_HTTP = {
    "50001": status.HTTP_404_NOT_FOUND,
    "50002": status.HTTP_409_CONFLICT,
    "50003": status.HTTP_409_CONFLICT,
    "50004": status.HTTP_409_CONFLICT,
    "50005": status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _extract_detail(message: str) -> str:
    """Pull the human-readable text that follows the business error number."""
    marker = re.search(r"\((5000[1-5])\)\s*(.*)", message)
    if marker:
        detail = marker.group(2).strip()
        # pyodbc appends driver noise; cut at the first bracket.
        detail = re.split(r"\s*\(SQL|\[Microsoft\]", detail)[0].strip()
        return detail or message
    return message


def map_sqlserver_error(exc: Exception) -> HTTPException:
    """
    Map a pyodbc/SQL Server error to the HTTP status the API contract uses.

    THROW 50001..50005 in the procedures carry the business meaning:
        50001 NOT_FOUND -> 404
        50002 DUPLICATE -> 409
        50003 REFERENCED -> 409
        50004 INVALID_STATE -> 409
        50005 INVALID_INPUT -> 422

    Native SQL Server errors are mapped too, so an unexpected constraint
    violation does not surface as a 500:
        2601/2627 unique violation -> 409
        547 foreign key / check -> 409
    """
    message = str(exc)

    match = re.search(r"\((5000[1-5])\)", message)
    if match:
        code = match.group(1)
        return HTTPException(
            status_code=BUSINESS_ERROR_HTTP[code],
            detail=_extract_detail(message),
        )

    if re.search(r"\(26(01|27)\)", message):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate value violates a UNIQUE constraint",
        )

    if re.search(r"\(547\)", message):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot complete the operation: the row is referenced by "
                "other records, or violates a CHECK constraint."
            ),
        )

    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
    )


# ---------------------------------------------------------------------------
# DbSession
# ---------------------------------------------------------------------------


class DbSession:
    """
    Thin wrapper around a pooled pyodbc connection.

    `call()` executes `EXEC dbo.sp_X @A=?, @B=?` and returns a list of result
    sets. Each result set is a list of dicts keyed by column name, so routers
    never depend on column position (the B10 bug: reading row[10] instead of
    the named `total_value` returned a value 350x too small).
    """

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    # -- core ---------------------------------------------------------------
    def call(self, sp_name: str, params: dict | None = None) -> list[list[dict]]:
        params = params or {}
        items = list(params.items())
        if items:
            arguments = ", ".join(f"@{key}=?" for key, _ in items)
            sql = f"EXEC dbo.{sp_name} {arguments}"
            values = [value for _, value in items]
        else:
            sql = f"EXEC dbo.{sp_name}"
            values = []

        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, values)
            result_sets: list[list[dict]] = []
            while True:
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    rows = [
                        {columns[i]: row[i] for i in range(len(columns))}
                        for row in cursor.fetchall()
                    ]
                    result_sets.append(rows)
                else:
                    result_sets.append([])
                if not cursor.nextset():
                    break
            return result_sets
        finally:
            cursor.close()

    def scalar(self, sp_name: str, params: dict | None = None, column: str | None = None):
        """Return the first value of the first row of the first result set."""
        sets = self.call(sp_name, params)
        if not sets or not sets[0]:
            return None
        row = sets[0][0]
        if column is not None:
            return row.get(column)
        return next(iter(row.values()))

    def rows(self, sp_name: str, params: dict | None = None, index: int = 0) -> list[dict]:
        """Return one result set as a list of dicts (default: the first)."""
        sets = self.call(sp_name, params)
        if index >= len(sets):
            return []
        return sets[index]

    def one(self, sp_name: str, params: dict | None = None) -> dict | None:
        """Return the first row of the first result set, or None."""
        rows = self.rows(sp_name, params, index=0)
        return rows[0] if rows else None

    # -- transaction helpers ------------------------------------------------
    def commit(self) -> None:
        """No-op: each stored procedure commits its own transaction."""
        return None

    def rollback(self) -> None:
        """No-op: each stored procedure rolls back its own transaction."""
        return None

    def close(self) -> None:
        try:
            self.connection.close()
        except Exception:
            pass


def get_db():
    """
    FastAPI dependency: one pooled pyodbc connection per request.

    `engine.raw_connection()` borrows from the SQLAlchemy pool, so a request
    does not pay the cost of a new TCP/TDS handshake. `close()` returns the
    connection to the pool.
    """
    connection = engine.raw_connection()
    session = DbSession(connection)
    try:
        yield session
    finally:
        session.close()


def check_database() -> tuple[bool, str | None]:
    """
    Health check. Returns (True, None) when a connection and a trivial query
    both succeed, otherwise (False, "<exception name>").

    Only the exception NAME is exposed - the pyodbc message can contain the
    server and login details.
    """
    connection = None
    cursor = None
    try:
        connection = engine.raw_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return True, None
    except Exception as exc:
        return False, type(exc).__name__
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

