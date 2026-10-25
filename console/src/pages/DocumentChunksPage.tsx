import { useState } from "react";
import {
  ArrowPathIcon,
  ArrowLeftIcon,
  ArrowUturnRightIcon,
  ClipboardDocumentCheckIcon,
  DocumentTextIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import toast from "react-hot-toast";
import { useNavigate, useParams } from "react-router-dom";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Button } from "../components/ui/Button";
import { ExpandableIconButton } from "../components/ui/ExpandableIconAction";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { useDocumentChunks } from "../features/chunks/hooks/useDocumentChunks";
import { OriginalDocumentPreview } from "../features/documents/components/OriginalDocumentPreview";
import {
  deleteDocument,
  rehydrateDocument,
} from "../api/documents";
import { formatBytes, formatDateOnly, formatIsoDate } from "../utils/format";
import { useAuth } from "../hooks/useAuth";
import { useLanguage } from "../i18n/LanguageProvider";

export function DocumentChunksPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { role } = useAuth();
  const { t, language } = useLanguage();
  const canManage = role === "curator" || role === "admin";
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
          {t("Selecciona un documento desde la vista de Documentos para ver sus detalles.")}
        </p>
      </div>
    );
  }

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(t("Fragmento copiado al portapapeles."));
    } catch (error) {
      console.error(error);
      toast.error(t("No pudimos copiar el texto."));
    }
  };

  const handleRehydrate = async () => {
    if (!detail) return;
    setActionLoading(true);
    try {
      await rehydrateDocument(detail.id);
      toast.success(t("Reingesta en curso. Actualiza en unos minutos."));
      setRehydrateOpen(false);
      await refresh();
    } catch (error) {
      console.error(error);
      toast.error(t("No pudimos reingestar este documento."));
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!detail) return;
    setActionLoading(true);
    try {
      await deleteDocument(detail.id);
      toast.success(t("Documento eliminado."));
      setDeleteOpen(false);
      navigate("/documents");
    } catch (error) {
      console.error(error);
      toast.error(t("No pudimos eliminar el documento."));
    } finally {
      setActionLoading(false);
    }
  };

  const start = totalChunks === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = totalChunks === 0 ? 0 : Math.min(totalChunks, start + chunks.length - 1);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div>
          <h2 className="text-2xl font-semibold text-ink">{t("Detalle del documento")}</h2>
          <p className="text-sm text-ink-muted">
            {t("Revisa su estado, información y opciones de gestión.")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ExpandableIconButton icon={<ArrowPathIcon className="h-5 w-5" />} label={t("Actualizar")} tone="quiet" width="short" onClick={() => refresh()} disabled={loadingDetail || loadingChunks} />
          <ExpandableIconButton icon={<ArrowLeftIcon className="h-5 w-5" />} label={t("Volver")} width="short" onClick={() => navigate("/documents")} />
          {canManage && <ExpandableIconButton icon={<ArrowUturnRightIcon className="h-5 w-5" />} label={t("Volver a procesar")} width="long" onClick={() => setRehydrateOpen(true)} disabled={!detail} />}
          {canManage && <ExpandableIconButton
            icon={<TrashIcon className="h-5 w-5" />}
            label={t("Eliminar")}
            tone="danger"
            width="short"
            onClick={() => setDeleteOpen(true)}
            disabled={!detail}
          />}
        </div>
      </div>

      <div className="grid gap-6">
        {detail && <OriginalDocumentPreview id={detail.id} filename={detail.filename} />}
        <details className="card order-3 group p-6">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 [&::-webkit-details-marker]:hidden">
            <div>
              <h3 className="text-lg font-semibold text-ink">{t("Fragmentos para diagnóstico")}</h3>
              <p className="text-sm text-ink-muted">
                {t("Vista técnica de cómo se dividió el documento para las búsquedas.")}
              </p>
            </div>
            <span className="text-xs font-medium text-ink-muted">
              {totalChunks} {t("Fragmentos").toLowerCase()} · <span className="group-open:hidden">{t("Mostrar")}</span><span className="hidden group-open:inline">{t("Ocultar")}</span>
            </span>
          </summary>
          <div className="mt-6 space-y-4">
            <p className="text-xs text-ink-muted">{language === "es" ? "Mostrando" : "Showing"} {start}–{end} {language === "es" ? "de" : "of"} {totalChunks}</p>
            {loadingChunks ? (
              <div className="flex min-h-[160px] items-center justify-center text-ink-muted">
                <span className="h-6 w-6 animate-spin rounded-full border-3 border-primary/30 border-t-primary" />
              </div>
            ) : chunks.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center text-sm text-ink-muted">
                {t("Aún no hay fragmentos disponibles para este documento.")}
              </div>
            ) : (
              chunks.map((chunk) => (
                <div key={chunk.chunk_id} className="rounded-2xl border border-border/70 bg-white/90 p-5 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary">
                      <DocumentTextIcon className="h-4 w-4" />
                      {language === "es" ? "Fragmento" : "Fragment"} #{chunk.chunk_no + 1}
                    </div>
                    <button
                      type="button"
                      className="inline-flex items-center gap-2 text-xs font-semibold text-primary transition hover:text-primary-dark"
                      onClick={() => handleCopy(chunk.text_preview)}
                    >
                      <ClipboardDocumentCheckIcon className="h-4 w-4" /> {t("Copiar")}
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
                {language === "es" ? "Página" : "Page"} <span className="font-semibold text-ink">{page}</span> {language === "es" ? "de" : "of"}
                <span className="font-semibold text-ink"> {pageCount}</span>
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1 || loadingChunks}
                >
                  {t("Anterior")}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setPage(Math.min(pageCount, page + 1))}
                  disabled={page === pageCount || loadingChunks}
                >
                  {t("Siguiente")}
                </Button>
              </div>
            </div>
          )}
        </details>

        <div className="card order-1 space-y-4 p-6">
          <h3 className="text-lg font-semibold text-ink">{t("Resumen del documento")}</h3>
          {loadingDetail || !detail ? (
            <div className="flex min-h-[180px] items-center justify-center text-ink-muted">
              {t("Cargando detalle...")}
            </div>
          ) : (
            <div className="space-y-4 text-sm text-ink-muted">
              <div>
                <p className="font-semibold text-ink">{detail.filename}</p>
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
                  <dt className="font-medium text-ink">{t("Subido por")}</dt>
                  <dd className="min-w-0 max-w-[70%] text-right break-all">
                    {detail.uploaded_by_email ? <><span className="block font-medium text-ink">{detail.uploaded_by_name || detail.uploaded_by_email}</span>{detail.uploaded_by_name && <span className="block">{detail.uploaded_by_email}</span>}</> : t("No registrado")}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">{t("Área")}</dt>
                  <dd>{detail.area ?? "--"}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">{t("Rol")}</dt>
                  <dd>{detail.role ?? "--"}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">{t("Vigencia")}</dt>
                  <dd>{formatDateOnly(detail.vigencia)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="font-medium text-ink">{t("Última ingesta")}</dt>
                  <dd>{formatIsoDate(detail.last_ingested_at)}</dd>
                </div>
              </dl>
              {detail.error_msg && (
                <div className="rounded-xl bg-red-50 px-4 py-3 text-xs text-red-600">
                  {t("Error")}: {detail.error_msg}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <ConfirmDialog
        open={rehydrateOpen}
        onClose={() => setRehydrateOpen(false)}
        title={t("Re-ingestar documento")}
        description={
          detail
            ? (language === "es" ? `Se volverá a procesar “${detail.filename}”. Esto puede tardar unos minutos.` : `“${detail.filename}” will be processed again. This may take a few minutes.`)
            : ""
        }
        confirmText={t("Re-ingestar")}
        onConfirm={handleRehydrate}
        loading={actionLoading}
      />

      <ConfirmDialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title={t("Eliminar documento")}
        description={
          detail
            ? (language === "es" ? `Eliminarás definitivamente “${detail.filename}” y su contenido de búsqueda.` : `You will permanently delete “${detail.filename}” and its search content.`)
            : ""
        }
        confirmText={t("Eliminar")}
        confirmVariant="danger"
        onConfirm={handleDelete}
        loading={actionLoading}
      />
    </div>
  );
}
