import {
  ArrowPathIcon,
  BoltIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
  QueueListIcon,
  SignalIcon,
} from "@heroicons/react/24/outline";
import { StatCard } from "../components/dashboard/StatCard";
import { ExpandableIconButton } from "../components/ui/ExpandableIconAction";
import { useMetricsOverview } from "../features/metrics/hooks/useMetricsOverview";
import { useLanguage } from "../i18n/LanguageProvider";

export function ObservabilityPage() {
  const { t, language } = useLanguage();
  const { metrics, loading, refresh } = useMetricsOverview();
  const chatLatency = metrics?.http.endpoints["POST /chat"];
  const streamLatency = metrics?.http.endpoints["POST /chat/stream"];
  const tokenStats = metrics?.tokens.totals;
  const errorCounts = metrics?.http.errors ?? {};
  const totalErrors = Object.values(errorCounts).reduce((sum, count) => sum + (count ?? 0), 0);
  const windowMinutes = metrics ? Math.round(metrics.window_seconds / 60) : null;
  const graphSteps = Object.entries(metrics?.graph.steps ?? {}).filter(
    ([name]) => !name.toLowerCase().endsWith("_count"),
  );
  const latency = (p50?: number | null, p95?: number | null) =>
    p50 == null || p95 == null ? "—" : `${p50.toFixed(0)} / ${p95.toFixed(0)} ms`;
  const errorDetails = ["400", "401", "403", "429", "500", "503", "other"]
    .map((code) => `${code === "other" ? (language === "es" ? "Otros 4xx" : "Other 4xx") : code}: ${errorCounts[code] ?? 0}`)
    .join(" · ");

  return (
    <div className="mx-auto max-w-7xl space-y-8 pb-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">{t("Diagnóstico técnico")}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">{t("Observabilidad")}</h1>
          <p className="mt-2 text-sm text-ink-muted">{t("Rendimiento y errores de los servicios que sostienen al asistente.")}</p>
        </div>
        <ExpandableIconButton
          icon={<ArrowPathIcon className={`h-5 w-5 ${loading ? "animate-spin" : ""}`} />}
          label={t("Actualizar métricas")}
          width="long"
          disabled={loading}
          aria-busy={loading}
          onClick={() => void refresh()}
        />
      </header>

      <div className="rounded-2xl border border-sky-100 bg-sky-50 px-5 py-4 text-sm leading-6 text-slate-700">
        {language === "es" ? `Esta vista muestra la actividad de los últimos ${windowMinutes ?? "—"} minutos. Las muestras viven en memoria y se reinician cuando se reinicia el servicio. Los conteos duraderos de documentos y consultas están en la Vista general.` : `This view shows activity from the last ${windowMinutes ?? "—"} minutes. Samples are stored in memory and reset when the service restarts. Persistent document and question counts are on the Overview.`}
      </div>

      <section aria-labelledby="service-heading" className="space-y-4">
        <h2 id="service-heading" className="text-xl font-semibold text-ink">{t("Servicio de chat")}</h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <StatCard
            label={t("Latencia HTTP p50 / p95")}
            value={latency(streamLatency?.p50_ms ?? chatLatency?.p50_ms, streamLatency?.p95_ms ?? chatLatency?.p95_ms)}
            icon={<BoltIcon className="h-6 w-6" />}
            trend={t("Tiempo de las solicitudes recientes del chat.")}
          />
          <StatCard
            label={t("Solicitudes al chat")}
            value={metrics ? (chatLatency?.count ?? 0) + (streamLatency?.count ?? 0) : "—"}
            icon={<SignalIcon className="h-6 w-6" />}
            trend={t("Incluye intentos fallidos; no equivale a personas únicas.")}
          />
          <StatCard
            label={t("Tokens por respuesta")}
            value={tokenStats?.avg_total_tokens != null ? Math.round(tokenStats.avg_total_tokens) : "—"}
            icon={<BoltIcon className="h-6 w-6" />}
            trend={tokenStats ? (language === "es" ? `${tokenStats.requests} respuestas medidas · ${tokenStats.total_tokens} tokens totales` : `${tokenStats.requests} measured responses · ${tokenStats.total_tokens} total tokens`) : t("Sin muestras recientes.")}
          />
        </div>
      </section>

      <section aria-labelledby="health-heading" className="space-y-4">
        <h2 id="health-heading" className="text-xl font-semibold text-ink">{t("Diagnóstico de operación")}</h2>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <StatCard
            label={t("Respuestas HTTP con error")}
            value={metrics ? totalErrors : "—"}
            icon={<ExclamationTriangleIcon className="h-6 w-6" />}
            variant={totalErrors ? "warning" : "default"}
            trend={errorDetails}
          />
          <StatCard
            label={t("Documentos pendientes en cola")}
            value={metrics?.ingestion.queue.pending ?? "—"}
            icon={<QueueListIcon className="h-6 w-6" />}
            trend={t("Estado de la cola de procesamiento en este momento.")}
          />
          <StatCard
            label={t("Sesiones guardadas en memoria")}
            value={metrics?.memory.active_sessions ?? "—"}
            icon={<CpuChipIcon className="h-6 w-6" />}
            trend={t("Sesiones en Redis; no representa usuarios conectados ahora.")}
          />
        </div>
      </section>

      <section className="card overflow-hidden">
        <div className="border-b border-border px-6 py-5">
          <h2 className="text-lg font-semibold text-ink">{t("Tiempos por etapa")}</h2>
          <p className="mt-1 text-sm text-ink-muted">{t("Percentiles de duración por paso del procesamiento; útiles para investigar lentitud.")}</p>
        </div>
        <div className="overflow-x-auto px-6 py-3">
          <table className="min-w-full text-left text-sm text-ink">
            <thead><tr className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
              <th className="py-3 pr-4">{t("Etapa")}</th><th className="py-3 pr-4">p50 / p95</th><th className="py-3 pr-4">{t("Ejecuciones")}</th>
            </tr></thead>
            <tbody>
              {graphSteps.length === 0 ? (
                <tr><td colSpan={3} className="py-6 text-ink-muted">{t("Todavía no hay tiempos recientes.")}</td></tr>
              ) : graphSteps.map(([step, data]) => (
                <tr key={step} className="border-t border-border/70">
                  <td className="py-3 pr-4 font-medium">{step.replaceAll("_", " ")}</td>
                  <td className="py-3 pr-4 tabular-nums text-ink-muted">{latency(data.p50_ms, data.p95_ms)}</td>
                  <td className="py-3 pr-4 tabular-nums text-ink-muted">{data.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
