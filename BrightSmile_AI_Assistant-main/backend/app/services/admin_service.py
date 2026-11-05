import psycopg
from psycopg.rows import dict_row

from app.core.config import settings

TABLE_REGISTRY: dict[str, str] = {
    "cases": "X-ray cases: patient/doctor ids, image metadata, findings, reviews, chat history.",
    "doctors": "Registered dentist accounts and their password hashes.",
    "patients": "Registered patient accounts and their password hashes.",
    "sessions": "Active login sessions (session token, role, subject id, expiry).",
}

REDACT_COLUMNS = {"password_hash", "token"}


class AdminTableAccessError(Exception):
    pass


def list_tables() -> list[dict]:
    return [{"name": name, "description": desc} for name, desc in TABLE_REGISTRY.items()]


def get_table_rows(table_name: str) -> list[dict]:
    if table_name not in TABLE_REGISTRY:
        raise AdminTableAccessError(f"unknown table '{table_name}'")
    if settings.storage_backend != "postgres":
        raise AdminTableAccessError("table browser requires the postgres backend")

    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {table_name} LIMIT 10")  # noqa: S608 -- table_name is allowlisted above
        rows = cur.fetchall()

    redacted = []
    for row in rows:
        redacted.append(
            {k: ("[redacted]" if k in REDACT_COLUMNS and v is not None else v) for k, v in row.items()}
        )
    return redacted
