from typing import List, Optional, Dict
import os
import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Json

EMBED_DIM = int(os.getenv("EMBED_DIM", 1536))

class VectorStore:
    def __init__(self, dsn: str):
        self.dsn = dsn.replace("+psycopg", "")

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
            where = "WHERE (metadata->>'role') = %s"
            params.append(filters["role"])

        sql = f"""
        SELECT content, metadata, 1 - (embedding <=> %s::vector) AS score
        FROM chunks {where}
        ORDER BY embedding <=> %s::vector
        LIMIT {k}
        """
        # 2º %s -> ORDER BY
        params = [query_embedding] + (params[1:] if len(params) > 1 else []) + [query_embedding]

        with psycopg.connect(self.dsn) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

        results = [{"content": r[0], "metadata": r[1], "score": float(r[2])} for r in rows]

        # 🔧 Fallback: si la búsqueda vectorial no trae nada, intenta coincidencia léxica simple
        if not results and qtext:
            like = f"%{qtext[:200]}%"  # evita consultas enormes
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT content, metadata, 1.0 AS score
                        FROM chunks
                        WHERE content ILIKE %s
                        ORDER BY id DESC
                        LIMIT %s
                        """,
                        (like, k),
                    )
                    rows = cur.fetchall()
            results = [{"content": r[0], "metadata": r[1], "score": float(r[2])} for r in rows]

        # 🔧 Fallback 2: si aún no hay nada, devuelve los últimos chunks (para demo)
        if not results:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT content, metadata, 1.0 AS score FROM chunks ORDER BY id DESC LIMIT %s", (k,))
                    rows = cur.fetchall()
            results = [{"content": r[0], "metadata": r[1], "score": float(r[2])} for r in rows]

        return results

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
