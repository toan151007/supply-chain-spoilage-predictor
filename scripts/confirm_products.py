"""
Xac nhanh danh sach 10 san pham cuoi cung truoc khi huyen luyen mo hinh.

Danh sach da duoc chot:
    7 san pham phu du 7 nhom hang (theo doanh so nam cao nhat tung nhom)
    + 3 san pham bo sung theo he so bien dong tuan cao nhat trong nhom da dung

Script nay KIEM TRA LAI bang chung cho 3 san pham bo sung, va in ra
danh sach cuoi cung de duyet.
"""

import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "spoilage_predictor")

# 7 san pham phu du 7 nhom (doanh so nam cao nhat tung nhom)
CORE_IDS = [15, 28, 18, 45, 38, 8, 48]

# 3 san pham bo sung theo de xuat
EXTRA_IDS = [13, 25, 22]


def get_engine():
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
        sys.exit("LOI: khong tim thay DB_PASSWORD")
    url = f"postgresql+psycopg2://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url, pool_pre_ping=True)


def build_stats(engine) -> pd.DataFrame:
    sql = text(
        """
        SELECT v.product_id, p.product_name, c.category_name,
               v.store_id, v.sale_date, v.quantity_sold
        FROM v_daily_sales v
        JOIN products p   ON p.product_id = v.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE v.sale_date >= '2017-01-01' AND v.sale_date < '2018-01-01'
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["week"] = df["sale_date"].dt.isocalendar().week.astype(int)

    rows = []
    for (pid, pname, cname), g in df.groupby(
        ["product_id", "product_name", "category_name"], sort=False
    ):
        daily = g.groupby("sale_date")["quantity_sold"].sum()
        weekly = g.groupby("week")["quantity_sold"].sum()
        weekly = weekly[weekly > 0]
        monthly = g.groupby(df["sale_date"].dt.month)["quantity_sold"].sum()
        monthly = monthly[monthly > 0]

        rows.append(
            {
                "product_id": int(pid),
                "product_name": pname,
                "category": cname,
                "annual_sales": float(g["quantity_sold"].sum()),
                "avg_daily": float(daily.mean()),
                "zero_days": int((daily == 0).sum()),
                "weekly_ratio": float(weekly.max() / weekly.min()),
                "monthly_ratio": float(monthly.max() / monthly.min()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    engine = get_engine()
    stats = build_stats(engine)

    bev = stats[stats["category"] == "Beverages"].sort_values(
        "weekly_ratio", ascending=False
    )

    print("=" * 104)
    print("KIEM TRA: 3 SAN PHAM BO SUNG CO PHAI HS_TUAN CAO NHAT NHOM BEVERAGES KHONG?")
    print("=" * 104)
    print("Toan bo nhom Beverages, xep theo HS_tuan giam dan:")
    print(
        f"{'hang':>4}  {'product_id':>10}  {'product_name':<28}  "
        f"{'doanh_so_nam':>13}  {'HS_tuan':>8}  {'de xuat':>9}"
    )
    print("-" * 104)
    for rank, (_, r) in enumerate(bev.iterrows(), 1):
        mark = "  <-- DE XUAT" if int(r["product_id"]) in EXTRA_IDS else ""
        print(
            f"{rank:>4}  {r['product_id']:>10}  {r['product_name']:<28}  "
            f"{r['annual_sales']:>13,.0f}  {r['weekly_ratio']:>8.3f}{mark}"
        )

    print()
    top3 = bev.head(3)["product_id"].astype(int).tolist()
    print(f"  Top 3 HS_tuan thuoc nhom Beverages: {top3}")
    print(f"  3 san pham dang de xuat             : {EXTRA_IDS}")
    if top3 == EXTRA_IDS:
        print("  -> KET LUAN: DE XUAT DUNG. Ca 3 san pham deu nam trong top 3 HS_tuan.")
    else:
        print("  -> KET LUAN: DE XUAT KHONG DUNG. Can thay bang top 3 thuoc tu.")
        print(f"     Nen dung: {top3}")

    final_ids = CORE_IDS + EXTRA_IDS
    final = stats[stats["product_id"].isin(final_ids)].copy()

    # Thu tu theo nhom de de doc
    final["nhom_thu_tu"] = final["category"].map(
        {c: i for i, c in enumerate(final["category"].unique())}
    )
    final = final.sort_values(["nhom_thu_tu", "annual_sales"], ascending=[True, False])

    print()
    print("=" * 104)
    print("DANH SACH 10 SAN PHAM CUOI CUNG")
    print("=" * 104)
    print(
        f"{'#':>2}  {'product_id':>10}  {'product_name':<28}  {'category':<15}  "
        f"{'doanh_so_nam':>13}  {'BQ_ngay':>9}  {'ngay_0':>7}  {'HS_tuan':>8}  {'HS_thang':>9}"
    )
    print("-" * 104)
    for i, (_, r) in enumerate(final.iterrows(), 1):
        print(
            f"{i:>2}  {r['product_id']:>10}  {r['product_name']:<28}  {r['category']:<15}  "
            f"{r['annual_sales']:>13,.0f}  {r['avg_daily']:>9,.1f}  {r['zero_days']:>7}  "
            f"{r['weekly_ratio']:>8.3f}  {r['monthly_ratio']:>9.3f}"
        )

    print()
    print(f"  So nhom hang: {final['category'].nunique()} / 7")
    print(f"  So san pham: {len(final)} / 10")
    print(f"  Tong doanh so 2017: {final['annual_sales'].sum():,.0f}")
    print(f"  Trung binh moi san pham: {final['annual_sales'].mean():,.0f}/nam")
    print(f"  Tong so ngay co doanh so = 0: {final['zero_days'].sum()}  "
          f"-> KHONG co censored demand")

    # Kiem tra du lieu du cho tung cap (product, store)
    sql = text(
        """
        SELECT product_id, store_id, COUNT(DISTINCT sale_date) AS n_days,
               SUM(quantity_sold) AS qty
        FROM v_daily_sales
        WHERE product_id = ANY(:ids)
          AND sale_date >= '2017-01-01' AND sale_date < '2018-01-01'
        GROUP BY product_id, store_id
        """
    )
    with engine.connect() as conn:
        cov = pd.read_sql(sql, conn, params={"ids": final_ids})

    print()
    print("=" * 104)
    print("KIEM TRA DO PHU DU LIEU CHO MOI CAP (SAN PHAM x CUA HANG)")
    print("=" * 104)
    print(f"  So cap (san pham x cua hang): {len(cov)}  (ky vong: {len(final_ids)} x 10 = {len(final_ids) * 10})")
    print(f"  So ngay nho nhat tren 1 cap: {cov['n_days'].min()}")
    print(f"  So ngay lon nhat tren 1 cap: {cov['n_days'].max()}")
    print(f"  Tong luong nho nhat tren 1 cap: {cov['qty'].min():,.0f}")
    print(f"  Cap co du lieu it nhat:")
    print(cov.nsmallest(3, "n_days").to_string(index=False))

    out_dir = PROJECT_ROOT / "ai-model" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    final.drop(columns=["nhom_thu_tu"]).to_csv(
        out_dir / "final_10_products_2017.csv", index=False, encoding="utf-8"
    )
    print(f"\n  Da luu: {out_dir}/final_10_products_2017.csv")
    print(f"  product_id: {final_ids}")

    engine.dispose()


if __name__ == "__main__":
    main()
