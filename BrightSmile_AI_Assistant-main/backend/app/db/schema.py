SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL DEFAULT '',
    patient_name TEXT NOT NULL DEFAULT '',
    doctor_id TEXT NOT NULL DEFAULT '',
    model_version TEXT NOT NULL,
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    disclaimer TEXT NOT NULL,
    created_at TEXT NOT NULL,
    original_findings JSONB NOT NULL DEFAULT '[]',
    reviews JSONB NOT NULL DEFAULT '[]',
    chat_history JSONB NOT NULL DEFAULT '[]',
    image_path TEXT NOT NULL
);

ALTER TABLE cases ADD COLUMN IF NOT EXISTS patient_name TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_cases_patient_id ON cases (patient_id);
CREATE INDEX IF NOT EXISTS idx_cases_doctor_id ON cases (doctor_id);

CREATE TABLE IF NOT EXISTS doctors (
    doctor_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

ALTER TABLE doctors ADD COLUMN IF NOT EXISTS password_hash TEXT;

CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    password_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    admin_id TEXT PRIMARY KEY,
    password_hash TEXT
);
"""

RAG_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    condition_tags TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    embedding vector(768)
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_source ON rag_chunks (source);
"""


def init_schema(conn) -> None:
    from app.core.security import default_password_hash

    default_hash = default_password_hash()
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
        cur.execute("UPDATE doctors SET password_hash = %s WHERE password_hash IS NULL", (default_hash,))
        cur.execute("UPDATE patients SET password_hash = %s WHERE password_hash IS NULL", (default_hash,))
        cur.execute(
            "INSERT INTO admins (admin_id, password_hash) VALUES ('admin', %s) ON CONFLICT (admin_id) DO NOTHING",
            (default_hash,),
        )
    conn.commit()


def init_rag_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(RAG_SCHEMA_SQL)
    conn.commit()
