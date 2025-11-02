import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowPathIcon,
  EyeIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import toast from "react-hot-toast";
import { Button } from "../components/ui/Button";
import { TextField } from "../components/ui/TextField";
import { SelectField } from "../components/ui/SelectField";
import { StatusBadge } from "../components/ui/StatusBadge";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { DocumentUploadModal } from "../features/documents/components/DocumentUploadModal";
import { useDocumentsList } from "../features/documents/hooks/useDocumentsList";
import {
  deleteDocument,
  rehydrateDocument,
} from "../api/documents";
import type { DocumentSummary } from "../types/admin";
import { formatBytes, formatDateOnly, formatIsoDate } from "../utils/format";

export function DocumentsPage() {
  const navigate = useNavigate();
  const {
    documents,
    total,
    page,
    pageCount,
    filters,
    loading,
    setPage,
    updateFilter,
    resetFilters,
    refresh,
    pageSize,
  } = useDocumentsList();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [rehydrateTarget, setRehydrateTarget] = useState<DocumentSummary | null>(
    null,
  );
  const [deleteTarget, setDeleteTarget] = useState<DocumentSummary | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const handleRehydrate = async () => {
    if (!rehydrateTarget) return;
    setActionLoading(true);
    try {
      await rehydrateDocument(rehydrateTarget.id);
      toast.success("Reingesta programada correctamente.");
      setRehydrateTarget(null);
      await refresh();
    } catch (error) {
      console.error(error);
      toast.error("No pudimos reingestar el documento.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setActionLoading(true);
    try {
      await deleteDocument(deleteTarget.id);
      toast.success("Documento eliminado.");
      setDeleteTarget(null);
      await refresh();
    } catch (error) {
      console.error(error);
      toast.error("No pudimos eliminar el documento.");
    } finally {
      setActionLoading(false);
    }
  };

  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(total, start + documents.length - 1);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h2 className="text-2xl font-semibold text-ink">Documentos</h2>
          <p className="text-sm text-ink-muted">
            Administra los archivos ingeridos por el agente, reingéstalos y controla su estado.
          </p>
        </div>
        <Button onClick={() => setUploadOpen(true)}>Nuevo documento</Button>
      </div>

      <div className="card p-4">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <TextField
            id="search"
            placeholder="Buscar por nombre"
            label="Buscar"
            value={filters.q}
            onChange={(event) => updateFilter("q", event.target.value)}
          />
          <SelectField
            id="status"
            label="Status"
            value={filters.status}
            onChange={(event) => updateFilter("status", event.target.value)}
          >
            <option value="">Todos</option>
            <option value="ready">Ready</option>
            <option value="processing">Processing</option>
            <option value="error">Error</option>
          </SelectField>
          <TextField
            id="role"
            placeholder="Rol"
            label="Rol"
            value={filters.role}
            onChange={(event) => updateFilter("role", event.target.value)}
          />
          <TextField
            id="area"
            placeholder="Área"
            label="Área"
            value={filters.area}
            onChange={(event) => updateFilter("area", event.target.value)}
          />
          <TextField
            id="vigencia"
            placeholder="aaaa-mm-dd"
            label="Vigencia"
            type="date"
            value={filters.vigencia}
            onChange={(event) => updateFilter("vigencia", event.target.value)}
          />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
          <p className="text-ink-muted">
            Mostrando <span className="font-semibold text-ink">{start}</span> -
            <span className="font-semibold text-ink"> {end}</span> de
            <span className="font-semibold text-ink"> {total}</span> documentos
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={resetFilters} disabled={loading}>
              Limpiar filtros
            </Button>
            <Button variant="ghost" onClick={() => refresh()} disabled={loading}>
              Actualizar
            </Button>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-slate-25 text-left text-xs font-semibold uppercase tracking-wide text-ink-muted">
              <tr>
                <th className="px-6 py-4">Archivo</th>
                <th className="px-6 py-4">Área</th>
                <th className="px-6 py-4">Rol</th>
                <th className="px-6 py-4">Vigencia</th>
                <th className="px-6 py-4">Tamaño</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Creado</th>
                <th className="px-6 py-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70 text-sm">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-6 py-10 text-center">
                    <div className="inline-flex items-center gap-3 text-ink-muted">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
                      Cargando documentos...
                    </div>
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr className="bg-white">
                  <td colSpan={8} className="px-6 py-10 text-center text-sm text-ink-muted">
                    Aún no has cargado documentos. Usa el botón "Nuevo documento" para comenzar.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="bg-white hover:bg-primary/5">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-semibold text-ink">{doc.filename}</span>
                        <span className="text-xs text-ink-muted">
                          Última actualización: {formatIsoDate(doc.updated_at)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-ink-muted">{doc.area ?? "--"}</td>
                    <td className="px-6 py-4 text-ink-muted">{doc.role ?? "--"}</td>
                    <td className="px-6 py-4 text-ink-muted">{formatDateOnly(doc.vigencia)}</td>
                    <td className="px-6 py-4 text-ink-muted">{formatBytes(doc.size_bytes)}</td>
                    <td className="px-6 py-4"><StatusBadge status={doc.status} /></td>
                    <td className="px-6 py-4 text-ink-muted">{formatIsoDate(doc.created_at)}</td>
                    <td className="px-6 py-4">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => navigate(`/documents/${doc.id}`)}
                          title="Ver chunks"
                        >
                          <EyeIcon className="h-5 w-5" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => setRehydrateTarget(doc)}
                          title="Re-ingestar"
                        >
                          <ArrowPathIcon className="h-5 w-5" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => setDeleteTarget(doc)}
                          title="Eliminar"
                        >
                          <TrashIcon className="h-5 w-5 text-red-500" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {pageCount > 1 && (
        <div className="flex flex-col items-center justify-between gap-4 rounded-2xl border border-border bg-white px-4 py-3 text-sm shadow-sm md:flex-row">
          <span className="text-ink-muted">
            Página <span className="font-semibold text-ink">{page}</span> de
            <span className="font-semibold text-ink"> {pageCount}</span>
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1 || loading}
            >
              Anterior
            </Button>
            <Button
              variant="secondary"
              onClick={() => setPage(Math.min(pageCount, page + 1))}
              disabled={page === pageCount || loading}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}

      <DocumentUploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={async (_doc) => {
          await refresh();
          setUploadOpen(false);
        }}
      />

      <ConfirmDialog
        open={Boolean(rehydrateTarget)}
        onClose={() => setRehydrateTarget(null)}
        title="Re-ingestar documento"
        description={
          rehydrateTarget
            ? `¿Deseas volver a procesar “${rehydrateTarget.filename}”? Se actualizarán sus chunks.`
            : ""
        }
        confirmText="Re-ingestar"
        confirmVariant="primary"
        onConfirm={handleRehydrate}
        loading={actionLoading}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Eliminar documento"
        description={
          deleteTarget
            ? `Esta acción es irreversible. Se eliminará “${deleteTarget.filename}” y sus chunks asociados.`
            : ""
        }
        confirmText="Eliminar"
        confirmVariant="danger"
        onConfirm={handleDelete}
        loading={actionLoading}
      />
    </div>
  );
}
