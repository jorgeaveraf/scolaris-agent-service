import type { Language } from "./types";

const locale: Record<Language, Record<string, string>> = {
  es: {
    title: "AI Scolaris Agent",
    subtitle: "Resuelve dudas sobre Scolaris al instante.",
    placeholder: "Escribe tu pregunta...",
    send: "Enviar",
    sending: "Enviando...",
    typing: "El agente está escribiendo...",
    citations: "Contexto",
    toggleCitations: "Ver contexto",
    memLabel: "Activar memoria de conversación",
    memTitle: "Memoria de conversación",
    memDescription: "Permite que el asistente recuerde el contexto de esta sesión para respuestas más personalizadas.",
    error400: "Revisa tu pregunta e inténtalo de nuevo.",
    error429: "Has enviado demasiadas consultas. Espera un momento.",
    error503: "El agente tardó demasiado en responder. Intenta de nuevo.",
    errorGeneric: "No pudimos responder. Vuelve a intentarlo.",
    badgeNew: "Nuevo",
    close: "Cerrar",
  },
  en: {
    title: "AI Scolaris",
    subtitle: "Get instant answers about Scolaris.",
    placeholder: "Type your question...",
    send: "Send",
    sending: "Sending...",
    typing: "Assistant is typing...",
    citations: "Context",
    toggleCitations: "View context",
    memLabel: "Enable conversation memory",
    memTitle: "Conversation memory",
    memDescription: "Let the assistant remember this session’s context for more tailored answers.",
    error400: "Please review your question and try again.",
    error429: "Too many requests. Please slow down.",
    error503: "The agent timed out. Try again.",
    errorGeneric: "We could not answer now. Please retry.",
    badgeNew: "New",
    close: "Close",
  },
};

export function t(lang: Language, key: string): string {
  return locale[lang]?.[key] || locale.es[key] || key;
}
