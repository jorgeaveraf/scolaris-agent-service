import { useState } from "react";
import {
  ArrowPathIcon,
  ClipboardDocumentCheckIcon,
  DocumentTextIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import toast from "react-hot-toast";
import { useNavigate, useParams } from "react-router-dom";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { useDocumentChunks } from "../features/chunks/hooks/useDocumentChunks";
import {
  deleteDocument,
  rehydrateDocument,
} from "../api/documents";
import { formatBytes, formatDateOnly, formatIsoDate } from "../utils/format";

export function DocumentChunksPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    detail,
    chunks,
    totalChunks,
    page,
    pageCount,
    pageSize,
    loadingDetail,
    loadingChunks,
    setPage,
    refresh,
  } = useDocumentChunks(id);
  const [rehydrateOpen, setRehydrateOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  if (!id) {
    return (
      <div className="card p-6">
        <p className="text-sm text-ink-muted">
          Selecciona un documento desde la vista de Documentos para ver sus chunks.
        </p>
      </div>
    );
  }

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Chunk copiado al portapapeles.");
    } catch (error) {
      console.error(error);
      toast.error("No pudimos copiar el texto.");
    }
  };

  const handleRehydrate = async () => {
    if (!detail) return;
    setActionLoading(true);
    try {
      await rehydrateDocument(detail.id);
      toast.success("Reingesta en curso. Actualiza en unos minutos.");
      setRehydrateOpen(false);
      await refresh();
    } catch (error) {
      console.error(error);
      toast.error("No pudimos reingestar este documento.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!detail) return;
    setActionLoading(true);
    try {
      await deleteDocument(detail.id);
      toast.success("Documento eliminado junto con sus chunks.");
      setDeleteOpen(false);
      navigate("/documents");
    } catch (error) {
      console.error(error);
      toast.error("No pudimos eliminar el documento.");
    } finally {
      setActionLoading(false);
    }
  };

  const start = totalChunks === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(totalChunks, start + chunks.length - 1);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div>
          <h2 className="text-2xl font-semibold text-ink">Detalle de chunks</h2>
          <p className="text-sm text-ink-muted">
            Visualiza el contexto que alimenta al agente para este documento.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ghost" onClick={() => refresh()} disabled={loadingDetail || loadingChunks}>
            Actualizar
          </Button>
          <Button variant="secondary" onClick={() => navigate("/documents")}>Volver</Button>
          <Button
            variant="secondary"
            onClick={() => setRehydrateOpen(true)}
            disabled={!detail}
            className="flex items-center gap-2"
          >
            <ArrowPathIcon className="h-5 w-5" /> Re-ingestar
          </Button>
          <Button
            variant="danger"
            onClick={() => setDeleteOpen(true)}
            disabled={!detail}
            className="flex items-center gap-2"
          >
            <TrashIcon className="h-5 w-5" /> Eliminar
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-ink">Contenido fragmentado</h3>
              <p className="text-sm text-ink-muted">
                {totalChunks} chunks registrados. Navega y copia los que necesites.
              </p>
            </div>
            <span className="text-xs font-medium text-ink-muted">
              Mostrando {start} - {end}
            </span>
          </div>
          <div className="mt-6 space-y-4">
            {loadingChunks ? (
              <div className="flex min-h-[160px] items-center justify-center text-ink-muted">
                <span className="h-6 w-6 animate-spin rounded-full border-3 border-primary/30 border-t-primary" />
              </div>
            ) : chunks.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center text-sm text-ink-muted">
                Aún no hay chunks disponibles para este documento.
              </div>
            ) : (
              chunks.map((chunk) => (
                <div key={chunk.chunk_id} className="rounded-2xl border border-border/70 bg-white/90 p-5 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary">
                      <DocumentTextIcon className="h-4 w-4" />
                      Chunk #{chunk.chunk_no + 1}
                    </div>
                    <button
                      type="button"
                      className="inline-flex items-center gap-2 text-xs font-semibold text-primary transition hover:text-primary-dark"
                      onClick={() => handleCopy(chunk.text_preview)}
                    >
                      <ClipboardDocumentCheckIcon className="h-4 w-4" /> Copiar
                    </button>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink">
                    {chunk.text_preview}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2 text-xs text-ink-muted">
                    <span className="rounded-full bg-primary/10 px-3 py-1 font-semibold text-primary">
                      {chunk.tokens} tokens
                    </span>
                    {Object.entries(chunk.metadata ?? {})
                      .filter(([, value]) => value !== null && value !== "")
                      .map(([key, value]) => (
                        <span
                          key={`${chunk.chunk_id}-${key}`}
                          className="rounded-full bg-slate-100 px-3 py-1 text-xs text-ink-muted"
                        >
                          {key}: {String(value)}
                        </span>
                      ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {pageCount > 1 && (
            <div className="mt-6 flex flex-col items-center justify-between gap-4 rounded-2xl border border-border bg-slate-25 px-4 py-3 text-sm md:flex-row">
              <span className="text-ink-muted">
                Página <span className="font-semibold text-ink">{page}</span> de
                <span className="font-semibold text-ink"> {pageCount}</span>
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1 || loadingChunks}
                >
                  Anterior
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setPage(Math.min(pageCount, page + 1))}
                  disabled={page === pageCount || loadingChunks}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="card space-y-4 p-6">
          <h3 className="text-lg font-semibold text-ink">Resumen del documento</h3>
          {loadingDetail || !detail ? (
            <div className="flex min-h-[180px] items-center justify-center text-ink-muted">
              Cargando detalle...
            </div>
          ) : (
            <div className="space-y-4 text-sm text-ink-muted">
              <div>
                <p className="font-semibold text-ink">{detail.filename}</p>
                <p className="text-xs">ID: {detail.id}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={detail.status} />
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs">
                  {formatBytes(detail.size_bytes)}
                </span>
                {detail.content_type && (
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs">
                    {detail.content_type}
                  </span>
                )}
              </div>
              <dl className="grid gap-2">
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">Área</dt>
                  <dd>{detail.area ?? "--"}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">Rol</dt>
                  <dd>{detail.role ?? "--"}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">Vigencia</dt>
                  <dd>{formatDateOnly(detail.vigencia)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">Chunks</dt>
                  <dd>{detail.chunks_count ?? "--"}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">Última ingesta</dt>
                  <dd>{formatIsoDate(detail.last_ingested_at)}</dd>
                </div>
              </dl>
              {detail.error_msg && (
                <div className="rounded-xl bg-red-50 px-4 py-3 text-xs text-red-600">
                  Error: {detail.error_msg}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={rehydrateOpen}
        onClose={() => setRehydrateOpen(false)}
        title="Re-ingestar documento"
        description={
          detail
            ? `Se reprocesarán los chunks de “${detail.filename}”. Esto puede tardar unos minutos.`
            : ""
        }
        confirmText="Re-ingestar"
        onConfirm={handleRehydrate}
        loading={actionLoading}
      />

      <ConfirmDialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Eliminar documento"
        description={
          detail
            ? `Eliminarás definitivamente “${detail.filename}” y sus ${detail.chunks_count ?? 0} chunks.`
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
