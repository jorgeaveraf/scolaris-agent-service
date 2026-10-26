import { Dialog, Menu, Transition } from "@headlessui/react";
import { Bars3Icon, ChartBarSquareIcon, ChevronDownIcon, ClipboardDocumentListIcon, DocumentDuplicateIcon, HomeIcon, LanguageIcon, PaintBrushIcon, PowerIcon, SwatchIcon, XMarkIcon, UsersIcon } from "@heroicons/react/24/outline";
import { Fragment, useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useLanguage } from "../i18n/LanguageProvider";
import { accents, useAccent } from "../theme/AccentProvider";
import { API_BASE_URL } from "../constants";
import { AgentChatBubble } from "../../../chat-widget/src/lib/AgentChatBubble";
import "../../../chat-widget/src/lib/styles.css";

const navigation = [
  { name: "Vista general", to: "/dashboard", icon: HomeIcon },
  { name: "Documentos", to: "/documents", icon: DocumentDuplicateIcon },
];
const organizationName = import.meta.env.VITE_ORGANIZATION_NAME?.trim();

export function DashboardLayout() {
  const { logout, role, actorEmail, actorName } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const { accent, setAccent, customHex, setCustomHex } = useAccent();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [customOpen, setCustomOpen] = useState(false);
  const [hexDraft, setHexDraft] = useState(customHex);
  const desktopSidebar = useRef<HTMLDivElement>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const expanded = hovered || pinned;
  const roleLabel = t(role === "admin" ? "Administrador" : role === "viewer" ? "Lector" : role === "curator" ? "Curador" : "Rol");
  const identityLabel = actorName || actorEmail || roleLabel;
  const identityCharacters = Array.from(identityLabel);
  const compactIdentityLabel = identityCharacters.length > 32
    ? `${identityCharacters.slice(0, 32).join("").trimEnd()}…`
    : identityLabel;
  const initials = actorName
    ? actorName.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase()
    : (actorEmail?.slice(0, 2) || "AS").toUpperCase();

  const cancelHoverTimer = () => {
    if (hoverTimer.current !== null) {
      window.clearTimeout(hoverTimer.current);
      hoverTimer.current = null;
    }
  };
  const handleSidebarEnter = () => {
    if (pinned || hovered || hoverTimer.current !== null) return;
    hoverTimer.current = window.setTimeout(() => {
      setHovered(true);
      hoverTimer.current = null;
    }, 300);
  };
  const handleSidebarLeave = () => {
    cancelHoverTimer();
    setHovered(false);
  };
  const handleSidebarClick = () => {
    cancelHoverTimer();
    setPinned(true);
  };

  useEffect(() => {
    const onOutside = (event: MouseEvent) => {
      if (desktopSidebar.current && !desktopSidebar.current.contains(event.target as Node)) setPinned(false);
    };
    document.addEventListener("click", onOutside);
    return () => document.removeEventListener("click", onOutside);
  }, []);
  useEffect(() => () => {
    if (hoverTimer.current !== null) window.clearTimeout(hoverTimer.current);
  }, []);
  useEffect(() => { setHexDraft(customHex); }, [customHex]);

  const navItems = [...navigation];
  if (role === "admin") {
    navItems.push({ name: "Personas", to: "/users", icon: UsersIcon });
    navItems.push({ name: "Historial del chat", to: "/chat-history", icon: ClipboardDocumentListIcon });
  }
  navItems.push({ name: "Observabilidad", to: "/observability", icon: ChartBarSquareIcon });

  const sidebar = (open: boolean) => (
    <div className="flex h-full flex-col overflow-hidden bg-white">
      <div className={`flex h-20 items-center gap-3 ${open ? "px-6" : "justify-center px-2"}`}>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-xs font-bold text-white">AS</div>
        {open && <p className="min-w-0 truncate text-sm font-semibold uppercase tracking-wide text-primary">Agent Service</p>}
      </div>
      <nav aria-label={t("Consola administrativa")} className={`flex flex-1 flex-col gap-1 text-sm font-medium ${open ? "px-4" : "px-2"}`}>
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} title={!open ? t(item.name) : undefined} aria-label={t(item.name)} onClick={() => setMobileOpen(false)}
            className={({ isActive }) => ["flex h-11 items-center rounded-xl transition-colors", open ? "gap-3 px-4" : "justify-center px-2", isActive || location.pathname.startsWith(item.to) ? "bg-primary !text-white shadow-sm hover:!text-white" : "text-ink-muted hover:bg-primary/10 hover:text-primary"].join(" ")}
          ><item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />{open && <span className="whitespace-nowrap">{t(item.name)}</span>}</NavLink>
        ))}
      </nav>
      <div className={`space-y-2 border-t border-border py-3 ${open ? "px-4" : "px-2"}`}>
        <div className={`flex min-h-11 items-center rounded-xl text-ink-muted ${open ? "gap-3 px-4" : "justify-center px-2"}`} title={!open ? t("Color de acento") : undefined}>
          <SwatchIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
          {open && <div aria-label={t("Color de acento")} className="flex items-center gap-2">
            {accents.map((option) => <button key={option.id} type="button" aria-label={t(option.label)} aria-pressed={accent === option.id} title={t(option.label)} onClick={() => { setAccent(option.id); setCustomOpen(false); }} className={`h-6 w-6 rounded-full border-2 border-white shadow-sm ring-offset-2 transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${accent === option.id ? "ring-2 ring-primary" : "ring-1 ring-slate-300"}`} style={{ backgroundColor: option.swatch }} />)}
            <button type="button" aria-label={t("Color personalizado")} aria-expanded={customOpen} title={t("Color personalizado")} onClick={() => setCustomOpen((current) => !current)} className={`flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-slate-100 text-slate-600 shadow-sm ring-offset-2 transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${accent === "custom" ? "ring-2 ring-primary" : "ring-1 ring-slate-300"}`}><PaintBrushIcon className="h-4 w-4" aria-hidden="true" /></button>
          </div>}
        </div>
        {open && customOpen && <div className="mx-1 rounded-xl border border-border bg-slate-25 p-3">
          <label htmlFor="accent-hex" className="mb-2 block text-xs font-semibold text-ink">{t("Color personalizado")}</label>
          <div className="flex items-center gap-2">
            <input type="color" aria-label={t("Abrir paleta de colores")} value={customHex} onChange={(event) => setCustomHex(event.target.value)} className="h-9 w-10 shrink-0 cursor-pointer rounded-lg border border-border bg-white p-1" />
            <input id="accent-hex" type="text" aria-label={t("Código HEX")} value={hexDraft} onChange={(event) => { const next = event.target.value; setHexDraft(next); if (/^#[0-9a-fA-F]{6}$/.test(next)) setCustomHex(next); }} onBlur={() => setHexDraft(customHex)} maxLength={7} spellCheck={false} className="min-w-0 flex-1 rounded-lg border border-border bg-white px-2 py-1.5 text-xs font-medium uppercase tracking-wide text-ink focus:border-primary focus:outline-none" />
          </div>
        </div>}
        <div className={`flex min-h-11 items-center rounded-xl text-ink-muted ${open ? "gap-3 px-4" : "justify-center px-2"}`}>
          <LanguageIcon className="h-5 w-5 shrink-0" aria-hidden="true" />
          {open ? <><label className="sr-only" htmlFor="console-language">{t("Idioma")}</label><select id="console-language" aria-label={t("Idioma")} value={language} onChange={(event) => setLanguage(event.target.value as "es" | "en")} className="min-w-0 flex-1 rounded-lg border border-border bg-white px-2 py-1 text-sm text-ink"><option value="es">ES</option><option value="en">EN</option></select></> : <span className="sr-only">{t("Idioma")}</span>}
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-slate-25">
      <Transition.Root show={mobileOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50 lg:hidden" onClose={setMobileOpen}>
          <Transition.Child as={Fragment} enter="transition-opacity duration-200" enterFrom="opacity-0" enterTo="opacity-100" leave="transition-opacity duration-200" leaveFrom="opacity-100" leaveTo="opacity-0"><div className="fixed inset-0 bg-slate-900/25" /></Transition.Child>
          <div className="fixed inset-0 flex"><Transition.Child as={Fragment} enter="transition duration-300 transform" enterFrom="-translate-x-full" enterTo="translate-x-0" leave="transition duration-300 transform" leaveFrom="translate-x-0" leaveTo="-translate-x-full"><Dialog.Panel className="relative mr-16 h-full w-full max-w-xs flex-1">{sidebar(true)}<button className="absolute left-full top-5 ml-3 rounded-lg p-2 text-white" onClick={() => setMobileOpen(false)} aria-label={t("Cerrar menú")}><XMarkIcon className="h-6 w-6" /></button></Dialog.Panel></Transition.Child></div>
        </Dialog>
      </Transition.Root>

      <div className={`hidden shrink-0 transition-[width] duration-200 ease-out lg:block ${expanded ? "w-72" : "w-20"}`}><div ref={desktopSidebar} onPointerEnter={handleSidebarEnter} onPointerLeave={handleSidebarLeave} onClick={handleSidebarClick} className="sticky top-0 z-40 h-screen w-full border-r border-border bg-white shadow-sm">{sidebar(expanded)}</div></div>
      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-border bg-white px-4 py-4 shadow-sm md:px-8">
          <div className="flex shrink-0 items-center gap-4">
            <button type="button" className="rounded-xl border border-border bg-white p-2 text-ink lg:hidden" onClick={() => setMobileOpen(true)} aria-label={t("Abrir menú")}><Bars3Icon className="h-6 w-6" aria-hidden="true" /></button>
            <div><h1 className="text-lg font-semibold text-ink">{t("Consola administrativa")}</h1>{organizationName && <p className="text-xs text-ink-muted">{organizationName}</p>}</div>
          </div>
          <Menu as="div" className="relative min-w-0">
            <Menu.Button className="flex max-w-64 items-center gap-2 rounded-xl px-2 py-1.5 text-left transition hover:bg-primary/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary lg:max-w-80" aria-label={`${t("Cuenta")}: ${identityLabel}`} title={actorEmail || undefined}>
              <div className="hidden min-w-0 text-right md:block"><p className="truncate text-sm font-semibold text-ink" title={identityLabel}>{compactIdentityLabel}</p><p className="text-xs text-ink-muted">{roleLabel}</p></div>
              <span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{initials}</span>
              <ChevronDownIcon className="hidden h-4 w-4 shrink-0 text-ink-muted md:block" aria-hidden="true" />
            </Menu.Button>
            <Menu.Items className="absolute right-0 z-50 mt-2 w-64 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-white p-2 shadow-xl focus:outline-none">
              <div className="border-b border-border px-3 py-2"><p className="truncate text-sm font-semibold text-ink">{identityLabel}</p>{actorEmail && <p className="truncate text-xs text-ink-muted">{actorEmail}</p>}</div>
              <Menu.Item>
                {({ active }) => <button type="button" onClick={() => setLogoutConfirmOpen(true)} className={`mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-semibold text-ink ${active ? "bg-primary/10" : ""}`}><PowerIcon className="h-5 w-5" aria-hidden="true" />{t("Cerrar sesión")}</button>}
              </Menu.Item>
            </Menu.Items>
          </Menu>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8"><Outlet /></main>
      </div>
      <AgentChatBubble baseUrl={API_BASE_URL} language={language} showConsoleLink={false} launcherInset={location.pathname.startsWith("/documents/")} />
      <Dialog open={logoutConfirmOpen} onClose={setLogoutConfirmOpen} className="relative z-[100]">
        <div className="fixed inset-0 bg-slate-900/40" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-sm rounded-2xl border border-border bg-white p-6 shadow-2xl">
            <Dialog.Title className="text-lg font-semibold text-ink">{language === "es" ? "¿Cerrar sesión?" : "Sign out?"}</Dialog.Title>
            <Dialog.Description className="mt-2 text-sm text-ink-muted">{language === "es" ? "Tendrás que iniciar sesión de nuevo para usar la consola y el chat." : "You’ll need to sign in again to use the console and chat."}</Dialog.Description>
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setLogoutConfirmOpen(false)} className="rounded-full border border-border px-4 py-2 text-sm font-semibold text-ink hover:bg-slate-25">{language === "es" ? "Cancelar" : "Cancel"}</button>
              <button type="button" onClick={() => { setLogoutConfirmOpen(false); logout(); }} className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark">{t("Cerrar sesión")}</button>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  );
}
