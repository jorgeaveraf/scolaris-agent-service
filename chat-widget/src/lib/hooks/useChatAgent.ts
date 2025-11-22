import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, Language } from "../types";
import { t } from "../i18n";

type Status = "idle" | "loading" | "streaming" | "error";

interface UseChatAgentOptions {
  baseUrl: string;
  role?: string | null;
  language: Language;
  memOptIn?: boolean;
}

const STORAGE_USER_ID = "scolaris_user_id";
const STORAGE_MEM_OPT_IN = "scolaris_mem_opt_in";

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
  const [memoryEnabled, setMemoryEnabled] = useState<boolean>(Boolean(memOptIn));
  const controllerRef = useRef<AbortController | null>(null);
  const userIdRef = useRef<string | null>(null);

  useEffect(() => {
    userIdRef.current = ensureUserId();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem(STORAGE_MEM_OPT_IN);
    setMemoryEnabled(stored === "1");
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

  const stopStreaming = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setTyping(false);
  }, []);

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
      const userId = userIdRef.current;
      const payload = {
        question: content.trim(),
        role,
        user_id: userId || undefined,
        mem_opt_in: memoryEnabled,
      };

      appendMessage({ id: crypto.randomUUID(), role: "user", content });
      setStatus("loading");
      setTyping(true);

      try {
        const controller = new AbortController();
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

        setStatus("streaming");
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        let finalAnswer = "";
        let citations: ChatMessage["citations"];

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\n\n");
          buffer = events.pop() ?? "";
          for (const raw of events) {
            if (!raw.trim()) continue;
            const [, dataLine] = raw.split("data:");
            if (!dataLine) continue;
            const payload = dataLine.trim();
            try {
              const parsed = JSON.parse(payload);
              if (parsed.answer) {
                finalAnswer = parsed.answer;
              } else if (Array.isArray(parsed)) {
                // citations from server as list
                citations = parsed.map((item: any) => ({
                  title: item.title || item.filename || "",
                  content: item.content || item.text || "",
                }));
              }
            } catch {
              // ignore malformed chunks
            }
          }
        }

        setTyping(false);
        setStatus("idle");
        appendMessage({
          id: crypto.randomUUID(),
          role: "agent",
          content: finalAnswer || t(language, "errorGeneric"),
          citations,
        });
      } catch (err: any) {
        if (err?.name === "AbortError") return;
        handleError();
      } finally {
        controllerRef.current = null;
      }
    },
    [appendMessage, baseUrl, handleError, language, memoryEnabled, role],
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
