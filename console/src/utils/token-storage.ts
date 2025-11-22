import { TOKEN_STORAGE_KEY, ROLE_STORAGE_KEY } from "../constants";

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // ignored on environments without storage
  }
}

export function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // ignored
  }
}

export function getStoredRole(): string | null {
  try {
    return localStorage.getItem(ROLE_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredRole(role: string | null): void {
  try {
    if (role) {
      localStorage.setItem(ROLE_STORAGE_KEY, role);
    } else {
      localStorage.removeItem(ROLE_STORAGE_KEY);
    }
  } catch {
    // ignored
  }
}

export function clearStoredRole(): void {
  try {
    localStorage.removeItem(ROLE_STORAGE_KEY);
  } catch {
    // ignored
  }
}
