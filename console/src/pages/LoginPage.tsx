import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { useAuth } from "../hooks/useAuth";
import { DEV_TOKEN_HINT } from "../constants";

interface FormValues {
  token: string;
}

export function LoginPage() {
  const { token, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    register,
    handleSubmit,
    setError,
    formState: { isSubmitting, errors },
    setValue,
  } = useForm<FormValues>({
    defaultValues: { token: "" },
  });

  useEffect(() => {
    if (token) {
      const redirectTo =
        (location.state as { from?: { pathname?: string } } | undefined)?.from
          ?.pathname ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    }
  }, [token, navigate, location.state]);

  useEffect(() => {
    if (DEV_TOKEN_HINT) {
      setValue("token", DEV_TOKEN_HINT.replace(/^Bearer\s+/i, ""));
    }
  }, [setValue]);

  const onSubmit = handleSubmit(async (values) => {
    try {
      await login(values.token);
      toast.success("Token validado correctamente");
      navigate("/dashboard", { replace: true });
    } catch (error) {
      console.error(error);
      setError("token", {
        type: "manual",
        message: "Token inválido o expirado.",
      });
      toast.error("No pudimos validar el token. Inténtalo de nuevo.");
    }
  });

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
            Ingresa tu token de administrador para acceder al panel.
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-6">
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
