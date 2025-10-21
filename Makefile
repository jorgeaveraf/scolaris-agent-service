    .PHONY: up down logs api sh ingest seed
    reconstruct:
		docker compose up -d --build
    up:
    docker compose up -d
    restart:
    docker compose restart api
    down:
		docker compose down -v
    logs:
		docker compose logs -f api
    api:
		docker compose exec api bash
    ingest:
		docker compose exec api python -m app.ingestion.ingest
    seed: up ingest
    ui: npm run dev
