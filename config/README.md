# Configuración de Agent Service

Usa `agent-service/.env.example` y `console/.env.example` como plantillas. Crea los `.env` localmente y no los subas a Git. La [guía de Google OIDC](../README.md#configurar-google-oidc-en-un-proyecto-nuevo) explica cómo crear el proyecto, el cliente web y los retornos autorizados.

| Grupo | Variables principales | Función |
|---|---|---|
| Identidad | `OIDC_ENABLED`, `GOOGLE_OIDC_CLIENT_ID`, `GOOGLE_OIDC_CLIENT_SECRET`, `GOOGLE_OIDC_REDIRECT_URI`, `OIDC_SESSION_SECRET`, `OIDC_BOOTSTRAP_ADMINS` | Google comprueba identidad y PostgreSQL asigna acceso por correo. |
| Direcciones | `OIDC_CHAT_URL`, `OIDC_CONSOLE_URL`, `ALLOWED_ORIGINS`, `VITE_API_BASE` | Deben reflejar los orígenes reales del chat, consola y API. |
| Cookies | `COOKIE_SECURE`, `COOKIE_SAMESITE` | Usa HTTPS y cookies seguras en despliegue. |
| Chat | `CHAT_LOGIN_REQUIRED`, `CHAT_SHOW_CITATIONS`, `ANSWER_REQUIRE_SOURCES`, `SOURCE_MIN_SCORE` | Acceso y exigencia de respaldo documental. |
| Reglas | `AGENT_SCOPE_POLICY`, `AGENT_ADVICE_POLICY`, `AGENT_DISCLAIMER_ES`, `AGENT_DISCLAIMER_EN` | Límites y aviso específicos de cada copia. |
| Documentos | `MAX_UPLOAD_MB`, `ALLOWED_EXTS`, `ALLOWED_MIME_TYPES`, `UPLOAD_ASYNC_ENABLED` | Validación y procesamiento de archivos. |
| Modelos | `OPENAI_API_KEY`, `MODEL_NAME`, `EMBED_MODEL`, `EMBED_DIM` | Generación y embeddings. |
| Datos | `DATABASE_URL`, `REDIS_URL` | PostgreSQL/pgvector, cola y memoria opcional. |

Las variables `VITE_*` son públicas en el navegador; nunca pongas allí secretos. La base de datos local conserva sus identificadores históricos para no romper los datos actuales. Para una instalación nueva se pueden elegir otros identificadores al provisionar PostgreSQL, manteniendo `DATABASE_URL` y Docker Compose de acuerdo entre sí.
