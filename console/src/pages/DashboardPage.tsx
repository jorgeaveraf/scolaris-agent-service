import {
  ArrowPathIcon,
  ArrowRightIcon,
  ChatBubbleLeftRightIcon,
  DocumentCheckIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  UserGroupIcon,
} from "@heroicons/react/24/outline";
import { Link } from "react-router-dom";
import { StatCard } from "../components/dashboard/StatCard";
import { useDashboardSummary } from "../features/metrics/hooks/useDashboardSummary";
import { useAuth } from "../hooks/useAuth";
import { useLanguage } from "../i18n/LanguageProvider";

export function DashboardPage() {
  const { summary, loading, error, refresh } = useDashboardSummary();
  const { role } = useAuth();
  const { t, language } = useLanguage();
  const documents = summary?.documents;
  const days = summary?.chat_window_days ?? 7;
  const identifiedPeople = summary?.identified_people;
  const anonymousInteractions = summary?.anonymous_interactions ?? 0;

  const status = !summary
    ? t("Cargando el estado de tus fuentes")
    : documents?.error
      ? t("Hay documentos que requieren atención")
      : documents?.processing
        ? t("Hay documentos en preparación")
        : documents?.ready
          ? t("Tus fuentes están disponibles")
          : t("Aún no hay documentos disponibles");
  const statusDetail = !summary
    ? t("Estamos consultando los datos de la consola.")
    : documents?.error
      ? t("Revisa los documentos con error para que el asistente pueda usarlos.")
      : documents?.processing
        ? t("Los documentos en proceso aparecerán como disponibles al terminar.")
        : documents?.ready
          ? t("El asistente ya puede consultar los documentos listos.")
          : t("Carga un documento para empezar a darle información al asistente.");

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">{t("Operación")}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">{t("Vista general")}</h1>
          <p className="mt-2 text-sm text-ink-muted">{t("Contenido disponible, uso reciente y acceso al asistente.")}</p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          aria-label={t("Actualizar datos")}
          title={t("Actualizar datos")}
          className="group inline-flex h-11 w-11 shrink-0 items-center justify-center gap-0 overflow-hidden rounded-xl border border-border bg-white text-sm font-semibold text-ink transition-[width,gap,border-color,color] duration-200 hover:w-48 hover:gap-2 hover:border-primary hover:text-primary focus-visible:w-48 focus-visible:gap-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-70 motion-reduce:transition-none"
        >
          <ArrowPathIcon className={`h-4 w-4 shrink-0 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
          <span className="max-w-0 overflow-hidden whitespace-nowrap opacity-0 transition-[max-width,opacity] duration-200 group-hover:max-w-32 group-hover:opacity-100 group-focus-visible:max-w-32 group-focus-visible:opacity-100 motion-reduce:transition-none">{t("Actualizar datos")}</span>
        </button>
      </header>

      {error && (
        <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
          {t("No se pudieron actualizar los datos. Se muestra la última información disponible, si la hay.")}
        </div>
      )}

      <section
        className="group relative isolate overflow-hidden rounded-[28px] px-7 py-8 text-white shadow-lg md:px-9 md:py-10"
        style={{ background: "linear-gradient(135deg, rgb(var(--accent-banner-start)), rgb(var(--accent-banner-end)))" }}
        onMouseMove={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          event.currentTarget.style.setProperty("--glow-x", `${event.clientX - bounds.left}px`);
          event.currentTarget.style.setProperty("--glow-y", `${event.clientY - bounds.top}px`);
        }}
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 motion-reduce:transition-none"
          style={{ background: "radial-gradient(185px circle at var(--glow-x, 50%) var(--glow-y, 50%), rgb(var(--accent-glow) / 0.23), rgb(var(--accent-glow) / 0.045) 46%, transparent 78%)" }}
        />
        <div className="relative z-10 flex flex-wrap items-end justify-between gap-6">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-200">{t("Estado del contenido")}</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight md:text-3xl">{status}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-200">{statusDetail}</p>
          </div>
          <Link to="/documents" className="inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 hover:bg-slate-100 hover:text-slate-900">
            {t("Ver documentos")} <ArrowRightIcon className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <section aria-labelledby="documents-heading" className="space-y-4">
        <div>
          <h2 id="documents-heading" className="text-xl font-semibold text-ink">{t("Documentos")}</h2>
          <p className="mt-1 text-sm text-ink-muted">{t("Estado actual de los archivos cargados; estas cifras se conservan entre sesiones.")}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label={t("Listos para consultar")} value={documents?.ready ?? "—"} icon={<DocumentCheckIcon className="h-6 w-6" />} trend={t("El asistente ya puede usar estos documentos para responder.")} />
          <StatCard label={t("En preparación")} value={documents?.processing ?? "—"} icon={<DocumentTextIcon className="h-6 w-6" />} trend={t("Se están procesando y aún no están disponibles para responder.")} />
          <StatCard label={t("Requieren atención")} value={documents?.error ?? "—"} icon={<ExclamationTriangleIcon className="h-6 w-6" />} variant={documents?.error ? "warning" : "default"} trend={t("Su procesamiento falló; revisa el detalle para volver a intentarlo.")} />
          <StatCard label={t("Total cargados")} value={documents?.total ?? "—"} icon={<DocumentTextIcon className="h-6 w-6" />} trend={t("Incluye todos los documentos cargados, sin importar su estado.")} />
        </div>
      </section>

      <section aria-labelledby="activity-heading" className="space-y-4">
        <div>
          <h2 id="activity-heading" className="text-xl font-semibold text-ink">{t("Uso del chat")}</h2>
          <p className="mt-1 text-sm text-ink-muted">{language === "es" ? `Consultas terminadas en los últimos ${days} días, tomadas del historial guardado.` : `Completed questions in the last ${days} days, from saved history.`}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard
            label={t("Personas identificadas que lo usaron")}
            value={identifiedPeople ?? "—"}
            icon={<UserGroupIcon className="h-6 w-6" />}
            trend={anonymousInteractions > 0 ? (language === "es" ? `${anonymousInteractions} consultas anónimas no permiten contar personas únicas.` : `${anonymousInteractions} anonymous questions cannot be used to count unique people.`) : t("Cada persona se cuenta una vez en el periodo.")}
          />
          <StatCard
            label={t("Consultas registradas")}
            value={summary?.chat_interactions ?? "—"}
            icon={<ChatBubbleLeftRightIcon className="h-6 w-6" />}
            trend={t("Incluye respuestas con fuente y respuestas que indicaron falta de respaldo.")}
          />
        </div>
      </section>

      <section aria-labelledby="access-heading" className="space-y-4">
        <div>
          <h2 id="access-heading" className="text-xl font-semibold text-ink">{t("Acceso habilitado")}</h2>
          <p className="mt-1 text-sm text-ink-muted">{t("Cuentas autorizadas actualmente; esto no indica cuántas personas están conectadas ahora.")}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard label={t("Cuentas habilitadas para el chat")} value={summary?.identity_enabled ? summary.chat_enabled_people : t("No aplica")} icon={<UserGroupIcon className="h-6 w-6" />} trend={t(summary?.chat_login_required ? "El chat exige acceso; incluye a quienes también administran la consola." : "El chat permite visitantes; esta cifra cuenta solo cuentas registradas.")} />
          <StatCard label={t("Pueden entrar a la consola")} value={summary?.identity_enabled ? summary.console_enabled_people : t("No aplica")} icon={<UserGroupIcon className="h-6 w-6" />} trend={t("Acceso de lectura, gestión de documentos o administración.")} />
        </div>
        {role === "admin" && (
          <Link to="/users" className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-primary-dark">
            {t("Gestionar personas y permisos")} <ArrowRightIcon className="h-4 w-4" />
          </Link>
        )}
      </section>
    </div>
  );
}
