"""Persistent, aggregate figures for the nontechnical console overview."""

from __future__ import annotations

import os

import psycopg

from .service import DocumentAdminService


DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+psycopg", "")
CHAT_WINDOW_DAYS = 7


def dashboard_summary(service: DocumentAdminService) -> dict:
    document_counts = service.get_ingestion_stats()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*) AS interactions,
                       count(DISTINCT actor_email) AS identified_people,
                       count(*) FILTER (WHERE actor_email IS NULL) AS anonymous_interactions
                FROM chat_history
                WHERE created_at >= now() - make_interval(days => %s)
                """,
                (CHAT_WINDOW_DAYS,),
            )
            interactions, identified_people, anonymous_interactions = cursor.fetchone()
            cursor.execute(
                """
                SELECT count(*) FILTER (WHERE active) AS chat_enabled,
                       count(*) FILTER (WHERE active AND role IN ('viewer', 'curator', 'admin'))
                         AS console_enabled
                FROM authorized_users
                """
            )
            chat_enabled, console_enabled = cursor.fetchone()

    identity_enabled = os.getenv("OIDC_ENABLED", "false").lower() == "true"
    return {
        "documents": {
            key: int(document_counts.get(key, 0) or 0)
            for key in ("total", "ready", "processing", "error", "other")
        },
        "chat_window_days": CHAT_WINDOW_DAYS,
        "chat_interactions": interactions,
        "identified_people": identified_people,
        "anonymous_interactions": anonymous_interactions,
        "identity_enabled": identity_enabled,
        "chat_login_required": os.getenv("CHAT_LOGIN_REQUIRED", "false").lower() == "true",
        "chat_enabled_people": chat_enabled if identity_enabled else None,
        "console_enabled_people": console_enabled if identity_enabled else None,
    }
