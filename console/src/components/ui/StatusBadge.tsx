import type { DocumentStatus } from "../../types/admin";

const STATUS_MAP: Record<
  string,
  { label: string; classes: string }
> = {
  ready: {
    label: "Ready",
    classes: "bg-emerald-100 text-emerald-700 ring-emerald-200",
  },
  processing: {
    label: "Processing",
    classes: "bg-amber-100 text-amber-700 ring-amber-200",
  },
  error: {
    label: "Error",
    classes: "bg-red-100 text-red-700 ring-red-200",
  },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const entry = STATUS_MAP[status.toLowerCase()] ?? {
    label: status,
    classes: "bg-slate-200 text-ink ring-border/70",
  };
  return (
    <span
      className={`badge ring-1 ${entry.classes}`}
      aria-label={`Estado ${entry.label}`}
    >
      {entry.label}
    </span>
  );
}
