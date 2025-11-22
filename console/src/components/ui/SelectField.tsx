import {
  forwardRef,
  type SelectHTMLAttributes,
  type ReactNode,
} from "react";
import { twMerge } from "tailwind-merge";

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: ReactNode;
  error?: string;
  hint?: string;
  children: ReactNode;
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(
  ({ id, label, error, hint, className, children, ...rest }, ref) => {
    return (
      <div className="space-y-2">
        {label && (
          <label htmlFor={id} className="label">
            {label}
          </label>
        )}
        <select
          id={id}
          ref={ref}
          className={twMerge(
            "input appearance-none bg-[url('data:image/svg+xml;utf8,<svg fill=\"%231E293B\" height=\"24\" viewBox=\"0 0 24 24\" width=\"24\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M7 10l5 5 5-5z\"/></svg>')] bg-[length:1.25rem] bg-[right_0.75rem_center] bg-no-repeat pr-10",
            error ? "border-red-400" : undefined,
            className,
          )}
          {...rest}
        >
          {children}
        </select>
        {error ? (
          <p className="text-sm text-red-500">{error}</p>
        ) : hint ? (
          <p className="text-xs text-ink-muted">{hint}</p>
        ) : null}
      </div>
    );
  },
);

SelectField.displayName = "SelectField";
