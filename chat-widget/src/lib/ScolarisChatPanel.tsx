import React, { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { clsx } from "clsx";
import { MessageList } from "./components/MessageList";
import { useChatAgent } from "./hooks/useChatAgent";
import { t } from "./i18n";
import { applyTheme, defaultTheme } from "./theme";
import type { Language, ScolarisChatBaseProps } from "./types";
import { ChatIcon, CloseIcon, LightningIcon, SendIcon } from "./components/icons";
import botIcon from "./botIcon.png";

export interface ScolarisChatPanelProps extends ScolarisChatBaseProps {
  onClose?: () => void;
  headerTitle?: string;
  subtitle?: string;
  showClose?: boolean;
  onMessage?: (message: { role: "user" | "agent"; content: string }) => void;
}

export function ScolarisChatPanel({
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
}: ScolarisChatPanelProps) {
  const lang: Language = language;
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

  const disabled = status === "loading" || status === "streaming";

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
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
    <div className="flex h-full max-h-[700px] w-full max-w-[420px] flex-col rounded-3xl bg-[var(--scol-surface)] shadow-2xl">
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
            <img
              src={botIcon}
              alt="Asistente Scolaris"
              className="h-9 w-9 rounded-2xl object-contain"
            />
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
        {showClose && (
          <button
            aria-label={t(lang, "close")}
            className="rounded-full p-2 text-[var(--scol-text-muted)] transition hover:bg-[var(--scol-surface-alt)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--scol-primary)]"
            onClick={onClose}
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        )}
      </header>

      <MessageList messages={messages} language={lang} />

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

      <form onSubmit={onSubmit} className="space-y-3 border-t border-[var(--scol-border)] px-4 py-3">
        <label className="flex cursor-pointer items-center justify-between gap-3 rounded-2xl bg-[var(--scol-surface-alt)] px-3 py-2">
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
            <p
              id="scol-mem-description"
              className="mt-0.5 text-[0.72rem] leading-snug text-[var(--scol-text-muted)]"
            >
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
            className="block w-full resize-none bg-transparent text-sm text-[var(--scol-text)] outline-none placeholder:text-[var(--scol-text-muted)]"
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
          <div className="mt-2 flex items-center justify-between text-[var(--scol-text-muted)]">
            <span className="text-xs">
              {input.length ? `${input.length} chars` : ""}
            </span>
            <button
              type="submit"
              disabled={disabled}
              className={clsx(
                "inline-flex items-center gap-2 rounded-full bg-[var(--scol-primary)] px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:bg-[var(--scol-primary-dark)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--scol-primary)]",
                disabled && "cursor-not-allowed opacity-60",
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
