import type { Language } from "./types";

const locale: Record<Language, Record<string, string>> = {
  es: {
    title: "Agent Service",
    subtitle: "Haz tus preguntas al asistente.",
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
    questionTooLong: "Reduce la pregunta para enviarla.",
    error429: "Has enviado demasiadas consultas. Espera un momento.",
    error503: "El agente tardó demasiado en responder. Intenta de nuevo.",
    errorGeneric: "No pudimos responder. Vuelve a intentarlo.",
    badgeNew: "Nuevo",
    close: "Cerrar",
    logout: "Cerrar sesión",
    logoutError: "No se pudo cerrar la sesión. Inténtalo de nuevo.",
  },
  en: {
    title: "Agent Service",
    subtitle: "Ask the assistant a question.",
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
    questionTooLong: "Shorten your question to send it.",
    error429: "Too many requests. Please slow down.",
    error503: "The agent timed out. Try again.",
    errorGeneric: "We could not answer now. Please retry.",
    badgeNew: "New",
    close: "Close",
    logout: "Sign out",
    logoutError: "Could not sign out. Please try again.",
  },
};

export function t(lang: Language, key: string): string {
  return locale[lang]?.[key] || locale.es[key] || key;
}
