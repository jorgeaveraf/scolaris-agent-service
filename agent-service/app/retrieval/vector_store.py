from typing import List, Optional, Dict
import os
import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Json
from ..security.document_guard import contains_prompt_injection

EMBED_DIM = int(os.getenv("EMBED_DIM", 1536))

class VectorStore:
    def __init__(self, dsn: str):
        self.dsn = dsn.replace("+psycopg", "")

    def document_exists(self, doc_id: str) -> bool:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM documents WHERE doc_id = %s LIMIT 1", (doc_id,))
                return cur.fetchone() is not None

    def search(
        self,
        query_embedding: list[float],
        k: int = 5,
        filters: Optional[Dict] = None,
        qtext: Optional[str] = None,   # 👈 texto original para fallback léxico
    ):
        where = ""
        params = [query_embedding]                      # 1er %s -> SELECT
        if filters and filters.get("role"):             # 👈 solo si hay rol real
            where = "WHERE (c.metadata->>'role') = %s"
            params.append(filters["role"])

        sql = f"""
        SELECT c.content, c.metadata, 1 - (c.embedding <=> %s::vector) AS score,
               d.title, d.source, c.doc_id, c.chunk_no
        FROM chunks c JOIN documents d ON d.doc_id = c.doc_id {where}
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
        """
        # 2º %s -> ORDER BY
        params = [query_embedding] + (params[1:] if len(params) > 1 else []) + [query_embedding, k]

        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                # IVFFlat with 100 lists can return no candidates while the
                # collection is still small. An exact scan is inexpensive at
                # this size and keeps the first uploaded documents searchable.
                cur.execute("SELECT COUNT(*) FROM chunks")
                if cur.fetchone()[0] < 1000:
                    cur.execute("SET LOCAL enable_indexscan = off")
                cur.execute(sql, params)
                rows = cur.fetchall()

        results = [
            {"content": r[0], "metadata": r[1], "score": float(r[2]), "title": r[3],
             "source": r[4], "doc_id": r[5], "chunk_no": r[6]}
            for r in rows if not contains_prompt_injection(r[0])
        ]

        if os.getenv("ANSWER_REQUIRE_SOURCES", "false").lower() == "true":
            minimum = float(os.getenv("SOURCE_MIN_SCORE", "0.72"))
            return [row for row in results if row["score"] >= minimum]

        # 🔧 Fallback: si la búsqueda vectorial no trae nada, intenta coincidencia léxica simple
        if not results and qtext:
            like = f"%{qtext[:200]}%"  # evita consultas enormes
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    role_clause = "AND (c.metadata->>'role') = %s" if filters and filters.get("role") else ""
                    cur.execute(
                        f"""
                        SELECT c.content, c.metadata, 1.0 AS score, d.title, d.source
                        FROM chunks c JOIN documents d ON d.doc_id = c.doc_id
                        WHERE c.content ILIKE %s
                        {role_clause}
                        ORDER BY c.id DESC
                        LIMIT %s
                        """,
                        (like, filters["role"], k) if filters and filters.get("role") else (like, k),
                    )
                    rows = cur.fetchall()
            results = [{"content": r[0], "metadata": r[1], "score": float(r[2]), "title": r[3], "source": r[4]} for r in rows if not contains_prompt_injection(r[0])]

        return results

    def search_document_passage(
        self, title_token: str, phrase: str, radius: int = 1, role: str | None = None
    ) -> list[dict]:
        """Find a passage in a named source and include its split neighbors."""
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.doc_id, c.chunk_no
                    FROM chunks c JOIN documents d ON d.doc_id = c.doc_id
                    WHERE d.title ILIKE %s
                      AND (%s::text IS NULL OR c.metadata->>'role' = %s)
                      AND to_tsvector('english', c.content) @@ plainto_tsquery('english', %s)
                    ORDER BY ts_rank_cd(
                        to_tsvector('english', c.content),
                        plainto_tsquery('english', %s)
                    ) DESC
                    LIMIT 1
                    """,
                    (f"%{title_token}%", role, role, phrase, phrase),
                )
                hit = cur.fetchone()
                if not hit:
                    return []
                cur.execute(
                    """
                    SELECT c.content, c.metadata, d.title, d.source, c.doc_id, c.chunk_no
                    FROM chunks c JOIN documents d ON d.doc_id = c.doc_id
                    WHERE c.doc_id = %s AND c.chunk_no BETWEEN %s AND %s
                      AND (%s::text IS NULL OR c.metadata->>'role' = %s)
                    ORDER BY c.chunk_no
                    """,
                    (hit[0], max(0, hit[1] - radius), hit[1] + radius, role, role),
                )
                rows = cur.fetchall()
        return [
            {"content": row[0], "metadata": row[1], "score": 1.0, "title": row[2],
             "source": row[3], "doc_id": row[4], "chunk_no": row[5]}
            for row in rows if not contains_prompt_injection(row[0])
        ]

    def neighboring_passages(self, doc_id: str, chunk_no: int, *, role: str | None = None) -> list[dict]:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.content, c.metadata, d.title, d.source, c.doc_id, c.chunk_no
                    FROM chunks c JOIN documents d ON d.doc_id = c.doc_id
                    WHERE c.doc_id = %s AND c.chunk_no BETWEEN %s AND %s
                      AND (%s::text IS NULL OR c.metadata->>'role' = %s)
                    ORDER BY c.chunk_no
                    """,
                    (doc_id, max(0, chunk_no - 1), chunk_no + 1, role, role),
                )
                rows = cur.fetchall()
        return [
            {"content": row[0], "metadata": row[1], "score": 1.0, "title": row[2],
             "source": row[3], "doc_id": row[4], "chunk_no": row[5]}
            for row in rows if not contains_prompt_injection(row[0])
        ]

    def upsert_chunks(self, rows: List[dict]):
        sql = """
        INSERT INTO documents (doc_id, title, source) VALUES (%s, %s, %s)
        ON CONFLICT (doc_id) DO UPDATE SET updated_at = now();
        """
        chunk_sql = """
        INSERT INTO chunks (doc_id, chunk_no, content, metadata, embedding)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
        """
        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                for r in rows:
                    cur.execute(sql, (r["doc_id"], r.get("title"), r.get("source")))
                    for i, ch in enumerate(r["chunks"]):
                        cur.execute(
                            chunk_sql,
                            (r["doc_id"], i, ch["content"], Json(ch.get("metadata", {})), ch["embedding"])
                        )
            conn.commit()

    def delete_document(self, doc_id: str):
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks WHERE doc_id = %s", (doc_id,))
                cur.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
            conn.commit()
