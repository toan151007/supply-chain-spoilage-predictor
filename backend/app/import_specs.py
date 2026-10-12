"""
Column definitions for the import templates and validation rules.

Kept apart from `import_router.py` so the column contract for each resource
lives in exactly one place: the router enforces what this module declares,
and the template endpoint emits the same headers. They cannot drift.
"""

from dataclasses import dataclass, field

# Column order in the generated template. Optional columns come last so a
# user filling the template by hand only has to look at the first few.
PRODUCTS_COLUMNS = [
    "product_code",
    "product_name",
    "category_id",
    "unit",
    "unit_cost",
    "selling_price",
    "shelf_life_days",
    "min_stock",
    "max_stock",
    "supplier",
]

INVENTORY_COLUMNS = [
    "product_id",
    "store_id",
    "quantity",
    "expiry_date",
    "batch_code",
    "received_date",
]

SALES_COLUMNS = [
    "order_code",
    "order_date",
    "store_id",
    "product_id",
    "quantity",
    "unit_price",
    "discount_percent",
    "order_type",
    "status",
    "payment_method",
    "customer_name",
]


@dataclass(frozen=True)
class ImportSpec:
    """
    The contract for one importable resource.

    `required` is what a missing or blank value fails on. Optional columns
    fall back to the listed default, so a minimal file still imports.
    """

    resource_type: str
    columns: list[str]
    required: list[str]
    description: str
    filename_stem: str = ""
    sample_rows: list[dict] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return f"{self.filename_stem or self.resource_type}_template.csv"


IMPORT_SPECS: dict[str, ImportSpec] = {
    "products": ImportSpec(
        resource_type="products",
        columns=PRODUCTS_COLUMNS,
        required=[
            "product_code",
            "product_name",
            "category_id",
            "unit",
            "unit_cost",
            "selling_price",
            "shelf_life_days",
        ],
        description=(
            "Danh sach san pham moi. product_code phai duy nhat toan he thong. "
            "category_id phai ton tai trong bang categories."
        ),
        sample_rows=[
            {
                "product_code": "SP9001",
                "product_name": "San pham mau 1",
                "category_id": 1,
                "unit": "hop",
                "unit_cost": 10000,
                "selling_price": 15000,
                "shelf_life_days": 180,
                "min_stock": 50,
                "max_stock": 300,
                "supplier": "Nha cung cap A",
            }
        ],
    ),
    "inventory": ImportSpec(
        resource_type="inventory",
        columns=INVENTORY_COLUMNS,
        required=["product_id", "store_id", "quantity", "expiry_date"],
        description=(
            "Lo hàng nhập kho. (store_id, product_id, expiry_date) phai duy "
            "nhat trong he thong. expiry_date duong dinh dang YYYY-MM-DD."
        ),
        sample_rows=[
            {
                "product_id": 1,
                "store_id": 1,
                "quantity": 120,
                "expiry_date": "2027-06-30",
                "batch_code": "BATCH-001",
                "received_date": "2026-10-01",
            }
        ],
    ),
    "sales": ImportSpec(
        resource_type="sales",
        columns=SALES_COLUMNS,
        required=["order_date", "store_id", "product_id", "quantity", "unit_price"],
        description=(
            "D lieu ban hang. Cac dong cung order_code se duoc gop thanh MOT don "
            "hang; dong khong co order_code se tao don rieng. line_total do DB "
            "tu tinh, khong cot san pham na."
        ),
        sample_rows=[
            {
                "order_code": "IMP-DEMO-001",
                "order_date": "2026-10-01",
                "store_id": 1,
                "product_id": 1,
                "quantity": 5,
                "unit_price": 15000,
                "discount_percent": 0,
                "order_type": "sale",
                "status": "completed",
                "payment_method": "cash",
                "customer_name": "Khach mau",
            },
            {
                "order_code": "IMP-DEMO-001",
                "order_date": "2026-10-01",
                "store_id": 1,
                "product_id": 2,
                "quantity": 2,
                "unit_price": 25000,
                "discount_percent": 10,
                "order_type": "sale",
                "status": "completed",
                "payment_method": "cash",
                "customer_name": "Khach mau",
            },
        ],
    ),
}

# Extension -> reader keyword. Anything not listed is rejected before pandas
# ever sees the bytes.
SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def get_spec(resource_type: str) -> ImportSpec | None:
    return IMPORT_SPECS.get(resource_type)
