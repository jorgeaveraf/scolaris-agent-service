import {
  BoltIcon,
  CpuChipIcon,
  DocumentArrowDownIcon,
  DocumentCheckIcon,
  DocumentMagnifyingGlassIcon,
  ExclamationTriangleIcon,
  QueueListIcon,
  SignalIcon,
} from "@heroicons/react/24/outline";
import { StatCard } from "../components/dashboard/StatCard";
import { Button } from "../components/ui/Button";
import { useMetricsOverview } from "../features/metrics/hooks/useMetricsOverview";

export function DashboardPage() {
  const { metrics, loading, refresh } = useMetricsOverview();
  const docStats = metrics?.ingestion.documents;
  const chatLatency = metrics?.http.endpoints["POST /chat"];
  const chatStreamLatency = metrics?.http.endpoints["POST /chat/stream"];
  const totalChatRequests =
    (chatLatency?.count ?? 0) + (chatStreamLatency?.count ?? 0);
  const errorCounts = metrics?.http.errors ?? {};
  const totalErrors = Object.values(errorCounts).reduce(
    (acc, value) => acc + (value ?? 0),
    0,
  );
  const errorTrend = ["400", "401", "403", "429", "503", "500"]
    .map((code) => `${code}: ${errorCounts[code] ?? 0}`)
    .join(" · ");
  const tokensChat = metrics?.tokens.by_endpoint["chat"];
  const queueStats = metrics?.ingestion.queue;
  const memoryStats = metrics?.memory;
  const graphSteps = Object.entries(metrics?.graph.steps ?? {});
  const windowMinutes = metrics
    ? Math.round(metrics.window_seconds / 60)
    : undefined;

  const formatLatency = (p50?: number | null, p95?: number | null) => {
    if (p50 == null || p95 == null) return "--";
    return `${p50} / ${p95} ms`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-ink">Métricas clave</h1>
          <p className="text-sm text-ink-muted">
            Ventana de observabilidad{" "}
            {windowMinutes ? `${windowMinutes} min` : "reciente"}.
          </p>
        </div>
        <Button variant="secondary" onClick={() => refresh()} loading={loading}>
          Actualizar
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total de documentos"
          value={docStats ? docStats.total : "--"}
          icon={<DocumentMagnifyingGlassIcon className="h-7 w-7" />}
        />
        <StatCard
          label="Listos para usar"
          value={docStats ? docStats.ready : "--"}
          icon={<DocumentCheckIcon className="h-7 w-7" />}
          variant="primary"
        />
        <StatCard
          label="En procesamiento"
          value={docStats ? docStats.processing : "--"}
          icon={<DocumentArrowDownIcon className="h-7 w-7" />}
          trend={
            queueStats?.pending != null
              ? `En cola: ${queueStats.pending} pendientes`
              : "Actualiza para ver el estado más reciente."
          }
        />
        <StatCard
          label="Con errores"
          value={docStats ? docStats.error : "--"}
          icon={<ExclamationTriangleIcon className="h-7 w-7" />}
          variant="warning"
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Latencia chat p50 / p95"
          value={formatLatency(chatLatency?.p50_ms, chatLatency?.p95_ms)}
          icon={<BoltIcon className="h-7 w-7" />}
          trend={
            chatStreamLatency
              ? `Stream p50/p95: ${formatLatency(
                  chatStreamLatency.p50_ms,
                  chatStreamLatency.p95_ms,
                )}`
              : undefined
          }
        />
        <StatCard
          label="Tráfico de chat"
          value={metrics ? `${totalChatRequests} reqs` : "--"}
          icon={<SignalIcon className="h-7 w-7" />}
          trend={
            windowMinutes
              ? `Ventana de ${windowMinutes} min`
              : "Ventana reciente"
          }
        />
        <StatCard
          label="Errores recientes"
          value={metrics ? totalErrors : "--"}
          icon={<ExclamationTriangleIcon className="h-7 w-7" />}
          variant="warning"
          trend={errorTrend}
        />
        <StatCard
          label="Memoria activa"
          value={
            memoryStats ? `${memoryStats.active_sessions} sesiones` : "--"
          }
          icon={<CpuChipIcon className="h-7 w-7" />}
          trend={
            memoryStats?.avg_turns != null
              ? `Vueltas promedio: ${memoryStats.avg_turns?.toFixed(2) ?? "-"}`
              : undefined
          }
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <StatCard
          label="Tokens por request"
          value={
            tokensChat?.avg_total_tokens != null
              ? `${tokensChat.avg_total_tokens} tokens`
              : "--"
          }
          icon={<BoltIcon className="h-7 w-7" />}
          trend={
            tokensChat
              ? `Totales: ${tokensChat.total_tokens} · Requests: ${tokensChat.requests}`
              : "Esperando actividad"
          }
        />
        <StatCard
          label="Cola de ingestión"
          value={
            queueStats?.pending != null ? queueStats.pending : "sin datos"
          }
          icon={<QueueListIcon className="h-7 w-7" />}
          trend={`Encolados: ${queueStats?.recent_enqueued ?? 0} · Procesados: ${
            queueStats?.recent_processed ?? 0
          }`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-ink">
                Pasos del grafo
              </h2>
              <p className="text-sm text-ink-muted">
                Latencia por nodo LangGraph (p50/p95 en ms).
              </p>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm text-ink">
              <thead>
                <tr className="text-ink-muted">
                  <th className="py-2 pr-4">Paso</th>
                  <th className="py-2 pr-4">p50 / p95</th>
                  <th className="py-2 pr-4">Ejecuciones</th>
                </tr>
              </thead>
              <tbody>
                {graphSteps.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="py-3 text-ink-muted">
                      Aún no hay ejecuciones recientes del grafo.
                    </td>
                  </tr>
                ) : (
                  graphSteps.map(([step, data]) => (
                    <tr key={step} className="border-t border-slate-100">
                      <td className="py-2 pr-4 font-medium capitalize">
                        {step.replace("_", " ")}
                      </td>
                      <td className="py-2 pr-4 text-ink-muted">
                        {formatLatency(data.p50_ms, data.p95_ms)}
                      </td>
                      <td className="py-2 pr-4 text-ink-muted">
                        {data.count}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card flex flex-col gap-3 p-6">
          <h2 className="text-lg font-semibold text-ink">Resumen rápido</h2>
          <p className="text-sm text-ink-muted">
            Métricas agregadas de ingestión y uso de memoria para diagnósticos
            rápidos.
          </p>
          <ul className="mt-2 space-y-2 text-sm text-ink">
            <li>
              <span className="font-semibold text-ink">Ingestión:</span>{" "}
              {docStats
                ? `${docStats.ready} ready · ${docStats.processing} processing · ${docStats.error} error`
                : "sin datos"}
            </li>
            <li>
              <span className="font-semibold text-ink">Cola:</span>{" "}
              {queueStats?.pending != null
                ? `${queueStats.pending} pendientes`
                : "cola no inicializada"}
            </li>
            <li>
              <span className="font-semibold text-ink">Memoria:</span>{" "}
              {memoryStats
                ? `${memoryStats.active_sessions} sesiones · ${
                    memoryStats.avg_turns != null
                      ? `${memoryStats.avg_turns} turns`
                      : "sin promedio"
                  }`
                : "sin datos"}
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
