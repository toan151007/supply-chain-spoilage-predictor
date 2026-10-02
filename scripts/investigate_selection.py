"""
Dieu tra xem he so bien dong mua vu co that su phan biet duoc san pham khong.

Ket qua scripts/select_products.py cho thay ca 50 san pham deu co he so
trong khoang 1.92-1.95. Dieu nay nghi la tieu chi khong dung de chon san pham.
Script nay tim hieu xem nen dung tieu chi nao.
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
        SELECT product_id, sale_date, EXTRACT(MONTH FROM sale_date)::INT AS m,
               EXTRACT(ISODOW FROM sale_date)::INT AS dow,
               quantity_sold
        FROM v_daily_sales
        WHERE sale_date >= '2017-01-01' AND sale_date < '2018-01-01'
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    print("=" * 90)
    print("DIEU TRA: TIEU CHI CHON SAN PHAM NAO HIEU QUA?")
    print("=" * 90)

    # --- 1. He so bien dong theo THANG tren toan he thong ---
    print("\n[1] Doanh so trung binh theo THANG (tat ca 50 san pham, tat ca 10 cua hang)")
    monthly = df.groupby("m")["quantity_sold"].sum()
    for m, v in monthly.items():
        bar = "#" * int(60 * v / monthly.max())
        print(f"  thang {m:>2}: {v:>12,.0f}  {bar}")
    print(f"  -> Ty le cao nhat / thap nhat = {monthly.max() / monthly.min():.2f}")
    print("  -> Thang dinh cao nhat la thang 7 (thang 7 moi), thap nhat la thang 1")

    # --- 2. He so bien dong theo THANG tren tung san pham ---
    print("\n[2] He so bien dong (max thang / min thang) - phan bo tren 50 san pham")
    per_product = df.groupby(["product_id", "m"])["quantity_sold"].sum().reset_index()
    ratios = []
    for pid, g in per_product.groupby("product_id"):
        s = g.set_index("m")["quantity_sold"]
        s = s[s > 0]
        ratios.append({"product_id": pid, "ratio": s.max() / s.min() if len(s) else None})
    r = pd.DataFrame(ratios).dropna()
    print(f"  nho nhat : {r['ratio'].min():.3f}")
    print(f"  trung binh: {r['ratio'].mean():.3f}")
    print(f"  lon nhat : {r['ratio'].max():.3f}")
    print(f"  do rong  : {r['ratio'].max() - r['ratio'].min():.3f}")
    print("  -> Do rong qua nho: KHONG phan biet duoc san pham")

    # --- 3. He so bien dong theo NGAY TRONG TUAN ---
    print("\n[3] Doanh so trung binh theo NGAY TRONG TUAN")
    dow = df.groupby("dow")["quantity_sold"].sum()
    labels = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
    for d, v in dow.items():
        bar = "#" * int(50 * v / dow.max())
        print(f"  {labels[int(d)]} (dow={int(d)}): {v:>12,.0f}  {bar}")
    print(f"  -> Ty le cao nhat / thap nhat = {dow.max() / dow.min():.2f}")
    print("  -> He so ngay trong tuan MANH HON he so thang")

    # --- 4. He so bien dong theo TUAN (weekly) tren tung san pham ---
    print("\n[4] He so bien dong theo TUAN (max/min) - phan bo tren 50 san pham")
    df2 = df.copy()
    # sale_date tu PostgreSQL ra ve dang object, phai chuyen ve datetime truoc
    df2["sale_date"] = pd.to_datetime(df2["sale_date"])
    df2["week"] = df2["sale_date"].dt.isocalendar().week.astype(int)
    weekly = df2.groupby(["product_id", "week"])["quantity_sold"].sum().reset_index()
    wratios = []
    for pid, g in weekly.groupby("product_id"):
        s = g.set_index("week")["quantity_sold"]
        s = s[s > 0]
        wratios.append({"product_id": pid, "ratio": s.max() / s.min() if len(s) else None})
    w = pd.DataFrame(wratios).dropna()
    print(f"  nho nhat : {w['ratio'].min():.3f}")
    print(f"  trung binh: {w['ratio'].mean():.3f}")
    print(f"  lon nhat : {w['ratio'].max():.3f}")
    print(f"  do rong  : {w['ratio'].max() - w['ratio'].min():.3f}")

    # --- 5. He so bien dong cua TONG toan he thong theo tuan ---
    print("\n[5] He so bien dong theo tuan tren TOAN HE THONG")
    sw = df2.groupby("week")["quantity_sold"].sum()
    print(f"  max/min = {sw.max() / sw.min():.2f}")

    # --- 6. Phan bo mua vu theo nam (co Nam Day la khong?) ---
    print("\n[6] Kiem tra ngay le Tet trong du lieu")
    tet = df[(df["sale_date"].astype(str).str.startswith("2017-01")) ]
    print(f"  Tong doanh so thang 1/2017: {tet['quantity_sold'].sum():,.0f}")
    print(f"  Ngay ban co ban nhat: {df.loc[df['quantity_sold'].idxmin(), 'sale_date'].date()}")
    print(f"  Ngay ban co ban cao nhat: {df.loc[df['quantity_sold'].idxmax(), 'sale_date'].date()}")

    engine.dispose()


if __name__ == "__main__":
    main()
