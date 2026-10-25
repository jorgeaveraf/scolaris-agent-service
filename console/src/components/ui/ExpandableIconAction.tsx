import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import { twMerge } from "tailwind-merge";

type Tone = "primary" | "neutral" | "quiet" | "danger";
type Width = "short" | "medium" | "long";

const widths: Record<Width, string> = {
  short: "hover:w-28 focus-visible:w-28",
  medium: "hover:w-40 focus-visible:w-40",
  long: "hover:w-48 focus-visible:w-48",
};

const tones: Record<Tone, string> = {
  primary: "gradient-button border-transparent text-white",
  neutral: "border-border bg-white text-ink hover:border-primary hover:text-primary",
  quiet: "border-transparent bg-transparent text-ink-muted hover:bg-primary/10 hover:text-primary",
  danger: "border-red-500 bg-red-500 text-white hover:border-red-600 hover:bg-red-600",
};

function actionClasses(tone: Tone, width: Width): string {
  return `group inline-flex h-11 w-11 shrink-0 items-center justify-center gap-0 overflow-hidden whitespace-nowrap rounded-xl border px-0 text-sm font-semibold transition-[width,gap,border-color,background-color,color] duration-200 hover:gap-2 focus-visible:gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none ${widths[width]} ${tones[tone]}`;
}

function ActionContent({ icon, label }: { icon: ReactNode; label: string }) {
  return <>
    <span className="h-5 w-5 shrink-0" aria-hidden="true">{icon}</span>
    <span className="max-w-0 overflow-hidden opacity-0 transition-[max-width,opacity] duration-200 group-hover:max-w-36 group-hover:opacity-100 group-focus-visible:max-w-36 group-focus-visible:opacity-100 motion-reduce:transition-none">{label}</span>
  </>;
}

type ActionButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children" | "aria-label"> & {
  icon: ReactNode;
  label: string;
  tone?: Tone;
  width?: Width;
};

export function ExpandableIconButton({ icon, label, tone = "neutral", width = "medium", type = "button", className, ...props }: ActionButtonProps) {
  return <button {...props} type={type} aria-label={label} className={twMerge(actionClasses(tone, width), className)}><ActionContent icon={icon} label={label} /></button>;
}

type ActionLinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "children" | "aria-label"> & {
  icon: ReactNode;
  label: string;
  tone?: Tone;
  width?: Width;
};

export function ExpandableIconLink({ icon, label, tone = "neutral", width = "medium", className, ...props }: ActionLinkProps) {
  return <a {...props} aria-label={label} className={twMerge(actionClasses(tone, width), className)}><ActionContent icon={icon} label={label} /></a>;
}
