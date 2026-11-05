import json
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.core.security import default_password_hash
from app.db.schema import init_schema
from app.models.schemas import (
    CaseRecord,
    ChatMessage,
    DoctorSummary,
    ImageDimensions,
    ReviewedFinding,
)
from app.storage.interface import CaseStorage
from app.storage.local_storage import LocalFilesystemCaseStorage


class PostgresCaseStorage(CaseStorage):
    """Case metadata (patient_id, doctor_id, findings, reviews, chat) lives in
    Postgres; original image bytes stay on the filesystem (same layout as
    LocalFilesystemCaseStorage) since blobs don't belong in relational rows
    at this scale.
    """

    def __init__(self, database_url: str, image_root: str | Path):
        self._database_url = database_url
        self._images = LocalFilesystemCaseStorage(image_root)
        with psycopg.connect(self._database_url) as conn:
            init_schema(conn)

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def save_original_image(self, case_id: str, image_bytes: bytes, extension: str) -> str:
        return self._images.save_original_image(case_id, image_bytes, extension)

    def get_original_image_path(self, case_id: str) -> Path | None:
        return self._images.get_original_image_path(case_id)

    def save_case_record(self, case: CaseRecord) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cases (
                    case_id, patient_id, patient_name, doctor_id, model_version,
                    image_width, image_height, disclaimer, created_at,
                    original_findings, image_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (case_id) DO UPDATE SET
                    patient_id = EXCLUDED.patient_id,
                    patient_name = EXCLUDED.patient_name,
                    doctor_id = EXCLUDED.doctor_id,
                    model_version = EXCLUDED.model_version,
                    image_width = EXCLUDED.image_width,
                    image_height = EXCLUDED.image_height,
                    disclaimer = EXCLUDED.disclaimer,
                    created_at = EXCLUDED.created_at,
                    original_findings = EXCLUDED.original_findings
                """,
                (
                    case.case_id,
                    case.patient_id,
                    case.patient_name,
                    case.dentist_name,
                    case.model_version,
                    case.image_dimensions.width,
                    case.image_dimensions.height,
                    case.disclaimer,
                    case.created_at,
                    json.dumps([f.model_dump(mode="json") for f in case.original_findings]),
                    str(self._images._case_dir(case.case_id)),
                ),
            )
            if case.dentist_name:
                cur.execute(
                    """
                    INSERT INTO doctors (doctor_id, name, created_at, password_hash)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (doctor_id) DO NOTHING
                    """,
                    (case.dentist_name, case.dentist_name, case.created_at, default_password_hash()),
                )
            if case.patient_id:
                cur.execute(
                    """
                    INSERT INTO patients (patient_id, name, created_at, password_hash)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (patient_id) DO NOTHING
                    """,
                    (case.patient_id, case.patient_name, case.created_at, default_password_hash()),
                )
            conn.commit()

    def load_case_record(self, case_id: str) -> CaseRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM cases WHERE case_id = %s", (case_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_cases(self) -> list[CaseRecord]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM cases ORDER BY created_at DESC")
            rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    def case_exists(self, case_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM cases WHERE case_id = %s", (case_id,))
            return cur.fetchone() is not None

    def save_reviews(self, case_id: str, reviews: list[ReviewedFinding]) -> None:
        payload = json.dumps([r.model_dump(mode="json") for r in reviews])
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE cases SET reviews = %s WHERE case_id = %s", (payload, case_id)
            )
            conn.commit()

    def load_reviews(self, case_id: str) -> list[ReviewedFinding]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT reviews FROM cases WHERE case_id = %s", (case_id,))
            row = cur.fetchone()
        if row is None:
            return []
        return [ReviewedFinding.model_validate(r) for r in row["reviews"]]

    def save_chat_history(self, case_id: str, messages: list[ChatMessage]) -> None:
        payload = json.dumps([m.model_dump(mode="json") for m in messages])
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE cases SET chat_history = %s WHERE case_id = %s", (payload, case_id)
            )
            conn.commit()

    def load_chat_history(self, case_id: str) -> list[ChatMessage]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT chat_history FROM cases WHERE case_id = %s", (case_id,))
            row = cur.fetchone()
        if row is None:
            return []
        return [ChatMessage.model_validate(m) for m in row["chat_history"]]

    def list_doctors(self) -> list[DoctorSummary]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.doctor_id, d.name, COUNT(c.case_id) AS case_count
                FROM doctors d
                LEFT JOIN cases c ON c.doctor_id = d.doctor_id
                GROUP BY d.doctor_id, d.name
                ORDER BY d.name
                """
            )
            rows = cur.fetchall()
        return [
            DoctorSummary(doctor_id=row["doctor_id"], name=row["name"], case_count=row["case_count"])
            for row in rows
        ]

    def list_cases_for_doctor(self, doctor_id: str) -> list[CaseRecord]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM cases WHERE doctor_id = %s ORDER BY created_at DESC",
                (doctor_id,),
            )
            rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_cases_for_patient(self, patient_id: str) -> list[CaseRecord]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM cases WHERE patient_id = %s ORDER BY created_at DESC",
                (patient_id,),
            )
            rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def _row_to_record(row: dict) -> CaseRecord:
        return CaseRecord(
            case_id=row["case_id"],
            patient_id=row["patient_id"],
            patient_name=row["patient_name"],
            dentist_name=row["doctor_id"],
            model_version=row["model_version"],
            image_dimensions=ImageDimensions(width=row["image_width"], height=row["image_height"]),
            original_findings=row["original_findings"],
            disclaimer=row["disclaimer"],
            created_at=row["created_at"],
        )
