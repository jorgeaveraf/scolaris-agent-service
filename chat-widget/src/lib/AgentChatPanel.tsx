import React, { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { clsx } from "clsx";
import { MessageList } from "./components/MessageList";
import { useChatAgent } from "./hooks/useChatAgent";
import { t } from "./i18n";
import { applyTheme, defaultTheme } from "./theme";
import type { Language, AgentChatBaseProps } from "./types";
import { ChatIcon, CloseIcon, LightningIcon, SendIcon } from "./components/icons";

export interface AgentChatPanelProps extends AgentChatBaseProps {
  onClose?: () => void;
  headerTitle?: string;
  subtitle?: string;
  showClose?: boolean;
  onMessage?: (message: { role: "user" | "agent"; content: string }) => void;
  showCitations?: boolean;
  maxQuestionChars?: number;
  onLanguageChange?: (language: Language) => void;
}

export function AgentChatPanel({
  baseUrl,
  role,
  language = "es",
  memOptIn = false,
  theme,
  onClose,
  headerTitle,
  subtitle,
  showClose = true,
  onMessage,
  showCitations = false,
  maxQuestionChars = 800,
  onLanguageChange,
}: AgentChatPanelProps) {
  const [lang, setLang] = useState<Language>(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem("agent_service_language") : null;
    return stored === "es" || stored === "en" ? stored : language;
  });
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const {
    messages,
    error,
    typing,
    status,
    memoryEnabled,
    setMemoryEnabled,
    sendMessage,
  } = useChatAgent({ baseUrl, role, language: lang, memOptIn });

  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last) onMessage?.({ role: last.role, content: last.content });
  }, [messages, onMessage]);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => { setLang(language); }, [language]);

  const changeLanguage = (value: Language) => {
    setLang(value);
    window.localStorage.setItem("agent_service_language", value);
    onLanguageChange?.(value);
  };

  const disabled = status === "loading" || status === "streaming";

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || input.trim().length > maxQuestionChars || disabled) return;
    sendMessage(input.trim());
    setInput("");
    textareaRef.current?.focus();
  };

  const outlinedButton = useMemo(
    () =>
      clsx(
        "inline-flex items-center gap-2 rounded-full border border-[var(--scol-border)] bg-[var(--scol-surface-alt)] px-3 py-1 text-xs font-semibold text-[var(--scol-text-muted)] shadow-sm",
      ),
    [],
  );

  return (
    <div className="flex h-full min-h-0 w-full max-w-[420px] flex-col rounded-3xl bg-[var(--scol-surface)] shadow-2xl">
      <header className="flex items-start gap-3 border-b border-[var(--scol-border)] px-5 py-4">
        <button
          type="button"
          onClick={onClose}
          className={clsx(
            "flex flex-1 items-start gap-3 rounded-2xl text-left transition",
            onClose && "cursor-pointer hover:bg-[var(--scol-surface-alt)]",
          )}
          aria-label={t(lang, "close")}
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl border-2 border-[var(--scol-primary)] bg-white text-[var(--scol-primary)] shadow-md">
            <span className="text-sm font-bold">AS</span>
          </div>
          <div className="flex-1">
            <p className="text-base font-semibold text-[var(--scol-text)]">
              {headerTitle || t(lang, "title")}
            </p>
            <p className="text-sm text-[var(--scol-text-muted)]">
              {subtitle || t(lang, "subtitle")}
            </p>
          </div>
        </button>
        <select
          aria-label={lang === "es" ? "Idioma del chat" : "Chat language"}
          value={lang}
          onChange={(event) => changeLanguage(event.target.value as Language)}
          className="self-center rounded-lg border border-[var(--scol-border)] bg-[var(--scol-surface)] px-2 py-1 text-xs font-semibold text-[var(--scol-text)]"
        >
          <option value="es">ES</option><option value="en">EN</option>
        </select>
        {showClose && (
          <button
            aria-label={t(lang, "close")}
            className="self-center rounded-full p-2 text-[var(--scol-text-muted)] transition hover:bg-[var(--scol-surface-alt)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--scol-primary)]"
            onClick={onClose}
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        )}
      </header>

      <MessageList messages={messages} language={lang} showCitations={showCitations} />

      <div className="space-y-2 px-4 pb-4">
        {typing && (
          <div className={clsx(outlinedButton, "w-fit")}>
            <LightningIcon className="h-4 w-4" />
            <span>{t(lang, "typing")}</span>
          </div>
        )}
        {error && (
          <div className="rounded-xl border border-[var(--scol-danger)]/20 bg-[var(--scol-danger)]/5 px-3 py-2 text-xs text-[var(--scol-danger)]">
            {error}
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="space-y-3 border-t border-[var(--scol-border)] px-4 pb-2 pt-3">
        <label className="group relative flex cursor-pointer items-center justify-between gap-3 rounded-2xl bg-[var(--scol-surface-alt)] px-3 py-2">
          <input
            type="checkbox"
            checked={memoryEnabled}
            onChange={(e) => setMemoryEnabled(e.target.checked)}
            className="sr-only"
            aria-label={t(lang, "memLabel")}
            aria-describedby="scol-mem-description"
          />
          <div className="flex-1">
            <p className="text-xs font-semibold text-[var(--scol-text)]">
              {t(lang, "memTitle")}
            </p>
            <p id="scol-mem-description" className="max-h-0 overflow-hidden text-[0.72rem] leading-snug text-[var(--scol-text-muted)] opacity-0 transition-[max-height,opacity,margin] duration-200 delay-0 group-hover:mt-1 group-hover:max-h-16 group-hover:opacity-100 group-hover:delay-500 motion-reduce:transition-none">
              {t(lang, "memDescription")}
            </p>
          </div>
          <div className="relative inline-flex items-center">
            <div
              className={clsx(
                "h-5 w-9 rounded-full transition-colors duration-200 ease-out",
                memoryEnabled
                  ? "bg-[var(--scol-primary)]"
                  : "bg-[var(--scol-border)]",
              )}
            >
              <div
                className={clsx(
                  "relative top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ease-out",
                  memoryEnabled
                    ? "translate-x-4 scale-105"
                    : "translate-x-0 scale-100",
                )}
              />
            </div>
          </div>
        </label>
        <div className="relative rounded-2xl border border-[var(--scol-border)] bg-[var(--scol-surface-alt)] px-3 py-2 shadow-inner">
          <textarea
            ref={textareaRef}
            className="scol-scrollbar block w-full resize-none overflow-y-auto bg-transparent text-sm text-[var(--scol-text)] outline-none placeholder:text-[var(--scol-text-muted)]"
            rows={3}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                onSubmit(e);
              }
            }}
            placeholder={t(lang, "placeholder")}
            aria-label={t(lang, "placeholder")}
            disabled={disabled}
          />
          <div className="mt-2 flex items-center justify-between gap-3 text-[var(--scol-text-muted)]">
            <span className={clsx("text-xs", input.trim().length > maxQuestionChars && "text-[var(--scol-danger)]")} aria-live="polite">
              {input.length ? `${input.trim().length}/${maxQuestionChars} ${lang === "es" ? "caracteres" : "characters"}` : ""}
              {input.trim().length > maxQuestionChars ? ` · ${t(lang, "questionTooLong")}` : ""}
            </span>
            <button
              type="submit"
              disabled={disabled || !input.trim() || input.trim().length > maxQuestionChars}
              className={clsx(
                "inline-flex items-center gap-2 rounded-full bg-[var(--scol-primary)] px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:bg-[var(--scol-primary-dark)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--scol-primary)]",
                (disabled || !input.trim() || input.trim().length > maxQuestionChars) && "cursor-not-allowed opacity-50",
              )}
            >
              {disabled ? t(lang, "sending") : t(lang, "send")}
              <SendIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
