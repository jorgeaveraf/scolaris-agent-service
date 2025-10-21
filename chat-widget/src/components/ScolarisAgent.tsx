// chat-widget/src/components/ScolarisAgent.tsx
import React, { useEffect, useMemo, useState } from "react";

export type ScolarisAgentProps = {
  apiBase: string;        // ej: http://localhost:8000
  role?: string | null;   // ej: "ventas", "soporte", null
};

export default function ScolarisAgent({ apiBase, role = null }: ScolarisAgentProps) {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [memOptIn, setMemOptIn] = useState(false);

  const STORAGE_USER_ID = "scolaris_user_id";
  const STORAGE_MEM_OPT_IN = "scolaris_mem_opt_in";

  const userId = useMemo(() => {
    if (typeof window === "undefined") return null;
    let stored = window.localStorage.getItem(STORAGE_USER_ID);
    if (!stored) {
      stored = (globalThis.crypto?.randomUUID?.() ?? `user-${Date.now()}`);
      window.localStorage.setItem(STORAGE_USER_ID, stored);
    }
    return stored;
  }, []);

  // Inicia cookie de sesión
  useEffect(() => {
    fetch(`${apiBase}/session/start`, { method: "POST", credentials: "include" }).catch(() => {});
  }, [apiBase]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedOptIn = window.localStorage.getItem(STORAGE_MEM_OPT_IN);
    setMemOptIn(storedOptIn === "1");
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_MEM_OPT_IN, memOptIn ? "1" : "0");
  }, [memOptIn]);

  const ask = async () => {
    setLoading(true);
    setAnswer(null);

    const res = await fetch(`${apiBase}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        question: q,
        role,
        user_id: userId,
        mem_opt_in: memOptIn
      })
    });

    const data = await res.json();
    setAnswer(data.answer);
    setLoading(false);
  };

  return (
    <div
      style={{
        padding: 16,
        maxWidth: 640,
        border: "1px solid #ddd",
        borderRadius: 16,
        fontFamily: "system-ui, sans-serif"
      }}
    >
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
      <label style={{ display: "block", marginTop: 12, fontSize: 14 }}>
        <input
          type="checkbox"
          checked={memOptIn}
          onChange={(e) => setMemOptIn(e.target.checked)}
          style={{ marginRight: 6 }}
        />
        Guardar historial reciente para continuar la conversación
      </label>

      {answer && (
        <div style={{ marginTop: 16 }}>
          <strong>Respuesta:</strong>
          <div style={{ whiteSpace: "pre-wrap", marginTop: 8 }}>{answer}</div>
        </div>
      )}
    </div>
  );
}
