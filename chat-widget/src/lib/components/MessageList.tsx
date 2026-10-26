import { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";
import type { ChatMessage } from "../types";

interface MessageListProps {
  messages: ChatMessage[];
  language: "es" | "en";
  showCitations?: boolean;
}

function SourcesHeading({ language, disclaimer, expanded }: { language: "es" | "en"; disclaimer?: string; expanded: boolean }) {
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const leaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const area = useRef<HTMLDivElement | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); if (leaveTimer.current) clearTimeout(leaveTimer.current); }, []);
  useEffect(() => {
    if (!expanded) {
      if (timer.current) clearTimeout(timer.current);
      timer.current = null;
      setOpen(false);
    }
  }, [expanded]);
  const showLater = () => { if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(() => setOpen(true), 300); };
  const hide = () => { if (timer.current) clearTimeout(timer.current); timer.current = null; setOpen(false); };
  const hideAfterLeave = () => {
    if (leaveTimer.current) clearTimeout(leaveTimer.current);
    leaveTimer.current = setTimeout(() => {
      if (!area.current?.matches(":hover")) hide();
    }, 150);
  };
  return (
    <div ref={area} className="w-full" onMouseEnter={() => { if (leaveTimer.current) clearTimeout(leaveTimer.current); }} onMouseLeave={hideAfterLeave}>
      <div className="flex items-center gap-2">
        <p className="font-semibold">{language === "es" ? "Fuentes consultadas" : "Sources consulted"}</p>
        {expanded && disclaimer && (
          <button type="button" aria-label={language === "es" ? "Aviso importante" : "Important notice"}
            aria-expanded={open} onMouseEnter={showLater}
            onFocus={(event) => { if (event.currentTarget.matches(":focus-visible")) showLater(); }}
            className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-current text-[10px] font-semibold opacity-70 focus-visible:outline focus-visible:outline-2">
            i
          </button>
        )}
      </div>
      {expanded && open && disclaimer && <p className="mt-2 w-full rounded-lg border border-[var(--scol-border)] bg-[var(--scol-surface)] px-3 py-2 text-xs leading-relaxed text-[var(--scol-text-muted)]">{disclaimer}</p>}
    </div>
  );
}

function SourcesBlock({ language, citations, disclaimer }: {
  language: "es" | "en";
  citations: NonNullable<ChatMessage["citations"]>;
  disclaimer?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const leaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const area = useRef<HTMLDivElement | null>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); if (leaveTimer.current) clearTimeout(leaveTimer.current); }, []);
  const openLater = () => { if (leaveTimer.current) clearTimeout(leaveTimer.current); if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(() => setExpanded(true), 500); };
  const close = () => { if (timer.current) clearTimeout(timer.current); timer.current = null; setExpanded(false); };
  const closeAfterLeave = () => {
    if (leaveTimer.current) clearTimeout(leaveTimer.current);
    leaveTimer.current = setTimeout(() => {
      if (!area.current?.matches(":hover")) close();
    }, 150);
  };
  return (
    <div ref={area} className="mt-3 border-t border-[var(--scol-border)] pt-2 text-xs text-[var(--scol-text-muted)]"
      onMouseEnter={openLater} onMouseLeave={closeAfterLeave}
      onFocus={(event) => { if ((event.target as HTMLElement).matches(":focus-visible")) openLater(); }}
      onBlur={(event) => { if (!area.current?.matches(":hover") && !event.currentTarget.contains(event.relatedTarget as Node | null)) close(); }}>
      <SourcesHeading language={language} disclaimer={disclaimer} expanded={expanded} />
      {expanded && (
        <ul className="scol-fade-in mt-2 space-y-1">
          {citations.map((citation, index) => (
            <li key={`${citation.title}-${index}`}>
              {citation.url ? (
                <a href={citation.url} target="_blank" rel="noopener noreferrer" className="underline">
                  {citation.title || (language === "es" ? "Documento" : "Document")}
                </a>
              ) : (citation.title || (language === "es" ? "Documento" : "Document"))}
              {citation.snippet && <p className="mt-0.5 line-clamp-3 opacity-80">{citation.snippet}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function MessageList({ messages, language, showCitations = false }: MessageListProps) {
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages]);

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const onWheel = (event: WheelEvent) => {
      let target = event.target as HTMLElement | null;
      while (target && target !== list) {
        const maxScroll = target.scrollHeight - target.clientHeight;
        const canScroll = event.deltaY < 0 ? target.scrollTop > 0 : target.scrollTop < maxScroll;
        if (maxScroll > 1 && canScroll && /auto|scroll/.test(getComputedStyle(target).overflowY)) break;
        target = target.parentElement;
      }
      event.preventDefault();
      event.stopPropagation();
      (target || list).scrollTop += event.deltaY;
    };
    list.addEventListener("wheel", onWheel, { passive: false });
    return () => list.removeEventListener("wheel", onWheel);
  }, []);

  return (
    <div
      ref={listRef}
      className="scol-scrollbar min-h-0 flex-1 overflow-y-auto overscroll-y-contain px-4 pb-4 pt-2"
      role="log"
      aria-live="polite"
    >
      {messages.map((msg) => (
        <article
          key={msg.id}
          className={clsx(
            "scol-fade-in mb-3 w-fit max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
            msg.role === "user"
              ? "ml-auto bg-[var(--scol-primary)] text-white"
              : "mr-auto bg-[var(--scol-surface-alt)] text-[var(--scol-text)]",
          )}
        >
          <p className={clsx("whitespace-pre-wrap [overflow-wrap:anywhere]", msg.role === "user" && "scol-scrollbar max-h-56 overflow-y-auto")}>
            {msg.content}
            {msg.role === "agent" && msg.status === "streaming" && (
              <span className="ml-0.5 inline-block animate-pulse" aria-label={language === "es" ? "Generando" : "Generating"}>
                ▍
              </span>
            )}
          </p>
          {msg.status === "error" && msg.errorMessage && (
            <p className="mt-2 text-xs text-[var(--scol-danger)]">{msg.errorMessage}</p>
          )}
          {showCitations && msg.role === "agent" && !!msg.citations?.length && (
            <SourcesBlock language={language} citations={msg.citations} disclaimer={msg.disclaimer} />
          )}
        </article>
      ))}
    </div>
  );
}
