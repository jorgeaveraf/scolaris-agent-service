import { Link } from "react-router-dom";

export function ChunksLandingPage() {
  return (
    <div className="card p-8">
      <h2 className="text-xl font-semibold text-ink">Explorador de chunks</h2>
      <p className="mt-2 text-sm text-ink-muted">
        Selecciona un documento desde la vista de{" "}
        <Link to="/documents" className="font-medium text-primary underline">
          Documentos
        </Link>{" "}
        para revisar sus chunks y metadatos en detalle.
      </p>
      <ul className="mt-6 space-y-2 text-sm text-ink-muted">
        <li>• Consulta el contenido fragmentado de cada documento.</li>
        <li>• Copia texto relevante y revisa tokens asociados.</li>
        <li>• Controla la vigencia y rol asignado a cada chunk.</li>
      </ul>
    </div>
  );
}
