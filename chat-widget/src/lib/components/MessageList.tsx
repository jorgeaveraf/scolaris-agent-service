import React, { useEffect, useRef } from "react";
import { clsx } from "clsx";
import type { ChatMessage } from "../types";

interface MessageListProps {
  messages: ChatMessage[];
  language: "es" | "en";
}

export function MessageList({ messages, language }: MessageListProps) {
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages]);

  return (
    <div
      ref={listRef}
      className="scol-scrollbar flex-1 overflow-y-auto px-4 pb-4"
      role="log"
      aria-live="polite"
    >
      {messages.map((msg) => (
        <article
          key={msg.id}
          className={clsx(
            "scol-fade-in mb-3 max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
            msg.role === "user"
              ? "ml-auto bg-[var(--scol-primary)] text-white"
              : "mr-auto bg-[var(--scol-surface-alt)] text-[var(--scol-text)]",
          )}
        >
          <p className="whitespace-pre-wrap">{msg.content}</p>
        </article>
      ))}
    </div>
  );
}
