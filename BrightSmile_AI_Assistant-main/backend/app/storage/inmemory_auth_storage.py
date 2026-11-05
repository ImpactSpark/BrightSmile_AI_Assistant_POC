import secrets
from datetime import datetime, timedelta, timezone

from app.core.security import default_password_hash
from app.storage.auth_interface import AuthStorage

SESSION_TTL = timedelta(days=7)


class InMemoryAuthStorage(AuthStorage):
    """Dev/test auth backend. Doctors/patients are known lazily: any id that
    hasn't been reset/logged-in-to yet is treated as having the default
    password, mirroring how LocalFilesystemCaseStorage needs no migrations.
    """

    def __init__(self):
        self._doctor_hashes: dict[str, str] = {}
        self._patient_hashes: dict[str, str] = {}
        self._admin_hash: str | None = None
        self._sessions: dict[str, tuple[str, str, datetime]] = {}

    def get_doctor_password_hash(self, doctor_id: str) -> str | None:
        return self._doctor_hashes.get(doctor_id, default_password_hash())

    def get_patient_password_hash(self, patient_id: str) -> str | None:
        return self._patient_hashes.get(patient_id, default_password_hash())

    def reset_doctor_password(self, doctor_id: str) -> None:
        self._doctor_hashes[doctor_id] = default_password_hash()

    def reset_patient_password(self, patient_id: str) -> None:
        self._patient_hashes[patient_id] = default_password_hash()

    def get_admin_password_hash(self) -> str | None:
        return self._admin_hash or default_password_hash()

    def reset_admin_password(self) -> None:
        self._admin_hash = default_password_hash()

    def create_session(self, role: str, subject_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (role, subject_id, datetime.now(timezone.utc) + SESSION_TTL)
        return token

    def get_session(self, token: str) -> tuple[str, str] | None:
        entry = self._sessions.get(token)
        if entry is None:
            return None
        role, subject_id, expires_at = entry
        if expires_at < datetime.now(timezone.utc):
            del self._sessions[token]
            return None
        return role, subject_id

    def delete_session(self, token: str) -> None:
        self._sessions.pop(token, None)
