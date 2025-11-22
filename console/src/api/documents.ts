import type { AxiosRequestConfig } from "axios";
import { apiClient } from "./client";
import type {
  DocumentsListResponse,
  DocumentDetail,
  ChunksListResponse,
  RehydrateResponse,
} from "../types/admin";

export interface DocumentFilters {
  q?: string;
  status?: string;
  area?: string;
  role?: string;
  vigencia?: string;
  limit?: number;
  offset?: number;
}

export async function listDocuments(
  filters: DocumentFilters,
): Promise<DocumentsListResponse> {
  const response = await apiClient.get<DocumentsListResponse>("/admin/docs", {
    params: filters,
  });
  return response.data;
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  const response = await apiClient.get<DocumentDetail>(`/admin/docs/${id}`);
  return response.data;
}

export async function uploadDocument(
  data: FormData,
  config?: AxiosRequestConfig,
): Promise<DocumentDetail> {
  const response = await apiClient.post<DocumentDetail>("/admin/docs", data, {
    ...config,
    headers: {
      "Content-Type": "multipart/form-data",
      ...(config?.headers ?? {}),
    },
  });
  return response.data;
}

export async function listChunks(
  id: string,
  params: { limit?: number; offset?: number } = {},
): Promise<ChunksListResponse> {
  const response = await apiClient.get<ChunksListResponse>(
    `/admin/docs/${id}/chunks`,
    { params },
  );
  return response.data;
}

export async function rehydrateDocument(
  id: string,
): Promise<RehydrateResponse> {
  const response = await apiClient.post<RehydrateResponse>(
    `/admin/docs/${id}/rehydrate`,
  );
  return response.data;
}

export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`/admin/docs/${id}`);
}
