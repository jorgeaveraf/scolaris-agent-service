import { useEffect, useState, useCallback } from "react";
import toast from "react-hot-toast";
import { listDocuments } from "../../../api/documents";

interface DocumentStats {
  total: number;
  ready: number;
  processing: number;
  error: number;
}

export function useDocumentStats() {
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const [overall, ready, processing, error] = await Promise.all([
        listDocuments({ limit: 1, offset: 0 }),
        listDocuments({ limit: 1, offset: 0, status: "ready" }),
        listDocuments({ limit: 1, offset: 0, status: "processing" }),
        listDocuments({ limit: 1, offset: 0, status: "error" }),
      ]);
      setStats({
        total: overall.total,
        ready: ready.total,
        processing: processing.total,
        error: error.total,
      });
    } catch (err) {
      console.error(err);
      toast.error("No pudimos cargar los totales de documentos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchStats();
  }, [fetchStats]);

  return {
    stats,
    loading,
    refresh: fetchStats,
  };
}
