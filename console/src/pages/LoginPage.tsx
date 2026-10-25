import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useLanguage } from "../i18n/LanguageProvider";
import { API_BASE_URL } from "../constants";

export function LoginPage() {
  const { authenticated, role } = useAuth();
  const { t, language, setLanguage } = useLanguage();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (authenticated) {
      const redirectTo =
        (location.state as { from?: { pathname?: string } } | undefined)?.from
          ?.pathname ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    }
  }, [authenticated, navigate, location.state]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-25 via-white to-primary/5 px-4 py-12">
      <div className="card w-full max-w-md p-10">
        <div className="mb-5 flex justify-end"><select aria-label={t("Idioma")} value={language} onChange={(event) => setLanguage(event.target.value as "es" | "en")} className="rounded-lg border border-border bg-white px-3 py-2 text-sm text-ink"><option value="es">ES</option><option value="en">EN</option></select></div>
        <div className="mb-8 text-center">
          <div className="mx-auto mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary font-bold text-white">AS</div>
          <h1 className="text-2xl font-semibold text-ink">{t("Consola Administrativa")}</h1>
          <p className="mt-2 text-sm text-ink-muted">{t("Usa tu cuenta de Google autorizada.")}</p>
          {role && <p className="mt-2 text-xs font-semibold uppercase text-primary">{t("Sesión previa detectada")} ({role})</p>}
        </div>
        <a
          href={`${API_BASE_URL}/auth/google/start?next=console`}
          className="login-glow-button group relative isolate flex w-full items-center justify-center overflow-hidden rounded-xl py-3 text-sm font-semibold shadow-md transition-shadow duration-200 hover:shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          onMouseMove={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect();
            event.currentTarget.style.setProperty("--glow-x", `${event.clientX - bounds.left}px`);
            event.currentTarget.style.setProperty("--glow-y", `${event.clientY - bounds.top}px`);
          }}
        >
          <span aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-visible:opacity-100 motion-reduce:transition-none" style={{ background: "radial-gradient(110px circle at var(--glow-x, 50%) var(--glow-y, 50%), rgb(var(--accent-glow) / 0.28), rgb(var(--accent-glow) / 0.06) 48%, transparent 80%)" }} />
          <span className="relative z-10">{t("Continuar con Google")}</span>
        </a>
      </div>
    </div>
  );
}
