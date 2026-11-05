from abc import ABC, abstractmethod


class AuthStorage(ABC):
    """Auth persistence: password hashes and sessions for doctors/patients."""

    @abstractmethod
    def get_doctor_password_hash(self, doctor_id: str) -> str | None:
        ...

    @abstractmethod
    def get_patient_password_hash(self, patient_id: str) -> str | None:
        ...

    @abstractmethod
    def reset_doctor_password(self, doctor_id: str) -> None:
        ...

    @abstractmethod
    def reset_patient_password(self, patient_id: str) -> None:
        ...

    @abstractmethod
    def get_admin_password_hash(self) -> str | None:
        ...

    @abstractmethod
    def reset_admin_password(self) -> None:
        ...

    @abstractmethod
    def create_session(self, role: str, subject_id: str) -> str:
        ...

    @abstractmethod
    def get_session(self, token: str) -> tuple[str, str] | None:
        ...

    @abstractmethod
    def delete_session(self, token: str) -> None:
        ...
