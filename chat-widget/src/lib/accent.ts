import type { AgentTheme } from "./types";

const colorPattern = /^#[0-9a-fA-F]{6}$/;

function cookieValue(name: string) {
  if (typeof document === "undefined") return null;
  const entry = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return entry ? decodeURIComponent(entry.slice(name.length + 1)) : null;
}

export function readSharedAccent(): Pick<AgentTheme, "primary" | "primaryDark"> | null {
  const primary = cookieValue("agent_service_accent_primary");
  const primaryDark = cookieValue("agent_service_accent_dark");
  return primary && primaryDark && colorPattern.test(primary) && colorPattern.test(primaryDark)
    ? { primary, primaryDark }
    : null;
}
