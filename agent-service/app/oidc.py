"""Google identity plus application-owned access control.

Google proves identity. An explicit local allowlist grants access and roles.
No Google access or refresh token is persisted.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import jwt
import psycopg
from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from psycopg.rows import dict_row
from starlette.middleware.sessions import SessionMiddleware


ENABLED = os.getenv("OIDC_ENABLED", "false").lower() == "true"
CLIENT_ID = os.getenv("GOOGLE_OIDC_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_OIDC_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("GOOGLE_OIDC_REDIRECT_URI", "")
SESSION_SECRET = os.getenv("OIDC_SESSION_SECRET", "")
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+psycopg", "")
SECURE_COOKIE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
CHAT_URL = os.getenv("OIDC_CHAT_URL", "http://localhost:5173")
CONSOLE_URL = os.getenv("OIDC_CONSOLE_URL", "http://localhost:5174")
COOKIE_NAME = "agent_auth"
ALLOWED_ROLES = {"chat", "viewer", "curator", "admin"}
oauth = OAuth()

if ENABLED:
    if not all((CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SESSION_SECRET, DATABASE_URL)):
        raise RuntimeError("OIDC requires Google client, callback, session secret, and database")
    oauth.register(
        name="google",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@dataclass(frozen=True)
class Actor:
    email: str
    google_sub: str
    display_name: str | None
    role: str


def _connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def bootstrap_admins() -> None:
    if not ENABLED:
        return
    emails = os.getenv("OIDC_BOOTSTRAP_ADMINS", "")
    with _connection() as conn:
        with conn.cursor() as cur:
            for raw in emails.split(","):
                email = raw.strip().lower()
                if email:
                    cur.execute(
                        "INSERT INTO authorized_users (email, role) VALUES (%s, 'admin') "
                        "ON CONFLICT (email) DO NOTHING",
                        (email,),
                    )


def _lookup(email: str) -> dict | None:
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT email, google_sub, display_name, role, active FROM authorized_users WHERE email = %s",
                (email,),
            )
            return cur.fetchone()


def current_actor(request: Request) -> Actor | None:
    if not ENABLED:
        return None
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        claims = jwt.decode(
            token,
            SESSION_SECRET,
            algorithms=["HS256"],
            audience="agent-service",
            issuer="agent-service",
        )
        email = str(claims["email"]).lower()
        subject = str(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None
    row = _lookup(email)
    if not row or not row["active"] or row["google_sub"] != subject:
        return None
    return Actor(email=email, google_sub=subject, display_name=row["display_name"], role=row["role"])


def require_actor(request: Request) -> Actor:
    actor = current_actor(request)
    if not actor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    return actor


class UserInput(BaseModel):
    email: EmailStr
    role: str
    active: bool = True


def register_oidc(app: FastAPI) -> None:
    if not ENABLED:
        return

    # Authlib stores only temporary OAuth state in this signed short-lived cookie.
    app.add_middleware(
        SessionMiddleware,
        secret_key=SESSION_SECRET,
        session_cookie="agent_oauth_state",
        max_age=600,
        same_site="lax",
        https_only=SECURE_COOKIE,
    )

    @app.get("/auth/google/start")
    async def google_start(request: Request, next: str = "chat"):
        request.session["after_login"] = "console" if next == "console" else "chat"
        return await oauth.google.authorize_redirect(
            request, REDIRECT_URI, prompt="select_account"
        )

    @app.get("/auth/google/callback")
    async def google_callback(request: Request):
        try:
            token = await oauth.google.authorize_access_token(request)
        except OAuthError as exc:
            # A user can cancel Google's consent screen. Authlib raises for
            # that ordinary outcome; it must not become an internal 500.
            if exc.error == "access_denied":
                raise HTTPException(status_code=400, detail="Google sign-in canceled") from exc
            raise HTTPException(status_code=400, detail="Google sign-in failed") from exc
        identity = token.get("userinfo") or {}
        email = str(identity.get("email") or "").strip().lower()
        sub = str(identity.get("sub") or "")
        display_name = str(identity.get("name") or "").strip()[:160]
        if not email or not sub or identity.get("email_verified") is not True:
            raise HTTPException(status_code=401, detail="Google identity not verified")
        row = _lookup(email)
        if not row or not row["active"]:
            raise HTTPException(status_code=403, detail="Account not invited")
        if row["google_sub"] and row["google_sub"] != sub:
            raise HTTPException(status_code=403, detail="Account identity mismatch")
        with _connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE authorized_users SET google_sub = %s, "
                    "display_name = COALESCE(NULLIF(%s, ''), display_name), updated_at = now() "
                    "WHERE email = %s AND (google_sub IS NULL OR google_sub = %s)",
                    (sub, display_name, email, sub),
                )
                if cur.rowcount != 1:
                    raise HTTPException(status_code=403, detail="Account identity mismatch")
        row = _lookup(email)
        destination = request.session.pop("after_login", "chat")
        if destination == "console" and row["role"] == "chat":
            raise HTTPException(status_code=403, detail="Console access not granted")
        return_url = CONSOLE_URL if destination == "console" else CHAT_URL
        if destination == "chat":
            return_url += ("&" if "?" in return_url else "?") + urlencode({"chat": "1"})
        response = RedirectResponse(return_url, status_code=303)
        now = int(time.time())
        session = jwt.encode(
            {"sub": sub, "email": email, "iss": "agent-service", "aud": "agent-service", "iat": now, "exp": now + 86400},
            SESSION_SECRET,
            algorithm="HS256",
        )
        response.set_cookie(
            COOKIE_NAME, session, httponly=True, secure=SECURE_COOKIE,
            samesite="lax", max_age=86400, path="/",
        )
        return response

    @app.get("/auth/me")
    def auth_me(request: Request):
        actor = require_actor(request)
        return {"email": actor.email, "name": actor.display_name, "role": actor.role}

    @app.post("/auth/logout")
    def auth_logout():
        response = Response(status_code=204)
        response.delete_cookie(COOKIE_NAME, path="/")
        return response

    @app.get("/admin/users")
    def list_users(request: Request):
        actor = require_actor(request)
        if actor.role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        with _connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT display_name, email, role, active, created_at FROM authorized_users ORDER BY email")
                return cur.fetchall()

    @app.put("/admin/users")
    def upsert_user(request: Request, body: UserInput):
        actor = require_actor(request)
        if actor.role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        if body.role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        email = str(body.email).lower()
        if email == actor.email and (body.role != "admin" or not body.active):
            raise HTTPException(status_code=400, detail="Cannot remove own admin access")
        with _connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO authorized_users (email, role, active) VALUES (%s, %s, %s) "
                    "ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role, active = EXCLUDED.active, updated_at = now()",
                    (email, body.role, body.active),
                )
        return {"email": email, "role": body.role, "active": body.active}

    @app.delete("/admin/users/{email}", status_code=204)
    def delete_user(request: Request, email: str):
        actor = require_actor(request)
        if actor.role != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        normalized_email = email.strip().lower()
        if normalized_email == actor.email:
            raise HTTPException(status_code=400, detail="Cannot delete own access")
        with _connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM authorized_users WHERE email = %s RETURNING email", (normalized_email,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Account not found")
        return Response(status_code=204)
