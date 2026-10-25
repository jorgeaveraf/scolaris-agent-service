# Agent Service Chat Widget

Widget de chat reutilizable para proyectos React. Incluye un panel y una burbuja flotante con tema configurable y textos en español e inglés.

## Instalación

```bash
npm install agent-service-chat-widget
```

## Uso rápido

```tsx
import { AgentChatBubble } from "agent-service-chat-widget";
import "agent-service-chat-widget/dist/style.css";

function Page() {
  return (
    <AgentChatBubble baseUrl="https://api.example.com" />
  );
}
```

## Componentes

- `AgentChatBubble`: botón flotante configurable que abre el panel (modal/drawer). Props:
  - `baseUrl` (string, requerido): endpoint del backend.
  - `role` (string | null): rol para el agente.
  - `language` ("es" | "en"): idioma de UI.
  - `memOptIn` (boolean): estado inicial de memoria conversacional.
  - `placement` ("bottom-right" | "bottom-left"): posición.
  - `open`, `onOpenChange`: control externo del estado.
  - `theme`: override opcional de colores (ver abajo).
- `AgentChatPanel`: mismo UI del chat, montable sin burbuja. Props:
  - `baseUrl`, `role`, `language`, `memOptIn`, `theme` (igual que arriba).
  - `headerTitle`, `subtitle`, `showClose`, `onClose`.

## Theming

El tema usa CSS vars; puedes sobrescribir parcialmente:

```tsx
const theme = {
  primary: "#1E1E24",
  primaryDark: "#14141A",
  surface: "#ffffff",
  surfaceAlt: "#F7F9FC",
  text: "#0F172A",
  textMuted: "#5B6475",
  border: "#E6E9EF",
  success: "#0BB07B",
  danger: "#DC4B57",
  shadow: "0 20px 60px rgba(6,40,77,0.12)",
};

<AgentChatBubble baseUrl="..." theme={{ primary: "#0A6EB0" }} />;
```

## Comportamiento

- Acceso: lee `/chat/config`; cuando el despliegue exige login, la burbuja muestra el acceso de Google antes de enviar preguntas. Al cerrar sesión desde el chat, elimina la sesión compartida con la consola, vacía la conversación visible y vuelve al acceso de Google; el siguiente inicio permite escoger otra cuenta. Un despliegue público conserva la identificación de navegador para el chat y no muestra salida de cuenta.
- Chat: envía POST `/chat/stream` con SSE manual; reconexión básica y manejo de errores 400/429/503.
- Memoria: interruptor opcional cuya preferencia persiste en el navegador. El panel visible inicia vacío al recargar; con memoria activada, el servidor puede usar el contexto anterior. El historial administrativo se guarda en ambos casos.
- Fuentes: cada respuesta documentada puede mostrar citas a pasajes. La lista se expande al pasar el cursor; el aviso de límites aparece solo dentro de una lista abierta. Saludos y respuestas sin fuentes no llevan ese aviso.
- Accesibilidad: `aria-live` en mensajes, focus visible, cierre con `Esc`, overlay modal/drawer responsive.
- i18n: textos en español/inglés mediante prop `language`.
- Color: si la consola comparte host (o dominio de cookie) con el chat, la burbuja y el panel toman el acento elegido en la consola al volver a enfocarse; `theme` sigue definiendo el resto de la paleta.

## Desarrollo local

```bash
npm install
npm run dev      # playground en http://localhost:5173
npm run build    # genera dist (ESM, CJS, tipos)
```

## Buenas prácticas

- Cargar el CSS de la librería una sola vez en el host (`import "agent-service-chat-widget/dist/style.css"`).
- Para sitios SSR, monta los componentes solo en cliente (usan `window`).
- Usa `baseUrl` sobre HTTPS en producción y configura CORS en el backend.
- Para el cliente web de Google, las direcciones de retorno y variables del servidor, consulta la [guía del monorepo](../README.md#configurar-google-oidc-en-un-proyecto-nuevo).
