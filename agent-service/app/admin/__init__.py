from fastapi import FastAPI

from .config import get_admin_settings
from .router import router
from .security import AdminAuthMiddleware


def register_admin_module(app: FastAPI) -> None:
    """
    Registers admin middleware and routes on the FastAPI app.
    Raises RuntimeError if the module is misconfigured (e.g., missing ADMIN_TOKEN).
    """
    settings = get_admin_settings()
    app.add_middleware(AdminAuthMiddleware, settings=settings)
    app.include_router(router, prefix="/admin")


__all__ = ["register_admin_module"]
