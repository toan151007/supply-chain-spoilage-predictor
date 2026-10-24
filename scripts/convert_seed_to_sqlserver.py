"""One-off helper: convert database/02-seed/seed-data.sql (PostgreSQL) to T-SQL.

Writes database/02-seed/seed-sqlserver.sql. Not part of the runtime.

Transformations:
  - drop BEGIN/COMMIT, psql SET and TRUNCATE ... CASCADE
  - prefix table names with dbo.
  - TRUE/FALSE -> 1/0
  - wrap explicit-identity inserts with SET IDENTITY_INSERT
"""

from pathlib import Path
import re

SRC = Path("database/02-seed/seed-data.sql")
DST = Path("database/02-seed/seed-sqlserver.sql")

IDENTITY_TABLES = {"categories", "stores", "products", "users"}

text = SRC.read_text(encoding="utf-8", errors="replace")
# Everything from COMMENT ON is psql-only metadata plus \echo verification
# commands that sqlcmd cannot parse. Keep only the INSERT statements.
text = text.split("COMMENT ON TABLE")[0]
lines = text.splitlines()

out = [
    "-- =============================================================================",
    "--  SEED DATA - BASE REFERENCE DATA (SQL Server / T-SQL)",
    "--  Generated from seed-data.sql by scripts/convert_seed_to_sqlserver.py",
    "--  Inserts categories, stores, products and users with their explicit ids.",
    "-- =============================================================================",
    "SET QUOTED_IDENTIFIER ON;",
    "SET ANSI_NULLS ON;",
    "GO",
    "",
]

skip_truncate = False
current_identity = None

for line in lines:
    stripped = line.strip()

    if skip_truncate:
        if stripped.endswith(";"):
            skip_truncate = False
        continue

    if stripped.startswith("TRUNCATE"):
        if not stripped.endswith(";"):
            skip_truncate = True
        continue
    if stripped in ("BEGIN;", "COMMIT;", ""):
        continue
    if stripped.startswith("SET client_min_messages"):
        continue
    if stripped.startswith("--") and not stripped.startswith("--  "):
        # keep ordinary comments; they are ASCII in this file
        out.append(line)
        continue

    match = re.match(r"INSERT INTO\s+([a-z_]+)", stripped)
    if match:
        table = match.group(1)
        if current_identity and current_identity != table:
            out.append(f"SET IDENTITY_INSERT dbo.{current_identity} OFF;")
            out.append("GO")
            out.append("")
            current_identity = None
        if table in IDENTITY_TABLES and current_identity != table:
            if current_identity:
                out.append(f"SET IDENTITY_INSERT dbo.{current_identity} OFF;")
                out.append("GO")
                out.append("")
            out.append(f"SET IDENTITY_INSERT dbo.{table} ON;")
            out.append("GO")
            out.append("")
            current_identity = table

    converted = re.sub(r"\bTRUE\b", "1", line)
    converted = re.sub(r"\bFALSE\b", "0", converted)
    converted = re.sub(
        r"\bINSERT INTO\s+(categories|stores|products|users)\b",
        r"INSERT INTO dbo.\1",
        converted,
    )
    out.append(converted)

if current_identity:
    out.append(f"SET IDENTITY_INSERT dbo.{current_identity} OFF;")
    out.append("GO")

DST.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"wrote {DST} ({len(out)} lines)")
