import { useEffect, useState } from "react";
import { ArrowPathIcon, MagnifyingGlassIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { apiClient } from "../api/client";
import { ExpandableIconButton } from "../components/ui/ExpandableIconAction";
import { useLanguage } from "../i18n/LanguageProvider";

type Source = { title: string; url?: string; snippet?: string };
type SourceGroup = Source & { passages: string[] };

function groupSources(sources: Source[]): SourceGroup[] {
  const groups = new Map<string, SourceGroup>();
  for (const source of sources) {
    const key = source.url || source.title;
    const group = groups.get(key) || { ...source, passages: [] };
    const passage = source.snippet?.trim();
    if (passage && !group.passages.includes(passage)) group.passages.push(passage);
    groups.set(key, group);
  }
  return [...groups.values()];
}

function sourceLabel(title: string): string {
  return title.replace(/^\d+[-_]/, "").replace(/\.(?:pdf|txt|docx?|html?|md)$/i, "")
    .replace(/[-_]+/g, " ")
    .replace(/\b(irs|sec|dst|upreit)\b/gi, (word) => word.toUpperCase())
    .replace(/\breits?\b/gi, (word) => word.length === 5 ? "REITs" : "REIT")
    .replace(/\bsightbridge\b/gi, "Sightbridge");
}
type ChatEntry = {
  id: string;
  actor_email: string | null;
  question: string;
  answer: string;
  sources: Source[];
  is_evaluation: boolean;
  created_at: string;
};
type HistoryResponse = { items: ChatEntry[]; total: number; limit: number; offset: number };
type UserGroup = { actor_email: string | null; display_name: string | null; message_count: number; last_message_at: string };
type UsersResponse = { items: UserGroup[]; total: number; limit: number; offset: number };

const PAGE_SIZE = 20;

export function ChatHistoryPage() {
  const { t, language } = useLanguage();
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [users, setUsers] = useState<UsersResponse | null>(null);
  const [selectedUser, setSelectedUser] = useState<UserGroup | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showEvaluations, setShowEvaluations] = useState(false);
  const [savingEntry, setSavingEntry] = useState<string | null>(null);

  const updateEvaluation = async (entry: ChatEntry) => {
    setSavingEntry(entry.id);
    try {
      await apiClient.patch(`/admin/chat-history/${entry.id}/evaluation`, { is_evaluation: !entry.is_evaluation });
      setRefreshVersion((version) => version + 1);
    } catch {
      setError(true);
    } finally {
      setSavingEntry(null);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(false);
    const params = { limit: PAGE_SIZE, offset: page * PAGE_SIZE, include_evaluation: showEvaluations, ...(query ? { q: query } : {}) };
    const request = selectedUser
      ? apiClient.get<HistoryResponse>("/admin/chat-history", { params: { ...params, actor_email: selectedUser.actor_email ?? "__anonymous__", newest_first: true } })
      : apiClient.get<UsersResponse>("/admin/chat-history/users", { params });
    request
      .then((response) => {
        if (!active) return;
        if (selectedUser) setData(response.data as HistoryResponse);
        else setUsers(response.data as UsersResponse);
      })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page, query, selectedUser, refreshVersion, showEvaluations]);

  const total = selectedUser ? data?.total : users?.total;
  const shown = selectedUser ? data?.items.length : users?.items.length;
  const formatDate = (date: string) => new Date(date).toLocaleString(language === "es" ? "es-MX" : "en-US", { dateStyle: "medium", timeStyle: "short" });

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <div>
        {selectedUser && (
          <button type="button" onClick={() => { setSelectedUser(null); setPage(0); }} className="mb-4 text-sm font-semibold text-primary hover:underline">
            ← {t("Volver a personas")}
          </button>
        )}
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="truncate text-2xl font-semibold text-ink">{selectedUser ? (selectedUser.display_name || selectedUser.actor_email || t("Visitantes anteriores")) : t("Historial del chat")}</h2>
            <p className="mt-1 truncate text-sm text-ink-muted">{selectedUser ? (selectedUser.actor_email || t("Consultas anteriores sin sesión")) : t("Explora las conversaciones por persona y abre una para ver sus mensajes.")}</p>
          </div>
          <ExpandableIconButton
            icon={<ArrowPathIcon className={`h-5 w-5 ${loading ? "animate-spin" : ""}`} />}
            label={t(selectedUser ? "Actualizar conversación" : "Actualizar historial")}
            tone="quiet"
            width="long"
            disabled={loading}
            onClick={() => { setPage(0); setRefreshVersion((version) => version + 1); }}
          />
        </div>
      </div>

      <label className="flex w-fit items-center gap-2 text-sm text-ink-muted">
        <input type="checkbox" checked={showEvaluations} onChange={(event) => { setShowEvaluations(event.target.checked); setPage(0); }} className="accent-primary" />
        {t("Incluir pruebas internas en el historial")}
      </label>

      <div className="relative">
        <label htmlFor="history-search" className="sr-only">{t("Buscar en el historial")}</label>
        <MagnifyingGlassIcon aria-hidden="true" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-muted" />
        <input
          id="history-search"
          type="text"
          maxLength={200}
          value={search}
          onChange={(event) => { setSearch(event.target.value); setPage(0); }}
          placeholder={t("Buscar por persona, fuente, pregunta o respuesta")}
          className="input !pl-12 !pr-12"
        />
        {search && <button type="button" onClick={() => { setSearch(""); setQuery(""); setPage(0); }} aria-label={t("Limpiar búsqueda")} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-ink-muted hover:bg-slate-100 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"><XMarkIcon aria-hidden="true" className="h-4 w-4" /></button>}
      </div>

      {!loading && !error && total !== undefined && (
        <div className="rounded-2xl border border-border bg-white px-5 py-4 text-sm text-ink-muted">
          <span className="text-2xl font-semibold text-ink">{total}</span>
          <span className="ml-3">{selectedUser ? (total === 1 ? t("intercambio en esta conversación") : t("intercambios en esta conversación")) : (total === 1 ? t("persona con conversación") : t("personas con conversaciones"))}</span>
        </div>
      )}

      {loading && <p className="text-sm text-ink-muted">{t("Cargando historial…")}</p>}
      {error && <p className="text-sm text-red-600" role="alert">{t("No se pudo cargar el historial.")}</p>}
      {!loading && !error && total === 0 && (
        <div className="card p-6 text-sm text-ink-muted">{query ? t("No hay consultas que coincidan con tu búsqueda.") : t(showEvaluations ? "Todavía no hay conversaciones registradas." : "No hay conversaciones operativas. Activa las pruebas internas para verlas.")}</div>
      )}
      {!loading && !error && !selectedUser && users?.items.map((user) => (
        <button
          key={user.actor_email ?? "legacy-visitors"}
          type="button"
          onClick={() => { setSelectedUser(user); setPage(0); }}
          className="card flex w-full items-center justify-between gap-4 p-5 text-left transition hover:border-primary/40 hover:shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-ink">{user.display_name || user.actor_email || t("Visitantes anteriores")}</span>
            {user.display_name && user.actor_email && <span className="mt-1 block truncate text-xs text-ink-muted">{user.actor_email}</span>}
            <span className="mt-2 block text-xs text-ink-muted">{user.message_count} {t(user.message_count === 1 ? "intercambio" : "intercambios")}</span>
          </span>
          <span className="shrink-0 text-right text-xs text-ink-muted">{formatDate(user.last_message_at)}<span className="mt-2 block font-semibold text-primary">{t("Ver conversación")} →</span></span>
        </button>
      ))}
      {!loading && !error && selectedUser && data && data.items.length > 0 && (
        <div className="card space-y-7 p-5 sm:p-7" aria-label={t("Conversación completa")}>
          {[...data.items].reverse().map((entry) => (
            <div key={entry.id} className="space-y-3">
              <time dateTime={entry.created_at} className="block text-center text-xs text-ink-muted">{formatDate(entry.created_at)}</time>
              <div className="ml-auto w-fit max-w-[85%] rounded-2xl bg-primary px-4 py-3 text-sm leading-6 text-white">
                <p className="max-h-72 overflow-y-auto whitespace-pre-wrap [overflow-wrap:anywhere]">{entry.question}</p>
              </div>
              <div className="mr-auto w-fit max-w-[85%] rounded-2xl bg-slate-100 px-4 py-3 text-sm leading-6 text-ink">
                <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{entry.answer}</p>
                {entry.is_evaluation && <p className="mt-2 text-xs font-semibold text-ink-muted">{t("Prueba interna")}</p>}
                {entry.sources.length > 0 && (
                  <div className="mt-3 border-t border-border pt-2 text-xs text-ink-muted">
                    <span className="font-semibold">{t("Fuentes")}: </span>
                    <div className="mt-1 space-y-1">
                      {groupSources(entry.sources).map((source, index) => (
                        <div key={`${entry.id}-source-${index}`}>
                          {source.url ? <a href={source.url} target="_blank" rel="noopener noreferrer" className="underline">{sourceLabel(source.title)}</a> : sourceLabel(source.title)}
                          {source.passages.length > 1 && <span> · {source.passages.length} {t("pasajes")}</span>}
                          {source.passages.length > 0 && (
                            <details className="mt-0.5 pl-2">
                              <summary className="cursor-pointer text-primary">{t("Ver pasajes citados")}</summary>
                              <ul className="mt-1 list-disc space-y-1 pl-4">
                                {source.passages.map((passage, passageIndex) => <li key={passageIndex}>{passage}</li>)}
                              </ul>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <button type="button" disabled={savingEntry === entry.id} onClick={() => void updateEvaluation(entry)} className="mt-2 text-xs font-medium text-primary underline disabled:opacity-50">
                  {t(entry.is_evaluation ? "Mover al historial operativo" : "Marcar como prueba interna")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && !!total && (
        <div className="flex items-center justify-between text-sm text-ink-muted">
          <span>{language === "es" ? "Mostrando" : "Showing"} {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + (shown ?? 0)} {language === "es" ? "de" : "of"} {total}</span>
          <div className="flex gap-2">
            <button className="rounded-lg border border-border px-3 py-2 disabled:opacity-40" disabled={page === 0} onClick={() => setPage(page - 1)}>{t("Anterior")}</button>
            <button className="rounded-lg border border-border px-3 py-2 disabled:opacity-40" disabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage(page + 1)}>{t("Siguiente")}</button>
          </div>
        </div>
      )}
    </section>
  );
}
