# @scolaris/chat-widget

Widget corporativo de chat para Scolaris, pensado como librería reutilizable en proyectos React. Incluye un panel premium y una burbuja flotante lista para producción, estilos alineados al sitio principal y soporte i18n (es/en).

## Instalación

```bash
npm install @scolaris/chat-widget
```

## Uso rápido

```tsx
import { ScolarisChatBubble } from "@scolaris/chat-widget";
import "@scolaris/chat-widget/dist/style.css";

function Page() {
  return (
    <ScolarisChatBubble baseUrl="https://api.scolaris.com" role="ventas" />
  );
}
```

## Componentes

- `ScolarisChatBubble`: botón flotante configurable que abre el panel (modal/drawer). Props:
  - `baseUrl` (string, requerido): endpoint del backend (ej. `https://api.scolaris.com`).
  - `role` (string | null): rol para el agente.
  - `language` ("es" | "en"): idioma de UI.
  - `memOptIn` (boolean): estado inicial de memoria conversacional.
  - `placement` ("bottom-right" | "bottom-left"): posición.
  - `open`, `onOpenChange`: control externo del estado.
  - `theme`: override opcional de colores (ver abajo).
- `ScolarisChatPanel`: mismo UI del chat, montable sin burbuja. Props:
  - `baseUrl`, `role`, `language`, `memOptIn`, `theme` (igual que arriba).
  - `headerTitle`, `subtitle`, `showClose`, `onClose`.

## Theming

El tema usa CSS vars; puedes sobrescribir parcialmente:

```tsx
const theme = {
  primary: "#0F8CDD",
  primaryDark: "#0A6EB0",
  surface: "#ffffff",
  surfaceAlt: "#F7F9FC",
  text: "#0F172A",
  textMuted: "#5B6475",
  border: "#E6E9EF",
  success: "#0BB07B",
  danger: "#DC4B57",
  shadow: "0 20px 60px rgba(6,40,77,0.12)",
};

<ScolarisChatBubble baseUrl="..." theme={{ primary: "#0A6EB0" }} />;
```

## Comportamiento

- Sesión: inicia `/session/start` automáticamente con cookies + `user_id` persistido en localStorage.
- Chat: envía POST `/chat/stream` con SSE manual; reconexión básica y manejo de errores 400/429/503.
- Memoria: toggle opt‑in visible, persiste preferencia en localStorage.
- Accesibilidad: `aria-live` en mensajes, focus visible, cierre con `Esc`, overlay modal/drawer responsive.
- i18n: textos en español/inglés mediante prop `language`.

## Desarrollo local

```bash
npm install
npm run dev      # playground en http://localhost:5173
npm run build    # genera dist (ESM, CJS, tipos)
```

## Buenas prácticas

- Cargar el CSS de la librería una sola vez en el host (`import "@scolaris/chat-widget/dist/style.css"`).
- Para sitios SSR, monta los componentes solo en cliente (usan `window`).
- Usa `baseUrl` sobre HTTPS en producción y configura CORS en el backend.
