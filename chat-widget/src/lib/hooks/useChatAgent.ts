import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, Language } from "../types";
import { t } from "../i18n";
import { SseParser, type SseEvent } from "../sse";

type Status = "idle" | "loading" | "streaming" | "error";

interface UseChatAgentOptions {
  baseUrl: string;
  role?: string | null;
  language: Language;
  memOptIn?: boolean;
}

const STORAGE_USER_ID = "agent_user_id";
const STORAGE_MEM_OPT_IN = "agent_mem_opt_in";

const ensureUserId = () => {
  if (typeof window === "undefined") return null;
  const cached = window.localStorage.getItem(STORAGE_USER_ID);
  if (cached) return cached;
  const value = crypto.randomUUID ? crypto.randomUUID() : `user-${Date.now()}`;
  window.localStorage.setItem(STORAGE_USER_ID, value);
  return value;
};

export function useChatAgent({ baseUrl, role, language, memOptIn }: UseChatAgentOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [typing, setTyping] = useState(false);
  const [memoryEnabled, setMemoryEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return Boolean(memOptIn);
    const stored = window.localStorage.getItem(STORAGE_MEM_OPT_IN);
    return stored === null ? Boolean(memOptIn) : stored === "1";
  });
  const controllerRef = useRef<AbortController | null>(null);
  const userIdRef = useRef<string | null>(null);
  const mountedRef = useRef(true);
  const activeMessageIdRef = useRef<string | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    userIdRef.current = ensureUserId();
    return () => {
      mountedRef.current = false;
      controllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_MEM_OPT_IN, memoryEnabled ? "1" : "0");
  }, [memoryEnabled]);

  // Kick session cookie
  useEffect(() => {
    fetch(`${baseUrl}/session/start`, { method: "POST", credentials: "include" }).catch(() => {});
  }, [baseUrl]);

  const appendMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const updateMessage = useCallback((id: string, update: (message: ChatMessage) => ChatMessage) => {
    if (!mountedRef.current) return;
    setMessages((prev) => prev.map((message) => (message.id === id ? update(message) : message)));
  }, []);

  const stopStreaming = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    const messageId = activeMessageIdRef.current;
    if (messageId) {
      updateMessage(messageId, (message) => ({
        ...message,
        status: message.content ? "error" : "completed",
      }));
    }
    activeMessageIdRef.current = null;
    setTyping(false);
    setStatus("idle");
  }, [updateMessage]);

  const handleError = useCallback(
    (code?: number) => {
      const message =
        code === 400
          ? t(language, "error400")
          : code === 429
            ? t(language, "error429")
            : code === 503
              ? t(language, "error503")
              : t(language, "errorGeneric");
      setError(message);
      setStatus("error");
      setTyping(false);
    },
    [language],
  );

  const sendMessage = useCallback(
    async (content: string) => {
      setError(null);
      if (!content.trim()) return;
      controllerRef.current?.abort();
      const userId = userIdRef.current;
      const payload = {
        question: content.trim(),
        language,
        role,
        user_id: userId || undefined,
        mem_opt_in: memoryEnabled,
      };

      appendMessage({ id: crypto.randomUUID(), role: "user", content });
      setStatus("loading");
      setTyping(true);
      const controller = new AbortController();
      let assistantMessageId: string | null = null;

      try {
        controllerRef.current = controller;
        const response = await fetch(`${baseUrl}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          handleError(response.status);
          return;
        }

        assistantMessageId = crypto.randomUUID();
        const streamMessageId = assistantMessageId;
        activeMessageIdRef.current = assistantMessageId;
        appendMessage({
          id: assistantMessageId,
          role: "agent",
          content: "",
          status: "streaming",
        });
        setStatus("streaming");
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        const parser = new SseParser();
        let accumulated = "";
        let streamFailed = false;

        const processEvent = (event: SseEvent) => {
          let parsed: any;
          try {
            parsed = JSON.parse(event.data);
          } catch {
            return;
          }

          if (event.event === "delta" && typeof parsed?.text === "string") {
            accumulated += parsed.text;
            updateMessage(streamMessageId, (message) => ({
              ...message,
              content: accumulated,
              status: "streaming",
            }));
          } else if (event.event === "citations" && Array.isArray(parsed)) {
            const citations = parsed.map((item: any) => ({
              title: item.title || item.filename || "",
              url: typeof item.url === "string" ? item.url : undefined,
              snippet: typeof item.snippet === "string" ? item.snippet : undefined,
            }));
            updateMessage(streamMessageId, (message) => ({ ...message, citations }));
          } else if (event.event === "disclaimer" && typeof parsed?.text === "string") {
            updateMessage(streamMessageId, (message) => ({ ...message, disclaimer: parsed.text }));
          } else if (event.event === "metadata" && parsed && typeof parsed === "object") {
            updateMessage(streamMessageId, (message) => ({ ...message, metadata: parsed }));
          } else if (event.event === "done") {
            updateMessage(streamMessageId, (message) => ({ ...message, status: "completed" }));
          } else if (event.event === "final" && typeof parsed?.answer === "string") {
            accumulated = parsed.answer;
            updateMessage(streamMessageId, (message) => ({
              ...message,
              content: parsed.answer,
              status: "completed",
            }));
          } else if (event.event === "error") {
            streamFailed = true;
            const controlledError = t(language, "errorGeneric");
            updateMessage(streamMessageId, (message) => ({
              ...message,
              content: message.content || controlledError,
              status: "error",
              errorMessage: message.content ? controlledError : undefined,
            }));
            setError(controlledError);
          }
        };

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          parser.feed(decoder.decode(value, { stream: true })).forEach(processEvent);
        }
        parser.feed(decoder.decode(), true).forEach(processEvent);

        setTyping(false);
        setStatus(streamFailed ? "error" : "idle");
        if (!streamFailed) {
          updateMessage(streamMessageId, (message) => ({
            ...message,
            content: message.content || t(language, "errorGeneric"),
            status: "completed",
          }));
        }
      } catch (err: any) {
        if (err?.name === "AbortError") {
          if (assistantMessageId) {
            updateMessage(assistantMessageId, (message) => ({
              ...message,
              status: message.content ? "error" : "completed",
            }));
          }
          return;
        }
        if (assistantMessageId) {
          updateMessage(assistantMessageId, (message) => ({
            ...message,
            content: message.content || t(language, "errorGeneric"),
            status: "error",
            errorMessage: message.content ? t(language, "errorGeneric") : undefined,
          }));
        }
        handleError();
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null;
        if (activeMessageIdRef.current === assistantMessageId) activeMessageIdRef.current = null;
      }
    },
    [appendMessage, baseUrl, handleError, language, memoryEnabled, role, updateMessage],
  );

  const reset = useCallback(() => {
    stopStreaming();
    setMessages([]);
    setStatus("idle");
    setError(null);
  }, [stopStreaming]);

  return {
    messages,
    status,
    error,
    typing,
    memoryEnabled,
    setMemoryEnabled,
    sendMessage,
    reset,
    stopStreaming,
  };
}
