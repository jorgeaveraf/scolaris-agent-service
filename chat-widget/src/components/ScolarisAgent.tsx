// chat-widget/src/components/ScolarisAgent.tsx
import React, { useEffect, useState } from "react";

export type ScolarisAgentProps = {
  apiBase: string;        // ej: http://localhost:8000
  role?: string | null;   // ej: "ventas", "soporte", null
};

export default function ScolarisAgent({ apiBase, role = null }: ScolarisAgentProps) {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Inicia sesión (setea cookie 'sid') una sola vez
  useEffect(() => {
    fetch(`${apiBase}/session/start`, { method: "POST", credentials: "include" }).catch(() => {});
  }, [apiBase]);

  const ask = async () => {
    setLoading(true);
    setAnswer(null);
    setCitations([]);
    const res = await fetch(`${apiBase}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ question: q, role })
    });
    const data = await res.json();
    setAnswer(data.answer);
    setCitations(data.citations || []);
    setLoading(false);
  };

  return (
    <div style={{ padding: 16, maxWidth: 640, border: "1px solid #ddd", borderRadius: 16 }}>
      <h2>Agente Scolaris</h2>
      <textarea
        style={{ width: "100%", padding: 8 }}
        rows={3}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Escribe tu pregunta"
      />
      <div>
        <button onClick={ask} disabled={loading} style={{ marginTop: 8 }}>
          {loading ? "Consultando..." : "Enviar"}
        </button>
      </div>

      {answer && (
        <div style={{ marginTop: 12 }}>
          <div><strong>Respuesta</strong></div>
          <div style={{ whiteSpace: "pre-wrap" }}>{answer}</div>
          {citations.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <div><strong>Fuentes</strong></div>
              <ul>
                {citations.map((c: any, i: number) => (
                  <li key={i}>
                    [{i + 1}] score={(c.score || 0).toFixed(2)} — {(c.content || "").slice(0, 80)}...
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
