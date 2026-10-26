import React, { useEffect, useMemo, useState } from "react";
import { clsx } from "clsx";
import { Overlay, PanelShell, Drawer } from "./components/Primitives";
import { AgentChatPanel } from "./AgentChatPanel";
import type { Language, AgentChatBaseProps } from "./types";
import { AgentIcon, BadgeDot } from "./components/icons";
import { defaultTheme } from "./theme";
import { readSharedAccent } from "./accent";

export interface AgentChatBubbleProps extends AgentChatBaseProps {
  placement?: "bottom-right" | "bottom-left";
  launcherInset?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  consoleUrl?: string;
  showConsoleLink?: boolean;
}

export function AgentChatBubble({
  baseUrl,
  role,
  language = "es",
  memOptIn,
  theme,
  placement = "bottom-right",
  launcherInset = false,
  open,
  onOpenChange,
  consoleUrl,
  showConsoleLink = true,
}: AgentChatBubbleProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = open ?? internalOpen;
  const [unread, setUnread] = useState(0);
  const isMobile = useIsMobile();
  const [access, setAccess] = useState<"checking" | "granted" | "required" | "error">("checking");
  const [showCitations, setShowCitations] = useState(false);
  const [loginRequired, setLoginRequired] = useState(false);
  const [consoleAccess, setConsoleAccess] = useState(false);
  const [maxQuestionChars, setMaxQuestionChars] = useState(800);
  const [selectedLanguage, setSelectedLanguage] = useState<Language>(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem("agent_service_language") : null;
    return stored === "es" || stored === "en" ? stored : language;
  });
  const [sharedAccent, setSharedAccent] = useState(readSharedAccent);

  useEffect(() => {
    const syncAccent = () => {
      const next = readSharedAccent();
      setSharedAccent((current) => current?.primary === next?.primary && current?.primaryDark === next?.primaryDark ? current : next);
    };
    window.addEventListener("focus", syncAccent);
    window.addEventListener("agent-service-accent-change", syncAccent);
    document.addEventListener("visibilitychange", syncAccent);
    const interval = window.setInterval(() => { if (document.visibilityState === "visible") syncAccent(); }, 1500);
    return () => {
      window.removeEventListener("focus", syncAccent);
      window.removeEventListener("agent-service-accent-change", syncAccent);
      document.removeEventListener("visibilitychange", syncAccent);
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("chat") === "1") {
      setInternalOpen(true);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    setAccess("checking");
    setConsoleAccess(false);
    fetch(`${baseUrl}/chat/config`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Chat configuration unavailable");
        const config = await response.json();
        if (!active) return;
        setShowCitations(config.show_citations === true);
        setLoginRequired(config.login_required === true);
        if (Number.isInteger(config.max_question_chars) && config.max_question_chars > 0) {
          setMaxQuestionChars(config.max_question_chars);
        }
        let signedIn = false;
        try {
          const me = await fetch(`${baseUrl}/auth/me`, { credentials: "include" });
          signedIn = me.ok;
          if (me.ok) {
            const identity = await me.json();
            if (!active) return;
            setConsoleAccess(["viewer", "curator", "admin"].includes(identity.role));
          }
        } catch {
          if (config.login_required === true) throw new Error("Session unavailable");
        }
        if (active) setAccess(config.login_required === true && !signedIn ? "required" : "granted");
      })
      .catch(() => { if (active) setAccess("error"); });
    return () => { active = false; };
  }, [baseUrl, isOpen]);

  const handleOpenChange = (value: boolean) => {
    if (value) setAccess("checking");
    onOpenChange?.(value);
    setInternalOpen(value);
    if (value) setUnread(0);
  };

  const signOut = async () => {
    const response = await fetch(`${baseUrl}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) throw new Error("Sign out failed");
    setAccess("required");
    setConsoleAccess(false);
    setUnread(0);
    handleOpenChange(false);
    window.dispatchEvent(new Event("agent-service-auth-change"));
  };

  useEffect(() => {
    if (open !== undefined) {
      setInternalOpen(open);
      if (open) setUnread(0);
    }
  }, [open]);

  const bubblePosition = placement === "bottom-right" ? "right-6" : "left-6";
  const resolvedConsoleUrl = consoleUrl ?? (typeof window !== "undefined" ? new URL("/console/", window.location.origin).toString() : "/console/");

  const effectiveTheme = useMemo(() => ({ ...defaultTheme, ...(theme || {}), ...(sharedAccent || {}) }), [theme, sharedAccent]);
  const themeStyle = useMemo(() => {
    const merged = effectiveTheme;
    return {
      "--scol-primary": merged.primary,
      "--scol-primary-dark": merged.primaryDark,
      "--scol-surface": merged.surface,
      "--scol-surface-alt": merged.surfaceAlt,
      "--scol-text": merged.text,
      "--scol-text-muted": merged.textMuted,
      "--scol-border": merged.border,
      "--scol-success": merged.success,
      "--scol-danger": merged.danger,
      "--scol-shadow": merged.shadow,
    } as React.CSSProperties;
  }, [effectiveTheme]);

  return (
    <div style={themeStyle}>
      <div className={clsx("group fixed z-30", launcherInset ? "bottom-32" : "bottom-6", bubblePosition)}>
        {!isOpen && (
          <span className={clsx(
            "pointer-events-none absolute bottom-full mb-3 w-max max-w-[220px] rounded-xl border border-[var(--scol-border)] bg-white px-3 py-2 text-xs font-medium text-[var(--scol-text)] shadow-lg opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100",
            placement === "bottom-right" ? "right-0" : "left-0",
          )}>
            {selectedLanguage === "es" ? "Hola, estoy aquí para ayudarte." : "Hi, I’m here to help."}
          </span>
        )}
        <button
          onClick={() => handleOpenChange(!isOpen)}
          className="agent-chat-launcher relative flex h-14 w-14 items-center justify-center rounded-full border-2 border-[var(--scol-primary)] bg-white text-[var(--scol-primary)] shadow-xl transition hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--scol-primary)]"
          aria-label={selectedLanguage === "es" ? "Abrir chat Agent Service" : "Open Agent Service chat"}
        >
          <AgentIcon aria-hidden="true" className="h-7 w-7" />
          {unread > 0 && <BadgeDot className="absolute -top-1 -right-1" />}
        </button>
      </div>

      {isOpen && access !== "checking" && (
        <Overlay onClose={() => handleOpenChange(false)}>
          {access !== "granted" ? (
            <div role="dialog" aria-modal="true" aria-label="Agent Service" className="absolute left-1/2 top-1/2 flex min-h-[280px] max-h-[calc(100vh-2rem)] w-[360px] max-w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center gap-4 overflow-y-auto rounded-3xl bg-white p-8 pt-12 text-center shadow-2xl">
              <h2 className="text-xl font-semibold text-[var(--scol-text)]">Agent Service</h2>
              <p className="text-sm text-[var(--scol-text-muted)]">
                {selectedLanguage === "es"
                  ? (access === "error" ? "No se pudo comprobar el acceso. Cierra y vuelve a abrir el chat." : "Inicia sesión para usar el asistente.")
                  : (access === "error" ? "Could not check access. Close and reopen the chat." : "Sign in to use the assistant.")}
              </p>
              {access === "required" && (
                <a
                  href={`${baseUrl}/auth/google/start?next=chat`}
                  className="group relative isolate overflow-hidden rounded-full bg-[var(--scol-primary)] px-5 py-3 text-sm font-semibold !text-white shadow-md transition-shadow duration-200 hover:shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--scol-primary)]"
                  onMouseMove={(event) => {
                    const bounds = event.currentTarget.getBoundingClientRect();
                    event.currentTarget.style.setProperty("--glow-x", `${event.clientX - bounds.left}px`);
                    event.currentTarget.style.setProperty("--glow-y", `${event.clientY - bounds.top}px`);
                  }}
                >
                  <span aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-visible:opacity-100 motion-reduce:transition-none" style={{ background: "radial-gradient(95px circle at var(--glow-x, 50%) var(--glow-y, 50%), rgba(255,255,255,0.24), rgba(255,255,255,0.05) 48%, transparent 80%)" }} />
                  <span className="relative z-10">{selectedLanguage === "es" ? "Continuar con Google" : "Continue with Google"}</span>
                </a>
              )}
              <select
                aria-label={selectedLanguage === "es" ? "Idioma del chat" : "Chat language"}
                value={selectedLanguage}
                onChange={(event) => {
                  const next = event.target.value as Language;
                  setSelectedLanguage(next);
                  window.localStorage.setItem("agent_service_language", next);
                }}
                className="absolute right-5 top-5 rounded-md border border-[var(--scol-border)] bg-white px-2 py-1 text-xs font-medium text-[var(--scol-text-muted)]"
              >
                <option value="es">ES</option><option value="en">EN</option>
              </select>
            </div>
          ) : isMobile ? (
            <Drawer side="right">
              <PanelShell>
                <AgentChatPanel
                  headerTitle="Agent Service"
                  baseUrl={baseUrl}
                  role={role}
                  language={selectedLanguage}
                  onLanguageChange={setSelectedLanguage}
                  memOptIn={memOptIn}
                  theme={effectiveTheme}
                  showCitations={showCitations}
                  maxQuestionChars={maxQuestionChars}
                  onClose={() => handleOpenChange(false)}
                  onLogout={loginRequired ? signOut : undefined}
                  consoleUrl={showConsoleLink && consoleAccess ? resolvedConsoleUrl : undefined}
                  showClose
                  onMessage={(msg) => {
                    if (!isOpen && msg.role === "agent") {
                      setUnread((n) => n + 1);
                    }
                  }}
                />
              </PanelShell>
            </Drawer>
          ) : (
            <div className={clsx("flex h-full items-end justify-end p-4", bubblePosition === "right-6" ? "justify-end" : "justify-start")}>
              <PanelShell className="h-[650px] w-[420px]">
                <AgentChatPanel
                  headerTitle="Agent Service"
                  baseUrl={baseUrl}
                  role={role}
                  language={selectedLanguage}
                  onLanguageChange={setSelectedLanguage}
                  memOptIn={memOptIn}
                  theme={effectiveTheme}
                  showCitations={showCitations}
                  maxQuestionChars={maxQuestionChars}
                  onClose={() => handleOpenChange(false)}
                  onLogout={loginRequired ? signOut : undefined}
                  consoleUrl={showConsoleLink && consoleAccess ? resolvedConsoleUrl : undefined}
                  showClose
                  onMessage={(msg) => {
                    if (!isOpen && msg.role === "agent") {
                      setUnread((n) => n + 1);
                    }
                  }}
                />
              </PanelShell>
            </div>
          )}
        </Overlay>
      )}
    </div>
  );
}

function useIsMobile() {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const handler = (e: MediaQueryListEvent | MediaQueryList) => setMobile(!!e.matches);
    handler(mq);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return mobile;
}
