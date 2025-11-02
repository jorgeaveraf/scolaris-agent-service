import { Dialog, Transition } from "@headlessui/react";
import {
  Bars3Icon,
  ClipboardDocumentListIcon,
  DocumentDuplicateIcon,
  HomeIcon,
  PowerIcon,
  ServerStackIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { Fragment, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const navigation = [
  { name: "Dashboard", to: "/dashboard", icon: HomeIcon },
  { name: "Documentos", to: "/documents", icon: DocumentDuplicateIcon },
  { name: "Chunks", to: "/chunks", icon: ServerStackIcon },
  { name: "Logs", to: "/logs", icon: ClipboardDocumentListIcon },
];

export function DashboardLayout() {
  const { logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navItems = navigation.map((item) => ({
    ...item,
    current: location.pathname.startsWith(item.to),
  }));

  const sidebar = (
    <div className="flex h-full flex-col bg-white">
      <div className="flex items-center gap-3 px-6 py-6">
        <img
          src="/logo-scolaris.png"
          alt="Scolaris"
          className="h-9 w-auto"
          onError={(event) => {
            (event.currentTarget as HTMLImageElement).style.display = "none";
          }}
        />
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-primary">
            Scolaris Agent
          </p>
          <p className="text-xs text-ink-muted">Consola administrativa</p>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-4 text-sm font-medium">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              [
                "flex items-center gap-3 rounded-xl px-4 py-2.5 transition-colors",
                isActive || item.current
                  ? "bg-primary text-white shadow-sm"
                  : "text-ink-muted hover:bg-primary/10 hover:text-primary",
              ].join(" ")
            }
          >
            <item.icon className="h-5 w-5" aria-hidden="true" />
            {item.name}
          </NavLink>
        ))}
      </nav>
      <button
        type="button"
        onClick={logout}
        className="m-4 flex items-center gap-3 rounded-xl border border-transparent px-4 py-2 text-sm font-semibold text-ink-muted transition hover:border-red-100 hover:bg-red-50 hover:text-red-500"
      >
        <PowerIcon className="h-5 w-5" />
        Cerrar sesión
      </button>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-slate-25">
      <Transition.Root show={sidebarOpen} as={Fragment}>
        <Dialog
          as="div"
          className="relative z-50 lg:hidden"
          onClose={setSidebarOpen}
        >
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-200"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-slate-900/25" />
          </Transition.Child>

          <div className="fixed inset-0 flex">
            <Transition.Child
              as={Fragment}
              enter="transition ease-in-out duration-300 transform"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="transition ease-in-out duration-300 transform"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
                <Transition.Child
                  as={Fragment}
                  enter="ease-in-out duration-300"
                  enterFrom="opacity-0"
                  enterTo="opacity-100"
                  leave="ease-in-out duration-300"
                  leaveFrom="opacity-100"
                  leaveTo="opacity-0"
                >
                  <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                    <button
                      type="button"
                      className="-m-2.5 p-2.5 text-ink"
                      onClick={() => setSidebarOpen(false)}
                    >
                      <span className="sr-only">Cerrar menú</span>
                      <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                    </button>
                  </div>
                </Transition.Child>
                {sidebar}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition.Root>

      <div className="hidden w-72 bg-white lg:flex lg:flex-col lg:border-r lg:border-border">
        {sidebar}
      </div>

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-border bg-white px-4 py-4 shadow-sm md:px-8">
          <div className="flex items-center gap-4">
            <button
              type="button"
              className="rounded-xl border border-border bg-white p-2 text-ink lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
              <span className="sr-only">Abrir menú</span>
            </button>
            <div>
              <h1 className="text-xl font-semibold text-ink">
                Consola Administrativa Scolaris Agent
              </h1>
              <p className="text-sm text-ink-muted">
                Gestiona documentos, monitorea la ingesta y analiza el contexto.
              </p>
            </div>
          </div>
          <div className="hidden shrink-0 flex-col items-end text-xs md:flex">
            <span className="font-semibold uppercase tracking-wide text-primary">
              Administrador
            </span>
            <span className="text-ink-muted">Scolaris Labs</span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
