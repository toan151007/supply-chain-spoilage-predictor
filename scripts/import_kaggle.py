"""
Import dataset Kaggle "Walmart Store Sales" vao PostgreSQL.

Nguon du lieu : https://www.kaggle.com/competitions/demand-forecasting-kernels-only
File         : datasets/raw/train.csv  (cot: date, store, item, sales)

Tại sao nạp vào orders + order_items mà không tạo bảng sales riêng:
    - Dataset không có giá, khách hàng, phương thức thanh toán. Tách thành bảng
      "sales" riêng sẽ tạo hai nơi lưu cùng một khái niệm doanh số → dễ lệch nhau.
    - Dùng schema chuẩn hoá sẵn có giúp dashboard và mô hình dự báo dùng
      chung một nguồn dữ liệu.

Cách chạy:
    python scripts/import_kaggle.py
    python scripts/import_kaggle.py --year 2016 --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Windows console defaults to cp1252, which cannot print the Vietnamese
# characters in this project's folder path ("Dồ án TN"). Force UTF-8 output.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# =============================================================================
# CAU HINH - doc tu bien moi truong, KHONG hardcode mat khau
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "datasets" / "raw" / "train.csv"

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "spoilage_predictor")

# So don hang tao moi trong mot lan INSERT. 5.000 an toan cho canh 2.000 dong.
BATCH_SIZE = 5000


def get_engine():
    """Tao SQLAlchemy engine. Uu tien bien moi truong, fallback sang .env."""
    password = DB_PASSWORD

    if password is None:
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DB_PASSWORD="):
                    password = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if password is None:
        print("LOI: khong tim thay DB_PASSWORD.", file=sys.stderr)
        print("Cach 1: dat bien moi truong  $env:DB_PASSWORD = \"...\"", file=sys.stderr)
        print("Cach 2: tao file .env o thu muc goc voi dong DB_PASSWORD=...", file=sys.stderr)
        sys.exit(1)

    url = (
        f"postgresql+psycopg2://{DB_USER}:{password}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    return create_engine(url, pool_pre_ping=True)


def load_csv(year: int) -> pd.DataFrame:
    """Doc CSV va loc theo nam."""
    if not CSV_PATH.exists():
        print(f"LOI: khong tim thay {CSV_PATH}", file=sys.stderr)
        print("Tai dataset tu Kaggle: xem datasets/README.md", file=sys.stderr)
        sys.exit(1)

    print(f"Doc {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])

    print(f"Tong so dong: {len(df):,}")
    print(f"Khoang ngay goc: {df['date'].min().date()} den {df['date'].max().date()}")

    df_year = df[df["date"].dt.year == year].copy()
    print(f"Loc nam {year}: {len(df_year):,} dong")
    print(f"  - stores: {sorted(df_year['store'].unique().tolist())}")
    print(f"  - items : {df_year['item'].nunique()} gia tri")

    return df_year


# =============================================================================
# BANG GIA MO PHONG - KHONG PHAI GIA THAT
# -----------------------------------------------------------------------------
# Dataset Kaggle chi co cot "sales" (so luong), KHONG co cot gia.
# De dashboard doanh thu co so lieu de chay, ta gan gia uoc luong theo nhom hang.
#
# ⚠️ DAY LA DU LIEU GIA LAP. KHONG duoc trinh bay trong bao cao nhu gia that cua
#    Walmart hay cua mot chuoi ban le Viet Nam nao.
#
# Vì sao khong gán MOT muc gia chung:
#    Rau củ (~20.000/kg) va thịt cá (~80.000/kg) khac nhau 4 lan. Dùng chung
#    một mức giá sẽ làm doanh thu sai lệch so với thực tế ngành.
#
# Luu y: category_id = 2 (Fresh Food) chua ca rau cu/trai cay (id 1-6) VA
#        thit/ca/trung (id 7-10), nen phai tach nho hon theo product_id.
# =============================================================================

DEFAULT_UNIT_PRICE = 25_000.0

# Gia theo category_id
PRICE_BY_CATEGORY = {
    3: 15_000.0,   # Beverages      - nuoc giai khat, tra, ca phe
    4: 25_000.0,   # Snacks         - banh, keo
    8: 35_000.0,   # Dairy          - sua, pho mat
    5: 30_000.0,   # Household      - ve sinh
    6: 30_000.0,   # Personal Care  - cham soc ca nhan
    7: 30_000.0,   # Baby Care      - dung cho tre em
}

# Category 2 (Fresh Food) tach nho theo product_id
PRICE_FRESH_PRODUCE = 20_000.0   # product_id 1-6: rau cu, trai cay
PRICE_FRESH_MEAT = 80_000.0      # product_id 7-10: thit, ca, trung

CATEGORY_FRESH_FOOD = 2
FRESH_PRODUCE_MAX_ID = 6


def resolve_price(product_id: int, category_id: int | None) -> float:
    """Tra ve gia don vi mo phong cho mot san pham."""
    if category_id == CATEGORY_FRESH_FOOD:
        return (
            PRICE_FRESH_PRODUCE
            if product_id <= FRESH_PRODUCE_MAX_ID
            else PRICE_FRESH_MEAT
        )
    return PRICE_BY_CATEGORY.get(category_id, DEFAULT_UNIT_PRICE)


def load_price_map(engine) -> dict:
    """Doc product_id -> category_id tu database de gan gia."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT product_id, category_id FROM products")
        ).all()

    price_map = {pid: resolve_price(pid, cid) for pid, cid in rows}

    print(f"\nBang gia mo phong ({len(price_map)} san pham):")
    grouped = {}
    for pid, price in price_map.items():
        grouped.setdefault(price, []).append(pid)
    for price in sorted(grouped):
        ids = sorted(grouped[price])
        print(f"  {price:>10,.0f} VND  -> {len(ids)} san pham (id {ids[0]}-{ids[-1]})")
    print("  ⚠  GIA LAP - dung de demo dashboard doanh thu, khong phai gia that.")

    return price_map


