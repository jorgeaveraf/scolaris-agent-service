import axios, { AxiosError, type AxiosRequestHeaders } from "axios";
import { API_BASE_URL } from "../constants";
import {
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  clearStoredRole,
} from "../utils/token-storage";

let inMemoryToken: string | null = getStoredToken();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

apiClient.interceptors.request.use((config) => {
  const headers = (config.headers ?? {}) as AxiosRequestHeaders;
  if (inMemoryToken) {
    headers.Authorization = `Bearer ${inMemoryToken}`;
  }
  config.headers = headers;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      clearAuthToken();
    }
    return Promise.reject(error);
  },
);

export function setAuthToken(token: string) {
  inMemoryToken = token;
  setStoredToken(token);
}

export function clearAuthToken() {
  inMemoryToken = null;
  clearStoredToken();
  clearStoredRole();
}

export function getAuthToken() {
  return inMemoryToken;
}
