"""Pydantic schemas for the alerts API.

The alerts table is read-only for creation: rows are produced by the
database function `fn_generate_inventory_alerts()`. The API exposes the
workflow actions a user performs on an alert instead - mark as read and
resolve.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page
from app.schemas.product_schema import ProductBrief
from app.schemas.store_schema import StoreBrief

ALERT_TYPE_PATTERN = (
    "^(expiring_soon|expired|low_stock|over_stock|forecast_anomaly)$"
)
SEVERITY_PATTERN = "^(low|medium|high|critical)$"


class AlertRead(BaseModel):
    """
    Response body returned by GET endpoints.

    `title` holds an i18n KEY such as `alert.title.EXPIRED`, not display
    text. Translations live in backend/app/i18n/vi.json. Storing keys in the
    database is what makes multi-language support possible without rewriting
    rows.
    """

    model_config = ConfigDict(from_attributes=True)

    alert_id: int
    store_id: int | None = None
    product_id: int | None = None
    alert_type: str
    severity: str
    title: str = Field(description="i18n key, not display text")
    message: str | None = None
    expiry_date: date | None = None
    current_stock: float | None = None
    threshold_value: float | None = None
    is_read: bool
    is_resolved: bool
    created_at: datetime
    resolved_at: datetime | None = None

    store: StoreBrief | None = None
    product: ProductBrief | None = None


class AlertPage(Page[AlertRead]):
    """Paginated list of alerts."""


class MarkReadRequest(BaseModel):
    """Body for PUT /api/v1/alerts/{id}/read."""

    # Lets the frontend flip a flag back, for example after an undo.
    is_read: bool = True


class ResolveRequest(BaseModel):
    """
    Body for PUT /api/v1/alerts/{id}/resolve.

    `note` is optional and free text. The router stamps `resolved_at`
    automatically because the database CHECK constraint requires it to be
    non-NULL exactly when `is_resolved` is TRUE.
    """

    is_resolved: bool = True
    note: str | None = None

