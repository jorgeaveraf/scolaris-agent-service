import { type ButtonHTMLAttributes, forwardRef } from "react";
import { twMerge } from "tailwind-merge";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "gradient-button inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold uppercase tracking-wide",
  secondary:
    "inline-flex items-center justify-center rounded-xl border border-border bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-primary hover:text-primary",
  ghost:
    "inline-flex items-center justify-center rounded-xl px-3 py-2 text-sm font-medium text-ink-muted transition hover:bg-primary/10 hover:text-primary",
  danger:
    "inline-flex items-center justify-center rounded-xl bg-red-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", loading, disabled, children, ...rest }, ref) => {
    const isDisabled = disabled || loading;
    return (
      <button
        ref={ref}
        className={twMerge(
          variantClasses[variant],
          isDisabled ? "cursor-not-allowed opacity-70" : undefined,
          className,
        )}
        disabled={isDisabled}
        {...rest}
      >
        {loading && (
          <span className="mr-2 inline-flex h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = "Button";
