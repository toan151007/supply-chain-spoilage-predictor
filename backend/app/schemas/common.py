"""
Shared Pydantic building blocks used by more than one router.

The paginated envelope lives here rather than in each schema module so all
list endpoints return the same shape. The frontend can then rely on one
contract instead of a slightly different object per resource.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """
    Paginated response envelope.

    `total` and `pages` let the frontend render pagination controls without
    a second counting request.

    Use as `Page[ProductRead]` when declaring a response model.
    """

    total: int = Field(description="Total rows matching the filter")
    page: int
    page_size: int
    pages: int = Field(description="Total number of pages")
    items: list[T]


class Message(BaseModel):
    """Simple acknowledgement body for endpoints that return no resource."""

    message: str