def check_prerequisites(engine) -> None:
    """Kiem tra products/stores da seed du chua truoc khi insert."""
    with engine.connect() as conn:
        n_products = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
        n_stores = conn.execute(text("SELECT COUNT(*) FROM stores")).scalar()
        max_p = conn.execute(text("SELECT MAX(product_id) FROM products")).scalar()
        max_s = conn.execute(text("SELECT MAX(store_id) FROM stores")).scalar()

    print("\nKiem tra du lieu dan duong:")
    print(f"  products: {n_products} (max id = {max_p})")
    print(f"  stores  : {n_stores} (max id = {max_s})")

    if n_products == 0 or n_stores == 0:
        print(
            "\nLOI: bang products hoac stores rong. Chay seed truoc:\n"
            "  psql -U postgres -d spoilage_predictor -f database/02-seed/seed-data.sql",
            file=sys.stderr,
        )
        sys.exit(1)


def build_rows(df_year: pd.DataFrame, price_map: dict):
    """
    Chuyen dataframe thanh 2 danh sach: orders va order_items.

   orders  : 1 dong cho moi cap (date, store)
    order_items : 1 dong cho moi cap (date, store, item)
    """
    orders = []
    order_items = []

    counter = 0
    # Gom theo (date, store) de moi don chi co 1 store, tranh lap don
    for (day, store_id), group in df_year.groupby(["date", "store"], sort=True):
        counter += 1
        order_code = f"ORD-{day.year}-{counter:06d}"

        order_id = None  # gan sau khi insert orders

        orders.append(
            {
                "_tmp_key": counter,
                "order_code": order_code,
                "store_id": int(store_id),
                "order_type": "sale",
                "order_date": pd.Timestamp(day).to_pydatetime(),
                "status": "completed",
                "total_amount": 0,  # cap nhat sau
                "total_quantity": float(group["sales"].sum()),
            }
        )

        for _, row in group.iterrows():
            qty = float(row["sales"])
            product_id = int(row["item"])

            # sales = 0 nghia la khong ban duoc. Van giu de phuc hoi
            # du lieu chay (censored demand) va de trung binh nhu that.
            price = price_map.get(product_id, DEFAULT_UNIT_PRICE)

            order_items.append(
                {
                    "_tmp_key": counter,
                    "product_id": product_id,
                    "quantity": qty,
                    "unit_price": price,
                    "discount_percent": 0,
                }
            )

    return orders, order_items


