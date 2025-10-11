from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from ..infrastructure.exceptions import BaseError
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)

class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except BaseError as e:
            logger.error(
                "Custom error occurred",
                error_code=e.error_code,
                message=e.message,
                details=e.details,
                trace_id=e.trace_id,
            )
            return JSONResponse(
                status_code=400,  # Or a more specific status code
                content=e.to_dict(),
            )
        except Exception as e:
            logger.exception(f"An unhandled exception occurred: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
            )