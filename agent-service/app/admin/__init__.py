from fastapi import FastAPI

from .config import get_admin_settings
from .router import router
from .security import AdminAuthMiddleware


def register_admin_module(app: FastAPI) -> None:
    """Register protected administrative routes and validate upload settings."""
    get_admin_settings()
    app.add_middleware(AdminAuthMiddleware)
    app.include_router(router, prefix="/admin")


__all__ = ["register_admin_module"]
