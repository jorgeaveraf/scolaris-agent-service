import {
  type InputHTMLAttributes,
  forwardRef,
  type ReactNode,
} from "react";
import { twMerge } from "tailwind-merge";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: ReactNode;
  error?: string;
  hint?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  ({ id, label, error, hint, className, ...rest }, ref) => {
    return (
      <div className="space-y-2">
        {label && (
          <label htmlFor={id} className="label">
            {label}
          </label>
        )}
        <input
          id={id}
          ref={ref}
          className={twMerge("input", error ? "border-red-400" : undefined, className)}
          {...rest}
        />
        {error ? (
          <p className="text-sm text-red-500">{error}</p>
        ) : hint ? (
          <p className="text-xs text-ink-muted">{hint}</p>
        ) : null}
      </div>
    );
  },
);

TextField.displayName = "TextField";
