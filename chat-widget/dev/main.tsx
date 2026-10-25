import React from "react";
import { createRoot } from "react-dom/client";
import { AgentChatBubble } from "../src/lib/AgentChatBubble";
import "../src/lib/styles.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div className="agent-dev-shell">
      <AgentChatBubble
        baseUrl={import.meta.env.VITE_AGENT_API ?? "http://localhost:8000"}
        role={import.meta.env.VITE_AGENT_ROLE ?? undefined}
      />
    </div>
  </React.StrictMode>,
);