def import_data(
    engine, df_year: pd.DataFrame, price_map: dict, override_price: float | None, dry_run: bool
) -> None:
    """Ghi vao database theo batch."""
    if override_price is not None:
        print(f"\nGhi de gia: gan {override_price:,.0f} VND cho MOI san pham.")
        price_map = {pid: override_price for pid in price_map}

    orders, order_items = build_rows(df_year, price_map)

    print(f"\nSe tao {len(orders):,} don va {len(order_items):,} dong chi tiet.")

    if dry_run:
        print("\n--- DRY RUN: khong ghi vao database ---")
        print("Vi du don hang dau tien:")
        for k, v in orders[0].items():
            print(f"    {k:15} = {v}")
        print("Vi du dong chi tiet dau tien:")
        for k, v in order_items[0].items():
            print(f"    {k:15} = {v}")
        print(f"\nTong don   : {len(orders):,}")
        print(f"Tong items : {len(order_items):,}")
        return

    year = int(df_year["date"].dt.year.iloc[0])

    with engine.begin() as conn:
        # Xoa don cu de chay lai nhieu lan khong bi trung order_code
        print("\nXoa don cu ...")
        conn.execute(text("TRUNCATE order_items, orders RESTART IDENTITY CASCADE"))

        print("Insert bang orders ...")
        conn.execute(
            text(
                """
                INSERT INTO orders
                    (order_code, store_id, order_type, order_date,
                     total_amount, total_quantity, status)
                VALUES
                    (:order_code, :store_id, :order_type, :order_date,
                     0, :total_quantity, :status)
                """
            ),
            orders,
        )
        print(f"  -> {len(orders):,} don da tao")

        # SQLAlchemy 2.x khong ho tro RETURNING khi insert nhieu dong.
        # order_code la UNIQUE nen tao ban do order_code -> order_id
        # bang cach doc lai cac don vua tao trong nam nay.
        print("Lay danh sach order_id ...")
        existing = conn.execute(
            text(
                """
                SELECT order_code, order_id
                FROM orders
                WHERE order_date >= :start AND order_date < :end
                """
            ),
            {"start": f"{year}-01-01", "end": f"{year + 1}-01-01"},
        ).all()

        code_to_id = {code: oid for code, oid in existing}
        print(f"  -> {len(code_to_id):,} ma don da doi chieu")

        missing = [o["order_code"] for o in orders if o["order_code"] not in code_to_id]
        if missing:
            print(
                f"LOI: {len(missing)} don khong doi chieu duoc, vi du {missing[:3]}",
                file=sys.stderr,
            )
            sys.exit(1)

        key_to_code = {o["_tmp_key"]: o["order_code"] for o in orders}
        for item in order_items:
            item["order_id"] = code_to_id[key_to_code[item.pop("_tmp_key")]]

        print("Insert bang order_items ...")
        total = 0
        for i in range(0, len(order_items), BATCH_SIZE):
            chunk = order_items[i : i + BATCH_SIZE]
            conn.execute(
                text(
                    """
                    INSERT INTO order_items
                        (order_id, product_id, quantity, unit_price, discount_percent)
                    VALUES
                        (:order_id, :product_id, :quantity, :unit_price, :discount_percent)
                    """
                ),
                chunk,
            )
            total += len(chunk)
            print(f"  -> {total:,}/{len(order_items):,}")

        # Cap nhat total_amount tu tong line_total
        print("Cap nhat orders.total_amount ...")
        conn.execute(
            text(
                """
                UPDATE orders o
                SET total_amount = sub.total
                FROM (
                    SELECT order_id, SUM(line_total) AS total
                    FROM order_items
                    GROUP BY order_id
                ) sub
                WHERE o.order_id = sub.order_id
                """
            )
        )

    print("\nImport thanh cong.")


