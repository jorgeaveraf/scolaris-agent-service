import React from "react";
import { clsx } from "clsx";

export function ChatIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path
        d="M7.5 17.5 4 21v-5.5m16 0A8.5 8.5 0 1 0 4 15.5h16Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LightningIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M13 2 6 14h7l-2 8 7-12h-7z" strokeLinejoin="round" />
    </svg>
  );
}

export function CloseIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="m6 6 12 12M6 18 18 6" strokeLinecap="round" />
    </svg>
  );
}

export function SendIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path
        d="M4 4.75 20 12 4 19.25 6 13 6 11 4 4.75Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ChevronDownIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="m5 9 7 7 7-7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function DocumentTextIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" {...props}>
      <path d="M7 4h7l4 4v12H7z" strokeLinejoin="round" />
      <path d="M14 4v4h4M9.5 13h5M9.5 16h5" />
    </svg>
  );
}

export function BadgeDot({ className }: { className?: string }) {
  return <span className={clsx("inline-block h-2.5 w-2.5 rounded-full bg-[var(--scol-danger)]", className)} />;
}
