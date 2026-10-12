"""
SQLAlchemy Core definitions for the read-only database views.

The dashboard aggregates over views that already do the heavy lifting in
PostgreSQL. Reflecting them lets the routers use `select()`, `join()` and
`group_by()` instead of raw SQL strings, which keeps the project rule
"all queries go through the ORM" intact.

These are NOT mapped classes: nothing calls `session.add()` on them. They
are read-only by design.
"""

from sqlalchemy import Table

from app.database import Base, engine

# Reflection reads the column definitions straight from the catalogue, so
# this stays correct even if the view definition changes in the database.
v_low_stock = Table(
    "v_low_stock", Base.metadata, autoload_with=engine
)

v_expiring_inventory = Table(
    "v_expiring_inventory", Base.metadata, autoload_with=engine
)

v_product_stock_summary = Table(
    "v_product_stock_summary", Base.metadata, autoload_with=engine
)

v_daily_sales = Table(
    "v_daily_sales", Base.metadata, autoload_with=engine
)

ALL_VIEWS = [
    v_low_stock,
    v_expiring_inventory,
    v_product_stock_summary,
    v_daily_sales,
]