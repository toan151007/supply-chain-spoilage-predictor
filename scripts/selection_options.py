"""
Phuong an thay the: chon san pham theo DOANH SO NAM, co dam bao da dang nhom hang.

Ly do can phuong an nay:
    Dieu tra cho thay he so bien dong mua vu (theo thang) khong phan biet duoc
    san pham nao: ca 50 san pham deu nam trong khoang 1.85-1.95 (do rong 0.098).
    Tieu chi "mua vu manh nhat" ho khong phan biet duoc gi.

    Ly do: mua vu cua Walmart chay theo thoi tiet va ngay le, ap dung giong nhe
    len moi mat hang, nen moi san pham deu bi anh huong nhu nhau.
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


def main() -> None:
    engine = get_engine()

    sql = text(
        """
        SELECT v.product_id, p.product_name, c.category_name,
               v.sale_date, v.quantity_sold
        FROM v_daily_sales v
        JOIN products p   ON p.product_id = v.product_id
        JOIN categories c ON c.category_id = p.category_id
        WHERE v.sale_date >= '2017-01-01' AND v.sale_date < '2018-01-01'
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    df["sale_date"] = pd.to_datetime(df["sale_date"])

    # He so bien dong theo tuan
    df["week"] = df["sale_date"].dt.isocalendar().week.astype(int)

    rows = []
    for (pid, pname, cname), g in df.groupby(
        ["product_id", "product_name", "category_name"], sort=False
    ):
        weekly = g.groupby("week")["quantity_sold"].sum()
        weekly = weekly[weekly > 0]
        rows.append(
            {
                "product_id": int(pid),
                "product_name": pname,
                "category": cname,
                "annual_sales": float(g["quantity_sold"].sum()),
                "avg_daily": float(
                    g.groupby("sale_date")["quantity_sold"].sum().mean()
                ),
                "zero_days": int((g.groupby("sale_date")["quantity_sold"].sum() == 0).sum()),
                "weekly_ratio": float(weekly.max() / weekly.min()) if len(weekly) else None,
            }
        )

    res = pd.DataFrame(rows).sort_values("annual_sales", ascending=False).reset_index(drop=True)

    print("=" * 108)
    print("PHUONG AN A: TOP 10 THEO DOANH SO NAM")
    print("=" * 108)
    print(
        f"{'#':>2}  {'product_id':>10}  {'product_name':<26}  {'category':<14}  "
        f"{'doanh_so_nam':>13}  {'BQ_ngay':>9}  {'ngay_bang_0':>10}  {'HS_tuan':>8}"
    )
    print("-" * 108)
    for i, (_, r) in enumerate(res.head(10).iterrows(), 1):
        print(
            f"{i:>2}  {r['product_id']:>10}  {r['product_name']:<26}  {r['category']:<14}  "
            f"{r['annual_sales']:>13,.0f}  {r['avg_daily']:>9,.1f}  {r['zero_days']:>10}  "
            f"{r['weekly_ratio']:>8.2f}"
        )

    print()
    print("=" * 108)
    print("PHUONG GAN B: DA DANG NHOM HANG - muon nhieu nhom, lay doanh so cao nhat tung nhom")
    print("=" * 108)
    picked = []
    for cname, g in res.groupby("category", sort=False):
        picked.append(g.iloc[0])
    picked = sorted(picked, key=lambda r: r["annual_sales"], reverse=True)
    print(
        f"{'#':>2}  {'product_id':>10}  {'product_name':<26}  {'category':<14}  "
        f"{'doanh_so_nam':>13}  {'BQ_ngay':>9}  {'ngay_bang_0':>10}  {'HS_tuan':>8}"
    )
    print("-" * 108)
    for i, r in enumerate(picked, 1):
        print(
            f"{i:>2}  {r['product_id']:>10}  {r['product_name']:<26}  {r['category']:<14}  "
            f"{r['annual_sales']:>13,.0f}  {r['avg_daily']:>9,.1f}  {r['zero_days']:>10}  "
            f"{r['weekly_ratio']:>8.2f}"
        )
    print(f"\n  So nhom san pham: {len(picked)}")
    print(f"  product_id: {[int(r['product_id']) for r in picked]}")

    print()
    print("=" * 108)
    print("SO SANH")
    print("=" * 108)
    a_ids = res.head(10)["product_id"].tolist()
    b_ids = [int(r["product_id"]) for r in picked]
    print(f"  A (top doanh so): {a_ids}")
    print(f"  B (da dang nhom) : {b_ids}")
    print(f"  A trung binh doanh so: {res.head(10)['annual_sales'].mean():,.0f}")
    print(f"  B trung binh doanh so: {res[res['product_id'].isin(b_ids)]['annual_sales'].mean():,.0f}")

    # Luu ca hai phuong an
    out_dir = PROJECT_ROOT / "ai-model" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    res.head(10).to_csv(out_dir / "selected_by_volume_2017.csv", index=False, encoding="utf-8")
    res[res["product_id"].isin(b_ids)].to_csv(
        out_dir / "selected_by_category_2017.csv", index=False, encoding="utf-8"
    )
    print(f"\n  Da luu: {out_dir}/selected_by_volume_2017.csv")
    print(f"  Da luu: {out_dir}/selected_by_category_2017.csv")

    engine.dispose()


if __name__ == "__main__":
    main()
