# Scolaris Agent — Monorepo

Panel conversacional + consola administrativa para gestionar la memoria RAG de Scolaris. El repositorio contiene el backend (FastAPI + LangChain), el widget de chat para el sitio público y una interfaz enterprise para administrar documentos y chunks.

## Estructura

```
agent-service/    # API principal (FastAPI) + ingesta de documentos
chat-widget/      # Widget de chat en React para embeder en scolaris.com.mx
console/          # Nueva consola administrativa (React + Vite + Tailwind)
docker-compose.yml
Makefile
```

## Requisitos locales

- Docker + Docker Compose plugin.
- GNU Make.
- Node.js **18.17+** (probado con 18.20 LTS).
- Cuenta OpenAI con clave válida (`OPENAI_API_KEY`).

> Si conservas varias versiones de Node, puedes definir `NODE_BIN=/ruta/a/tu/node/bin` al invocar `make`. Por defecto usará el `npm` global disponible en tu entorno (Node 18 es suficiente).

## Variables de entorno

### Backend (`agent-service/.env`)

1. Copia `agent-service/.env.example` → `agent-service/.env`.
2. Variables relevantes:
   - `DATABASE_URL`: DSN de Postgres/pgvector (por defecto apunta al contenedor `db`).
   - `REDIS_URL`: cola de memoria conversacional.
   - `OPENAI_API_KEY`, `MODEL_NAME`, `EMBED_MODEL`, `EMBED_DIM`.
   - `ALLOWED_ORIGINS`: orígenes permitidos para CORS (widget y consola).
   - `ADMIN_TOKEN`: token Bearer requerido por los endpoints `/admin/*`.
   - `MAX_UPLOAD_MB`, `ALLOWED_EXTS`: restricciones para la ingesta.

### Consola (`console/.env`)

Copia `.env.example` y ajusta según tu entorno:

```bash
cp console/.env.example console/.env
```

Variables:
- `VITE_API_BASE`: URL pública del backend (`http://localhost:8000` en local).
- `VITE_CONSOLE_AUTH`: opcional, permite precargar el token Bearer en desarrollo.

### Widget (`chat-widget/`)

No requiere variables adicionales; consume el backend en `http://localhost:8000` por defecto. Ajusta la URL en código si lo despliegas en otro origen.

## Uso de Docker/Make

Todos los comandos usan `docker compose` y, por defecto, el `npm` global de tu sistema.

| Comando                   | Acción |
|---------------------------|--------|
| `make reconstruct`        | `docker compose up -d --build` (recompone la infraestructura).
| `make up`                 | Levanta los contenedores sin reconstruir imágenes.
| `make restart`            | Reinicia solo el servicio `api`.
| `make down`               | Apaga y borra volúmenes (`docker compose down -v`).
| `make ps`                 | Lista el estado de los contenedores.
| `make logs`               | Sigue los logs del backend (`api`).
| `make api-shell`          | Bash dentro del contenedor `api` (alias `make api`).
| `make db-shell`           | Abre `psql` contra Postgres (`scol/scolpwd`).
| `make redis-shell`        | Abre `redis-cli` contra Redis.
| `make ingest`             | Ejecuta el script de ingesta por lotes (`python -m app.ingestion.ingest`).
| `make seed`               | Levanta los contenedores y luego corre `ingest`.
| `make ui-install`         | `npm install` del widget (`chat-widget`).
| `make ui-build`           | Build de producción del widget.
| `make ui` / `make ui-dev` | `npm run dev --prefix chat-widget` (puerto 5173).
| `make console-install`    | `npm install` de la consola admin.
| `make console-build`      | Build de producción de la consola (`console/dist`).
| `make console`            | `npm run dev --prefix console` (puerto 5174 por defecto).
| `make admin-test`         | Checa acceso `Bearer` contra `/admin/docs` (`ADMIN_TOKEN` env).

## Flujo típico de trabajo

1. **Preparar entorno**
   ```bash
   cp agent-service/.env.example agent-service/.env
   cp console/.env.example console/.env   # opcional en dev
   export OPENAI_API_KEY=...              # si no lo defines en el .env
   ```
2. **Levantar servicios base**
   ```bash
   make reconstruct   # o `make up` si ya tienes las imágenes
   ```
3. **Desarrollo frontend**
   ```bash
   make ui            # widget de chat (http://localhost:5173)
   make console       # consola admin (http://localhost:5174)
   ```
4. **Cargar documentos**
   - Desde la consola (botón "Nuevo documento").
   - Vía API `POST /admin/docs` (multipart/form-data).
   - Por CLI con `make ingest` si dejas archivos en `agent-service/app/ingestion/data/`.

## Consola administrativa

