# Configuración por servicio

## API (`agent-service`)

| Variable | Descripción | Valores de ejemplo |
|----------|-------------|--------------------|
| `DATABASE_URL` | DSN de Postgres (pgvector). | `postgresql+psycopg://scol:scolpwd@db:5432/scolaris` |
| `REDIS_URL` | Redis usado por memoria conversacional y cola de ingestión. | `redis://redis:6379/0` |
| `OPENAI_API_KEY` | Clave de OpenAI para embeddings y chat. | `your-openai-key` |
| `RBAC_DISABLED` | Activa modo compat (token único) cuando es `true`. | `true` (dev) / `false` (staging/prod) |
| `ADMIN_TOKEN` | Token Bearer de compatibilidad (solo si `RBAC_DISABLED=true`). | `change-me-for-dev` |
| `JWT_SECRET` / `JWT_PUBLIC_KEY` | Claves para firmar/verificar JWT de roles. | HS256 para dev, clave pública para prod. |
| `JWT_PRIVATE_KEY` | Clave privada opcional para firmar con algoritmos RS*. | PEM (solo si usas RS256) |
| `JWT_EXPIRES_SECONDS` | Duración del JWT emitido por `/auth/login`. | `86400` |
| `AUTH_PASSWORD_ADMIN` / `AUTH_PASSWORD_CURATOR` / `AUTH_PASSWORD_VIEWER` | Contraseñas PoC por rol (`/auth/login`). | `scolarisAdmin`, etc. |
| `AUTH_LOGIN_RATE_LIMIT` / `AUTH_LOGIN_RATE_WINDOW_SECONDS` | Rate limit dedicado a `/auth/login`. | `5`, `300` |
| `CHAT_ALLOWED_ROLES` | Catálogo de roles aceptados en `/chat`. | `consultor,ventas,soporte` |
| `CHAT_MAX_QUESTION_CHARS` | Máximo de caracteres permitidos en `question`. | `800` |
| `RATE_LIMIT_ENABLED`, `CHAT_IP_LIMIT`, `CHAT_ID_LIMIT`, `CHAT_RATE_WINDOW_SECONDS` | Configuración del rate limiting (IP/identidad). | `true`, `30`, `15`, `300` |
| `AGENT_TIMEOUT_SECONDS`, `LLM_TIMEOUT_SECONDS`, `EMBED_TIMEOUT_SECONDS` | Timeouts del grafo y de llamadas a OpenAI. | `25`, `20`, `10` |
| `UPLOAD_ASYNC_ENABLED` | Activa ingestión asíncrona (cola + worker). | `true` |
| `UPLOAD_QUEUE_NAME` | Nombre de la lista en Redis para la cola. | `ingest:default` |
| `MAX_UPLOAD_MB`, `ALLOWED_EXTS`, `ALLOWED_MIME_TYPES` | Restricciones de carga para documentos. | `20`, `.pdf,.docx,...` |
| `UPLOAD_MAX_PAGES`, `UPLOAD_MAX_PARAGRAPHS` | Validaciones estructurales adicionales. | `200`, `2000` |
| `UPLOAD_AV_POLICY` | Política del hook AV (`allow`, `monitor`, `deny_all`). | `allow` |
| `ALLOWED_ORIGINS` | Orígenes permitidos para CORS. | `http://localhost:5173,...` |
| `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN` | Configuración de la cookie `sid`. | `false`, `lax`, `.tu-dominio.com` |

## Base de datos (`db`)

| Variable | Descripción | Valores de ejemplo |
|----------|-------------|--------------------|
| `POSTGRES_USER` | Usuario de Postgres. | `scol` |
| `POSTGRES_PASSWORD` | Contraseña de Postgres. | `scolpwd` |
| `POSTGRES_DB` | Base de datos por defecto. | `scolaris` |

## Redis (`redis`)

El contenedor oficial no requiere variables adicionales; expone el puerto `6379`. Ajusta `REDIS_URL` en el API si cambias host/puerto/DB.
