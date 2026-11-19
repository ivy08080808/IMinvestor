"""Application errors and their JSON representation.

Every error response has the shape ``{"error": {"code": str, "message": str}}``
(see docs/API.md). Services raise :class:`AppError`; routers never build error
responses by hand.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """A business-rule violation that should be shown to the user."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class NotImplementedYet(AppError):
    """Placeholder raised by service stubs until the owning module is implemented."""

    def __init__(self, feature: str, owner: str) -> None:
        super().__init__(
            code="NOT_IMPLEMENTED",
            message=f"尚未實作：{feature}（負責：{owner}）",
            status_code=501,
        )


def install_handlers(app: FastAPI) -> None:
    """Register the JSON error handler on the FastAPI app."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
