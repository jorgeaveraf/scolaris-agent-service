import React from "react";
import { createRoot } from "react-dom/client";
import { ScolarisChatBubble } from "../src/lib/ScolarisChatBubble";
import "../src/lib/styles.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div className="scolaris-dev-shell">
      <ScolarisChatBubble
        baseUrl={import.meta.env.VITE_AGENT_API ?? "http://localhost:8000"}
        role={import.meta.env.VITE_AGENT_ROLE ?? undefined}
      />
    </div>
  </React.StrictMode>,
);
