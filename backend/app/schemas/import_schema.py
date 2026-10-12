"""
Pydantic schemas for the file-import API (B7).

An import is validated row by row BEFORE anything is written, so a bad file
never leaves half-imported rows behind. The response reports what would be
written (or what was written) and, on failure, one entry per offending row
with the spreadsheet row number the user actually sees in Excel.

`row_number` is deliberately 1-based and points at the data row, not the
CSV line: row 1 in the response is the first line under the header.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# Transaction strategies for a failed import.
#
# rollback - validate everything first, write only if every row passed.
#            Nothing is written when any row is bad.
# skip     - write the good rows, report the bad ones. The caller opts in
#            knowingly, since it leaves a partial dataset behind.
OnErrorStrategy = Literal["rollback", "skip"]

# Resource types the import and template endpoints understand.
ImportType = Literal["products", "inventory", "sales"]


class RowError(BaseModel):
    """
    One rejected row.

    `row_number` matches the number in the spreadsheet's own row header, so
    the user can jump straight to it. `column` names the offending field,
    or is None when the whole row is unusable (for example a blank line).
    """

    row_number: int = Field(
        description="1-based index of the data row, header excluded"
    )
    column: str | None = Field(
        None, description="Column that failed validation, None for row-level errors"
    )
    message: str = Field(description="Why the row was rejected")


class ImportResult(BaseModel):
    """
    Outcome of one import request.

    Always HTTP 200 even when rows were rejected - the request itself
    succeeded, it is the file contents that failed. A malformed file or a
    missing required column is a 4xx instead; see the router.
    """

    file_name: str
    resource_type: str
    strategy: str

    total_rows: int = Field(description="Data rows read from the file")
    success_rows: int = Field(description="Rows accepted (and written, unless rolled back)")
    error_rows: int = Field(description="Rows rejected")

    # Capped by MAX_REPORTED_ERRORS in the router: a file with 50,000 bad
    # rows should not produce a 50,000-element JSON array in the response.
    errors: list[RowError] = []
    errors_truncated: bool = Field(
        False, description="True when more bad rows existed than were reported"
    )

    # Rows actually written. Empty when strategy rolled back.
    created_ids: list[int] = Field(
        default_factory=list,
        description="Primary keys created; empty if the transaction was rolled back",
    )

    message: str = ""


class TemplateInfo(BaseModel):
    """Metadata for one downloadable template."""

    resource_type: str
    filename: str
    format: str = Field(description="csv or xlsx")
    columns: list[str]
    required_columns: list[str]
    description: str
