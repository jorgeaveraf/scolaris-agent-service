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
   - `REDIS_URL`: usado tanto por la memoria conversacional como por la cola de ingestión.
   - `OPENAI_API_KEY`, `MODEL_NAME`, `EMBED_MODEL`, `EMBED_DIM`.
   - `ALLOWED_ORIGINS`: orígenes permitidos para CORS (widget y consola).
   - `RBAC_DISABLED`, `ADMIN_TOKEN`, `JWT_SECRET`/`JWT_PUBLIC_KEY`: controlan el modo compat (token único) o el uso de JWT con roles (`admin`, `curator`, `viewer`) en `/admin/*`.
   - `CHAT_ALLOWED_ROLES`, `CHAT_MAX_QUESTION_CHARS`, `RATE_LIMIT_ENABLED`, `CHAT_IP_LIMIT`, `CHAT_ID_LIMIT`: validación estricta y rate limiting para `/chat`.
   - `AGENT_TIMEOUT_SECONDS`, `LLM_TIMEOUT_SECONDS`, `EMBED_TIMEOUT_SECONDS`: límites de tiempo para el grafo y las llamadas a OpenAI.
   - `UPLOAD_ASYNC_ENABLED`, `UPLOAD_QUEUE_NAME`, `UPLOAD_MAX_PAGES`, `UPLOAD_MAX_PARAGRAPHS`, `UPLOAD_AV_POLICY`: comportamiento de la ingesta asíncrona y validaciones reforzadas antes de encolar un documento.
   - `MAX_UPLOAD_MB`, `ALLOWED_EXTS`, `ALLOWED_MIME_TYPES`: restricciones de tamaño, extensión y MIME.

### Consola (`console/.env`)

Copia `.env.example` y ajusta según tu entorno:

```bash
cp console/.env.example console/.env
```

Variables:
- `VITE_API_BASE`: URL pública del backend (`http://localhost:8000` en local).
- `VITE_CONSOLE_AUTH`: opcional, permite precargar un token (compat) o JWT por rol en desarrollo.

### Widget (`chat-widget/`)

No requiere variables adicionales; consume el backend en `http://localhost:8000` por defecto. Ajusta la URL en código si lo despliegas en otro origen.

### Perfiles de entorno

| Perfil | Ajustes sugeridos | Uso |
|--------|-------------------|-----|
| `dev`  | `RBAC_DISABLED=true`, `ADMIN_TOKEN` definido, límites de rate limit relajados, `UPLOAD_ASYNC_ENABLED=true`, `COOKIE_SECURE=false`. | Desarrollo local rápido; permite seguir usando el token único. |
| `staging` | `RBAC_DISABLED=false`, `JWT_SECRET` (HS256) o `JWT_PUBLIC_KEY` (RS256), límites de rate limit moderados, `STRICT_VALIDATION=true`. | Pre-producción con permisos reales y trazabilidad. |
| `prod` | Igual que `staging`, pero con claves almacenadas en gestor de secretos, `COOKIE_SECURE=true`, `AGENT_FAILOVER_MESSAGE` opcional, límites de rate limit más estrictos. | Producción endurecida. |

El archivo `docker-compose.yml` ofrece el servicio `worker` bajo el perfil `worker`; actívalo con `docker compose --profile worker up -d worker` o mediante `make worker`.

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
| `make worker`             | Levanta el worker de ingestión (cola Redis) bajo el perfil `worker`.
| `make worker-down`        | Detiene el worker de ingestión.
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
- Login basado en tokens firmados (JWT) con roles `admin`, `curator` y `viewer` o, en modo compat, con `ADMIN_TOKEN`.
- Vista de métricas (total, ready, processing, error) y seguimiento del estado `processing`/`ready` tras las ingestas asíncronas.
- Tabla con filtros (status, área, rol, vigencia), paginación y acciones.
- Modal de subida con barra de progreso, metadata opcional y feedback inmediato (respuesta 202).
- Detalle de chunks con paginación, copia rápida del texto y badges de metadata.
- Reingesta y eliminación con confirmaciones controladas por permisos.

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
Body validado (`ChatRequest`): `question` no vacía, `role` opcional (catálogo), `user_id` con formato esperado, `mem_opt_in` booleano.
| `POST` | `/chat/stream`     | Variante SSE que emite eventos `citations` (chunks recuperados) y `final` (respuesta). |
| `POST` | `/auth/login`      | PoC: recibe `{ "password": "..." }`, aplica rate limit y devuelve JWT firmado (`token`, `role`, `expires_in`). |

La memoria conversacional se guarda en Redis (`app/agent/memory.py`) cuando `mem_opt_in = true` y existe `user_id` o cookie `sid`.
Las entradas inválidas responden con **HTTP 400**, las ráfagas excedidas con **HTTP 429** y los timeouts del agente con **HTTP 503** (opcionalmente, mensaje de reserva via `AGENT_FAILOVER_MESSAGE`).

