import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { getMetricsOverview } from "../../../api/metrics";
import type { MetricsOverview } from "../../../types/admin";

export function useMetricsOverview(pollMs = 15000) {
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [hadSuccess, setHadSuccess] = useState(false);
  const [lastErrorToast, setLastErrorToast] = useState<number | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getMetricsOverview();
      setMetrics(data);
      setHadSuccess(true);
      setLastErrorToast(null);
    } catch (err) {
      console.error(err);
      const now = Date.now();
      // evita spamear el toast en cada poll si ya se mostró recientemente
      if (!lastErrorToast || now - lastErrorToast > 15000 || !hadSuccess) {
        toast.error("No pudimos cargar las métricas de observabilidad.");
        setLastErrorToast(now);
      }
    } finally {
      setLoading(false);
    }
  }, [hadSuccess, lastErrorToast]);

  useEffect(() => {
    void fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    if (!pollMs) return;
    const id = setInterval(() => {
      void fetchMetrics();
    }, pollMs);
    return () => clearInterval(id);
  }, [fetchMetrics, pollMs]);

  return {
    metrics,
    loading,
    refresh: fetchMetrics,
  };
}
