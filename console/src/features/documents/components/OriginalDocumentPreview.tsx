import { lazy, Suspense, useEffect, useState } from "react";
import { ArrowDownTrayIcon } from "@heroicons/react/24/outline";
import { ExpandableIconLink } from "../../../components/ui/ExpandableIconAction";
import { getOriginalDocument } from "../../../api/documents";
import { useLanguage } from "../../../i18n/LanguageProvider";

const MarkdownPreview = lazy(() => import("./MarkdownPreview"));

type PreviewKind = "pdf" | "markdown" | "html" | "text" | "other";
type PreviewState = {
  loading: boolean;
  error: boolean;
  originalUrl: string | null;
  previewUrl: string | null;
  text: string;
};

function previewKind(filename: string): PreviewKind {
  const extension = filename.split(".").pop()?.toLowerCase();
  if (extension === "pdf") return "pdf";
  if (extension === "md") return "markdown";
  if (extension === "html") return "html";
  if (extension === "txt") return "text";
  return "other";
}

const emptyPreview: PreviewState = {
  loading: true,
  error: false,
  originalUrl: null,
  previewUrl: null,
  text: "",
};

export function OriginalDocumentPreview({ id, filename }: { id: string; filename: string }) {
  const { t } = useLanguage();
  const kind = previewKind(filename);
  const [preview, setPreview] = useState<PreviewState>(emptyPreview);

  useEffect(() => {
    let cancelled = false;
    let originalUrl: string | null = null;
    let previewUrl: string | null = null;
    setPreview(emptyPreview);

    void getOriginalDocument(id).then(async (blob) => {
      originalUrl = URL.createObjectURL(blob);
      let text = "";
      if (kind === "markdown" || kind === "text" || kind === "html") {
        text = await blob.text();
      }
      if (kind === "html") {
        // Uploaded HTML remains visually useful without running scripts or loading outside resources.
        const policy = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:">`;
        previewUrl = URL.createObjectURL(new Blob([policy, text], { type: "text/html" }));
      }
      if (cancelled) {
        URL.revokeObjectURL(originalUrl);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        return;
      }
      setPreview({ loading: false, error: false, originalUrl, previewUrl, text });
    }).catch(() => {
      if (!cancelled) setPreview({ ...emptyPreview, loading: false, error: true });
    });

    return () => {
      cancelled = true;
      if (originalUrl) URL.revokeObjectURL(originalUrl);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [id, kind]);

  return (
    <section aria-labelledby="original-document-heading" className="card order-2 space-y-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 id="original-document-heading" className="text-lg font-semibold text-ink">{t("Archivo original")}</h3>
          <p className="mt-1 text-sm text-ink-muted">{t("Vista del archivo tal como fue cargado, separada de los fragmentos de búsqueda.")}</p>
        </div>
        {preview.originalUrl && <ExpandableIconLink href={preview.originalUrl} download={filename} icon={<ArrowDownTrayIcon className="h-5 w-5" />} label={t("Descargar original")} width="long" />}
      </div>

      {preview.loading ? (
        <div className="flex min-h-48 items-center justify-center text-sm text-ink-muted">{t("Cargando vista previa...")}</div>
      ) : preview.error ? (
        <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-5 text-sm text-amber-900">{t("No se pudo mostrar el archivo original. Puede que ya no esté disponible.")}</div>
      ) : kind === "pdf" && preview.originalUrl ? (
        <iframe title={filename} src={preview.originalUrl} sandbox="" referrerPolicy="no-referrer" className="h-[640px] w-full rounded-xl border border-border bg-white" />
      ) : kind === "html" && preview.previewUrl ? (
        <iframe title={filename} src={preview.previewUrl} sandbox="" referrerPolicy="no-referrer" className="h-[640px] w-full rounded-xl border border-border bg-white" />
      ) : kind === "markdown" ? (
        <Suspense fallback={<div className="flex min-h-48 items-center justify-center text-sm text-ink-muted">{t("Cargando vista previa...")}</div>}>
          <MarkdownPreview text={preview.text} />
        </Suspense>
      ) : kind === "text" ? (
        <pre className="max-h-[640px] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-border bg-white p-6 text-sm leading-6 text-ink">{preview.text}</pre>
      ) : (
        <div className="rounded-xl border border-border bg-slate-25 px-4 py-5 text-sm text-ink-muted">{t("Este formato no tiene vista previa fiel en el navegador. Descarga el original para abrirlo.")}</div>
      )}
    </section>
  );
}
