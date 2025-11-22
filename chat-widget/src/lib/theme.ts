import "./styles.css";
import type { ScolarisTheme } from "./types";

export const defaultTheme: ScolarisTheme = {
  primary: "#0F8CDD",
  primaryDark: "#0A6EB0",
  surface: "#FFFFFF",
  surfaceAlt: "#F7F9FC",
  text: "#0F172A",
  textMuted: "#5B6475",
  border: "#E6E9EF",
  success: "#0BB07B",
  danger: "#DC4B57",
  shadow: "0 20px 60px rgba(6, 40, 77, 0.12)",
};

export function applyTheme(theme?: Partial<ScolarisTheme>) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const merged = { ...defaultTheme, ...(theme || {}) };
  Object.entries(merged).forEach(([key, value]) => {
    root.style.setProperty(`--scol-${key.replace(/[A-Z]/g, m => `-${m.toLowerCase()}`)}`, value);
  });
}
