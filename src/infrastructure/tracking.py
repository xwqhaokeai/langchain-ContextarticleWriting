import uuid
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

REQUEST_ID_HEADER = "X-Request-ID"
request_id_var: ContextVar[str] = ContextVar(REQUEST_ID_HEADER, default=None)

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    中间件，用于为每个请求添加唯一的ID，以便于追踪。
    """
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request_id_var.set(request_id)
        
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

def get_request_id() -> str:
    """
    获取当前请求的ID。
    """
    return request_id_var.get()