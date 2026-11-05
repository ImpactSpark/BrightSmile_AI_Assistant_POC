"""One-time backfill: reads existing storage/cases/<case_id>/{prediction,review,chat}.json
directories written by LocalFilesystemCaseStorage and inserts them into Postgres via
PostgresCaseStorage. Existing filesystem case dirs are left untouched (images stay there;
Postgres storage reads images from the same paths).

Usage (from backend/):
    python -m scripts.migrate_to_postgres
"""

from app.core.config import settings
from app.storage.local_storage import LocalFilesystemCaseStorage
from app.storage.postgres_storage import PostgresCaseStorage


def migrate() -> None:
    source = LocalFilesystemCaseStorage(settings.storage_root)
    dest = PostgresCaseStorage(settings.database_url, settings.storage_root)

    records = source.list_cases()
    print(f"found {len(records)} case(s) in {settings.storage_root}")

    for record in records:
        dest.save_case_record(record)
        reviews = source.load_reviews(record.case_id)
        if reviews:
            dest.save_reviews(record.case_id, reviews)
        chat_history = source.load_chat_history(record.case_id)
        if chat_history:
            dest.save_chat_history(record.case_id, chat_history)
        print(f"migrated case_id={record.case_id} dentist={record.dentist_name!r}")

    print("done")


if __name__ == "__main__":
    migrate()
