    .PHONY: up down logs api sh ingest seed
    up:
		docker compose up -d --build
    down:
		docker compose down -v
    logs:
		docker compose logs -f api
    api:
		docker compose exec api bash
    ingest:
		docker compose exec api python -m app.ingestion.ingest
    seed: up ingest
