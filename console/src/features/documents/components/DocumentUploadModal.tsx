import { useEffect, useState } from "react";
import { isAxiosError } from "axios";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { uploadDocument } from "../../../api/documents";
import type { DocumentDetail } from "../../../types/admin";
import { Button } from "../../../components/ui/Button";
import { TextField } from "../../../components/ui/TextField";
import { Modal } from "../../../components/ui/Modal";
import { useLanguage } from "../../../i18n/LanguageProvider";

type Phase = "idle" | "uploading" | "processing" | "done";

interface FormValues {
  file: FileList;
  area: string;
  role: string;
  vigencia: string;
  sourceUrl: string;
}

interface DocumentUploadModalProps {
  open: boolean;
  onClose: () => void;
  onUploaded: (document: DocumentDetail) => void | Promise<void>;
}

export function DocumentUploadModal({ open, onClose, onUploaded }: DocumentUploadModalProps) {
  const { t, language } = useLanguage();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
    setError,
    watch,
  } = useForm<FormValues>({
    defaultValues: { area: "", role: "", vigencia: "", sourceUrl: "" },
  });
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!open) {
      setTimeout(() => {
        setPhase("idle");
        setProgress(0);
        reset();
      }, 200);
    }
  }, [open, reset]);

  const fileList = watch("file");
  const fileName = fileList && fileList.length > 0 ? fileList[0].name : "";

  const handleClose = () => {
    if (isSubmitting) return;
    onClose();
  };

  const onSubmit = handleSubmit(async (values) => {
    const file = values.file?.[0];
    if (!file) {
      setError("file", { message: t("Selecciona un archivo válido.") });
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    if (values.area) formData.append("area", values.area.trim());
    if (values.role) formData.append("role", values.role.trim());
    if (values.vigencia) formData.append("vigencia", values.vigencia);
    if (values.sourceUrl.trim()) formData.append("source_url", values.sourceUrl.trim());

    try {
      setPhase("uploading");
      const document = await uploadDocument(formData, {
        onUploadProgress: (event) => {
          if (!event.total) {
            setProgress((prev) => (prev < 40 ? prev + 5 : prev));
            return;
          }
          const pct = Math.round((event.loaded / event.total) * 80);
          setProgress(Math.min(90, Math.max(10, pct)));
        },
      });
      setProgress(100);
      setPhase(document.status === "ready" ? "done" : "processing");
      await onUploaded(document);
      if (document.status === "ready") {
        toast.success(language === "es" ? `Documento “${document.filename}” listo.` : `Document “${document.filename}” is ready.`);
      } else {
        toast.success(
          language === "es" ? `Documento “${document.filename}” cargado. Procesamiento en curso…` : `Document “${document.filename}” uploaded. Processing…`,
        );
      }
      setTimeout(() => {
        setPhase("done");
        onClose();
        reset();
        setProgress(0);
      }, 600);
    } catch (error: unknown) {
      toast.error(isAxiosError(error) && error.response?.status === 422
        ? (language === "es" ? "Archivo rechazado: formato inválido o contenido inseguro." : "File rejected: invalid format or unsafe content.")
        : t("No pudimos subir el documento. Intenta nuevamente."));
      setPhase("idle");
      setProgress(0);
    }
  });

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={t("Subir documento")}
      description={t("Acepta PDF, DOCX, TXT, MD y HTML. Máximo 20 MB por archivo.")}
    >
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="space-y-2">
          <label className="label">{t("Archivo")}</label>
          <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-primary/40 bg-primary/5 px-6 py-8 text-center text-sm text-primary transition hover:border-primary hover:bg-primary/10">
            <input
              type="file"
              className="sr-only"
              accept=".pdf,.docx,.txt,.md,.html"
              {...register("file")}
            />
            <span className="font-semibold">
              {fileName || t("Selecciona un archivo o arrástralo aquí")}
            </span>
            <span className="text-xs text-primary/70">
              {t("Formatos permitidos")}: PDF, DOCX, TXT, MD, HTML
            </span>
          </label>
          {errors.file && <p className="text-sm text-red-500">{errors.file.message}</p>}
        </div>

        <TextField
          id="sourceUrl"
          label={language === "es" ? "Enlace público de la fuente" : "Public source link"}
          placeholder="https://"
          hint={language === "es" ? "Opcional. Se mostrará junto al pasaje citado." : "Optional. Shown with the cited passage."}
          {...register("sourceUrl", {
            validate: value => !value || /^https:\/\/[^\s/]+/.test(value.trim()) ||
              (language === "es" ? "Usa un enlace HTTPS válido." : "Use a valid HTTPS link."),
          })}
        />
        {errors.sourceUrl && <p className="text-sm text-red-500">{errors.sourceUrl.message}</p>}

        <div className="grid gap-4 md:grid-cols-3">
          <TextField
            id="area"
            label={t("Área")}
            placeholder={t("Ej. Operaciones")}
            {...register("area")}
          />
          <TextField
            id="role"
            label={t("Rol")}
            placeholder={t("Ej. Analista")}
            {...register("role")}
          />
          <TextField
            id="vigencia"
            label={t("Vigencia")}
            type="date"
            hint={t("Opcional: define fecha de expiración")}
            {...register("vigencia")}
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-ink-muted">
            <span>{t("Estado")}</span>
            <span>
              {phase === "uploading"
                ? t("Subiendo…")
                : phase === "processing"
                  ? t("Procesando…")
                  : phase === "done"
                    ? t("Listo")
                    : t("En espera")}
            </span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-primary-dark transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={handleClose} type="button" disabled={isSubmitting}>
            {t("Cancelar")}
          </Button>
          <Button type="submit" loading={isSubmitting}>
            {t("Subir y procesar")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
