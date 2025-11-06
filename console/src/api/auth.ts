import { apiClient } from "./client";

export interface PasswordLoginResponse {
  token: string;
  role: string;
  expires_in: number;
}

export async function loginWithPassword(
  password: string,
): Promise<PasswordLoginResponse> {
  const response = await apiClient.post<PasswordLoginResponse>(
    "/auth/login",
    { password },
  );
  return response.data;
}
