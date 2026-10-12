"""
Set real bcrypt passwords for the three seeded users.

The seeded rows carry the literal string 'PLACEHOLDER_NOT_A_REAL_HASH' in
`password_hash`, which no password can ever match. This script replaces
them with real bcrypt hashes.

Development credentials only - they are printed to stdout so you know what
they are, and they must not survive into a deployed database.

Usage (from the repository root):
    $env:DB_PASSWORD="..."; python scripts/reset_user_passwords.py
"""

import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.security import hash_password  # noqa: E402

# username -> development password
DEV_PASSWORDS = {
    "owner": "Owner@2026",
    "manager": "Manager@2026",
    "staff": "Staff@2026",
}


def main() -> int:
    password = os.environ.get("DB_PASSWORD")
    if not password:
        print("DB_PASSWORD is not set. Export it before running this script.")
        return 1

    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "spoilage_predictor"),
        user=os.environ.get("DB_USER", "postgres"),
        password=password,
    )
    cur = conn.cursor()

    for username, pwd in DEV_PASSWORDS.items():
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE username = %s "
            "RETURNING user_id, role",
            (hash_password(pwd), username),
        )
        row = cur.fetchone()
        if row is None:
            print(f"  [SKIP] no user named {username!r}")
            continue
        print(f"  user_id={row[0]:<3} role={row[1]:<8} username={username}")

    conn.commit()

    cur.execute("SELECT username, length(password_hash), left(password_hash, 4) "
                "FROM users ORDER BY user_id")
    print("\nVerification:")
    for username, length, prefix in cur.fetchall():
        print(f"  {username:<8} hash_len={length} prefix={prefix}")

    cur.close()
    conn.close()
    print("\nDevelopment passwords:")
    for username, pwd in DEV_PASSWORDS.items():
        print(f"  {username:<8} / {pwd}")
    print("\nThese are development credentials - rotate them for any real "
          "deployment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
