import type { ReactNode } from "react";
import { twMerge } from "tailwind-merge";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  trend?: string;
  variant?: "default" | "primary" | "success" | "warning";
}

const variantClasses: Record<string, string> = {
  default: "bg-white",
  primary: "bg-gradient-to-br from-primary to-primary-dark text-white",
  success: "bg-emerald-50",
  warning: "bg-amber-50",
};

export function StatCard({
  label,
  value,
  icon,
  trend,
  variant = "default",
}: StatCardProps) {
  return (
    <div
      className={twMerge(
        "card group flex flex-col p-6",
        variantClasses[variant] ?? variantClasses.default,
      )}
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p
            className={twMerge(
              "text-sm font-medium",
              variant === "primary" ? "text-white/80" : "text-ink-muted",
            )}
          >
            {label}
          </p>
          <p
            className={twMerge(
              "mt-2 text-3xl font-semibold",
              variant === "primary" ? "text-white" : "text-ink",
            )}
          >
            {value}
          </p>
        </div>
        {icon && (
          <div
            className={twMerge(
              "rounded-2xl p-3",
              variant === "primary"
                ? "bg-white/20 text-white"
                : "bg-primary/10 text-primary",
            )}
          >
            {icon}
          </div>
        )}
      </div>
      {trend && <p className={twMerge("max-h-0 overflow-hidden text-xs font-medium leading-5 opacity-0 transition-[max-height,opacity,margin] duration-200 delay-0 group-hover:mt-3 group-hover:max-h-24 group-hover:opacity-100 group-hover:delay-500 motion-reduce:transition-none", variant === "primary" ? "text-white/80" : "text-ink-muted")}>{trend}</p>}
    </div>
  );
}
