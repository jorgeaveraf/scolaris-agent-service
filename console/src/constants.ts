export const TOKEN_STORAGE_KEY = "scolaris_console_token";
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE?.toString() ?? "http://localhost:8000";
export const DEV_TOKEN_HINT = import.meta.env.VITE_CONSOLE_AUTH ?? "";
