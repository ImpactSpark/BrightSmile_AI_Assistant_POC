import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from rank_bm25 import BM25Okapi

from app.db.schema import init_rag_schema
from app.models.schemas import RetrievedChunk
from app.storage.rag_interface import RagIndex


class PgVectorRagIndex(RagIndex):
    """Chunk index on Postgres+pgvector. Reuses the existing Postgres
    dependency instead of standing up a second stateful service -- at a
    corpus of hundreds-to-low-thousands of chunks, pgvector's IVFFlat/HNSW
    indexes are plenty fast."""

    def __init__(self, database_url: str):
        self._database_url = database_url
        with psycopg.connect(self._database_url) as conn:
            init_rag_schema(conn)

    def _connect(self):
        conn = psycopg.connect(self._database_url, row_factory=dict_row)
        register_vector(conn)
        return conn

    def upsert_chunks(self, chunks: list[RetrievedChunk], embeddings: list[list[float]]) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            for chunk, embedding in zip(chunks, embeddings):
                cur.execute(
                    """
                    INSERT INTO rag_chunks (chunk_id, source, doc_type, url, condition_tags, text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        source = EXCLUDED.source,
                        doc_type = EXCLUDED.doc_type,
                        url = EXCLUDED.url,
                        condition_tags = EXCLUDED.condition_tags,
                        text = EXCLUDED.text,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        chunk.chunk_id,
                        chunk.source,
                        chunk.doc_type,
                        chunk.url,
                        chunk.condition_tags,
                        chunk.text,
                        embedding,
                    ),
                )
            conn.commit()

    def search_dense(
        self, query_embedding: list[float], k: int, condition_filter: str | None = None
    ) -> list[RetrievedChunk]:
        where = "WHERE condition_tags ILIKE %s" if condition_filter else ""
        sql = f"""
            SELECT chunk_id, source, doc_type, url, text,
                   1 - (embedding <=> %s) AS score
            FROM rag_chunks
            {where}
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        vector_param = Vector(query_embedding)
        params: list = [vector_param]
        if condition_filter:
            params.append(f"%{condition_filter}%")
        params += [vector_param, k]

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                text=r["text"],
                source=r["source"],
                doc_type=r["doc_type"],
                url=r["url"],
                score=float(r["score"]),
            )
            for r in rows
        ]

    def search_sparse(
        self, query: str, k: int, condition_filter: str | None = None
    ) -> list[RetrievedChunk]:
        # BM25 rebuilt in-memory per query -- fine at this corpus size
        # (hundreds-to-low-thousands of chunks); avoids persisting a second
        # index alongside the pgvector one.
        where = "WHERE condition_tags ILIKE %s" if condition_filter else ""
        params = [f"%{condition_filter}%"] if condition_filter else []
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT chunk_id, source, doc_type, url, text FROM rag_chunks {where}",
                params,
            )
            rows = cur.fetchall()

        if not rows:
            return []

        tokenized = [r["text"].lower().split() for r in rows]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(query.lower().split())
        ranked = sorted(zip(rows, scores), key=lambda pair: pair[1], reverse=True)[:k]

        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                text=r["text"],
                source=r["source"],
                doc_type=r["doc_type"],
                url=r["url"],
                score=float(score),
            )
            for r, score in ranked
        ]

    def delete_source(self, source: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM rag_chunks WHERE source = %s", (source,))
            conn.commit()
