# Consola de Agent Service

La consola muestra el estado operativo a primera vista: documentos disponibles, uso reciente del chat y personas habilitadas. **Observabilidad** reúne latencias, errores y consumo técnico. Los fragmentos usados por RAG están dentro del detalle de cada documento.

## Arranque

Desde la raíz del repositorio:

```bash
cp console/.env.example console/.env
npm install --prefix console
npm run dev --prefix console
```

Configura `VITE_API_BASE` con la URL de la API. Para el inicio de sesión, la API debe tener Google OIDC configurado como explica el [README principal](../README.md#configurar-google-oidc-en-un-proyecto-nuevo). El navegador usa una cookie de sesión del servidor; la consola no solicita contraseñas propias ni guarda tokens de acceso en `localStorage`.

## Permisos y datos

- Google comprueba la identidad. La lista de correos autorizados en PostgreSQL determina si alguien puede usar el chat, ver la consola, gestionar documentos o administrar personas e historial.
- **Personas** permite dar acceso, cambiar permisos, suspender y eliminar cuentas; la propia cuenta administradora no puede retirarse su acceso.
- **Historial del chat** agrupa intercambios por persona y admite una búsqueda sobre persona, fuente, pregunta y respuesta. Solo el administrador puede verlo.
- **Documentos** permite cargar, revisar estado y ver el original. La vista de fragmentos es una herramienta técnica dentro del detalle.
- La vista general usa datos persistentes y señala el periodo de uso; Observabilidad usa muestras recientes que se reinician al reiniciar el servidor.

## Compilar

```bash
npm run build --prefix console
```

`VITE_ORGANIZATION_NAME` permite mostrar una organización en la consola sin acoplar la base. `VITE_ACCENT_COOKIE_DOMAIN` es opcional cuando el chat comparte un dominio de cookie. No pongas secretos en variables `VITE_*`: Vite las incluye en el navegador.
