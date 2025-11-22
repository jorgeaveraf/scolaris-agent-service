import React, { useEffect, useMemo, useState } from "react";
import { clsx } from "clsx";
import { Overlay, PanelShell, Drawer } from "./components/Primitives";
import { ScolarisChatPanel } from "./ScolarisChatPanel";
import type { Language, ScolarisChatBaseProps } from "./types";
import { BadgeDot, ChatIcon } from "./components/icons";
import { defaultTheme } from "./theme";
import botIcon from "./botIcon.png";

export interface ScolarisChatBubbleProps extends ScolarisChatBaseProps {
  placement?: "bottom-right" | "bottom-left";
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function ScolarisChatBubble({
  baseUrl,
  role,
  language = "es",
  memOptIn,
  theme,
  placement = "bottom-right",
  open,
  onOpenChange,
}: ScolarisChatBubbleProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = open ?? internalOpen;
  const [unread, setUnread] = useState(0);
  const isMobile = useIsMobile();

  const handleOpenChange = (value: boolean) => {
    onOpenChange?.(value);
    setInternalOpen(value);
    if (value) setUnread(0);
  };

  useEffect(() => {
    if (open !== undefined) {
      setInternalOpen(open);
      if (open) setUnread(0);
    }
  }, [open]);

  const bubblePosition = placement === "bottom-right" ? "right-6" : "left-6";

  const themeStyle = useMemo(() => {
    const merged = { ...defaultTheme, ...(theme || {}) };
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
  }, [theme]);

  return (
    <div style={themeStyle}>
      <button
        onClick={() => handleOpenChange(!isOpen)}
        className={clsx(
          "fixed z-30 flex h-14 w-14 items-center justify-center rounded-full border-2 border-[var(--scol-primary)] bg-white text-[var(--scol-primary)] shadow-xl transition hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--scol-primary)]",
          bubblePosition,
          "bottom-6",
        )}
        aria-label="Abrir chat Scolaris"
      >
        <img
          src={botIcon}
          alt="Asistente Scolaris"
          className="h-8 w-8 rounded-2xl object-contain"
        />
        {unread > 0 && <BadgeDot className="absolute -top-1 -right-1" />}
      </button>

      {isOpen && (
        <Overlay onClose={() => handleOpenChange(false)}>
          {isMobile ? (
            <Drawer side="right">
              <PanelShell>
                <ScolarisChatPanel
                  baseUrl={baseUrl}
                  role={role}
                  language={language}
                  memOptIn={memOptIn}
                  theme={theme}
                  onClose={() => handleOpenChange(false)}
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
                <ScolarisChatPanel
                  baseUrl={baseUrl}
                  role={role}
                  language={language as Language}
                  memOptIn={memOptIn}
                  theme={theme}
                  onClose={() => handleOpenChange(false)}
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
