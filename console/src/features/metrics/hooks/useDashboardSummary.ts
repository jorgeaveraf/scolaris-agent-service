import { useCallback, useEffect, useState } from "react";
import { apiClient } from "../../../api/client";
import type { DashboardSummary } from "../../../types/admin";

export function useDashboardSummary() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get<DashboardSummary>("/admin/dashboard/summary");
      setSummary(response.data);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { summary, loading, error, refresh };
}
