import { apiClient } from "./client";
import type { MetricsOverview } from "../types/admin";

export async function getMetricsOverview(): Promise<MetricsOverview> {
  const response = await apiClient.get<MetricsOverview>("/admin/metrics/overview");
  return response.data;
}
