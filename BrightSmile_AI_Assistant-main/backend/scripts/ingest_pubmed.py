"""Expands the RAG corpus with open-access PubMed articles, scoped to dental
MeSH terms. Reuses the same chunking/embedding/ingestion pipeline as
scripts/ingest_ada_docs.py; tagged doc_type='pubmed' (lower trust weight
than ADA guidelines, see app/services/rag/hybrid.py TRUST_WEIGHT).

Usage:
    python scripts/ingest_pubmed.py --mesh-term "Dental Caries" --mesh-term "Periodontitis"
"""
import argparse
import asyncio
import hashlib

from app.core.config import settings
from app.models.schemas import RetrievedChunk
from app.services.rag.chunking import chunk_document
from app.services.rag.embeddings import get_embedding_model
from app.services.rag.pubmed_client import PubMedClient
from app.storage.pgvector_rag_storage import PgVectorRagIndex


async def ingest(mesh_terms: list[str], max_results: int) -> None:
    index = PgVectorRagIndex(settings.rag_database_url or settings.database_url)
    embedding_model = get_embedding_model(settings.rag_embedding_model)
    client = PubMedClient(mesh_terms=mesh_terms, max_results=max_results)

    pmids = await client.search_open_access()
    if not pmids:
        print("No open-access PubMed articles found for the given MeSH terms.")
        return

    docs = await client.fetch_documents(pmids)
    for doc in docs:
        pieces = chunk_document(
            doc.text,
            max_tokens=settings.rag_chunk_tokens,
            overlap_tokens=settings.rag_chunk_overlap,
        )
        if not pieces:
            continue
        chunks = [
            RetrievedChunk(
                chunk_id=hashlib.sha256(f"{doc.source}:{i}".encode()).hexdigest(),
                text=piece,
                source=doc.source,
                doc_type="pubmed",
                url=doc.url,
                condition_tags=",".join(mesh_terms),
            )
            for i, piece in enumerate(pieces)
        ]
        embeddings = embedding_model.embed([c.text for c in chunks])
        index.upsert_chunks(chunks, embeddings)
        print(f"  {doc.source}: ingested {len(chunks)} chunks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh-term", action="append", dest="mesh_terms", required=True)
    parser.add_argument("--max-results", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(ingest(args.mesh_terms, args.max_results))
