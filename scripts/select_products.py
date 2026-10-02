"""
Chon 10 san pham tieu bieu de huyen luyen mo hinh du bao.

Tieu chi (theo quyet dinh 02/10/2026):
    1. He so bien dong mua vu = max(doanh so thang) / min(doanh so thang)
       tinh tren doanh so nam 2017
    2. Loai bo san pham co tong doanh so nam < MIN_ANNUAL_SALES
    3. Sap xep theo he so bien dong giam dan
    4. Chon top 10

Vi sao can loai bo san pham doanh so thap:
    Mot san pham ban duoc vai don thang se co he so bien dong rat cao
    vi mau so nho, nhung la ngau nhien chu khong phai mua vu that.
    Nhipp vao top 10 chi do ngau nhien se lam nhieu mo hinh du bao sai.

Cach chay:
    python scripts/select_products.py
    python scripts/select_products.py --top 15 --year 2017
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Console Windows dung cp1252, khong in duoc dau tieng Viet
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "spoilage_predictor")

# San pham ban duoc it hon ngan san pham trong ca nam 2017 se bi loai
MIN_ANNUAL_SALES = 1000


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
        print("Dat bien moi truong:  $env:DB_PASSWORD = \"...\"", file=sys.stderr)
        sys.exit(1)

    url = (
        f"postgresql+psycopg2://{DB_USER}:{password}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    return create_engine(url, pool_pre_ping=True)


def load_sales(engine, year: int) -> pd.DataFrame:
    """
    Doc doanh so tu view v_daily_sales - day la nguon du lieu duy nhat
    cho mo hinh du bao (khong dung inventory_transactions).
    """
    sql = text(
        """
        SELECT
            v.product_id,
            p.product_name,
            c.category_name,
            v.store_id,
            v.sale_date,
            EXTRACT(MONTH FROM v.sale_date)::INT AS month_of_year,
            v.quantity_sold
        FROM v_daily_sales v
        JOIN products p   ON p.product_id = v.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE v.sale_date >= :start AND v.sale_date < :end
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(
            sql,
            conn,
            params={"start": f"{year}-01-01", "end": f"{year + 1}-01-01"},
        )
    return df


def score_products(df: pd.DataFrame, year: int, min_annual: int) -> pd.DataFrame:
    """
    Tinh chi so bien dong mua vu cho tung san pham.

    He so = max(doanh so thang) / min(doanh so thang)
    - He so = 1.0  : doanh so deu, khong co mua vu
    - He so > 2.0  : mua vu manh
    """
    monthly = (
        df.groupby(["product_id", "product_name", "category_name", "month_of_year"])
        ["quantity_sold"]
        .sum()
        .reset_index()
    )

    rows = []
    for (pid, pname, cname), group in monthly.groupby(
        ["product_id", "product_name", "category_name"], sort=False
    ):
        by_month = group.set_index("month_of_year")["quantity_sold"]
        # Bo cac thang khong ban duoc gi de tranh bien min = 0
        sold = by_month[by_month > 0]

        annual = float(by_month.sum())
        n_months = len(by_month)

        if len(sold) < 6 or annual <= 0:
            # Qua it thong thuc te: khong the uoc luong duoc mua vu
            seasonal_ratio = float("nan")
            peak_month = int(by_month.idxmax())
            low_month = int(by_month.idxmin())
            peak_qty = float(by_month.max())
            low_qty = float(by_month.min())
        else:
            seasonal_ratio = float(sold.max() / sold.min())
            peak_month = int(by_month.idxmax())
            low_month = int(by_month.idxmin())
            peak_qty = float(by_month.max())
            low_qty = float(by_month.min())

        rows.append(
            {
                "product_id": int(pid),
                "product_name": pname,
                "category": cname,
                "annual_sales": annual,
                "months_with_data": n_months,
                "seasonal_ratio": seasonal_ratio,
                "peak_month": peak_month,
                "peak_qty": peak_qty,
                "low_month": low_month,
                "low_qty": low_qty,
            }
        )

    result = pd.DataFrame(rows)

    # Loc san pham doanh so thap va khong uoc luong duoc mua vu
    eligible = result[
        (result["annual_sales"] >= min_annual) & result["seasonal_ratio"].notna()
    ].copy()

    return eligible.sort_values("seasonal_ratio", ascending=False).reset_index(drop=True), result


def main() -> None:
    parser = argparse.ArgumentParser(description="Chon san pham tieu bieu de du bao")
    parser.add_argument("--year", type=int, default=2017, help="Nam du lieu (mac dinh 2017)")
    parser.add_argument("--top", type=int, default=10, help="So san pham can chon")
    parser.add_argument(
        "--min-annual",
        type=int,
        default=MIN_ANNUAL_SALES,
        help="Nguong tong doanh so nam de khong bi loai (mac dinh 1000)",
    )
    args = parser.parse_args()

    print("=" * 100)
    print("CHON SAN PHAM TIEU BIEU DE DU BAO")
    print("=" * 100)

    engine = get_engine()
    df = load_sales(engine, args.year)
    print(f"Tong so dong du lieu {args.year}: {len(df):,}")

    eligible, all_scores = score_products(df, args.year, args.min_annual)

    print(f"Tong so san pham: {len(all_scores)}")
    print(f"Sau khi loai doanh so < {args.min_annual} va khong duoc uoc luong: {len(eligible)}")

    top = eligible.head(args.top)

    print()
    print("=" * 100)
    print(f"TOP {len(top)} SAN PHAM TIEU BIEU")
    print("=" * 100)
    header = (
        f"{'#':>2}  {'product_id':>10}  {'product_name':<26}  "
        f"{'category':<14}  {'doanh_so_nam':>13}  {'HS_mua_vu':>10}  "
        f"{'thang_cao':>9}  {'cao_nhat':>9}  {'thang_thap':>10}  {'thap_nhat':>9}"
    )
    print(header)
    print("-" * 100)

    for i, (_, row) in enumerate(top.iterrows(), start=1):
        print(
            f"{i:>2}  {row['product_id']:>10}  {row['product_name']:<26}  "
            f"{row['category']:<14}  {row['annual_sales']:>13,.0f}  "
            f"{row['seasonal_ratio']:>10.2f}  {row['peak_month']:>9}  "
            f"{row['peak_qty']:>9,.0f}  {row['low_month']:>10}  {row['low_qty']:>9,.0f}"
        )

    # Luu ra file de khong phai chay lai
    out_dir = PROJECT_ROOT / "ai-model" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"selected_products_{args.year}.csv"
    top.to_csv(out_path, index=False, encoding="utf-8")
    print(f"\nDa luu danh sach: {out_path}")

    # In them: phan bo so san pham theo he so bien dong
    print()
    print("=" * 100)
    print("PHAN BO HE SO BIEN DONG MUA VU (san pham du dieu kien)")
    print("=" * 100)
    bands = [
        ("1.0 - 1.5 (it bien dong)", 1.0, 1.5),
        ("1.5 - 2.0 (vua)", 1.5, 2.0),
        ("2.0 - 3.0 (mua vu manh)", 2.0, 3.0),
        ("3.0 - tren (rat manh)", 3.0, 999.0),
    ]
    for label, lo, hi in bands:
        n = len(eligible[(eligible["seasonal_ratio"] >= lo) & (eligible["seasonal_ratio"] < hi)])
        print(f"  {label:<30} {n:>3} san pham")

    top_ids = ", ".join(str(int(x)) for x in top["product_id"].tolist())
    print(f"\nDanh sach product_id: [{top_ids}]")

    engine.dispose()


if __name__ == "__main__":
    main()
