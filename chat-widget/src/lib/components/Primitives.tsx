import React, { useEffect } from "react";
import { clsx } from "clsx";

type OverlayProps = {
  children: React.ReactNode;
  onClose?: () => void;
};

export function Overlay({ children, onClose }: OverlayProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-40 bg-[rgba(8,22,48,0.35)] backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      {children}
    </div>
  );
}

type PanelShellProps = {
  children: React.ReactNode;
  className?: string;
};

export function PanelShell({ children, className }: PanelShellProps) {
  return (
    <div
      className={clsx(
        "scol-card flex h-full max-h-[80vh] w-full max-w-[420px] flex-col rounded-2xl bg-white shadow-2xl transition-all",
        className,
      )}
      role="dialog"
      aria-modal="true"
    >
      {children}
    </div>
  );
}

type DrawerProps = {
  children: React.ReactNode;
  side?: "right" | "left";
};

export function Drawer({ children, side = "right" }: DrawerProps) {
  return (
    <div
      className={clsx(
        "fixed inset-y-0 z-50 w-full max-w-md bg-transparent",
        side === "right" ? "right-0" : "left-0",
      )}
    >
      <div className="h-full p-4">{children}</div>
    </div>
  );
}
