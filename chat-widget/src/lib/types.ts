export type Language = "es" | "en";

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  citations?: Array<{ title?: string; content?: string }>;
}

export interface ScolarisChatBaseProps {
  baseUrl: string;
  role?: string | null;
  language?: Language;
  memOptIn?: boolean;
  theme?: Partial<ScolarisTheme>;
}

export interface ScolarisTheme {
  primary: string;
  primaryDark: string;
  surface: string;
  surfaceAlt: string;
  text: string;
  textMuted: string;
  border: string;
  success: string;
  danger: string;
  shadow: string;
}
