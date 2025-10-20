# Scolaris Agent — Monorepo Skeleton

This repo contains:
- `agent-service/`: FastAPI + LangChaih backend with pgvector and Redis.
- `chat-widget/`: React (Vite + TS) widget that consumes the agent.
- `docker-compose.yml`: local dev infra (Postgres+pgvector, Redis, API).
- `Makefile`: handy shortcuts.

## Quickstart
1) Copy `agent-service/.env.example` to `agent-service/.env` and set your keys.
2) `docker compose up -d --build` (from repo root) to start DB/Redis/API.
3) Optional: Put a `.txt` doc under `agent-service/app/ingestion/data/` and run `make ingest`.
4) In `chat-widget/`: `npm install` then `npm run dev` to start the widget.
