import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row

from app.core.security import default_password_hash
from app.storage.auth_interface import AuthStorage

SESSION_TTL = timedelta(days=7)


class PostgresAuthStorage(AuthStorage):
    def __init__(self, database_url: str):
        self._database_url = database_url

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def get_doctor_password_hash(self, doctor_id: str) -> str | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM doctors WHERE doctor_id = %s", (doctor_id,))
            row = cur.fetchone()
        return row["password_hash"] if row else None

    def get_patient_password_hash(self, patient_id: str) -> str | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM patients WHERE patient_id = %s", (patient_id,))
            row = cur.fetchone()
        return row["password_hash"] if row else None

    def reset_doctor_password(self, doctor_id: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE doctors SET password_hash = %s WHERE doctor_id = %s",
                (default_password_hash(), doctor_id),
            )
            conn.commit()

    def reset_patient_password(self, patient_id: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE patients SET password_hash = %s WHERE patient_id = %s",
                (default_password_hash(), patient_id),
            )
            conn.commit()

    def get_admin_password_hash(self) -> str | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM admins WHERE admin_id = 'admin'")
            row = cur.fetchone()
        return row["password_hash"] if row else None

    def reset_admin_password(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE admins SET password_hash = %s WHERE admin_id = 'admin'",
                (default_password_hash(),),
            )
            conn.commit()

    def create_session(self, role: str, subject_id: str) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + SESSION_TTL).isoformat()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (token, role, subject_id, expires_at) VALUES (%s, %s, %s, %s)",
                (token, role, subject_id, expires_at),
            )
            conn.commit()
        return token

    def get_session(self, token: str) -> tuple[str, str] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT role, subject_id, expires_at FROM sessions WHERE token = %s", (token,))
            row = cur.fetchone()
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            self.delete_session(token)
            return None
        return row["role"], row["subject_id"]

    def delete_session(self, token: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token = %s", (token,))
            conn.commit()
