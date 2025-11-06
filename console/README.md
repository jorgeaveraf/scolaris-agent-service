# Scolaris Agent Console

Panel administrativo para gestionar la memoria RAG del agente de Scolaris. Permite cargar documentos con metadata, revisar su estado, analizar los chunks generados y ejecutar acciones como reingesta o eliminación.

## Requisitos

- Node.js 22.12 o superior (se recomienda utilizar `nvm` o instalar el binario oficial).
- Dependencias instaladas con `npm install` dentro del directorio `console/`.
- Servicio del agente ejecutándose en `http://localhost:8000` (o ajustar `VITE_API_BASE`).

## Configuración de entorno

1. Copia el archivo de ejemplo y ajusta los valores según tu entorno:

   ```bash
   cp console/.env.example console/.env
   ```

2. Variables disponibles:

   - `VITE_API_BASE`: URL base del backend del agente.
   - `VITE_CONSOLE_AUTH`: (opcional) token JWT o Bearer de compatibilidad precargado para desarrollo (rol `viewer`/`curator`/`admin`).

## Comandos principales

```bash
npm install        # Instala dependencias
npm run dev        # Levanta la consola en modo desarrollo (http://localhost:5173)
npm run build      # Genera la build de producción en console/dist
npm run preview    # Previsualiza la build generada
```

> Desde la raíz del monorepo puedes usar `npm run dev --prefix console` y `npm run build --prefix console`.

## Características clave

- Login basado en tokens firmados y persistencia en `localStorage`; admite contraseña o token manual (cuando el backend está en modo compat).
- Dashboard con métricas de documentos (`ready`, `processing`, `error`).
- Gestión completa de documentos: filtros avanzados, subida con progreso, reingesta y eliminación.
- Permisos aplicados según rol (`viewer`, `curator`, `admin`) para las acciones sensibles.
- Explorador de chunks con metadatos, paginación y copia rápida del contenido.
- Diseño responsivo con React, TypeScript, Vite y Tailwind CSS.
- Componentes reutilizables (modales, toasts, badges) y feedback visual en todas las acciones.

## Inicio de sesión por contraseña

- La vista de login permite ingresar una contraseña; si coincide con las variables `AUTH_PASSWORD_*` del backend, la API emite un JWT automáticamente (`POST /auth/login`).
- El token y el rol se guardan en `localStorage` (`scolaris_console_token`, `scolaris_console_role`) y se reutilizan en cada petición `/admin/*`.
- Si se excede el rate limit de `/auth/login`, el frontend muestra un error genérico hasta que la ventana se reinicie.
- Cuando `RBAC_DISABLED=true`, se habilita además la pestaña para pegar manualmente un token (`ADMIN_TOKEN` o uno generado vía `VITE_CONSOLE_AUTH`).

## Estructura relevante

```
console/
├─ src/
│  ├─ api/                # Cliente axios y llamadas al backend
│  ├─ components/         # UI reutilizable y elementos de layout
│  ├─ features/           # Lógica específica de documentos y chunks
│  ├─ pages/              # Páginas principales (login, dashboard, etc.)
│  └─ providers/          # Contextos (auth, rutas protegidas)
├─ public/                # Recursos estáticos (logo)
├─ .env.example           # Variables de entorno para desarrollo
└─ vite.config.ts         # Configuración de Vite
```

## Notas

- El token se guarda bajo la llave `scolaris_console_token`.
- Los endpoints consumidos corresponden al módulo `/admin` del agente existente.
- Si la base de datos está limpia, la tabla mostrará un mensaje orientativo hasta que cargues el primer documento.
