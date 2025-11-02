import {
  DocumentArrowDownIcon,
  DocumentCheckIcon,
  DocumentMagnifyingGlassIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import { useDocumentStats } from "../features/documents/hooks/useDocumentStats";
import { StatCard } from "../components/dashboard/StatCard";
import { Button } from "../components/ui/Button";
import { Link } from "react-router-dom";

export function DashboardPage() {
  const { stats, loading, refresh } = useDocumentStats();

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total de documentos"
          value={stats ? stats.total : "--"}
          icon={<DocumentMagnifyingGlassIcon className="h-7 w-7" />}
        />
        <StatCard
          label="Listos para usar"
          value={stats ? stats.ready : "--"}
          icon={<DocumentCheckIcon className="h-7 w-7" />}
          variant="primary"
        />
        <StatCard
          label="En procesamiento"
          value={stats ? stats.processing : "--"}
          icon={<DocumentArrowDownIcon className="h-7 w-7" />}
          trend="Actualiza para ver el estado más reciente."
        />
        <StatCard
          label="Con errores"
          value={stats ? stats.error : "--"}
          icon={<ExclamationTriangleIcon className="h-7 w-7" />}
          variant="warning"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-ink">
                Actividad reciente
              </h2>
              <p className="text-sm text-ink-muted">
                Consulta los últimos documentos ingeridos y su estado.
              </p>
            </div>
            <Button variant="secondary" onClick={() => refresh()} loading={loading}>
              Actualizar
            </Button>
          </div>
          <div className="mt-6 flex flex-col gap-4 text-sm text-ink-muted">
            <p>
              Los registros más recientes aparecerán aquí una vez que comiences a
              cargar documentos.
            </p>
            <Link
              to="/documents"
              className="inline-flex items-center gap-2 text-primary"
            >
              Ir a Documentos
              <span aria-hidden>→</span>
            </Link>
          </div>
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-semibold text-ink">Sugerencias</h2>
          <ul className="mt-4 space-y-3 text-sm text-ink-muted">
            <li>• Reingesta documentos con errores para reconstruir sus chunks.</li>
            <li>• Usa los filtros por rol y área para segmentar la información.</li>
            <li>• Elimina archivos obsoletos para mantener el RAG preciso.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
