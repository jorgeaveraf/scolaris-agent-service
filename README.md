# Agent Service

Base reutilizable para un asistente que responde con documentos, una burbuja de chat y una consola para gestionar fuentes, acceso e historial. El comportamiento de cada despliegue se define con configuración; no contiene reglas de Sightbridge ni de un sector concreto.

## Componentes

- `agent-service/`: API FastAPI, carga e indexación de documentos, recuperación, respuestas y control de acceso.
- `chat-widget/`: burbuja y panel de conversación en React.
- `console/`: vista general, documentos, personas, historial y observabilidad.
- `embedding-service/` y `llm-service/`: servicios internos de modelos.
- PostgreSQL con pgvector y Redis para datos, cola y memoria opcional.

## Inicio local

Necesitas Docker Compose, Node.js 22.12 o superior y una clave válida de la API del modelo. Copia `agent-service/.env.example` a `agent-service/.env` y `console/.env.example` a `console/.env`. Completa las credenciales de Google, `OPENAI_API_KEY` y el correo del primer administrador en los archivos locales; **no los subas a Git**.

```bash
docker compose up -d --build
docker compose --profile worker up -d worker
npm install --prefix chat-widget
npm install --prefix console
npm run dev --prefix chat-widget  # localhost:5173
npm run dev --prefix console      # localhost:5174
```

El backend local escucha en `http://localhost:8000`. `GET /ready` comprueba sus dependencias. Los documentos se suben desde la consola; el worker los procesa. El archivo original permanece disponible para vista y descarga dentro del detalle, sujeto al acceso administrativo.

## Configurar Google OIDC en un proyecto nuevo

1. Crea un proyecto en [Google Cloud Console](https://console.cloud.google.com/) bajo la organización que administrará la aplicación. En **Google Auth Platform → Branding**, define el nombre que verán los usuarios, un correo de soporte y los datos de contacto solicitados. Usa una marca neutral para la base; la copia específica puede usar un cliente web independiente dentro del mismo proyecto.
2. En **Audience**, elige **External** si accederán cuentas fuera de tu organización. En estado **Testing**, Google limita el acceso a usuarios de prueba añadidos allí; el registro de personas dentro de nuestra consola no sustituye esa lista. Para que el administrador pueda dar acceso a nuevas cuentas externas sin incorporarlas también como usuarios de prueba, revisa los requisitos de publicación de Google y coloca la aplicación en **In production**. No presupongas que la aprobación de marca o de permisos adicionales es inmediata.
3. En **Data access**, solicita únicamente los permisos de identidad que usa esta aplicación: `openid`, `email` y `profile`. No necesita acceso a Gmail, Drive ni otros datos de Google.
4. En **Clients**, crea un cliente OAuth de tipo **Web application**. Añade como retorno autorizado `http://localhost:8000/auth/google/callback` para desarrollo. El valor de `GOOGLE_OIDC_REDIRECT_URI` debe coincidir exactamente. Al desplegar, añade el retorno HTTPS real y actualiza esa variable. Usa un cliente distinto para cada despliegue si necesitas separar sus retornos y credenciales.
5. Guarda el ID y secreto del cliente en `agent-service/.env` como `GOOGLE_OIDC_CLIENT_ID` y `GOOGLE_OIDC_CLIENT_SECRET`. Configura `OIDC_ENABLED=true`, una clave aleatoria privada en `OIDC_SESSION_SECRET`, y el primer correo administrador en `OIDC_BOOTSTRAP_ADMINS`. Al iniciar, ese correo se incorpora a la lista local de acceso; los demás se administran desde **Personas**. Google verifica identidad y la base asigna el rol.
6. Ajusta `OIDC_CHAT_URL`, `OIDC_CONSOLE_URL` y `ALLOWED_ORIGINS` a las direcciones reales. En `console/.env`, configura `VITE_API_BASE` con la URL de la API. En producción usa HTTPS y `COOKIE_SECURE=true`. Sirve chat, consola y API bajo el mismo sitio registrable para que la cookie de sesión funcione con `SameSite=lax`.

La consola y el chat comparten una sesión del servidor. La cookie es `HttpOnly`; el navegador no guarda tokens de Google en `localStorage`. La configuración actual solo pide identidad básica. Consulta la [guía oficial del cliente web OAuth](https://developers.google.com/identity/protocols/oauth2/web-server) y las [reglas de audiencia y publicación](https://support.google.com/cloud/answer/15549945?hl=en) si cambia la interfaz de Cloud o los requisitos de verificación.

## Comportamiento por despliegue

- `CHAT_LOGIN_REQUIRED=true` exige sesión para usar el chat. La consola siempre exige sesión y rol `viewer`, `curator` o `admin`.
- `CHAT_SHOW_CITATIONS=true` presenta fuentes; `ANSWER_REQUIRE_SOURCES=true` retiene respuestas sin respaldo suficiente.
- `AGENT_SCOPE_POLICY` delimita temas y `AGENT_ADVICE_POLICY` describe solicitudes personalizadas que deben rechazarse. Si están vacías, la base no añade esos límites de dominio.
- `AGENT_DISCLAIMER_ES` y `AGENT_DISCLAIMER_EN` personalizan el aviso. En esta interfaz aparece junto a las fuentes de respuestas documentadas, después de expandirlas; no aparece en saludos ni respuestas sin fuente. Un encargo que exija aviso en *cada* respuesta requiere una presentación adicional en su copia.
- La carga de PDF, DOCX, TXT, Markdown o HTML admite un enlace público HTTPS opcional. Ese enlace se conserva como procedencia para las citas. Verifica cada enlace y lista las fuentes del despliegue en su README.
- Cada intercambio completo guarda pregunta, respuesta, fuentes, fecha y correo verificado (o visitante en chat público), sin depender del interruptor de memoria. Solo el administrador puede consultar el historial. La memoria opcional afecta el contexto del usuario, no el registro administrativo.
- La consola separa información operativa de observabilidad técnica. Los fragmentos de búsqueda están dentro del detalle de cada documento.

La selección de pasajes y comprobación de respuestas emplean un modelo: rechazan respuestas sin respaldo encontrado, pero no garantizan exactitud perfecta. Prueba las preguntas reales y revisa las citas antes de entregar una copia.

## Verificación y entrega

```bash
npm run build --prefix chat-widget
npm run build --prefix console
make api-test
```

`make api-test` monta los tests temporalmente; la imagen de producción no los incluye. Para una entrega concreta, prueba login, permisos, carga de fuentes, respuestas citadas, rechazos, memoria e historial; documenta sus fuentes, limitaciones, URL desplegada y horas empleadas. Mantén credenciales, documentos privados y datos de usuarios fuera del repositorio.
