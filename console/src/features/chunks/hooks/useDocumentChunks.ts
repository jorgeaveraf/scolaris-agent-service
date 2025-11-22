import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { getDocument, listChunks } from "../../../api/documents";
import type { DocumentDetail, ChunkItem } from "../../../types/admin";

const PAGE_SIZE = 10;

export function useDocumentChunks(documentId?: string) {
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingChunks, setLoadingChunks] = useState(false);

  const fetchDetail = useCallback(async () => {
    if (!documentId) return;
    setLoadingDetail(true);
    try {
      const response = await getDocument(documentId);
      setDetail(response);
    } catch (error) {
      console.error(error);
      toast.error("No pudimos obtener el detalle del documento.");
    } finally {
      setLoadingDetail(false);
    }
  }, [documentId]);

  const fetchChunks = useCallback(async () => {
    if (!documentId) return;
    setLoadingChunks(true);
    try {
      const response = await listChunks(documentId, {
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      });
      setChunks(response.items);
      setTotalChunks(response.total);
    } catch (error) {
      console.error(error);
      toast.error("No pudimos cargar los chunks del documento.");
    } finally {
      setLoadingChunks(false);
    }
  }, [documentId, page]);

  useEffect(() => {
    setPage(1);
  }, [documentId]);

  useEffect(() => {
    void fetchDetail();
  }, [fetchDetail]);

  useEffect(() => {
    void fetchChunks();
  }, [fetchChunks]);

  const pageCount = useMemo(
    () => Math.max(1, Math.ceil(totalChunks / PAGE_SIZE)),
    [totalChunks],
  );

  const refresh = useCallback(async () => {
    await Promise.all([fetchDetail(), fetchChunks()]);
  }, [fetchDetail, fetchChunks]);

  return {
    detail,
    chunks,
    totalChunks,
    page,
    pageCount,
    pageSize: PAGE_SIZE,
    loadingDetail,
    loadingChunks,
    setPage,
    refresh,
  };
}
