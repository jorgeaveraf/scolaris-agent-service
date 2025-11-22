import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import {
  listDocuments,
  type DocumentFilters,
} from "../../../api/documents";
import type { DocumentSummary } from "../../../types/admin";
import { normalizeFilterValue } from "../../../utils/format";

const PAGE_SIZE = 10;

export interface FiltersState {
  q: string;
  status: string;
  area: string;
  role: string;
  vigencia: string;
}

const DEFAULT_FILTERS: FiltersState = {
  q: "",
  status: "",
  area: "",
  role: "",
  vigencia: "",
};

export function useDocumentsList() {
  const [filters, setFilters] = useState<FiltersState>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const apiFilters = useMemo<DocumentFilters>(() => {
    const base: DocumentFilters = {
      q: normalizeFilterValue(filters.q),
      status: normalizeFilterValue(filters.status),
      area: normalizeFilterValue(filters.area),
      role: normalizeFilterValue(filters.role),
      vigencia: normalizeFilterValue(filters.vigencia),
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    };
    return base;
  }, [filters, page]);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await listDocuments(apiFilters);
      setDocuments(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error(error);
      toast.error("No pudimos cargar los documentos.");
    } finally {
      setLoading(false);
    }
  }, [apiFilters]);

  useEffect(() => {
    void fetchDocuments();
  }, [fetchDocuments]);

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const updateFilter = useCallback(
    (key: keyof FiltersState, value: string) => {
      setPage(1);
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const resetFilters = useCallback(() => {
    setPage(1);
    setFilters(DEFAULT_FILTERS);
  }, []);

  return {
    documents,
    total,
    page,
    pageCount,
    filters,
    loading,
    setPage,
    updateFilter,
    resetFilters,
    refresh: fetchDocuments,
    pageSize: PAGE_SIZE,
  };
}