def verify(engine, year: int) -> None:
    """Kiem tra ket qua import."""
    with engine.connect() as conn:
        n_orders = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        n_items = conn.execute(text("SELECT COUNT(*) FROM order_items")).scalar()

        rng = conn.execute(
            text(
                "SELECT MIN(order_date)::date, MAX(order_date)::date FROM orders"
            )
        ).first()

        print("\n=== KIEM TRA KET QUA ===")
        print(f"orders      : {n_orders:,}")
        print(f"order_items : {n_items:,}")
        print(f"Khoang ngay: {rng[0]} den {rng[1]}")

        money = conn.execute(
            text(
                """
                SELECT MIN(oi.unit_price),
                       MAX(oi.unit_price),
                       SUM(oi.line_total)
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.order_id
                WHERE o.order_date >= :start AND o.order_date < :end
                """
            ),
            {"start": f"{year}-01-01", "end": f"{year + 1}-01-01"},
        ).first()

        # ⚠ KHONG duoc tinh SUM(total_amount) tren join voi order_items:
        #   moi don co ~50 dong chi tiet nen tong se bi nhan 50 lan.
        #   Toi doan duoi day chi lay tong line_total cua don.
        total_orders = conn.execute(
            text(
                """
                SELECT SUM(total_amount) FROM orders
                WHERE order_date >= :start AND order_date < :end
                """
            ),
            {"start": f"{year}-01-01", "end": f"{year + 1}-01-01"},
        ).scalar()

        if money[2] is not None and money[2] != 0:
            print(f"Doanh thu   : {money[2]:,.0f} VND (tong line_total)")
        else:
            print("Doanh thu   : 0 (khong co du lieu)")
        print(f"  doi chieu : tong orders.total_amount = {total_orders:,.0f} VND")
        print(f"Bien gia    : {money[0]:,.0f} den {money[1]:,.0f} VND (gia MO PHONG)")

        print("\n--- 5 dong mau ---")
        sample = conn.execute(
            text(
                """
                SELECT o.order_code, o.order_date, s.store_code,
                       p.product_code, oi.quantity, oi.unit_price, oi.line_total
                FROM orders o
                JOIN stores s        ON s.store_id   = o.store_id
                JOIN order_items oi  ON oi.order_id  = o.order_id
                JOIN products p      ON p.product_id = oi.product_id
                ORDER BY o.order_id, oi.order_item_id
                LIMIT 5
                """
            )
        )
        for row in sample:
            print(
                f"  {row[0]} | {row[1].date()} | {row[2]} | {row[3]} "
                f"| qty={row[4]} | price={row[5]} | total={row[6]}"
            )

        print("\n--- Do phu (ky vong: 50 san pham, 10 cua hang) ---")
        cover = conn.execute(
            text(
                """
                SELECT COUNT(DISTINCT oi.product_id) AS products,
                       COUNT(DISTINCT o.store_id)    AS stores,
                       COUNT(DISTINCT o.order_date::date) AS days
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.order_id
                """
            )
        ).first()
        print(f"  san pham: {cover[0]} | cua hang: {cover[1]} | so ngay: {cover[2]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Kaggle dataset vao PostgreSQL")
    parser.add_argument("--year", type=int, default=2017, help="Nam can import (mac dinh 2017)")
    parser.add_argument(
        "--unit-price",
        type=float,
        default=None,
        help=(
            "Ghi de gia don vi cho MOI san pham. Mac dinh: gia mo phong theo "
            "nhom hang (xem PRICE_BY_CATEGORY trong file nay)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chi xem ke qua, khong ghi vao database",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("IMPORT DU LIEU KAGGLE VAO POSTGRESQL")
    print("=" * 60)

    engine = get_engine()
    check_prerequisites(engine)
    price_map = load_price_map(engine)

    df_year = load_csv(args.year)

    if df_year.empty:
        print(f"\nLOI: khong co du lieu nao cho nam {args.year}.", file=sys.stderr)
        sys.exit(1)

    import_data(engine, df_year, price_map, args.unit_price, args.dry_run)

    if not args.dry_run:
        verify(engine, args.year)

    engine.dispose()


if __name__ == "__main__":
    main()