### Login por password (PoC)
En agent-service/.env
- Configura las variables `AUTH_PASSWORD_ADMIN`, `AUTH_PASSWORD_CURATOR`, `AUTH_PASSWORD_VIEWER` según el rol deseado.  
- El endpoint `/auth/login` verifica la contraseña en orden (admin → curator → viewer) usando comparación en tiempo constante.  
- Tras cada solicitud se aplica rate limit específico (`AUTH_LOGIN_RATE_LIMIT` / `AUTH_LOGIN_RATE_WINDOW_SECONDS`).  
- El backend emite un JWT con duración configurable (`JWT_EXPIRES_SECONDS`) y las claims `sub`, `role`, `iat`, `exp`, además de `iss`/`aud` si están definidos en el entorno.  
- Los tokens emitidos son compatibles con el middleware actual y funcionan tanto en modo RBAC normal como en modo compat (`RBAC_DISABLED=true`) junto al `ADMIN_TOKEN`.  
- PoC: no hay gestión de usuarios ni recuperación de contraseña; limita su uso a entornos controlados.

En .env
Backend acepta:
JWT emitidos por POST /auth/login (siempre que el backend no esté en modo compat estricto que lo deshabilite, lo cual no hicimos).
ADMIN_TOKEN únicamente si el backend está en compatibilidad (RBAC_DISABLED=true).
En la UI, el campo “Token manual” solo aparece si:
VITE_ADMIN_TOKEN_UI=true, o
VITE_CONSOLE_AUTH tiene valor (precarga para dev).

Variables relevantes (añadidas):

| Variable | Descripción | Default sugerido |
|----------|-------------|------------------|
| `AUTH_PASSWORD_ADMIN` | Contraseña para obtener rol `admin`. | - |
| `AUTH_PASSWORD_CURATOR` | Contraseña para `curator`. | - |
| `AUTH_PASSWORD_VIEWER` | Contraseña para `viewer`. | - |
| `AUTH_LOGIN_RATE_LIMIT` | Intentos permitidos por ventana. | `5` |
| `AUTH_LOGIN_RATE_WINDOW_SECONDS` | Ventana (segundos). | `300` |
| `JWT_EXPIRES_SECONDS` | Duración del JWT en segundos. | `86400` |
| `JWT_PRIVATE_KEY` | Opcional, clave privada para algoritmos RS*. | - |

## API administrativa (`/admin/*`)

Todos los endpoints requieren `Authorization: Bearer <token>`, donde el token firma un rol (`viewer`, `curator` o `admin`). En modo compat (`RBAC_DISABLED=true`) se acepta `ADMIN_TOKEN` como hasta ahora.

| Método | Endpoint                         | Descripción |
|--------|----------------------------------|-------------|
| `POST` | `/admin/docs`                    | Sube un archivo (multipart). Campos opcionales: `area`, `role`, `vigencia`. Responde 202 y encola la ingesta.|
| `GET`  | `/admin/docs`                    | Lista documentos. Filtros: `q`, `status`, `area`, `role`, `vigencia`, `limit`, `offset`.
| `GET`  | `/admin/docs/{document_id}`      | Detalle con metadata y estado.
| `GET`  | `/admin/docs/{document_id}/chunks` | Lista de chunks con paginación.
| `POST` | `/admin/docs/{document_id}/rehydrate` | Reprocesa el documento en background (cola).
| `DELETE` | `/admin/docs/{document_id}`     | Elimina documento, chunks y archivo almacenado.

La consola consume estos endpoints directamente; puedes probarlos con `make admin-test`.

## Ingesta por lote

- Coloca archivos (`.pdf`, `.docx`, `.txt`, `.md`, `.html`) en `agent-service/app/ingestion/data/`.
- Corre `make ingest` para ejecutar `python -m app.ingestion.ingest` dentro del contenedor (modo batch).
- La ingesta vía API funciona de forma asíncrona: el servicio encola el documento y el *worker* (`agent-service/app/ingestion/worker.py`) lo procesa usando Redis. En Docker Compose se expone como servicio `worker` y puede activarse con perfiles (ver `docker-compose.yml`).
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

- **Token inválido (401/403)**: revisa que el header `Authorization: Bearer ...` tenga un JWT válido (rol permitido) o, en modo compat, que coincida con `ADMIN_TOKEN`.
- **Node no encontrado**: define `NODE_BIN=/ruta/a/tu/node/bin make console` si necesitas forzar otra versión.
- **Sin chunks visibles**: asegúrate de haber corrido `make ingest` o de subir documentos desde la consola; la base limpia no contiene contexto por defecto.
- **Error `ivfflat index created with little data`**: mensaje informativo de pgvector tras truncar las tablas; desaparece una vez que ingestas suficientes documentos.

---
Para cualquier tarea adicional (nuevos roles, dashboards, autenticación SSO), documenta los cambios en este README y extiende el Makefile para mantener un flujo de trabajo consistente.
