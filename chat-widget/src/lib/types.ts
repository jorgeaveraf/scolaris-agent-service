export type Language = "es" | "en";

export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  status?: "streaming" | "completed" | "error";
  errorMessage?: string;
  citations?: Array<{ title?: string; url?: string; snippet?: string }>;
  disclaimer?: string;
  metadata?: Record<string, unknown>;
}

export interface AgentChatBaseProps {
  baseUrl: string;
  role?: string | null;
  language?: Language;
  memOptIn?: boolean;
  theme?: Partial<AgentTheme>;
}

export interface AgentTheme {
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
