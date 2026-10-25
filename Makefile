.PHONY: reconstruct up restart down ps logs api-shell api db-shell redis-shell ingest seed worker worker-down ui ui-install ui-build console console-dev console-install console-build api-test

COMPOSE ?= docker compose
NODE_BIN ?= $(HOME)/.local/node-latest/bin

NODE_BIN_EXISTS := $(wildcard $(NODE_BIN))
ifeq ($(NODE_BIN_EXISTS),)
NPM ?= npm
else
NPM ?= PATH=$(NODE_BIN):$$PATH npm
endif

reconstruct:
	$(COMPOSE) up -d --build

up:
	$(COMPOSE) up -d

restart:
	$(COMPOSE) restart api

down:
	$(COMPOSE) down -v

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f api

api-shell api:
	$(COMPOSE) exec api bash

db-shell:
	$(COMPOSE) exec db psql -U scol -d scolaris

redis-shell:
	$(COMPOSE) exec redis redis-cli

ingest:
	$(COMPOSE) exec api python -m app.ingestion.ingest

seed: up ingest

worker:
	$(COMPOSE) --profile worker up -d worker

worker-down:
	$(COMPOSE) --profile worker stop worker

ui-install:
	$(NPM) install --prefix chat-widget

ui-build:
	$(NPM) run build --prefix chat-widget

ui ui-dev:
	$(NPM) run dev --prefix chat-widget

console-install:
	$(NPM) install --prefix console

console-build:
	$(NPM) run build --prefix console

console console-dev:
	$(NPM) run dev --prefix console

api-test:
	$(COMPOSE) run --rm --no-deps -v "$(CURDIR)/agent-service/tests:/app/tests:ro" api python -m unittest discover -s tests -q
