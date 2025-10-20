/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_AGENT_API: string
    readonly VITE_AGENT_ROLE?: string
  }
  interface ImportMeta {
    readonly env: ImportMetaEnv
  }
  