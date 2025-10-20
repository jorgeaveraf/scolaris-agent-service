// chat-widget/src/App.tsx
import React from "react";
import ScolarisAgent from "./components/ScolarisAgent";

export default function App() {
  const apiBase = import.meta.env.VITE_AGENT_API || "http://localhost:8000";
  const role = import.meta.env.VITE_AGENT_ROLE ?? null;

  return (
    <div className="min-h-screen p-6">
      <ScolarisAgent apiBase={apiBase} role={role} />
    </div>
  );
}
