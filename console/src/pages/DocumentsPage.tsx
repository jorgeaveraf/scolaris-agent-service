import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowPathIcon, BackspaceIcon, PlusIcon } from "@heroicons/react/24/outline";
import { Button } from "../components/ui/Button";
import { ExpandableIconButton } from "../components/ui/ExpandableIconAction";
import { TextField } from "../components/ui/TextField";
import { SelectField } from "../components/ui/SelectField";
import { StatusBadge } from "../components/ui/StatusBadge";
import { DocumentUploadModal } from "../features/documents/components/DocumentUploadModal";
import { useDocumentsList } from "../features/documents/hooks/useDocumentsList";
import { formatIsoDate } from "../utils/format";
import { useAuth } from "../hooks/useAuth";
import { useLanguage } from "../i18n/LanguageProvider";

export function DocumentsPage() {
  const { role } = useAuth();
  const { t, language } = useLanguage();
  const canManage = role === "curator" || role === "admin";
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

  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = total === 0 ? 0 : Math.min(total, start + documents.length - 1);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h2 className="text-2xl font-semibold text-ink">{t("Documentos")}</h2>
          <p className="text-sm text-ink-muted">
            {t("Carga y administra las fuentes que el asistente puede consultar.")}
          </p>
        </div>
        {canManage && <ExpandableIconButton icon={<PlusIcon className="h-5 w-5" />} label={t("Nuevo documento")} tone="primary" width="long" onClick={() => setUploadOpen(true)} />}
      </div>

      <div className="card p-4">
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            id="search"
            placeholder={t("Buscar por nombre")}
            label={t("Buscar")}
            value={filters.q}
            onChange={(event) => updateFilter("q", event.target.value)}
          />
          <SelectField
            id="status"
            label={t("Estado")}
            value={filters.status}
            onChange={(event) => updateFilter("status", event.target.value)}
          >
            <option value="">{t("Todos")}</option>
            <option value="ready">{t("Listo")}</option>
            <option value="processing">{t("Procesando")}</option>
            <option value="error">{t("Error")}</option>
          </SelectField>
        </div>
        <details className="mt-4 border-t border-border/70 pt-4">
          <summary className="cursor-pointer text-sm font-semibold text-primary">{t("Más filtros")}</summary>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <TextField id="role" placeholder={t("Rol")} label={t("Rol")} value={filters.role} onChange={(event) => updateFilter("role", event.target.value)} />
            <TextField id="area" placeholder={t("Área")} label={t("Área")} value={filters.area} onChange={(event) => updateFilter("area", event.target.value)} />
            <TextField id="updated" placeholder="yyyy-mm-dd" label={t("Actualizado")} type="date" value={filters.updated} onChange={(event) => updateFilter("updated", event.target.value)} />
          </div>
        </details>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
          <p className="text-ink-muted">
            {language === "es" ? "Mostrando" : "Showing"} <span className="font-semibold text-ink">{start}</span> -
            <span className="font-semibold text-ink"> {end}</span> {language === "es" ? "de" : "of"}
            <span className="font-semibold text-ink"> {total}</span> {t("Documentos").toLowerCase()}
          </p>
          <div className="flex gap-2">
            <ExpandableIconButton icon={<BackspaceIcon className="h-5 w-5" />} label={t("Limpiar filtros")} width="medium" onClick={resetFilters} disabled={loading} />
            <ExpandableIconButton icon={<ArrowPathIcon className="h-5 w-5" />} label={t("Actualizar")} tone="quiet" width="short" onClick={() => refresh()} disabled={loading} />
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-slate-25 text-left text-xs font-semibold uppercase tracking-wide text-ink-muted">
              <tr>
                <th className="px-6 py-4">{t("Archivo")}</th>
                <th className="px-6 py-4">{t("Estado")}</th>
                <th className="px-6 py-4">{t("Actualizado")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70 text-sm">
              {loading ? (
                <tr>
                  <td colSpan={3} className="px-6 py-10 text-center">
                    <div className="inline-flex items-center gap-3 text-ink-muted">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
                      {t("Cargando documentos...")}
                    </div>
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr className="bg-white">
                  <td colSpan={3} className="px-6 py-10 text-center text-sm text-ink-muted">
                    {t('Aún no has cargado documentos. Usa el botón "Nuevo documento" para comenzar.')}
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="bg-white hover:bg-primary/5">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <Link to={`/documents/${doc.id}`} className="w-fit break-all font-semibold text-primary hover:underline focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                          {doc.filename}
                        </Link>
                      </div>
                    </td>
                    <td className="px-6 py-4"><StatusBadge status={doc.status} /></td>
                    <td className="px-6 py-4 text-ink-muted">{formatIsoDate(doc.updated_at)}</td>
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
            {language === "es" ? "Página" : "Page"} <span className="font-semibold text-ink">{page}</span> {language === "es" ? "de" : "of"}
            <span className="font-semibold text-ink"> {pageCount}</span>
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1 || loading}
            >
              {t("Anterior")}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setPage(Math.min(pageCount, page + 1))}
              disabled={page === pageCount || loading}
            >
              {t("Siguiente")}
            </Button>
          </div>
        </div>
      )}

      <DocumentUploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={async () => {
          await refresh();
          setUploadOpen(false);
        }}
      />

    </div>
  );
}
