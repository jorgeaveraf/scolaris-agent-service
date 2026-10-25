import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Accent = "blue" | "teal" | "graphite" | "custom";

// eslint-disable-next-line react-refresh/only-export-components
export const accents: { id: Exclude<Accent, "custom">; label: string; swatch: string; primary: string; dark: string; light: string }[] = [
  { id: "blue", label: "Azul tinta", swatch: "#284F78", primary: "40 79 120", dark: "26 56 88", light: "61 106 153" },
  { id: "teal", label: "Verde petróleo", swatch: "#176E68", primary: "23 110 104", dark: "13 82 77", light: "41 137 129" },
  { id: "graphite", label: "Grafito", swatch: "#1E1E24", primary: "30 30 36", dark: "20 20 26", light: "57 57 64" },
];

function colorChannels(hex: string) {
  const rgb = [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16));
  const luminance = (values: number[]) => values.map((value) => {
    const channel = value / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
  while (luminance(rgb) > 0.18) rgb.forEach((value, index) => { rgb[index] = Math.round(value * 0.9); });
  const dark = rgb.map((value) => Math.round(value * 0.78));
  const light = rgb.map((value) => Math.round(value + (255 - value) * 0.16));
  return { primary: rgb.join(" "), dark: dark.join(" "), light: light.join(" ") };
}

const blend = (base: number[], accent: number[], amount: number) => base.map((value, index) => Math.round(value * (1 - amount) + accent[index] * amount)).join(" ");
const toHex = (channels: string) => `#${channels.split(" ").map((value) => Number(value).toString(16).padStart(2, "0")).join("").toUpperCase()}`;

type AccentContextValue = { accent: Accent; setAccent: (accent: Accent) => void; customHex: string; setCustomHex: (hex: string) => void };
const AccentContext = createContext<AccentContextValue | null>(null);

export function AccentProvider({ children }: { children: ReactNode }) {
  const [accent, updateAccent] = useState<Accent>(() => {
    const saved = window.localStorage.getItem("agent_service_console_accent");
    return saved === "custom" || accents.some((item) => item.id === saved) ? saved as Accent : "graphite";
  });
  const [customHex, updateCustomHex] = useState(() => {
    const saved = window.localStorage.getItem("agent_service_console_custom_hex");
    return saved && /^#[0-9a-fA-F]{6}$/.test(saved) ? saved.toUpperCase() : "#34556E";
  });

  useEffect(() => {
    const selected = accent === "custom" ? colorChannels(customHex) : accents.find((item) => item.id === accent) ?? accents[0];
    document.documentElement.style.setProperty("--accent-primary", selected.primary);
    document.documentElement.style.setProperty("--accent-dark", selected.dark);
    document.documentElement.style.setProperty("--accent-light", selected.light);
    const channels = selected.primary.split(" ").map(Number);
    document.documentElement.style.setProperty("--accent-banner-start", blend([15, 23, 42], channels, 0.18));
    document.documentElement.style.setProperty("--accent-banner-end", blend([17, 39, 55], channels, 0.55));
    document.documentElement.style.setProperty("--accent-glow", blend(channels, [245, 249, 255], 0.62));
    const domain = import.meta.env.VITE_ACCENT_COOKIE_DOMAIN?.trim();
    const cookieScope = domain && /^[a-zA-Z0-9.-]+$/.test(domain) ? `; Domain=${domain}` : "";
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `agent_service_accent_primary=${encodeURIComponent(toHex(selected.primary))}; Path=/; SameSite=Lax; Max-Age=31536000${cookieScope}${secure}`;
    document.cookie = `agent_service_accent_dark=${encodeURIComponent(toHex(selected.dark))}; Path=/; SameSite=Lax; Max-Age=31536000${cookieScope}${secure}`;
    window.dispatchEvent(new Event("agent-service-accent-change"));
    window.localStorage.setItem("agent_service_console_accent", accent);
    window.localStorage.setItem("agent_service_console_custom_hex", customHex);
  }, [accent, customHex]);

  const setCustomHex = (hex: string) => {
    if (!/^#[0-9a-fA-F]{6}$/.test(hex)) return;
    updateCustomHex(hex.toUpperCase());
    updateAccent("custom");
  };
  const value = useMemo(() => ({ accent, setAccent: updateAccent, customHex, setCustomHex }), [accent, customHex]);
  return <AccentContext.Provider value={value}>{children}</AccentContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAccent() {
  const context = useContext(AccentContext);
  if (!context) throw new Error("AccentProvider is missing");
  return context;
}
