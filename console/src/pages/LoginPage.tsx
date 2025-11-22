import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { useAuth } from "../hooks/useAuth";
import {
  DEV_TOKEN_HINT,
  ADMIN_TOKEN_UI_ENABLED,
} from "../constants";

interface FormValues {
  password: string;
  token: string;
}

export function LoginPage() {
  const { token, role, loginWithPassword, loginWithToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const allowTokenMode =
    ADMIN_TOKEN_UI_ENABLED || Boolean(DEV_TOKEN_HINT);
  const [mode, setMode] = useState<"password" | "token">(
    allowTokenMode ? "password" : "password",
  );
  const {
    register,
    handleSubmit,
    setError,
    formState: { isSubmitting, errors },
    setValue,
  } = useForm<FormValues>({
    defaultValues: { password: "", token: "" },
  });

  useEffect(() => {
    if (token) {
      const redirectTo =
        (location.state as { from?: { pathname?: string } } | undefined)?.from
          ?.pathname ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    }
  }, [token, navigate, location.state]);

  const onSubmit = handleSubmit(async (values) => {
    try {
      if (mode === "password" || !allowTokenMode) {
        await loginWithPassword(values.password);
        toast.success("Acceso concedido.");
      } else {
        if (!values.token.trim()) {
          setError("token", {
            type: "manual",
            message: "Proporciona un token válido.",
          });
          return;
        }
        await loginWithToken(values.token);
        toast.success("Token validado correctamente.");
      }
      const redirectTo =
        (location.state as { from?: { pathname?: string } } | undefined)?.from
          ?.pathname ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      console.error(error);
      if (mode === "password" || !allowTokenMode) {
        setError("password", {
          type: "manual",
          message: "Credenciales inválidas o intentos excedidos.",
        });
        toast.error("Credenciales inválidas o intentos excedidos.");
      } else {
        setError("token", {
          type: "manual",
          message: "Token inválido o expirado.",
        });
        toast.error("Token inválido o expirado.");
      }
    }
  });

  useEffect(() => {
    if (allowTokenMode && DEV_TOKEN_HINT) {
      setValue("token", DEV_TOKEN_HINT.replace(/^Bearer\s+/i, ""));
    }
  }, [allowTokenMode, setValue]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-25 via-white to-primary/5 px-4 py-12">
      <div className="card w-full max-w-md p-10">
        <div className="mb-8 text-center">
          <img
            src="/logo-scolaris.png"
            alt="Scolaris"
            className="mx-auto mb-6 h-12"
            onError={(event) => {
              (event.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
          <h1 className="text-2xl font-semibold text-ink">
            Consola Administrativa
          </h1>
          <p className="mt-2 text-sm text-ink-muted">
            {mode === "password"
              ? "Inicia sesión con tu contraseña corporativa."
              : "Pega un token de acceso válido."}
          </p>
          {role && (
            <p className="mt-2 text-xs font-semibold uppercase text-primary">
              Sesión previa detectada ({role})
            </p>
          )}
        </div>

        <form onSubmit={onSubmit} className="space-y-6">
          {allowTokenMode && (
            <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1 text-sm font-semibold text-ink-muted">
              <button
                type="button"
                className={`rounded-lg px-3 py-2 transition ${
                  mode === "password"
                    ? "bg-white text-primary shadow"
                    : "hover:text-primary"
                }`}
                onClick={() => setMode("password")}
              >
                Contraseña
              </button>
              <button
                type="button"
                className={`rounded-lg px-3 py-2 transition ${
                  mode === "token"
                    ? "bg-white text-primary shadow"
                    : "hover:text-primary"
                }`}
                onClick={() => setMode("token")}
              >
                Token manual
              </button>
            </div>
          )}

          {mode === "password" ? (
            <div className="space-y-2">
              <label htmlFor="password" className="label">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                className="input"
                placeholder="Introduce tu contraseña"
                {...register("password", {
                  required: "Este campo es obligatorio",
                })}
              />
              {errors.password && (
                <p className="text-sm text-red-500">{errors.password.message}</p>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <label htmlFor="token" className="label">
                Token de acceso
              </label>
              <input
                id="token"
                type="password"
                className="input"
                placeholder="Introduce tu ADMIN_TOKEN"
                {...register("token", { required: "Este campo es obligatorio" })}
              />
              {errors.token && (
                <p className="text-sm text-red-500">{errors.token.message}</p>
              )}
            </div>
          )}

          <button
            type="submit"
            className="gradient-button flex w-full items-center justify-center rounded-xl py-3 text-sm font-semibold uppercase tracking-wide"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                Validando...
              </span>
            ) : (
              "Ingresar"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
