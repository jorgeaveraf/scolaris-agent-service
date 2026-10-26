from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID
import os

import psycopg
from psycopg.rows import dict_row


DSN = os.getenv("DATABASE_URL", "").replace("+psycopg", "")

DOCUMENT_COLUMNS = (
    "id",
    "filename",
    "content_type",
    "size_bytes",
    "checksum",
    "status",
    "area",
    "role",
    "vigencia",
    "source_url",
    "uploaded_by_email",
    "uploaded_by_name",
    "doc_id",
    "upload_path",
    "chunks_count",
    "last_ingested_at",
    "error_msg",
    "created_at",
    "updated_at",
)


def _ensure_dsn() -> str:
    if not DSN:
        raise RuntimeError("DATABASE_URL no está configurado.")
    return DSN


def _connect():
    return psycopg.connect(_ensure_dsn(), row_factory=dict_row)


def create_document(
    *,
    document_id: UUID,
    filename: str,
    content_type: str | None,
    size_bytes: int,
    checksum: str,
    status: str,
    area: str | None,
    role: str | None,
    vigencia: str | None,
    source_url: str | None,
    uploaded_by_email: str,
    uploaded_by_name: str | None,
    upload_path: str,
) -> dict[str, Any]:
    sql = f"""
        INSERT INTO raw_documents (
            id, filename, content_type, size_bytes, checksum, status,
            area, role, vigencia, source_url, uploaded_by_email, uploaded_by_name, upload_path
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {", ".join(DOCUMENT_COLUMNS)}
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    document_id,
                    filename,
                    content_type,
                    size_bytes,
                    checksum,
                    status,
                    area,
                    role,
                    vigencia,
                    source_url,
                    uploaded_by_email,
                    uploaded_by_name,
                    upload_path,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def update_document(document_id: UUID, **fields: Any) -> dict[str, Any]:
    if not fields:
        return get_document(document_id)

    assignments: list[str] = []
    values: list[Any] = []

    for column, value in fields.items():
        assignments.append(f"{column} = %s")
        values.append(value)

    assignments.append("updated_at = now()")

    sql = f"""
        UPDATE raw_documents
        SET {", ".join(assignments)}
        WHERE id = %s
        RETURNING {", ".join(DOCUMENT_COLUMNS)}
    """
    values.append(document_id)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            row = cur.fetchone()
        conn.commit()
    if row is None:
        raise LookupError(f"Documento {document_id} no encontrado.")
    return row


def get_document(document_id: UUID) -> dict[str, Any] | None:
    sql = f"""
        SELECT {", ".join(DOCUMENT_COLUMNS)}
        FROM raw_documents
        WHERE id = %s
        LIMIT 1
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (document_id,))
            return cur.fetchone()


def get_document_by_checksum(checksum: str) -> dict[str, Any] | None:
    sql = f"""
        SELECT {", ".join(DOCUMENT_COLUMNS)}
        FROM raw_documents
        WHERE checksum = %s
        LIMIT 1
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (checksum,))
            return cur.fetchone()


def list_documents(
    *,
    filters: dict[str, Any],
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    conditions: list[str] = []
    params: list[Any] = []

    def _add_condition(column: str, value: Any, op: str = "="):
        conditions.append(f"{column} {op} %s")
        params.append(value)

    if search := filters.get("q"):
        conditions.append("filename ILIKE %s")
        params.append(f"%{search}%")
    if status := filters.get("status"):
        _add_condition("status", status)
    if area := filters.get("area"):
        _add_condition("area", area)
    if role := filters.get("role"):
        _add_condition("role", role)
    if vigencia := filters.get("vigencia"):
        _add_condition("vigencia", vigencia)
    if updated_from := filters.get("updated_from"):
        _add_condition("updated_at", updated_from, ">=")
    if updated_before := filters.get("updated_before"):
        _add_condition("updated_at", updated_before, "<")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query_sql = f"""
        SELECT {", ".join(DOCUMENT_COLUMNS)}
        FROM raw_documents
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    count_sql = f"SELECT COUNT(*) FROM raw_documents {where_clause}"

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(count_sql, params)
            total = int(cur.fetchone()["count"])  # type: ignore[index]

            cur.execute(query_sql, params + [limit, offset])
            items = cur.fetchall()

    return total, items


def get_chunks_for_doc(
    doc_id: str,
    *,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    query_sql = """
        SELECT id, chunk_no, content, metadata
        FROM chunks
        WHERE doc_id = %s
        ORDER BY chunk_no ASC
        LIMIT %s OFFSET %s
    """
    count_sql = "SELECT COUNT(*) FROM chunks WHERE doc_id = %s"

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(count_sql, (doc_id,))
            total = int(cur.fetchone()["count"])  # type: ignore[index]

            cur.execute(query_sql, (doc_id, limit, offset))
            items = cur.fetchall()

    return total, items


def delete_document(document_id: UUID) -> None:
    sql = "DELETE FROM raw_documents WHERE id = %s"
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (document_id,))
        conn.commit()


def count_documents_by_status() -> dict[str, int]:
    sql = "SELECT status, COUNT(*) as total FROM raw_documents GROUP BY status"
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return {row["status"]: int(row["total"]) for row in rows}


def update_status(
    document_id: UUID,
    *,
    status: str,
    error_msg: str | None = None,
    doc_id: str | None = None,
    chunks_count: int | None = None,
    last_ingested_at: datetime | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "status": status,
        "error_msg": error_msg,
    }
    if doc_id is not None:
        fields["doc_id"] = doc_id
    if chunks_count is not None:
        fields["chunks_count"] = chunks_count
    if last_ingested_at is not None:
        fields["last_ingested_at"] = last_ingested_at
    return update_document(document_id, **fields)


def update_upload_metadata(
    document_id: UUID,
    *,
    filename: str,
    content_type: str | None,
    size_bytes: int,
    checksum: str,
    area: str | None,
    role: str | None,
    vigencia: str | None,
    source_url: str | None,
    uploaded_by_email: str,
    uploaded_by_name: str | None,
    upload_path: str,
) -> dict[str, Any]:
    return update_document(
        document_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        checksum=checksum,
        area=area,
        role=role,
        vigencia=vigencia,
        source_url=source_url,
        uploaded_by_email=uploaded_by_email,
        uploaded_by_name=uploaded_by_name,
        upload_path=upload_path,
    )


def attach_source_url(document_id: UUID, doc_id: str | None, source_url: str) -> dict[str, Any]:
    """Attach a public citation link to an already indexed duplicate upload."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE raw_documents SET source_url = %s, updated_at = now() WHERE id = %s "
                f"RETURNING {', '.join(DOCUMENT_COLUMNS)}",
                (source_url, document_id),
            )
            row = cur.fetchone()
            if doc_id:
                cur.execute("UPDATE documents SET source = %s, updated_at = now() WHERE doc_id = %s", (source_url, doc_id))
        conn.commit()
    return row


def record_duplicate_upload_actor(
    document_id: UUID, *, uploaded_by_email: str, uploaded_by_name: str | None
) -> dict[str, Any]:
    """Attribute a re-upload only when the original record has no uploader."""
    sql = f"""
        UPDATE raw_documents
        SET uploaded_by_email = %s, uploaded_by_name = %s, updated_at = now()
        WHERE id = %s AND uploaded_by_email IS NULL
        RETURNING {", ".join(DOCUMENT_COLUMNS)}
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (uploaded_by_email, uploaded_by_name, document_id))
            row = cur.fetchone()
        conn.commit()
    return row or get_document(document_id)