La app en `console/` replica un dashboard SaaS:
- Login protegido por token Bearer (`ADMIN_TOKEN`).
- Vista de métricas (total, ready, processing, error).
- Tabla con filtros (status, área, rol, vigencia), paginación y acciones.
- Modal de subida con barra de progreso, metadata opcional y feedback.
- Detalle de chunks con paginación, copia rápida del texto y badges de metadata.
- Reingesta y eliminación con confirmaciones.

Comandos útiles:
```bash
make console-install   # instala dependencias (Node 22)
make console           # modo desarrollo
make console-build     # build para despliegue (console/dist)
```

## Widget de chat

El widget en `chat-widget/` consume los endpoints públicos del agente (`/session/start`, `/chat`, `/chat/stream`). Arranca con:
```bash
make ui-install
make ui
```

## API del agente (FastAPI)

| Método | Endpoint           | Descripción |
|--------|--------------------|-------------|
| `GET`  | `/health`          | Healthcheck simple `{"ok": true}`.
| `POST` | `/session/start`   | Crea/recupera cookie `sid` para tracking de sesiones.  
Valores relevantes: `mem_opt_in` (habilita memoria en Redis) y `role` (filtra chunks por metadata `role`).
| `POST` | `/chat`            | Devuelve respuesta completa (JSON) del agente.  
Body (`ChatIn`): `{ question: string, role?: string, user_id?: string, mem_opt_in?: boolean }`.
| `POST` | `/chat/stream`     | Variante SSE que emite eventos `citations` (chunks recuperados) y `final` (respuesta). |

La memoria conversacional se guarda en Redis (`app/agent/memory.py`) cuando `mem_opt_in = true` y existe `user_id` o cookie `sid`.

## API administrativa (`/admin/*`)

Todos los endpoints requieren `Authorization: Bearer <ADMIN_TOKEN>`.

| Método | Endpoint                         | Descripción |
|--------|----------------------------------|-------------|
| `POST` | `/admin/docs`                    | Sube un archivo (multipart). Campos opcionales: `area`, `role`, `vigencia`.|
| `GET`  | `/admin/docs`                    | Lista documentos. Filtros: `q`, `status`, `area`, `role`, `vigencia`, `limit`, `offset`.
| `GET`  | `/admin/docs/{document_id}`      | Detalle con metadata y estado.
| `GET`  | `/admin/docs/{document_id}/chunks` | Lista de chunks con paginación.
| `POST` | `/admin/docs/{document_id}/rehydrate` | Reprocesa el documento en background.
| `DELETE` | `/admin/docs/{document_id}`     | Elimina documento, chunks y archivo almacenado.

La consola consume estos endpoints directamente; puedes probarlos con `make admin-test`.

## Ingesta por lote

- Coloca archivos (`.pdf`, `.docx`, `.txt`, `.md`, `.html`) en `agent-service/app/ingestion/data/`.
- Corre `make ingest` para ejecutar `python -m app.ingestion.ingest` dentro del contenedor.
- El script evita duplicados mediante `checksum` y genera metadata (`role`, `area`, `vigencia`).

## Base de datos

La base usa `pgvector`:
- Tabla `documents`: registro lógico de cada doc (`doc_id` es clave única usada en chunks).
- Tabla `chunks`: texto, metadata JSONB y vector `embedding`.
- Tabla `raw_documents`: estado del pipeline de ingestión (usada por la consola admin).

`make db-shell` abre un `psql` listo para consultas.

## Desarrollo adicional

- El vector store (`app/retrieval/vector_store.py`) combina búsqueda semántica + fallback léxico para asegurar contexto en respuestas.
- Redis almacena las últimas interacciones por usuario (`memory:{user_id}`) con TTL configurable vía `MEMORY_TTL_SECONDS`.
- El historial se adjunta al prompt siempre que el usuario haga opt-in (`mem_opt_in`).

## Troubleshooting

- **Token inválido (401/403)**: revisa que el header `Authorization: Bearer ...` coincida con `ADMIN_TOKEN` tanto en consola como en Postman.
- **Node no encontrado**: define `NODE_BIN=/ruta/a/tu/node/bin make console` si necesitas forzar otra versión.
- **Sin chunks visibles**: asegúrate de haber corrido `make ingest` o de subir documentos desde la consola; la base limpia no contiene contexto por defecto.
- **Error `ivfflat index created with little data`**: mensaje informativo de pgvector tras truncar las tablas; desaparece una vez que ingestas suficientes documentos.

---
Para cualquier tarea adicional (nuevos roles, dashboards, autenticación SSO), documenta los cambios en este README y extiende el Makefile para mantener un flujo de trabajo consistente.
