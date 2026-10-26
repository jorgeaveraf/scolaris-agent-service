import { useEffect, useRef, useState } from "react";
import { PlusIcon } from "@heroicons/react/24/outline";
import { apiClient } from "../api/client";
import { Button } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { ExpandableIconButton } from "../components/ui/ExpandableIconAction";
import { Modal } from "../components/ui/Modal";
import { useAuth } from "../hooks/useAuth";
import { useLanguage } from "../i18n/LanguageProvider";

type Role = "chat" | "viewer" | "curator" | "admin";
type User = { display_name?: string | null; email: string; role: Role; active: boolean };

export function UsersPage() {
  const { t, language } = useLanguage();
  const { actorEmail } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [email, setEmail] = useState("");
  const emailInput = useRef<HTMLInputElement>(null);
  const [emailError, setEmailError] = useState<"required" | "invalid" | null>(null);
  const [role, setRole] = useState<Role>("chat");
  const [addOpen, setAddOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const roleOptions: { value: Role; label: string; description: string }[] = [
    { value: "chat", label: t("Solo usar el chat"), description: t("Puede conversar con el asistente, sin acceso a la consola.") },
    { value: "viewer", label: t("Usar el chat y ver la consola"), description: t("Puede consultar documentos y métricas, sin modificarlos.") },
    { value: "curator", label: t("Usar el chat y gestionar documentos"), description: t("Puede cargar, volver a procesar y eliminar documentos.") },
    { value: "admin", label: t("Administrar todo"), description: t("También puede gestionar personas, permisos e historial.") },
  ];
  const normalizedEmail = email.trim().toLowerCase();
  const existingUser = users.find((user) => user.email.toLowerCase() === normalizedEmail);
  const selfEmail = actorEmail?.toLowerCase() ?? "";
  const displayedUsers = [...users].sort(
    (left, right) => Number(right.email.toLowerCase() === selfEmail) - Number(left.email.toLowerCase() === selfEmail),
  );

  const load = async () => {
    const response = await apiClient.get<User[]>("/admin/users");
    setUsers(response.data);
  };

  useEffect(() => {
    void apiClient.get<User[]>("/admin/users").then((response) => setUsers(response.data)).catch(() => setMessage(t("No se pudo cargar la lista."))).finally(() => setLoading(false));
  }, [t]);

  const save = async (entry: User): Promise<boolean> => {
    if (actorEmail === entry.email.toLowerCase() && (entry.role !== "admin" || !entry.active)) {
      setMessage(t("No puedes cambiar ni suspender tu propio acceso de administrador."));
      return false;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiClient.put("/admin/users", entry);
      await load();
      setMessage(t("Acceso actualizado."));
      return true;
    } catch {
      setMessage(t("No se pudo actualizar el acceso."));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const closeAdd = () => {
    if (!busy) setAddOpen(false);
  };

  const remove = async () => {
    if (!deleteTarget) return;
    if (actorEmail === deleteTarget.email.toLowerCase()) {
      setMessage(t("No puedes eliminar tu propio acceso."));
      setDeleteTarget(null);
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiClient.delete(`/admin/users/${encodeURIComponent(deleteTarget.email)}`);
      setUsers((current) => current.filter((user) => user.email !== deleteTarget.email));
      setDeleteTarget(null);
      setMessage(t("Acceso eliminado."));
    } catch {
      setMessage(t("No se pudo eliminar el acceso."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-ink">{t("Personas y acceso")}</h2>
          <p className="mt-1 text-sm text-ink-muted">
            {t("Controla qué cuentas de Google pueden usar el asistente y la consola.")}
          </p>
        </div>
        <ExpandableIconButton icon={<PlusIcon className="h-5 w-5" />} label={t("Agregar persona")} tone="primary" width="medium" onClick={() => { setMessage(""); setEmailError(null); setAddOpen(true); }} />
      </div>

      <div tabIndex={0} className="group rounded-2xl border border-border bg-white px-5 py-4 text-sm text-ink-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
        <span className="text-2xl font-semibold text-ink">{loading ? "—" : users.filter((user) => user.active).length}</span>
        <span className="ml-3">{users.filter((user) => user.active).length === 1 ? t("persona con acceso habilitado") : t("personas con acceso habilitado")}</span>
        <p className="max-h-0 overflow-hidden text-xs leading-5 opacity-0 transition-[max-height,opacity,margin] duration-200 delay-0 group-hover:mt-2 group-hover:max-h-20 group-hover:opacity-100 group-hover:delay-500 group-focus-visible:mt-2 group-focus-visible:max-h-20 group-focus-visible:opacity-100 group-focus-visible:delay-500 motion-reduce:transition-none">{t("Solo chat permite conversar. Lectura permite revisar la consola. Documentos permite gestionar fuentes. Administrador también gestiona personas e historial.")}</p>
      </div>

      <Modal open={addOpen} onClose={closeAdd} title={t("Agregar persona")} description={t("Autoriza una cuenta de Google. No se envía un correo de invitación.")} size="lg">
        <form noValidate className="space-y-6" onSubmit={(event) => {
          event.preventDefault();
          if (!normalizedEmail) {
            setEmailError("required");
            emailInput.current?.focus();
            return;
          }
          if (!emailInput.current?.checkValidity()) {
            setEmailError("invalid");
            emailInput.current?.focus();
            return;
          }
          setEmailError(null);
          void save({ email: normalizedEmail, role, active: true }).then((saved) => {
            if (saved) {
              setAddOpen(false);
              setEmail("");
              setRole("chat");
            }
          });
        }}>
          <label className="block space-y-2 text-sm font-semibold text-ink">
            <span>{t("Correo electrónico")}</span>
            <input ref={emailInput} className="input" type="email" autoComplete="email" required aria-invalid={Boolean(emailError)} aria-describedby={emailError ? "add-person-email-error" : undefined} value={email} onChange={(event) => { setEmail(event.target.value); setEmailError(null); }} placeholder="name@example.com" />
          </label>
          {emailError && <p id="add-person-email-error" role="alert" className="-mt-4 text-sm font-medium text-red-600">{t(emailError === "required" ? "Escribe un correo electrónico." : "Escribe un correo electrónico válido.")}</p>}
          {existingUser && <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{t("Esta cuenta ya existe. Al guardar, actualizarás su permiso y reactivarás su acceso.")}</p>}
          {message && <p role="status" className="rounded-xl border border-border bg-slate-25 px-4 py-3 text-sm text-ink-muted">{message}</p>}
          <fieldset>
            <legend className="mb-3 text-sm font-semibold text-ink">{t("Permiso")}</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {roleOptions.map((option) => <label key={option.value} className="cursor-pointer">
                <input type="radio" name="new-person-role" value={option.value} checked={role === option.value} onChange={() => setRole(option.value)} className="peer sr-only" />
                <span className="block min-h-28 rounded-xl border border-border bg-white p-4 transition-colors hover:border-primary/50 peer-checked:border-primary peer-checked:bg-primary/5 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary">
                  <span className="block text-sm font-semibold text-ink">{option.label}</span>
                  <span className="mt-2 block text-xs leading-5 text-ink-muted">{option.description}</span>
                </span>
              </label>)}
            </div>
          </fieldset>
          <div className="flex justify-end gap-3 border-t border-border pt-5">
            <Button type="button" variant="secondary" onClick={closeAdd} disabled={busy}>{t("Cancelar")}</Button>
            <Button type="submit" loading={busy}>{t(existingUser ? "Actualizar acceso" : "Conceder acceso")}</Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={t("Eliminar acceso")}
        description={deleteTarget ? `${t("Se eliminará el acceso de")} ${deleteTarget.email}. ${t("Su sesión dejará de funcionar; el historial del chat se conserva.")}` : ""}
        confirmText={t("Eliminar acceso")}
        confirmVariant="danger"
        loading={busy}
        onClose={() => { if (!busy) setDeleteTarget(null); }}
        onConfirm={remove}
      />

      {message && <p className="text-sm text-ink-muted" role="status">{message}</p>}
      <div className="card overflow-hidden">
        <div className="border-b border-border px-5 py-4 text-sm font-semibold text-ink">{t("Accesos registrados")}</div>
        <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] table-fixed text-left text-sm">
          <colgroup>
            <col className="w-[21%]" /><col className="w-[27%]" /><col className="w-[25%]" /><col className="w-[10%]" /><col className="w-[17%]" />
          </colgroup>
          <thead className="bg-slate-50 text-ink-muted"><tr>
            <th className="px-5 py-3">{t("Nombre")}</th><th className="px-5 py-3">{t("Correo")}</th><th className="px-5 py-3">{t("Permiso")}</th><th className="px-5 py-3">{t("Estado")}</th><th className="px-5 py-3 text-center">{t("Acción")}</th>
          </tr></thead>
          <tbody>{displayedUsers.map((user) => {
            const isSelf = selfEmail === user.email.toLowerCase();
            return <tr key={user.email} className="border-t border-border">
            <td className="px-5 py-3 font-medium text-ink"><span className="flex min-w-0 items-center gap-1.5"><span className="min-w-0 truncate" title={user.display_name || t("Pendiente de sincronizar con Google")}>{user.display_name || <span className="font-normal text-ink-muted">{t("Pendiente de sincronizar con Google")}</span>}</span>{isSelf && <span className="shrink-0 text-xs font-medium text-ink-muted">({t("Tú")})</span>}</span></td>
            <td className="px-5 py-3 text-ink-muted"><span className="block truncate" title={user.email}>{user.email}</span></td>
            <td className="px-5 py-3">{isSelf ? <span
              className="flex min-h-[30px] w-full min-w-0 items-center rounded-lg border border-transparent bg-white py-1 pl-[11px] pr-2 text-ink"
              title={t("No puedes cambiar tu propio permiso.")}
            >{roleOptions.find((option) => option.value === user.role)?.label}</span> : <select
              aria-label={`${t("Permiso")} ${language === "es" ? "de" : "for"} ${user.email}`}
              className="w-full min-w-0 rounded-lg border border-border bg-white px-2 py-1"
              value={user.role}
              disabled={busy}
              onChange={(event) => void save({ ...user, role: event.target.value as Role })}
            >
              {roleOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>}</td>
            <td className="px-5 py-3">{t(user.active ? "Activo" : "Suspendido")}</td>
            <td className="px-5 py-3 text-center">{isSelf ? <span className="text-ink-muted" aria-label={t("No puedes eliminar ni suspender tu propia cuenta.")}>—</span> : <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
              <button type="button" className="font-semibold text-primary disabled:opacity-50" disabled={busy} onClick={() => void save({ ...user, active: !user.active })}>{t(user.active ? "Suspender" : "Reactivar")}</button>
              <button type="button" className="font-semibold text-red-600 hover:text-red-700 disabled:opacity-50" disabled={busy} onClick={() => setDeleteTarget(user)}>{t("Eliminar")}</button>
            </div>}</td>
          </tr>})}</tbody>
        </table>
        </div>
      </div>
    </section>
  );
}
