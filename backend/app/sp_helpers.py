"""
Helper nho de chuyen row (dict) tu Stored Procedure thanh payload dung schema.

Cac SP tra ve cot phang tu JOIN (`store_code`, `product_code`,
`category_name`). Schema Pydantic lai long cac object `store`, `product`,
`category`. Cac ham duoi day chi ghep lai, KHONG tinh toan nghiep vu.
"""


def attach_store(row: dict) -> dict:
    """Add a nested `store` object when the row carries store columns."""
    if row.get("store_code") is None:
        return row
    row["store"] = {
        "store_id": row.get("store_id"),
        "store_code": row.get("store_code"),
        "store_name": row.get("store_name"),
    }
    return row


def attach_product(row: dict) -> dict:
    """Add a nested `product` object when the row carries product columns."""
    if row.get("product_code") is None:
        return row
    row["product"] = {
        "product_id": row.get("product_id"),
        "product_code": row.get("product_code"),
        "product_name": row.get("product_name"),
    }
    return row


def attach_category(row: dict) -> dict:
    """Add a nested `category` object when the row carries category columns."""
    if row.get("category_name") is None:
        return row
    row["category"] = {
        "category_id": row.get("category_id"),
        "category_name": row.get("category_name"),
    }
    return row


def as_bool(value) -> bool | None:
    """SQL Server BIT arrives as 0/1 or bool depending on the driver."""
    if value is None:
        return None
    return bool(value)


def as_bit(value: bool | None) -> int | None:
    """Convert a Python bool to the 0/1 the BIT parameters expect."""
    if value is None:
        return None
    return 1 if value else 0
