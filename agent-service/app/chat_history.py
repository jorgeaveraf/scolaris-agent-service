"""Durable, admin-only record of completed chat answers."""

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json


DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+psycopg", "")


def save_chat_answer(*, actor_email: str | None, question: str, answer: str, sources: list[dict[str, Any]]) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_history (id, actor_email, question, answer, sources) "
                "VALUES (%s, %s, %s, %s, %s)",
                (uuid4(), actor_email, question, answer, Json(sources)),
            )


_SEARCH_WHERE = (
    "position(lower(%s) in lower(coalesce(actor_email, ''))) > 0 "
    "OR position(lower(%s) in lower(question)) > 0 "
    "OR position(lower(%s) in lower(answer)) > 0 "
    "OR position(lower(%s) in lower(sources::text)) > 0"
)


def _history_filter(q: str | None, actor_email: str | None = None) -> tuple[str, tuple[Any, ...]]:
    term = (q or "").strip()
    clauses: list[str] = []
    params: list[Any] = []
    if term:
        clauses.append(f"({_SEARCH_WHERE})")
        params.extend([term] * 4)
    if actor_email is not None:
        clauses.append("actor_email IS NULL" if actor_email == "__anonymous__" else "actor_email = %s")
        if actor_email != "__anonymous__":
            params.append(actor_email.lower())
    return ("WHERE " + " AND ".join(clauses) if clauses else "", tuple(params))


def list_chat_users(*, limit: int, offset: int, q: str | None = None) -> dict[str, Any]:
    where, params = _history_filter(q)
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT count(*) AS total FROM (SELECT actor_email FROM chat_history {where} GROUP BY actor_email) users", params)
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT grouped.actor_email, grouped.message_count, grouped.last_message_at, users.display_name "
                "FROM (SELECT actor_email, count(*) AS message_count, max(created_at) AS last_message_at "
                f"FROM chat_history {where} GROUP BY actor_email) grouped "
                "LEFT JOIN authorized_users users ON users.email = grouped.actor_email "
                "ORDER BY grouped.last_message_at DESC, grouped.actor_email LIMIT %s OFFSET %s",
                (*params, limit, offset),
            )
            return {"items": cursor.fetchall(), "total": total, "limit": limit, "offset": offset}


def list_chat_history(*, limit: int, offset: int, q: str | None = None, actor_email: str | None = None, newest_first: bool = False) -> dict[str, Any]:
    where, params = _history_filter(q, actor_email)
    direction = "DESC" if newest_first else "ASC"
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT count(*) AS total FROM chat_history {where}", params)
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT id, actor_email, question, answer, sources, created_at "
                f"FROM chat_history {where} ORDER BY created_at {direction}, id {direction} LIMIT %s OFFSET %s",
                (*params, limit, offset),
            )
            return {"items": cursor.fetchall(), "total": total, "limit": limit, "offset": offset}
