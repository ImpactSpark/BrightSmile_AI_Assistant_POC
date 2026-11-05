"""Ingests ADA guideline PDFs into the RAG pgvector index.

Usage:
    python scripts/ingest_ada_docs.py --corpus-dir rag_corpus

Expects a directory of PDFs. Each PDF's filename (minus extension) is used
as its `source` label. Optionally, place a sibling `<name>.json` with
{"doc_type": "ada_guideline", "url": "...", "condition_tags": "caries,periodontitis"}
to override defaults.
"""
import argparse
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

from app.core.config import settings
from app.models.schemas import RetrievedChunk
from app.services.rag.chunking import chunk_document
from app.services.rag.embeddings import get_embedding_model
from app.storage.pgvector_rag_storage import PgVectorRagIndex

DEFAULT_METADATA = {"doc_type": "ada_guideline", "url": "", "condition_tags": ""}


def _load_metadata(pdf_path: Path) -> dict:
    meta_path = pdf_path.with_suffix(".json")
    if meta_path.exists():
        return {**DEFAULT_METADATA, **json.loads(meta_path.read_text())}
    return dict(DEFAULT_METADATA)


def _extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def ingest(corpus_dir: Path) -> None:
    index = PgVectorRagIndex(settings.rag_database_url or settings.database_url)
    embedding_model = get_embedding_model(settings.rag_embedding_model)

    pdf_paths = sorted(corpus_dir.glob("*.pdf"))
    if not pdf_paths:
        print(f"No PDFs found in {corpus_dir}")
        return

    for pdf_path in pdf_paths:
        source = pdf_path.stem
        metadata = _load_metadata(pdf_path)
        text = _extract_text(pdf_path)
        pieces = chunk_document(
            text,
            max_tokens=settings.rag_chunk_tokens,
            overlap_tokens=settings.rag_chunk_overlap,
        )
        if not pieces:
            print(f"  {source}: no extractable text, skipping")
            continue

        chunks = [
            RetrievedChunk(
                chunk_id=hashlib.sha256(f"{source}:{i}".encode()).hexdigest(),
                text=piece,
                source=source,
                doc_type=metadata["doc_type"],
                url=metadata["url"],
                condition_tags=metadata["condition_tags"],
            )
            for i, piece in enumerate(pieces)
        ]
        embeddings = embedding_model.embed([c.text for c in chunks])
        index.upsert_chunks(chunks, embeddings)
        print(f"  {source}: ingested {len(chunks)} chunks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default=settings.rag_corpus_dir)
    args = parser.parse_args()
    ingest(Path(args.corpus_dir))
